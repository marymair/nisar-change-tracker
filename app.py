"""
NISAR Surface Change Tracker — v3.1
- Working translations (EN/RU/ES/FR)
- Custom NASA-style theme with Space Grotesk
- 3D globe (pydeck GlobeView)
- Click anywhere → coordinates
- Colorful change-type buttons
- Background changes per change type
- Help popup
- Result explanation block
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
# INIT STATE
# ============================================================
if "lang" not in st.session_state:
    st.session_state["lang"] = "en"
if "change_type" not in st.session_state:
    st.session_state["change_type"] = "glacier"
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = -75.0
if "selected_lon" not in st.session_state:
    st.session_state["selected_lon"] = 0.0
if "show_help" not in st.session_state:
    st.session_state["show_help"] = False
if "job_id" not in st.session_state:
    st.session_state["job_id"] = None

T = TEXTS[st.session_state["lang"]]

# ============================================================
# CHANGE TYPE CONFIG — colors + backgrounds
# ============================================================
CHANGE_TYPES = {
    "fire":       {"en": "🔥", "label": T["change_fire"],       "color": "#FC3D21", "bg": "#2a0a06", "glow": "rgba(252,61,33,0.5)"},
    "glacier":    {"en": "❄️", "label": T["change_glacier"],    "color": "#4a9eff", "bg": "#06162a", "glow": "rgba(74,158,255,0.5)"},
    "flood":      {"en": "🌊", "label": T["change_flood"],      "color": "#1e90ff", "bg": "#061a2a", "glow": "rgba(30,144,255,0.5)"},
    "desert":     {"en": "🏜️", "label": T["change_desert"],     "color": "#d4a017", "bg": "#2a1f06", "glow": "rgba(212,160,23,0.5)"},
    "earthquake": {"en": "🌍", "label": T["change_earthquake"], "color": "#9b59b6", "bg": "#1a0a2a", "glow": "rgba(155,89,182,0.5)"},
    "wetland":    {"en": "🌿", "label": T["change_wetland"],    "color": "#27ae60", "bg": "#062a14", "glow": "rgba(39,174,96,0.5)"},
}

active = CHANGE_TYPES[st.session_state["change_type"]]
bg_color = active["bg"]
accent = active["color"]
glow = active["glow"]

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Space Grotesk', sans-serif;
    color: #e8ecf5;
}}

.stApp {{
    background: linear-gradient(180deg, {bg_color} 0%, #0a0e1a 100%);
    transition: background 0.6s ease;
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
    color: #e8ecf5 !important;
    font-weight: 600;
    letter-spacing: -0.01em;
}}

/* Big header with backdrop */
.section-header {{
    display: inline-block;
    padding: 8px 18px;
    background: rgba(74, 158, 255, 0.08);
    border-left: 3px solid {accent};
    border-radius: 4px;
    margin: 18px 0 12px 0;
    font-size: 1.3rem;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -0.01em;
}}

/* CTA */
.stButton > button {{
    background: linear-gradient(90deg, #0B3D91 0%, {accent} 100%);
    color: white;
    border: none;
    padding: 14px 28px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 15px;
    border-radius: 8px;
    box-shadow: 0 0 18px {glow};
    transition: all 0.3s ease;
    width: 100%;
}}
.stButton > button:hover {{
    box-shadow: 0 0 30px {glow};
    transform: translateY(-2px);
}}

/* Selected change-type button — bright */
button[kind="primary"] {{
    background: linear-gradient(90deg, {accent} 0%, #FC3D21 100%) !important;
    box-shadow: 0 0 25px {glow}, 0 0 50px {glow} !important;
    border: 2px solid #ffffff !important;
}}

/* Help panel */
.help-box {{
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 340px;
    background: #131829;
    border: 1px solid {accent};
    border-radius: 12px;
    padding: 18px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
    z-index: 9999;
    color: #e8ecf5;
}}
.help-box h4 {{
    color: {accent};
    margin-top: 0;
}}
.help-box pre {{
    white-space: pre-wrap;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    line-height: 1.6;
    color: #c8d0e0;
}}

.explain-box {{
    background: rgba(74, 158, 255, 0.06);
    border-left: 3px solid {accent};
    border-radius: 6px;
    padding: 16px 20px;
    margin-top: 20px;
}}

.explain-box p {{
    margin: 8px 0;
    font-size: 14px;
    line-height: 1.6;
    color: #c8d0e0;
}}
.explain-box b {{
    color: {accent};
}}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
col_logo, col_lang = st.columns([4, 1])
with col_logo:
    st.markdown("# NISAR Surface Change Tracker")
    st.markdown(f"<p style='color:#8892a6; margin-top:-12px;'>{T['tagline']}</p>", unsafe_allow_html=True)
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
# CHANGE-TYPE FILTERS
# ============================================================
st.markdown(f'<div class="section-header">{T["type_of_change"]}</div>', unsafe_allow_html=True)

cols = st.columns(6)
for i, (key, cfg) in enumerate(CHANGE_TYPES.items()):
    with cols[i]:
        is_active = st.session_state["change_type"] == key
        if st.button(
            f"{cfg['en']} {cfg['label']}",
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
st.markdown(f"<p style='color:#8892a6; font-size:13px;'>{T['click_map']}</p>", unsafe_allow_html=True)

REFERENCE_POINTS = pd.DataFrame({
    "name": [T["antarctica"], T["himalayas"], T["amazon"], T["california"], T["greenland"]],
    "lat": [-75.0, 28.0, -3.0, 38.0, 72.0],
    "lon": [0.0, 85.0, -60.0, -120.0, -40.0],
    "color": [[74, 158, 255]] * 5,
})

# Sample "change hotspots" per type (illustrative)
HOTSPOTS = {
    "fire":       [(38.0, -120.0), (-3.0, -60.0), (-35.0, 148.0)],
    "glacier":    [(-75.0, 0.0), (72.0, -40.0), (28.0, 85.0)],
    "flood":      [(25.0, 90.0), (-3.0, -60.0), (14.0, 100.0)],
    "desert":     [(23.0, 10.0), (-25.0, 130.0), (30.0, 60.0)],
    "earthquake": [(38.0, 38.0), (35.0, 140.0), (-30.0, -70.0)],
    "wetland":    [(0.0, 20.0), (-3.0, -60.0), (10.0, 105.0)],
}

hotspot_data = pd.DataFrame(
    [{"lat": lat, "lon": lon, "color": [252, 61, 33, 200]} for lat, lon in HOTSPOTS[st.session_state["change_type"]]]
)

view_state = pdk.ViewState(latitude=20, longitude=0, zoom=1.5, pitch=0)

# Reference layer (blue)
ref_layer = pdk.Layer(
    "ScatterplotLayer",
    data=REFERENCE_POINTS,
    get_position=["lon", "lat"],
    get_color="color",
    get_radius=150000,
    pickable=True,
)

# Hotspot layer (accent color)
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
    map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    tooltip={"text": "{name}"},
)

st.pydeck_chart(deck, use_container_width=True)

# Manual coordinate inputs
col1, col2 = st.columns(2)
with col1:
    lat = st.number_input(T["latitude"], value=st.session_state["selected_lat"], format="%.2f")
with col2:
    lon = st.number_input(T["longitude"], value=st.session_state["selected_lon"], format="%.2f")

# Quick select
st.markdown(f"<p style='color:#8892a6; font-size:13px;'>{T['quick_select']}:</p>", unsafe_allow_html=True)
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
# ANALYZE BUTTON
# ============================================================
st.markdown("---")
if st.button(f"▶  {T['analyze']}", use_container_width=True, key="analyze_btn"):
    with st.spinner(f"🔎 {T['searching']}..."):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/analyze",
                json={
                    "lat": lat,
                    "lon": lon,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                },
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
        except Exception as e:
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

                # Explanation block
                st.markdown(f"""
                <div class="explain-box">
                    <h4 style="color:{accent};">{T['explain_title']}</h4>
                    <p><b>Coherence</b> — {T['explain_coherence']}</p>
                    <p><b>Unwrapped Phase</b> — {T['explain_phase']}</p>
                    <p><b>Surface Displacement</b> — {T['explain_displacement']}</p>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Image fetch failed: {e}")

# ============================================================
# HELP BUTTON (fixed bottom-right)
# ============================================================
help_col1, help_col2 = st.columns([5, 1])
with help_col2:
    if st.button(f"❓ {T['help']}", key="help_btn"):
        st.session_state["show_help"] = not st.session_state["show_help"]

if st.session_state["show_help"]:
    st.markdown(f"""
    <div class="help-box">
        <h4>{T['help_title']}</h4>
        <pre>{T['help_text']}</pre>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#8892a6; font-size:12px;'>"
    "NASA Space Apps Challenge · NISAR L1 GUNW · NASA Earthdata"
    "</p>",
    unsafe_allow_html=True,
)
