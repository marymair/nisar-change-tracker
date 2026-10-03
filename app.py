"""
NISAR Surface Change Tracker — v3.3
- Clickable satellite map (folium) with coordinate marker
- Reverse geocoding via Nominatim (address lookup)
- Check for NISAR data availability
- Theme toggle (light/dark)
- Help popup at top
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
    "selected_address": "",
    "show_help": False,
    "job_id": None,
    "theme": "dark",
    "map_center": [-30, 0],
    "map_zoom": 2,
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
# THEME
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
# CSS
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
}}
h2, h3 {{ color: {text_main} !important; font-weight: 600; }}

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
.help-box {{
    background: {card_bg};
    border: 1px solid {accent};
    border-radius: 10px;
    padding: 16px 20px;
    margin: 12px 0 18px 0;
    color: {text_main};
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}}
.help-box h4 {{ color: {accent}; margin: 0 0 10px 0; font-size: 16px; }}
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
.explain-box p {{ margin: 8px 0; font-size: 14px; line-height: 1.6; color: {text_muted}; }}
.explain-box b {{ color: {accent}; }}
.info-box {{
    background: {card_bg};
    border-left: 3px solid {accent};
    border-radius: 6px;
    padding: 14px 18px;
    margin: 10px 0;
    color: {text_main};
    font-size: 14px;
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
    label = "Light" if st.session_state["theme"] == "dark" else "Dark"
    if st.button(f"{theme_icon} {label}", key="theme_toggle"):
        st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"
        st.rerun()

with col_lang:
    lang_options = {"English": "en", "Русский": "ru", "Español": "es", "Français": "fr"}
    lang_name = st.selectbox(
        "Language", list(lang_options.keys()),
        index=list(lang_options.values()).index(st.session_state["lang"]),
        label_visibility="collapsed", key="lang_selector",
    )
    new_lang = lang_options[lang_name]
    if new_lang != st.session_state["lang"]:
        st.session_state["lang"] = new_lang
        st.rerun()

# ============================================================
# HELP TOGGLE
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

# ============================================================
# INTERACTIVE MAP
# ============================================================
st.markdown(f'<div class="section-header">{T["select_location"]}</div>', unsafe_allow_html=True)
st.markdown(f"<p style='color:{text_muted}; font-size:13px;'>{T['click_map']}</p>", unsafe_allow_html=True)

# NISAR reference regions (where data exists)
NISAR_REGIONS = [
    (T["antarctica"], -75.0, 0.0),
    (T["himalayas"], 28.0, 85.0),
    (T["amazon"], -3.0, -60.0),
    (T["california"], 38.0, -120.0),
    (T["greenland"], 72.0, -40.0),
]

# Build folium map
if st.session_state["theme"] == "dark":
    tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    attr = "NASA Earth Imagery"
else:
    tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    attr = "NASA Earth Imagery"

m = folium.Map(
    location=st.session_state["map_center"],
    zoom_start=st.session_state["map_zoom"],
    tiles=tiles,
    attr=attr,
    control_scale=True,
)

# Add NISAR reference markers
for name, lat, lon in NISAR_REGIONS:
    folium.CircleMarker(
        location=[lat, lon],
        radius=6,
        color="#4a9eff",
        fill=True,
        fill_color="#4a9eff",
        fill_opacity=0.7,
        tooltip=f"<b>{name}</b><br>NISAR data available",
    ).add_to(m)

# Add the selected marker (bigger, accent-colored)
folium.Marker(
    location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
    popup=f"Selected: {st.session_state['selected_lat']:.2f}, {st.session_state['selected_lon']:.2f}",
    tooltip="Selected location",
    icon=folium.Icon(color="red", icon="crosshair", prefix="fa"),
).add_to(m)

# Render map and capture click
map_data = st_folium(m, height=500, use_container_width=True, key="nisar_map")

# Handle click
if map_data and map_data.get("last_clicked"):
    new_lat = map_data["last_clicked"]["lat"]
    new_lon = map_data["last_clicked"]["lng"]
    if abs(new_lat - st.session_state["selected_lat"]) > 0.001 or abs(new_lon - st.session_state["selected_lon"]) > 0.001:
        st.session_state["selected_lat"] = new_lat
        st.session_state["selected_lon"] = new_lon
        # Reverse geocode
        try:
            geolocator = Nominatim(user_agent="nisar_tracker")
            location = geolocator.reverse(f"{new_lat}, {new_lon}", timeout=5)
            if location:
                st.session_state["selected_address"] = location.address
            else:
                st.session_state["selected_address"] = "Ocean / remote area"
        except Exception:
            st.session_state["selected_address"] = f"{new_lat:.3f}, {new_lon:.3f}"
        st.rerun()

# Show selected coordinates and address
st.markdown(f"""
<div class="info-box">
    <b>📍 {T['selected']}:</b> {st.session_state['selected_lat']:.3f}, {st.session_state['selected_lon']:.3f}
    {"<br><i>" + st.session_state["selected_address"] + "</i>" if st.session_state.get("selected_address") else ""}
</div>
""", unsafe_allow_html=True)

# Quick select buttons
st.markdown(f"<p style='color:{text_muted}; font-size:13px;'>{T['quick_select']}:</p>", unsafe_allow_html=True)
qcols = st.columns(5)
for i, (name, qlat, qlon) in enumerate(NISAR_REGIONS):
    with qcols[i]:
        if st.button(name, key=f"quick_{i}", use_container_width=True):
            st.session_state["selected_lat"] = qlat
            st.session_state["selected_lon"] = qlon
            st.session_state["map_center"] = [qlat, qlon]
            st.session_state["map_zoom"] = 4
            try:
                geolocator = Nominatim(user_agent="nisar_tracker")
                loc = geolocator.reverse(f"{qlat}, {qlon}", timeout=5)
                st.session_state["selected_address"] = loc.address if loc else name
            except Exception:
                st.session_state["selected_address"] = name
            st.rerun()

# ============================================================
# DATA AVAILABILITY CHECK
# ============================================================
if st.button(f"🔍 Check NISAR data availability", key="check_btn", use_container_width=True):
    with st.spinner("Checking NASA Earthdata..."):
        try:
            r = requests.post(
                f"{BACKEND_URL}/search",
                json={"lat": st.session_state["selected_lat"], "lon": st.session_state["selected_lon"],
                      "start_date": "2026-09-01", "end_date": "2026-09-30"},
                timeout=60,
            )
            d = r.json()
            count = d.get("count", 0)
            if count == 0:
                st.warning(f"⚠️ {T['no_data']}")
            else:
                st.success(f"✅ Found {count} NISAR scenes for this location")
                for s in d.get("scenes", [])[:5]:
                    st.markdown(f"- `{s['name']}` — {s.get('level', '?')} — {s.get('date', '?')}")
        except Exception as e:
            st.error(f"❌ {e}")

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
if st.button(f"▶  {T['analyze']}", use_container_width=True, key="analyze_btn", type="primary"):
    with st.spinner(f"🔎 {T['searching']}..."):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/analyze",
                json={
                    "lat": st.session_state["selected_lat"],
                    "lon": st.session_state["selected_lon"],
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
    d = {}
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
                st.download_button(f"⬇  {T['download']}", data=img_resp.content,
                                   file_name=f"nisar_{job_id}.png", mime="image/png")
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
