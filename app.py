"""
NISAR Surface Change Tracker — v3.5
- Correct step order: type → location → dates → availability → analyze → result
- Availability check uses selected dates
- All filters tied to backend request
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
    "change_type": None,
    "selected_lat": -75.0,
    "selected_lon": 0.0,
    "selected_address": "",
    "show_help": False,
    "job_id": None,
    "theme": "dark",
    "map_center": [20, 0],
    "map_zoom": 2,
    "availability_checked": False,
    "availability_count": None,
    "availability_scenes": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

T = TEXTS[st.session_state["lang"]]

# ============================================================
# CHANGE TYPES
# ============================================================
CHANGE_TYPES = {
    "fire":       {"icon": "🔥", "label": T["change_fire"],       "color": "#FC3D21", "map_color": "#FC3D21", "dark_bg": "#1a0605", "light_bg": "#fff2ef"},
    "glacier":    {"icon": "❄️", "label": T["change_glacier"],    "color": "#3a7bd5", "map_color": "#5bc8ff", "dark_bg": "#061226", "light_bg": "#eef5ff"},
    "flood":      {"icon": "🌊", "label": T["change_flood"],      "color": "#1e90ff", "map_color": "#1e90ff", "dark_bg": "#061425", "light_bg": "#eaf5ff"},
    "desert":     {"icon": "🏜️", "label": T["change_desert"],     "color": "#c98a00", "map_color": "#e6b800", "dark_bg": "#1a1506", "light_bg": "#fdf6e3"},
    "earthquake": {"icon": "🌍", "label": T["change_earthquake"], "color": "#9b59b6", "map_color": "#b06cd9", "dark_bg": "#160a22", "light_bg": "#f5eefc"},
    "wetland":    {"icon": "🌿", "label": T["change_wetland"],    "color": "#27ae60", "map_color": "#3ed87a", "dark_bg": "#061a10", "light_bg": "#eafaf1"},
}

HOTSPOTS_BY_TYPE = {
    "fire": [
        ("California, USA", 38.0, -120.0, 0.95),
        ("Amazon, Brazil", -3.0, -60.0, 0.85),
        ("Victoria, Australia", -37.0, 145.0, 0.80),
        ("Siberia, Russia", 62.0, 105.0, 0.75),
        ("British Columbia, Canada", 54.0, -125.0, 0.70),
    ],
    "glacier": [
        ("Antarctica", -75.0, 0.0, 0.95),
        ("Greenland", 72.0, -40.0, 0.90),
        ("Himalayas, Nepal", 28.0, 85.0, 0.85),
        ("Alps, Switzerland", 46.5, 8.0, 0.70),
        ("Patagonia, Chile", -50.0, -73.0, 0.75),
    ],
    "flood": [
        ("Bangladesh", 24.0, 90.0, 0.95),
        ("Amazon, Brazil", -3.0, -60.0, 0.80),
        ("Mekong Delta, Vietnam", 10.0, 105.0, 0.85),
        ("Mississippi, USA", 32.0, -91.0, 0.75),
        ("Nile Delta, Egypt", 31.0, 31.0, 0.70),
    ],
    "desert": [
        ("Sahara, Algeria", 27.0, 5.0, 0.90),
        ("Sahel, Niger", 15.0, 8.0, 0.85),
        ("Gobi, Mongolia", 43.0, 105.0, 0.80),
        ("Kalahari, Botswana", -23.0, 22.0, 0.75),
        ("Aral Sea, Uzbekistan", 45.0, 58.0, 0.95),
    ],
    "earthquake": [
        ("Turkey-Syria", 37.0, 38.0, 0.95),
        ("Japan", 35.0, 140.0, 0.90),
        ("California, USA", 35.0, -119.0, 0.85),
        ("Chile", -30.0, -71.0, 0.80),
        ("Nepal", 28.0, 85.0, 0.75),
    ],
    "wetland": [
        ("Okavango, Botswana", -19.0, 23.0, 0.90),
        ("Pantanal, Brazil", -17.0, -57.0, 0.95),
        ("Sundarbans, Bangladesh", 22.0, 89.0, 0.85),
        ("Everglades, USA", 25.5, -80.5, 0.80),
        ("Congo Basin", 0.0, 20.0, 0.75),
    ],
}

active = CHANGE_TYPES.get(st.session_state["change_type"]) if st.session_state["change_type"] else None
accent = active["color"] if active else "#3a7bd5"

# ============================================================
# THEME
# ============================================================
if st.session_state["theme"] == "dark":
    bg_top = active["dark_bg"] if active else "#0a0e1a"
    bg_bottom = "#0a0e1a"
    text_main = "#e8ecf5"
    text_muted = "#8892a6"
    card_bg = "#131829"
    card_border = "#1f2640"
else:
    bg_top = active["light_bg"] if active else "#f7f9fc"
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
html, body, [class*="css"] {{ font-family: 'Space Grotesk', sans-serif; color: {text_main}; }}
.stApp {{ background: linear-gradient(180deg, {bg_top} 0%, {bg_bottom} 100%); transition: background 0.5s ease; }}
h1 {{ background: linear-gradient(90deg, {accent} 0%, #FC3D21 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 2.6rem !important; }}
h2, h3 {{ color: {text_main} !important; font-weight: 600; }}
.section-header {{ display: inline-block; padding: 8px 18px; background: {card_bg}; border-left: 3px solid {accent}; border-radius: 4px; margin: 18px 0 12px 0; font-size: 1.25rem; font-weight: 600; color: {text_main}; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
.stButton > button {{ background: {card_bg}; color: {text_main}; border: 1px solid {card_border}; padding: 12px 22px; font-family: 'Space Grotesk', sans-serif; font-weight: 500; font-size: 14px; border-radius: 8px; transition: all 0.25s ease; width: 100%; }}
.stButton > button:hover {{ border-color: {accent}; box-shadow: 0 0 14px {accent}44; transform: translateY(-1px); }}
button[kind="primary"] {{ background: linear-gradient(90deg, {accent} 0%, #FC3D21 100%) !important; color: white !important; border: none !important; box-shadow: 0 0 20px {accent}88 !important; }}
.help-box {{ background: {card_bg}; border: 1px solid {accent}; border-radius: 10px; padding: 16px 20px; margin: 12px 0 18px 0; color: {text_main}; box-shadow: 0 4px 20px rgba(0,0,0,0.15); }}
.help-box h4 {{ color: {accent}; margin: 0 0 10px 0; font-size: 16px; }}
.help-box pre {{ white-space: pre-wrap; font-family: 'Space Grotesk', sans-serif; font-size: 13px; line-height: 1.7; color: {text_muted}; margin: 0; }}
.explain-box {{ background: {card_bg}; border-left: 3px solid {accent}; border-radius: 6px; padding: 16px 20px; margin-top: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
.explain-box p {{ margin: 8px 0; font-size: 14px; line-height: 1.6; color: {text_muted}; }}
.explain-box b {{ color: {accent}; }}
.info-box {{ background: {card_bg}; border-left: 3px solid {accent}; border-radius: 6px; padding: 14px 18px; margin: 10px 0; color: {text_main}; font-size: 14px; }}
.type-badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; background: {accent}; color: white; font-weight: 600; font-size: 14px; margin-left: 8px; }}
.scene-row {{ background: {card_bg}; border-left: 3px solid {accent}; border-radius: 6px; padding: 10px 14px; margin: 6px 0; font-size: 13px; color: {text_main}; }}
.scene-row b {{ color: {accent}; }}
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
    lang_name = st.selectbox("Language", list(lang_options.keys()),
        index=list(lang_options.values()).index(st.session_state["lang"]),
        label_visibility="collapsed", key="lang_selector")
    new_lang = lang_options[lang_name]
    if new_lang != st.session_state["lang"]:
        st.session_state["lang"] = new_lang
        st.rerun()

# ============================================================
# HELP
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
# STEP 1 — TYPE OF CHANGE
# ============================================================
st.markdown(f'<div class="section-header">1. {T["type_of_change"]}</div>', unsafe_allow_html=True)

cols = st.columns(6)
for i, (key, cfg) in enumerate(CHANGE_TYPES.items()):
    with cols[i]:
        is_active = st.session_state["change_type"] == key
        if st.button(f"{cfg['icon']} {cfg['label']}", key=f"btn_{key}",
                     use_container_width=True, type="primary" if is_active else "secondary"):
            if st.session_state["change_type"] != key:
                st.session_state["change_type"] = key
                st.session_state["availability_checked"] = False
                st.session_state["job_id"] = None
            st.rerun()

if st.session_state["change_type"]:
    st.markdown(f"<p style='color:{accent}; font-size:14px; text-align:center;'>"
                f"{T['selected']}: <span class='type-badge'>{active['icon']} {active['label']}</span></p>",
                unsafe_allow_html=True)
else:
    st.info("👆 Выберите тип изменения, чтобы продолжить")
    st.stop()

# ============================================================
# STEP 2 — LOCATION
# ============================================================
st.markdown(f'<div class="section-header">2. {T["select_location"]}</div>', unsafe_allow_html=True)
st.markdown(f"<p style='color:{text_muted}; font-size:13px;'>{T['click_map']}</p>", unsafe_allow_html=True)

m = folium.Map(
    location=st.session_state["map_center"],
    zoom_start=st.session_state["map_zoom"],
    min_zoom=2,
    max_zoom=10,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="NASA Earth Imagery",
    control_scale=True,
    world_copy_jump=False,
    no_wrap=True,
)

hotspots = HOTSPOTS_BY_TYPE[st.session_state["change_type"]]
for name, hlat, hlon, intensity in hotspots:
    radius = 8 + int(intensity * 12)
    folium.CircleMarker(
        location=[hlat, hlon],
        radius=radius,
        color=active["map_color"],
        fill=True,
        fill_color=active["map_color"],
        fill_opacity=0.65,
        weight=2,
        tooltip=f"<b>{name}</b><br>{active['label']}<br>Intensity: {int(intensity*100)}%",
        popup=f"<b>{name}</b><br>Type: {active['label']}<br>Intensity: {int(intensity*100)}%",
    ).add_to(m)

folium.Marker(
    location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
    tooltip="Selected",
    icon=folium.Icon(color="red", icon="crosshair", prefix="fa"),
).add_to(m)

map_data = st_folium(m, height=500, use_container_width=True, key="nisar_map")

if map_data and map_data.get("last_clicked"):
    new_lat = map_data["last_clicked"]["lat"]
    new_lon = map_data["last_clicked"]["lng"]
    if abs(new_lat - st.session_state["selected_lat"]) > 0.001 or abs(new_lon - st.session_state["selected_lon"]) > 0.001:
        st.session_state["selected_lat"] = new_lat
        st.session_state["selected_lon"] = new_lon
        st.session_state["availability_checked"] = False
        st.session_state["job_id"] = None
        try:
            geolocator = Nominatim(user_agent="nisar_tracker")
            loc = geolocator.reverse(f"{new_lat}, {new_lon}", timeout=5)
            st.session_state["selected_address"] = loc.address if loc else "Remote area"
        except Exception:
            st.session_state["selected_address"] = f"{new_lat:.3f}, {new_lon:.3f}"
        st.rerun()

st.markdown(f"""
<div class="info-box">
    <b>📍 {T['selected']}:</b> {st.session_state['selected_lat']:.3f}, {st.session_state['selected_lon']:.3f}
    {"<br><i>" + st.session_state["selected_address"] + "</i>" if st.session_state.get("selected_address") else ""}
