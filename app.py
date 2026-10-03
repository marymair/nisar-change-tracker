"""
NISAR Surface Change Tracker — v6.0
- Auto-load regions when type is selected
- Clickable scene list → different map markers
- Address + type + intensity in selected info
- Button Analyze glows on hover/click
- Deep blue floods, light cyan glaciers
- Custom colors per change type
"""
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import pandas as pd
import requests
import time
from PIL import Image
from io import BytesIO
from translations import TEXTS

BACKEND_URL = "https://nisar-backend-production-feb6.up.railway.app"

st.set_page_config(page_title="NISAR Surface Change Tracker", page_icon="🛰️",
                   layout="wide", initial_sidebar_state="collapsed")

# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    "lang": "en", "change_type": None,
    "selected_lat": -75.0, "selected_lon": 0.0, "selected_address": "",
    "scene_lat": None, "scene_lon": None, "scene_name": None,
    "show_help": False, "job_id": None, "theme": "dark",
    "availability_checked": False, "availability_count": None, "availability_scenes": [],
    "onboarded": False,
    "regions_checked": False, "regions_results": [],
    "auto_check_done_for": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# CALLBACKS
# ============================================================
def toggle_theme():
    st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"

def toggle_help():
    st.session_state["show_help"] = not st.session_state["show_help"]

def go_to_app(): st.session_state["onboarded"] = True
def go_to_landing(): st.session_state["onboarded"] = False

def set_change_type(key):
    if st.session_state["change_type"] != key:
        st.session_state["change_type"] = key
        st.session_state["availability_checked"] = False
        st.session_state["availability_count"] = None
        st.session_state["availability_scenes"] = []
        st.session_state["regions_checked"] = False
        st.session_state["regions_results"] = []
        st.session_state["scene_lat"] = None
        st.session_state["scene_lon"] = None
        st.session_state["scene_name"] = None
        st.session_state["job_id"] = None

def select_scene(name, lat, lon):
    st.session_state["scene_name"] = name
    st.session_state["scene_lat"] = lat
    st.session_state["scene_lon"] = lon

# ============================================================
# LANGUAGE
# ============================================================
lang_options = {"English": "en", "Русский": "ru", "Español": "es", "Français": "fr"}
lang_name = st.selectbox("🌐 Language", list(lang_options.keys()),
    index=list(lang_options.values()).index(st.session_state["lang"]),
    key="lang_selector", label_visibility="collapsed")
T = TEXTS[st.session_state["lang"]]

# ============================================================
# CHANGE TYPES — deep blue floods, light cyan glaciers
# ============================================================
CHANGE_TYPES = {
    "fire":       {"icon": "🔥", "label": T["change_fire"],       "color": "#D8351A", "map_color": "#FC3D21", "glow": "rgba(252,61,33,0.5)",  "grad": "#FC3D21,#D8351A", "dark_bg": "#1a0605", "light_bg": "#fff2ef"},
    "glacier":    {"icon": "❄️", "label": T["change_glacier"],    "color": "#3a7bd5", "map_color": "#7FE5FF", "glow": "rgba(127,229,255,0.5)","grad": "#7FE5FF,#3a7bd5", "dark_bg": "#061226", "light_bg": "#eef5ff"},
    "flood":      {"icon": "🌊", "label": T["change_flood"],      "color": "#0033A0", "map_color": "#0033A0", "glow": "rgba(0,51,160,0.5)",   "grad": "#0033A0,#001a4d", "dark_bg": "#030825", "light_bg": "#eaf0ff"},
    "desert":     {"icon": "🏜️", "label": T["change_desert"],     "color": "#c98a00", "map_color": "#e6b800", "glow": "rgba(230,184,0,0.5)",  "grad": "#e6b800,#c98a00", "dark_bg": "#1a1506", "light_bg": "#fdf6e3"},
    "earthquake": {"icon": "🌍", "label": T["change_earthquake"], "color": "#8e44ad", "map_color": "#b06cd9", "glow": "rgba(176,108,217,0.5)","grad": "#b06cd9,#8e44ad", "dark_bg": "#160a22", "light_bg": "#f5eefc"},
    "wetland":    {"icon": "🌿", "label": T["change_wetland"],    "color": "#1e8449", "map_color": "#3ed87a", "glow": "rgba(62,216,122,0.5)", "grad": "#3ed87a,#1e8449", "dark_bg": "#061a10", "light_bg": "#eafaf1"},
}

