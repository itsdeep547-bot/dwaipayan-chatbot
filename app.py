# app.py
import streamlit as st
import requests
import math
import ast
from pint import UnitRegistry

# Theme settings for LinkedIn-style blue
st.set_page_config(page_title="Dwaipayan's AI Assistant",
                   page_icon="🤖",
                   layout="centered",
                   initial_sidebar_state="expanded")

# Custom CSS for theme
st.markdown("""
    <style>
    .stApp { background-color: #f7f9fb; }
    footer {visibility: hidden;}
    .reportview-container .main footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

ALLOWED_NAMES = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
ALLOWED_NAMES.update({"pi": math.pi, "e": math.e})

class SafeEval(ast.NodeVisitor):
    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.Call, ast.Name, ast.Constant
    )
    def visit(self, node):
        if not isinstance(node, self.allowed_nodes):
            raise ValueError(f"Unsupported expression: {type(node).__name__}")
        return super().visit(node)
    def eval(self, expr: str):
        tree = ast.parse(expr, mode='eval')
        self.visit(tree)
        return eval(compile(tree, "<ast>", "eval"), {"__builtins__": {}}, ALLOWED_NAMES)

ureg = UnitRegistry()
Q_ = ureg.Quantity

def try_convert_units(text: str):
    import re
    pat = re.compile(r"(?i)(?:convert\s+)?([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z°/]+)\s*(?:to|in)\s*([a-zA-Z°/]+)")
    m = pat.search(text)
    if not m:
        return None
    value, from_unit, to_unit = m.groups()
    try:
        qty = Q_(float(value), from_unit)
        conv = qty.to(to_unit)
        return f"{qty} = {conv}"
    except Exception as e:
        return f"Sorry, I couldn't convert those units ({e})."

def wikipedia_summary(query: str):
    import urllib.parse
    title = urllib.parse.quote(query.strip())
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return None
    data = r.json()
    if 'extract' in data:
        return data['title'], data.get('extract')
    return None

def geocode_city(city: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(url, params={"name": city, "count": 1}, timeout=10)
    if r.status_code != 200:
        return None
    data = r.json()
    if not data.get("results"):
        return None
    top = data["results"][0]
    return {"name": top["name"], "lat": top["latitude"], "lon": top["longitude"], "country": top.get("country")}

def weather_now(city: str):
    g = geocode_city(city)
    if not g:
        return None
    wurl = "https://api.open-meteo.com/v1/forecast"
    r = requests.get(wurl, params={"latitude": g["lat"], "longitude": g["lon"], "current_weather": True}, timeout=10)
    if r.status_code != 200:
        return None
    cw = r.json().get("current_weather", {})
    if not cw:
        return None
    return g, cw

def route_message(text: str):
    text_strip = text.strip()
    conv = try_convert_units(text_strip)
    if conv:
        return ("unit", conv)
    if any(op in text_strip for op in ["+", "-", "*", "/", "%", "^"]):
        expr = text_strip.replace("^", "**")
        try:
            val = SafeEval().eval(expr)
            return ("calc", f"{expr} = {val}")
        except Exception:
            pass
    if text_strip.lower().startswith(("weather", "forecast")) or "weather in" in text_strip.lower():
        import re
        m = re.search(r"(?i)weather(?: in)? ([a-zA-Z\s,]+)", text_strip)
        city = m.group(1).strip() if m else text_strip.split()[-1]
        w = weather_now(city)
        if w:
            g, cw = w
            return ("weather", f"Weather in {g['name']}, {g.get('country','')}: {cw.get('temperature')}°C, wind {cw.get('windspeed')} km/h (as of {cw.get('time')}).")
        else:
            return ("weather", "I couldn't find the weather for that location.")
    if text_strip.lower().startswith(("who is", "what is", "tell me about", "wiki", "wikipedia")):
        q = text_strip.split(" ", 1)[1] if " " in text_strip else text_strip
        res = wikipedia_summary(q)
        if res:
            title, summary = res
            return ("wiki", f"**{title}** — {summary}")
        else:
            return ("wiki", "I couldn't find a Wikipedia summary for that.")
    return ("chat", "I can help with: math (e.g., 2*(3+4)^2), unit conversion (e.g., 10 km to mi), weather (e.g., weather in Delhi), and Wikipedia summaries (e.g., who is Ada Lovelace).")

st.title("🤖 Dwaipayan's AI Assistant")
st.caption("AI-powered assistant with math, weather, and Wikipedia skills.")

with st.sidebar:
    st.markdown("### Capabilities")
    st.write("- Calculator (safe eval)\n- Unit conversion (Pint)\n- Wikipedia summaries\n- Weather (Open-Meteo)")
    st.markdown("---")
    st.markdown("**Try:** `convert 10 km to miles`, `2*(3+4)^2`, `weather in Delhi`, `who is Nikola Tesla`.")

if "chat" not in st.session_state:
    st.session_state.chat = []

for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Type your message...")
if prompt:
    st.session_state.chat.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    kind, reply = route_message(prompt)
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.session_state.chat.append({"role": "assistant", "content": reply})

# Footer branding
st.markdown("---")
st.markdown("<p style='text-align:center; font-size:14px; color:gray;'>Made by <b>Dwaipayan Boral</b> — AI-powered assistant with math, weather, and Wikipedia skills.</p>", unsafe_allow_html=True)