</div>
""", unsafe_allow_html=True)

# Legend
st.markdown(f"<p style='color:{accent}; font-weight:600; margin-top:12px;'>"
            f"📌 {T['legend']} — {active['label']}:</p>", unsafe_allow_html=True)
legend_cols = st.columns(5)
for i, (name, hlat, hlon, intensity) in enumerate(hotspots):
    with legend_cols[i]:
        st.markdown(f"""
        <div style="background:{card_bg}; border-left:3px solid {active['map_color']}; border-radius:6px; padding:8px 12px; margin:4px 0; font-size:12px;">
            <b style="color:{active['map_color']};">● {name}</b><br>
            <span style="color:{text_muted};">Intensity: {int(intensity*100)}%</span>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# STEP 3 — DATE RANGE
# ============================================================
st.markdown(f'<div class="section-header">3. {T["date_range"]}</div>', unsafe_allow_html=True)
col_d1, col_d2 = st.columns(2)
with col_d1:
    start_date = st.date_input(T["from"], value=pd.Timestamp("2026-09-01"))
with col_d2:
    end_date = st.date_input(T["to"], value=pd.Timestamp("2026-09-28"))

# ============================================================
# STEP 4 — AVAILABILITY CHECK (auto)
# ============================================================
st.markdown(f'<div class="section-header">4. {T["check_avail"]}</div>', unsafe_allow_html=True)

