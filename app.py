"""
NISAR Surface Change Tracker — v3.2
- Working translations (EN/RU/ES/FR)
- Light / Dark theme toggle
- Help popup moved to top, toggles on/off
- Fixed full names for quick-select regions
- Fixed background per change type
"""
import streamlit as st
import pydeck as pdk
import pandas as pd
import requests
import time
from PIL import Image
from io import BytesIO
from translations import TEXTS

BACKEND_URL = "https://nisar-backend-production-feb6.up.railway.app"

st.set_page_config(
    page_title="NISAR Surface Change Tracker",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    "lang": "en",
    "change_type": "glacier",
    "selected_lat": -75.0,
    "selected_lon": 0.0,
    "show_help": False,
    "job_id": None,
    "theme": "dark",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

T = TEXTS[st.session_state["lang"]]

# ============================================================
# CHANGE TYPES
# ============================================================
CHANGE_TYPES = {
    "fire":       {"icon": "🔥", "label": T["change_fire"],       "color": "#FC3D21", "dark_bg": "#1a0605", "light_bg": "#fff2ef"},
    "glacier":    {"icon": "❄️", "label": T["change_glacier"],    "color": "#3a7bd5", "dark_bg": "#061226", "light_bg": "#eef5ff"},
    "flood":      {"icon": "🌊", "label": T["change_flood"],      "color": "#1e90ff", "dark_bg": "#061425", "light_bg": "#eaf5ff"},
    "desert":     {"icon": "🏜️", "label": T["change_desert"],     "color": "#c98a00", "dark_bg": "#1a1506", "light_bg": "#fdf6e3"},
    "earthquake": {"icon": "🌍", "label": T["change_earthquake"], "color": "#9b59b6", "dark_bg": "#160a22", "light_bg": "#f5eefc"},
    "wetland":    {"icon": "🌿", "label": T["change_wetland"],    "color": "#27ae60", "dark_bg": "#061a10", "light_bg": "#eafaf1"},
}

active = CHANGE_TYPES[st.session_state["change_type"]]
accent = active["color"]

# ============================================================
# THEME COLORS
# ============================================================
if st.session_state["theme"] == "dark":
    bg_top = active["dark_bg"]
    bg_bottom = "#0a0e1a"
    text_main = "#e8ecf5"
    text_muted = "#8892a6"
    card_bg = "#131829"
    card_border = "#1f2640"
else:
    bg_top = active["light_bg"]
    bg_bottom = "#f7f9fc"
    text_main = "#0a0e1a"
    text_muted = "#5a6478"
    card_bg = "#ffffff"
    card_border = "#d8dfeb"

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Space Grotesk', sans-serif;
    color: {text_main};
}}

.stApp {{
    background: linear-gradient(180deg, {bg_top} 0%, {bg_bottom} 100%);
    transition: background 0.5s ease;
}}