HOTSPOTS_BY_TYPE = {
    "fire": [("California, USA", 38.0, -120.0, 0.95, "Aug 2026"), ("Amazon, Brazil", -3.0, -60.0, 0.85, "Sep 2026"), ("Victoria, Australia", -37.0, 145.0, 0.80, "Jan 2026"), ("Siberia, Russia", 62.0, 105.0, 0.75, "Jul 2026")],
    "glacier": [("Antarctica", -75.0, 0.0, 0.95, "Sep 2026"), ("Greenland", 72.0, -40.0, 0.90, "Aug 2026"), ("Himalayas, Nepal", 28.0, 85.0, 0.85, "Sep 2026"), ("Alps, Switzerland", 46.5, 8.0, 0.70, "Jun 2026")],
    "flood": [("Bangladesh", 24.0, 90.0, 0.95, "Jul 2026"), ("Amazon, Brazil", -3.0, -60.0, 0.80, "Mar 2026"), ("Mekong Delta, Vietnam", 10.0, 105.0, 0.85, "Oct 2026"), ("Mississippi, USA", 32.0, -91.0, 0.75, "May 2026")],
    "desert": [("Sahara, Algeria", 27.0, 5.0, 0.90, "2026"), ("Sahel, Niger", 15.0, 8.0, 0.85, "2026"), ("Gobi, Mongolia", 43.0, 105.0, 0.80, "2026"), ("Aral Sea, Uzbekistan", 45.0, 58.0, 0.95, "2026")],
    "earthquake": [("Turkey-Syria", 37.0, 38.0, 0.95, "Feb 2026"), ("Japan", 35.0, 140.0, 0.90, "Jan 2026"), ("California, USA", 35.0, -119.0, 0.85, "Apr 2026"), ("Chile", -30.0, -71.0, 0.80, "Sep 2026")],
    "wetland": [("Okavango, Botswana", -19.0, 23.0, 0.90, "2026"), ("Pantanal, Brazil", -17.0, -57.0, 0.95, "2026"), ("Sundarbans, Bangladesh", 22.0, 89.0, 0.85, "2026"), ("Everglades, USA", 25.5, -80.5, 0.80, "2026")],
}

active = CHANGE_TYPES.get(st.session_state["change_type"]) if st.session_state["change_type"] else None
accent = active["color"] if active else "#3a7bd5"
accent_map = active["map_color"] if active else "#5bc8ff"
glow = active["glow"] if active else "rgba(74,158,255,0.5)"
grad = active["grad"] if active else "#3a7bd5,#FC3D21"

if st.session_state["theme"] == "dark":
    bg_top = active["dark_bg"] if active else "#0a0e1a"; bg_bottom = "#0a0e1a"
    text_main = "#e8ecf5"; text_muted = "#8892a6"
    card_bg = "#131829"; card_border = "#1f2640"
else:
    bg_top = active["light_bg"] if active else "#f7f9fc"; bg_bottom = "#f7f9fc"
    text_main = "#0a0e1a"; text_muted = "#5a6478"
    card_bg = "#ffffff"; card_border = "#d8dfeb"