if st.button(f"🔍 {T['check_avail']}", key="check_btn", use_container_width=True):
    with st.spinner("Checking NASA Earthdata..."):
        try:
            r = requests.post(
                f"{BACKEND_URL}/search",
                json={"lat": st.session_state["selected_lat"], "lon": st.session_state["selected_lon"],
                      "start_date": str(start_date), "end_date": str(end_date)},
                timeout=60,
            )
            d = r.json()
            count = d.get("count", 0)
            st.session_state["availability_count"] = count
            st.session_state["availability_scenes"] = d.get("scenes", [])
            st.session_state["availability_checked"] = True
        except Exception as e:
            st.error(f"❌ {e}")

if st.session_state["availability_checked"]:
    count = st.session_state["availability_count"]
    if count == 0:
        st.warning(f"⚠️ {T['no_data']}")
    else:
        st.success(f"✅ Found {count} NISAR scenes for this location and period:")
        for s in st.session_state["availability_scenes"][:10]:
            st.markdown(f"""
            <div class="scene-row">
                <b>{s.get('level', '?')}</b> · {s.get('name', 'unknown')}<br>
                <span style='color:{text_muted};'>Date: {s.get('date', 'unknown')}</span>
            </div>
            """, unsafe_allow_html=True)

        # ============================================================
        # STEP 5 — ANALYZE
        # ============================================================
        st.markdown(f'<div class="section-header">5. {T["analyze"]}</div>', unsafe_allow_html=True)
        if st.button(f"▶  {T['analyze']}", use_container_width=True, key="analyze_btn", type="primary"):
            with st.spinner(f"🔎 {T['searching']}..."):
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/analyze",
                        json={"lat": st.session_state["selected_lat"], "lon": st.session_state["selected_lon"],
                              "start_date": str(start_date), "end_date": str(end_date)},
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

        if st.session_state["change_type"]:
            st.markdown(f"<p style='font-size:15px;'>"
                        f"<b>{T['type_of_change']}:</b> <span class='type-badge'>{active['icon']} {active['label']}</span></p>",
                        unsafe_allow_html=True)

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