h1 {{
    background: linear-gradient(90deg, {accent} 0%, #FC3D21 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 2.6rem !important;
    letter-spacing: -0.02em;
}}

h2, h3 {{
    color: {text_main} !important;
    font-weight: 600;
}}

.section-header {{
    display: inline-block;
    padding: 8px 18px;
    background: {card_bg};
    border-left: 3px solid {accent};
    border-radius: 4px;
    margin: 18px 0 12px 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: {text_main};
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}}

.stButton > button {{
    background: {card_bg};
    color: {text_main};
    border: 1px solid {card_border};
    padding: 12px 22px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
    font-size: 14px;
    border-radius: 8px;
    transition: all 0.25s ease;
    width: 100%;
}}
.stButton > button:hover {{
    border-color: {accent};
    box-shadow: 0 0 14px {accent}44;
    transform: translateY(-1px);
}}

button[kind="primary"] {{
    background: linear-gradient(90deg, {accent} 0%, #FC3D21 100%) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 0 20px {accent}88 !important;
}}

/* Help panel — top-right, below header */
.help-box {{
    background: {card_bg};
    border: 1px solid {accent};
    border-radius: 10px;
    padding: 16px 20px;
    margin: 12px 0 18px 0;
    color: {text_main};
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}}
.help-box h4 {{
    color: {accent};
    margin: 0 0 10px 0;
    font-size: 16px;
}}
.help-box pre {{
    white-space: pre-wrap;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    line-height: 1.7;
    color: {text_muted};
    margin: 0;
}}

.explain-box {{
    background: {card_bg};
    border-left: 3px solid {accent};
    border-radius: 6px;
    padding: 16px 20px;
    margin-top: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}}
.explain-box p {{
    margin: 8px 0;
    font-size: 14px;
    line-height: 1.6;
    color: {text_muted};
}}
.explain-box b {{
    color: {accent};
}}

p, span, label {{
    color: {text_main};
}}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
col_logo, col_theme, col_lang = st.columns([3, 1, 1])

with col_logo:
    st.markdown("# NISAR Surface Change Tracker")
    st.markdown(f"<p style='color:{text_muted}; margin-top:-12px;'>{T['tagline']}</p>", unsafe_allow_html=True)

with col_theme:
    theme_icon = "☀️" if st.session_state["theme"] == "dark" else "🌙"
    if st.button(f"{theme_icon} {'Light' if st.session_state['theme'] == 'dark' else 'Dark'}", key="theme_toggle"):
        st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"
        st.rerun()

with col_lang:
    lang_options = {"English": "en", "Русский": "ru", "Español": "es", "Français": "fr"}
    lang_name = st.selectbox(
        "Language",
        list(lang_options.keys()),
        index=list(lang_options.values()).index(st.session_state["lang"]),
        label_visibility="collapsed",
        key="lang_selector",
    )
    new_lang = lang_options[lang_name]
    if new_lang != st.session_state["lang"]:
        st.session_state["lang"] = new_lang
        st.rerun()

# ============================================================
# HELP BUTTON — TOP, toggles on/off
# ============================================================
help_col1, help_col2 = st.columns([5, 1])
with help_col2:
    help_label = f"❌ {T['help']}" if st.session_state["show_help"] else f"❓ {T['help']}"
    if st.button(help_label, key="help_btn", use_container_width=True):
        st.session_state["show_help"] = not st.session_state["show_help"]
        st.rerun()

if st.session_state["show_help"]:
    st.markdown(f"""
    <div class="help-box">
        <h4>{T['help_title']}</h4>
        <pre>{T['help_text']}</pre>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# CHANGE-TYPE FILTERS
# ============================================================
st.markdown(f'<div class="section-header">{T["type_of_change"]}</div>', unsafe_allow_html=True)

cols = st.columns(6)
for i, (key, cfg) in enumerate(CHANGE_TYPES.items()):
    with cols[i]:
        is_active = st.session_state["change_type"] == key
        if st.button(
            f"{cfg['icon']} {cfg['label']}",
            key=f"btn_{key}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state["change_type"] = key
            st.rerun()

st.markdown(
    f"<p style='color:{accent}; text-align:center; font-size:14px;'>"
    f"{T['selected']}: <b>{active['label']}</b></p>",
    unsafe_allow_html=True,
)

# ============================================================
# GLOBE
# ============================================================
st.markdown(f'<div class="section-header">{T["select_location"]}</div>', unsafe_allow_html=True)
st.markdown(f"<p style='color:{text_muted}; font-size:13px;'>{T['click_map']}</p>", unsafe_allow_html=True)

REFERENCE_POINTS = pd.DataFrame({
    "name": [T["antarctica"], T["himalayas"], T["amazon"], T["california"], T["greenland"]],
    "lat": [-75.0, 28.0, -3.0, 38.0, 72.0],
    "lon": [0.0, 85.0, -60.0, -120.0, -40.0],
    "color": [[74, 158, 255, 220]] * 5,
})

HOTSPOTS = {
    "fire":       [(38.0, -120.0), (-3.0, -60.0), (-35.0, 148.0)],
    "glacier":    [(-75.0, 0.0), (72.0, -40.0), (28.0, 85.0)],
    "flood":      [(25.0, 90.0), (-3.0, -60.0), (14.0, 100.0)],
    "desert":     [(23.0, 10.0), (-25.0, 130.0), (30.0, 60.0)],
    "earthquake": [(38.0, 38.0), (35.0, 140.0), (-30.0, -70.0)],
    "wetland":    [(0.0, 20.0), (-3.0, -60.0), (10.0, 105.0)],
}
hotspot_data = pd.DataFrame(
    [{"lat": la, "lon": lo, "color": [252, 61, 33, 230]} for la, lo in HOTSPOTS[st.session_state["change_type"]]]
)

# Map style depends on theme
map_style = (
    "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
    if st.session_state["theme"] == "dark"
    else "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
)

view_state = pdk.ViewState(latitude=20, longitude=0, zoom=1.5, pitch=0)

ref_layer = pdk.Layer(
    "ScatterplotLayer",
    data=REFERENCE_POINTS,
    get_position=["lon", "lat"],
    get_color="color",
    get_radius=150000,
    pickable=True,
)

hotspot_layer = pdk.Layer(
    "ScatterplotLayer",
    data=hotspot_data,
    get_position=["lon", "lat"],
    get_color="color",
    get_radius=120000,
    pickable=True,
)

deck = pdk.Deck(
    layers=[ref_layer, hotspot_layer],
    initial_view_state=view_state,
    map_style=map_style,
    tooltip={"text": "{name}"},
)

st.pydeck_chart(deck, use_container_width=True)

# Coordinates
col1, col2 = st.columns(2)
with col1:
    lat = st.number_input(T["latitude"], value=st.session_state["selected_lat"], format="%.2f")
with col2:
    lon = st.number_input(T["longitude"], value=st.session_state["selected_lon"], format="%.2f")

# Quick select
st.markdown(f"<p style='color:{text_muted}; font-size:13px;'>{T['quick_select']}:</p>", unsafe_allow_html=True)
qcols = st.columns(5)
quick = [
    (T["antarctica"], -75.0, 0.0),
    (T["himalayas"], 28.0, 85.0),
    (T["amazon"], -3.0, -60.0),
    (T["california"], 38.0, -120.0),
    (T["greenland"], 72.0, -40.0),
]
for i, (name, qlat, qlon) in enumerate(quick):
    with qcols[i]:
        if st.button(name, key=f"quick_{i}", use_container_width=True):
            st.session_state["selected_lat"] = qlat
            st.session_state["selected_lon"] = qlon
            st.rerun()

# ============================================================
# DATE RANGE
# ============================================================
st.markdown(f'<div class="section-header">{T["date_range"]}</div>', unsafe_allow_html=True)
col_d1, col_d2 = st.columns(2)
with col_d1:
    start_date = st.date_input(T["from"], value=pd.Timestamp("2026-09-01"))
with col_d2:
    end_date = st.date_input(T["to"], value=pd.Timestamp("2026-09-28"))

# ============================================================
# ANALYZE
# ============================================================
st.markdown("---")
if st.button(f"▶  {T['analyze']}", use_container_width=True, key="analyze_btn"):
    with st.spinner(f"🔎 {T['searching']}..."):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/analyze",
                json={"lat": lat, "lon": lon, "start_date": str(start_date), "end_date": str(end_date)},
                timeout=30,
            )
            data = resp.json()
            if "error" in data:
                st.error(f"❌ {data['error']}")
            else:
                st.session_state["job_id"] = data.get("job_id")
                st.success(f"✅ Job: `{data.get('job_id')}`")
                st.info(f"📡 {data.get('scene_name', '')}")
        except Exception as e:
            st.error(f"❌ Backend: {e}")

# ============================================================
# RESULT
# ============================================================
if st.session_state["job_id"]:
    job_id = st.session_state["job_id"]
    st.markdown(f'<div class="section-header">{T["processing"]}...</div>', unsafe_allow_html=True)
    progress_bar = st.progress(0)
    status_text = st.empty()

    status = "processing"
    for i in range(60):
        try:
            r = requests.get(f"{BACKEND_URL}/status/{job_id}", timeout=10)
            d = r.json()
            status = d.get("status", "unknown")
            if status == "processing":
                progress_bar.progress(min((i + 1) * 2, 95))
                status_text.text(f"⏳ {d.get('scene_name', '')}")
                time.sleep(5)
            elif status == "done":
                progress_bar.progress(100)
                status_text.text("✅")
                break
            elif status == "error":
                st.error(f"❌ {d.get('error', 'unknown')}")
                break
        except Exception:
            time.sleep(5)

    if status == "done":
        st.markdown(f'<div class="section-header">{T["result"]}</div>', unsafe_allow_html=True)
        try:
            img_resp = requests.get(f"{BACKEND_URL}/image/{job_id}", timeout=30)
            if img_resp.status_code == 200:
                img = Image.open(BytesIO(img_resp.content))
                st.image(img, use_container_width=True)
                st.download_button(
                    f"⬇  {T['download']}",
                    data=img_resp.content,
                    file_name=f"nisar_{job_id}.png",
                    mime="image/png",
                )
                stats = d.get("stats", {})
                if stats:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(T["phase_min"], f"{stats.get('phase_min', 0):.2f} rad")
                    c2.metric(T["phase_max"], f"{stats.get('phase_max', 0):.2f} rad")
                    c3.metric(T["disp_min"], f"{stats.get('disp_min_cm', 0):.2f} cm")
                    c4.metric(T["disp_max"], f"{stats.get('disp_max_cm', 0):.2f} cm")

                st.markdown(f"""
                <div class="explain-box">
                    <h4 style="color:{accent}; margin:0 0 10px 0;">{T['explain_title']}</h4>
                    <p><b>Coherence</b> — {T['explain_coherence']}</p>
                    <p><b>Unwrapped Phase</b> — {T['explain_phase']}</p>
                    <p><b>Surface Displacement</b> — {T['explain_displacement']}</p>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Image fetch failed: {e}")

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    f"<p style='text-align:center; color:{text_muted}; font-size:12px;'>"
    "NASA Space Apps Challenge · NISAR L1 GUNW · NASA Earthdata</p>",
    unsafe_allow_html=True,
)