# ============================================================
# CSS
# ============================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Space Grotesk', sans-serif; color: {text_main}; }}
.stApp {{ background: linear-gradient(180deg, {bg_top} 0%, {bg_bottom} 100%); }}
h1 {{ background: linear-gradient(90deg, {accent} 0%, {accent_map} 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 3rem !important; }}
h2 {{ color: {text_main} !important; font-weight: 600; font-size: 1.8rem !important; }}
h3 {{ color: {text_main} !important; font-weight: 600; }}

.section-header {{ display: inline-block; padding: 8px 18px; background: {card_bg}; border-left: 3px solid {accent_map}; border-radius: 4px; margin: 18px 0 12px 0; font-size: 1.25rem; font-weight: 600; color: {text_main}; }}

/* Regular button */
.stButton > button {{
    background: {card_bg};
    color: {text_main};
    border: 1px solid {card_border};
    padding: 12px 22px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
    font-size: 14px;
    border-radius: 8px;
    width: 100%;
    transition: all 0.2s ease;
}}
.stButton > button:hover {{
    border-color: {accent_map};
    box-shadow: 0 0 18px {glow};
    transform: translateY(-1px);
}}
.stButton > button:active {{
    box-shadow: 0 0 28px {glow};
}}

/* Primary (Analyze) — bright, glows on hover/click */
button[kind="primary"] {{
    background: linear-gradient(90deg, {grad}) !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    box-shadow: 0 0 24px {glow} !important;
    transition: all 0.25s ease !important;
}}
button[kind="primary"]:hover {{
    box-shadow: 0 0 42px {glow}, 0 0 68px {glow} !important;
    transform: translateY(-2px) scale(1.01) !important;
}}
button[kind="primary"]:active {{
    box-shadow: 0 0 55px {glow} !important;
    transform: scale(0.99) !important;
}}

/* Change type active */
button[kind="secondary"]:hover {{
    box-shadow: 0 0 14px {glow} !important;
}}

.help-box {{ background: {card_bg}; border: 1px solid {accent_map}; border-radius: 10px; padding: 16px 20px; margin: 12px 0 18px 0; }}
.help-box h4 {{ color: {accent_map}; margin: 0 0 10px 0; }}
.help-box pre {{ white-space: pre-wrap; font-family: 'Space Grotesk', sans-serif; font-size: 13px; line-height: 1.7; color: {text_muted}; margin: 0; }}

.explain-box {{ background: {card_bg}; border-left: 3px solid {accent_map}; border-radius: 6px; padding: 16px 20px; margin-top: 20px; }}
.explain-box p {{ margin: 8px 0; font-size: 14px; line-height: 1.6; color: {text_muted}; }}
.explain-box b {{ color: {accent_map}; }}

.info-box {{ background: {card_bg}; border-left: 3px solid {accent_map}; border-radius: 6px; padding: 14px 18px; margin: 10px 0; color: {text_main}; font-size: 14px; line-height: 1.7; }}
.type-badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; background: {accent_map}; color: white; font-weight: 600; font-size: 14px; margin-left: 8px; }}

.landing-card {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 12px; padding: 24px; margin: 12px 0; }}
.landing-card h3 {{ color: {accent_map}; margin: 0 0 10px 0; font-size: 1.1rem; }}
.landing-card p {{ color: {text_muted}; font-size: 14px; line-height: 1.6; margin: 0; }}

.pipeline-step {{ display: flex; align-items: flex-start; margin: 12px 0; padding: 12px 16px; background: {card_bg}; border-left: 3px solid {accent_map}; border-radius: 6px; }}
.pipeline-step-num {{ background: {accent_map}; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; margin-right: 14px; }}

.impact-box {{ background: {card_bg}; border-radius: 10px; padding: 20px; margin: 8px 0; border: 1px solid {card_border}; }}
.impact-box h4 {{ color: {accent_map}; margin: 0 0 8px 0; font-size: 1rem; }}
.impact-box p {{ color: {text_muted}; font-size: 13px; line-height: 1.5; margin: 0; }}

