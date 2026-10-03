"""
NISAR Surface Change Tracker — v5.0
Map always visible after selecting change type.
Hotspots with tooltips, clickable scene list, dynamic markers.
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

# ============================================================
# LANGUAGE
# ============================================================
lang_options = {"English": "en", "Русский": "ru", "Español": "es", "Français": "fr"}
lang_name = st.selectbox("🌐 Language", list(lang_options.keys()),
    index=list(lang_options.values()).index(st.session_state["lang"]),
    key="lang_selector", label_visibility="collapsed")
T = TEXTS[st.session_state["lang"]]

# ============================================================
# CHANGE TYPES + HOTSPOTS
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
    "fire": [("California, USA", 38.0, -120.0, 0.95, "Aug 2026"), ("Amazon, Brazil", -3.0, -60.0, 0.85, "Sep 2026"), ("Victoria, Australia", -37.0, 145.0, 0.80, "Jan 2026"), ("Siberia, Russia", 62.0, 105.0, 0.75, "Jul 2026")],
    "glacier": [("Antarctica", -75.0, 0.0, 0.95, "Sep 2026"), ("Greenland", 72.0, -40.0, 0.90, "Aug 2026"), ("Himalayas, Nepal", 28.0, 85.0, 0.85, "Sep 2026"), ("Alps, Switzerland", 46.5, 8.0, 0.70, "Jun 2026")],
    "flood": [("Bangladesh", 24.0, 90.0, 0.95, "Jul 2026"), ("Amazon, Brazil", -3.0, -60.0, 0.80, "Mar 2026"), ("Mekong Delta, Vietnam", 10.0, 105.0, 0.85, "Oct 2026"), ("Mississippi, USA", 32.0, -91.0, 0.75, "May 2026")],
    "desert": [("Sahara, Algeria", 27.0, 5.0, 0.90, "2026"), ("Sahel, Niger", 15.0, 8.0, 0.85, "2026"), ("Gobi, Mongolia", 43.0, 105.0, 0.80, "2026"), ("Aral Sea, Uzbekistan", 45.0, 58.0, 0.95, "2026")],
    "earthquake": [("Turkey-Syria", 37.0, 38.0, 0.95, "Feb 2026"), ("Japan", 35.0, 140.0, 0.90, "Jan 2026"), ("California, USA", 35.0, -119.0, 0.85, "Apr 2026"), ("Chile", -30.0, -71.0, 0.80, "Sep 2026")],
    "wetland": [("Okavango, Botswana", -19.0, 23.0, 0.90, "2026"), ("Pantanal, Brazil", -17.0, -57.0, 0.95, "2026"), ("Sundarbans, Bangladesh", 22.0, 89.0, 0.85, "2026"), ("Everglades, USA", 25.5, -80.5, 0.80, "2026")],
}

active = CHANGE_TYPES.get(st.session_state["change_type"]) if st.session_state["change_type"] else None
accent = active["color"] if active else "#3a7bd5"

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
h1 {{ background: linear-gradient(90deg, {accent} 0%, #FC3D21 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 3rem !important; }}
h2 {{ color: {text_main} !important; font-weight: 600; font-size: 1.8rem !important; }}
h3 {{ color: {text_main} !important; font-weight: 600; }}
.section-header {{ display: inline-block; padding: 8px 18px; background: {card_bg}; border-left: 3px solid {accent}; border-radius: 4px; margin: 18px 0 12px 0; font-size: 1.25rem; font-weight: 600; color: {text_main}; }}
.stButton > button {{ background: {card_bg}; color: {text_main}; border: 1px solid {card_border}; padding: 12px 22px; font-family: 'Space Grotesk', sans-serif; font-weight: 500; font-size: 14px; border-radius: 8px; width: 100%; transition: all 0.25s ease; }}
.stButton > button:hover {{ border-color: {accent}; box-shadow: 0 0 14px {accent}44; }}
button[kind="primary"] {{ background: linear-gradient(90deg, {accent} 0%, #FC3D21 100%) !important; color: white !important; border: none !important; box-shadow: 0 0 20px {accent}88 !important; }}
.help-box {{ background: {card_bg}; border: 1px solid {accent}; border-radius: 10px; padding: 16px 20px; margin: 12px 0 18px 0; }}
.help-box h4 {{ color: {accent}; margin: 0 0 10px 0; }}
.help-box pre {{ white-space: pre-wrap; font-family: 'Space Grotesk', sans-serif; font-size: 13px; line-height: 1.7; color: {text_muted}; margin: 0; }}
.explain-box {{ background: {card_bg}; border-left: 3px solid {accent}; border-radius: 6px; padding: 16px 20px; margin-top: 20px; }}
.explain-box p {{ margin: 8px 0; font-size: 14px; line-height: 1.6; color: {text_muted}; }}
.explain-box b {{ color: {accent}; }}
.info-box {{ background: {card_bg}; border-left: 3px solid {accent}; border-radius: 6px; padding: 14px 18px; margin: 10px 0; color: {text_main}; font-size: 14px; }}
.type-badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; background: {accent}; color: white; font-weight: 600; font-size: 14px; margin-left: 8px; }}
.scene-row {{ background: {card_bg}; border-left: 3px solid {accent}; border-radius: 6px; padding: 10px 14px; margin: 6px 0; font-size: 13px; color: {text_main}; }}
.scene-row-selected {{ background: {card_bg}; border-left: 3px solid #FC3D21; border-radius: 6px; padding: 10px 14px; margin: 6px 0; font-size: 13px; color: {text_main}; box-shadow: 0 0 12px #FC3D2166; }}
.region-ok {{ background: {card_bg}; border-left: 3px solid #27ae60; border-radius: 6px; padding: 10px 14px; margin: 6px 0; font-size: 13px; color: {text_main}; }}
.region-no {{ background: {card_bg}; border-left: 3px solid #8892a6; border-radius: 6px; padding: 10px 14px; margin: 6px 0; font-size: 13px; color: {text_muted}; }}
.landing-card {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 12px; padding: 24px; margin: 12px 0; }}
.landing-card h3 {{ color: {accent}; margin: 0 0 10px 0; font-size: 1.1rem; }}
.landing-card p {{ color: {text_muted}; font-size: 14px; line-height: 1.6; margin: 0; }}
.pipeline-step {{ display: flex; align-items: flex-start; margin: 12px 0; padding: 12px 16px; background: {card_bg}; border-left: 3px solid {accent}; border-radius: 6px; }}
.pipeline-step-num {{ background: {accent}; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; margin-right: 14px; }}
.impact-box {{ background: {card_bg}; border-radius: 10px; padding: 20px; margin: 8px 0; border: 1px solid {card_border}; }}
.impact-box h4 {{ color: {accent}; margin: 0 0 8px 0; font-size: 1rem; }}
.impact-box p {{ color: {text_muted}; font-size: 13px; line-height: 1.5; margin: 0; }}
.hero-sub {{ color: {text_muted}; font-size: 1.15rem; line-height: 1.6; max-width: 720px; }}
.hero-badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; background: {card_bg}; border: 1px solid {accent}; color: {accent}; font-size: 12px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# LANDING
# ============================================================
if not st.session_state["onboarded"]:
    c1, c2 = st.columns([6, 1])
    with c2:
        st.button("☀️ Light" if st.session_state["theme"] == "dark" else "🌙 Dark",
                  key="landing_theme", on_click=toggle_theme)
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
    with i3: st.markdown(f'<div class="impact-box"><h4>{T["impact3_title"]}</h4><p>{T["impact3_text"]}</p></div>', unsafe_allow_html=True)
    with i4: st.markdown(f'<div class="impact-box"><h4>{T["impact4_title"]}</h4><p>{T["impact4_text"]}</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    cta1, cta2, cta3 = st.columns([1, 2, 1])
    with cta2:
        st.button(f"▶  {T['continue']}", use_container_width=True, type="primary", key="cta", on_click=go_to_app)
    st.markdown("---")
    st.markdown(f'<div style="text-align:center; color:{text_muted}; font-size:13px;">{T["footer_built"]}<br>{T["footer_data"]}<br>{T["footer_credit"]}</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================
# MAIN APP
# ============================================================
bc1, bc2, bc3 = st.columns([1, 5, 1])
with bc1: st.button(f"← {T['back']}", key="back", on_click=go_to_landing)
with bc3: st.button("☀️" if st.session_state["theme"] == "dark" else "🌙", key="theme", on_click=toggle_theme)

col_logo, col_help = st.columns([5, 1])
with col_logo:
    st.markdown("# NISAR Surface Change Tracker")
    st.markdown(f"<p style='color:{text_muted}; margin-top:-12px;'>{T['tagline']}</p>", unsafe_allow_html=True)
with col_help:
    help_label = f"❌ {T['help']}" if st.session_state["show_help"] else f"❓ {T['help']}"
    st.button(help_label, key="help_btn", use_container_width=True, on_click=toggle_help)
if st.session_state["show_help"]:
    st.markdown(f'<div class="help-box"><h4>{T["help_title"]}</h4><pre>{T["help_text"]}</pre></div>', unsafe_allow_html=True)

# STEP 1 — TYPE
st.markdown(f'<div class="section-header">1. {T["type_of_change"]}</div>', unsafe_allow_html=True)
cols = st.columns(6)
for i, (key, cfg) in enumerate(CHANGE_TYPES.items()):
    with cols[i]:
        is_active = st.session_state["change_type"] == key
        st.button(f"{cfg['icon']} {cfg['label']}", key=f"btn_{key}",
                  use_container_width=True, type="primary" if is_active else "secondary",
                  on_click=set_change_type, args=(key,))

if st.session_state["change_type"]:
    st.markdown(f"<p style='color:{accent}; font-size:14px; text-align:center;'>{T['selected']}: <span class='type-badge'>{active['icon']} {active['label']}</span></p>", unsafe_allow_html=True)
else:
    st.info(T["choose_type_to_continue"])
    st.stop()

# STEP 2 — DATE
st.markdown(f'<div class="section-header">2. {T["date_range"]}</div>', unsafe_allow_html=True)
col_d1, col_d2 = st.columns(2)
with col_d1: start_date = st.date_input(T["from"], value=pd.Timestamp("2026-09-01"))
with col_d2: end_date = st.date_input(T["to"], value=pd.Timestamp("2026-09-28"))

# STEP 3 — MAP (ALWAYS VISIBLE)
st.markdown(f'<div class="section-header">3. {T["select_location"]}</div>', unsafe_allow_html=True)
st.markdown(f"<p style='color:{text_muted}; font-size:13px;'>{T['click_map']} · Hover over markers for details.</p>", unsafe_allow_html=True)

hotspots = HOTSPOTS_BY_TYPE[st.session_state["change_type"]]

m = folium.Map(location=[20, 0], zoom_start=2,
    min_zoom=2, max_zoom=10,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="NASA Earth Imagery", control_scale=True, world_copy_jump=False, no_wrap=True)

# Draw all hotspots with rich tooltips
for entry in hotspots:
    name, hlat, hlon, intensity, date = entry
    radius = 10 + int(intensity * 10)
    tooltip_html = f"<div style='font-family: Space Grotesk, sans-serif;'><b>{name}</b><br>Type: {active['label']}<br>Date: {date}<br>Intensity: {int(intensity*100)}%</div>"
    folium.CircleMarker(
        location=[hlat, hlon], radius=radius,
        color=active["map_color"], fill=True, fill_color=active["map_color"],
        fill_opacity=0.7, weight=2,
        tooltip=folium.Tooltip(tooltip_html, sticky=True),
    ).add_to(m)

# Selected point marker (red crosshair)
folium.Marker(
    location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
    tooltip="Selected point",
    icon=folium.Icon(color="red", icon="crosshair", prefix="fa"),
).add_to(m)

# Scene marker (orange, if scene picked from list)
if st.session_state.get("scene_lat") is not None:
    folium.Marker(
        location=[st.session_state["scene_lat"], st.session_state["scene_lon"]],
        tooltip=f"Scene: {st.session_state.get('scene_name', '')}",
        icon=folium.Icon(color="orange", icon="satellite", prefix="fa"),
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

# Selected info
st.markdown(f'<div class="info-box"><b>📍 {T["selected"]}:</b> {st.session_state["selected_lat"]:.3f}, {st.session_state["selected_lon"]:.3f} · <b>{active["icon"]} {active["label"]}</b>{"<br><i>" + st.session_state["selected_address"] + "</i>" if st.session_state.get("selected_address") else ""}</div>', unsafe_allow_html=True)

# ============================================================
# MOST SIGNIFICANT CHANGES — legend below map
# ============================================================
st.markdown(f"<p style='color:{accent}; font-weight:600; margin-top:16px;'>📌 {T['legend']} — {active['label']}:</p>", unsafe_allow_html=True)

legend_cols = st.columns(len(hotspots))
for i, entry in enumerate(hotspots):
    name, hlat, hlon, intensity, date = entry
    with legend_cols[i]:
        st.markdown(f'''
        <div style="background:{card_bg}; border-left:3px solid {active["map_color"]}; border-radius:6px; padding:10px 12px; margin:4px 0; font-size:12px; height:100%;">
            <b style="color:{active["map_color"]};">● {name}</b><br>
            <span style="color:{text_muted};">{date} · Intensity: {int(intensity*100)}%</span>
        </div>
        ''', unsafe_allow_html=True)

# STEP 4 — CHECK AVAILABILITY
st.markdown(f'<div class="section-header">4. {T["check_avail"]}</div>', unsafe_allow_html=True)
if st.button(f"🔍 {T['check_avail']}", key="check_btn", use_container_width=True):
    with st.spinner(T["checking_earthdata"]):
        try:
            r = requests.post(f"{BACKEND_URL}/search",
                json={"lat": st.session_state["selected_lat"], "lon": st.session_state["selected_lon"],
                      "start_date": str(start_date), "end_date": str(end_date)}, timeout=60)
            d = r.json()
            st.session_state["availability_count"] = d.get("count", 0)
            st.session_state["availability_scenes"] = d.get("scenes", [])
            st.session_state["availability_checked"] = True
            st.rerun()
        except Exception as e:
            st.error(f"❌ {e}")

if st.session_state["availability_checked"]:
    count = st.session_state["availability_count"]
    if count == 0:
        st.warning(f"⚠️ {T['no_data']}")
    else:
        st.success(f"✅ {count} {T['scenes_found']} — click a scene to highlight it on the map:")

        # Clickable scene list
        for i, s in enumerate(st.session_state["availability_scenes"][:10]):
            scene_name = s.get("name", "unknown")
            level = s.get("level", "?")
            date = s.get("date", "unknown")
            is_selected = st.session_state.get("scene_name") == scene_name

            btn_label = f"{'🎯 ' if is_selected else ''}{level} · {scene_name[:60]}... · {date}"
            if st.button(btn_label, key=f"scene_{i}", use_container_width=True):
                # Parse coordinates from scene name (approximate — we use the current selected point)
                st.session_state["scene_lat"] = st.session_state["selected_lat"]
                st.session_state["scene_lon"] = st.session_state["selected_lon"]
                st.session_state["scene_name"] = scene_name
                st.rerun()

        # ANALYZE
        st.markdown(f'<div class="section-header">5. {T["analyze"]}</div>', unsafe_allow_html=True)
        if st.button(f"▶  {T['analyze']}", use_container_width=True, key="analyze_btn", type="primary"):
            with st.spinner(f"🔎 {T['searching']}..."):
                try:
                    resp = requests.post(f"{BACKEND_URL}/analyze",
                        json={"lat": st.session_state["selected_lat"], "lon": st.session_state["selected_lon"],
                              "start_date": str(start_date), "end_date": str(end_date)}, timeout=30)
                    data = resp.json()
                    if "error" in data:
                        st.error(f"❌ {data['error']}")
                    else:
                        st.session_state["job_id"] = data.get("job_id")
                        st.success(f"✅ Job: `{data.get('job_id')}`")
                except Exception as e:
                    st.error(f"❌ Backend: {e}")

# RESULT
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
                progress_bar.progress(100); status_text.text("✅"); break
            elif status == "error":
                st.error(f"❌ {d.get('error', 'unknown')}"); break
        except Exception:
            time.sleep(5)

    if status == "done":
        st.markdown(f'<div class="section-header">{T["result"]}</div>', unsafe_allow_html=True)
        if st.session_state["change_type"]:
            st.markdown(f"<p style='font-size:15px;'><b>{T['type_of_change']}:</b> <span class='type-badge'>{active['icon']} {active['label']}</span></p>", unsafe_allow_html=True)
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
                st.markdown(f'<div class="explain-box"><h4 style="color:{accent}; margin:0 0 10px 0;">{T["explain_title"]}</h4><p><b>Coherence</b> — {T["explain_coherence"]}</p><p><b>Unwrapped Phase</b> — {T["explain_phase"]}</p><p><b>Surface Displacement</b> — {T["explain_displacement"]}</p></div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Image fetch failed: {e}")

st.markdown("---")
st.markdown(f'<p style="text-align:center; color:{text_muted}; font-size:12px;">NASA Space Apps Challenge · NISAR L1 GUNW · NASA Earthdata</p>', unsafe_allow_html=True)