.hero-sub {{ color: {text_muted}; font-size: 1.15rem; line-height: 1.6; max-width: 720px; }}
.hero-badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; background: {card_bg}; border: 1px solid {accent_map}; color: {accent_map}; font-size: 12px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# LANDING
# ============================================================
if not st.session_state["onboarded"]:
    c1, c2 = st.columns([6, 1])
    with c2:
        st.button("☀️ Light" if st.session_state["theme"] == "dark" else "🌙 Dark",
                  key="landing_theme_btn", on_click=toggle_theme)

    st.markdown(f'<span class="hero-badge">{T["hero_badge"]}</span>', unsafe_allow_html=True)
    st.markdown("# NISAR Surface Change Tracker")
    st.markdown(f'<p class="hero-sub">{T["hero_sub"]}</p>', unsafe_allow_html=True)
    st.markdown("---")

    f1, f2, f3 = st.columns(3)
    with f1: st.markdown(f'<div class="landing-card"><h3>📡 {T["feature1_title"]}</h3><p>{T["feature1_text"]}</p></div>', unsafe_allow_html=True)
    with f2: st.markdown(f'<div class="landing-card"><h3>🌍 {T["feature2_title"]}</h3><p>{T["feature2_text"]}</p></div>', unsafe_allow_html=True)
    with f3: st.markdown(f'<div class="landing-card"><h3>🔬 {T["feature3_title"]}</h3><p>{T["feature3_text"]}</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f'## {T["method_title"]}')
    for i, (title, desc) in enumerate([(T["step1_title"], T["step1_text"]), (T["step2_title"], T["step2_text"]), (T["step3_title"], T["step3_text"]), (T["step4_title"], T["step4_text"]), (T["step5_title"], T["step5_text"])], 1):
        st.markdown(f'<div class="pipeline-step"><div class="pipeline-step-num">{i}</div><div><b>{title}</b> — {desc}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f'## {T["validation_title"]}')
    v1, v2, v3, v4 = st.columns(4)
    with v1: st.metric(T["validation_phase"], "−26.75 … +27.53 rad")
    with v2: st.metric(T["validation_disp"], "−51.09 … +52.57 cm")
    with v3: st.metric(T["validation_coh"], "0.000 … 0.939")
    with v4: st.metric(T["validation_size"], "4185 × 4293 px")

    st.markdown("---")
    st.markdown(f'## {T["impact_title"]}')
    i1, i2, i3, i4 = st.columns(4)
    with i1: st.markdown(f'<div class="impact-box"><h4>{T["impact1_title"]}</h4><p>{T["impact1_text"]}</p></div>', unsafe_allow_html=True)
    with i2: st.markdown(f'<div class="impact-box"><h4>{T["impact2_title"]}</h4><p>{T["impact2_text"]}</p></div>', unsafe_allow_html=True)
    with i3: st.markdown(f'<div class="impact-box"><h4>Любознательные</h4><p>Просто интересно посмотреть, как выглядит Земля из космоса в радиодиапазоне — без оборудования и профильной подготовки.</p></div>', unsafe_allow_html=True)
    with i4: st.markdown(f'<div class="impact-box"><h4>{T["impact4_title"]}</h4><p>{T["impact4_text"]}</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    cta1, cta2, cta3 = st.columns([1, 2, 1])
    with cta2:
        st.button(f"▶  {T['continue']}", use_container_width=True, type="primary", key="cta_btn", on_click=go_to_app)

    st.markdown("---")
    st.markdown(f'<div style="text-align:center; color:{text_muted}; font-size:13px;">{T["footer_built"]}<br>{T["footer_data"]}<br>{T["footer_credit"]}</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================
# MAIN APP
# ============================================================
bc1, bc2, bc3 = st.columns([1, 5, 1])
with bc1:
    st.button(f"← {T['back']}", key="back_btn", on_click=go_to_landing)
with bc3:
    st.button("☀️" if st.session_state["theme"] == "dark" else "🌙",
              key="theme_toggle_btn", on_click=toggle_theme)

col_logo, col_help = st.columns([5, 1])
with col_logo:
    st.markdown("# NISAR Surface Change Tracker")
    st.markdown(f"<p style='color:{text_muted}; margin-top:-12px;'>{T['tagline']}</p>", unsafe_allow_html=True)
with col_help:
    help_label = f"❌ {T['help']}" if st.session_state["show_help"] else f"❓ {T['help']}"
    st.button(help_label, key="help_btn", use_container_width=True, on_click=toggle_help)

if st.session_state["show_help"]:
    st.markdown(f'<div
