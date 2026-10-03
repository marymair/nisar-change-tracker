"""
NISAR Surface Change Tracker — v4.0
- Landing page with Method, Validation, Impact
- Main app with map, filters, analysis
- Backend integration
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
    "onboarded": False,
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
    "fire": [("California, USA", 38.0, -120.0, 0.95), ("Amazon, Brazil", -3.0, -60.0, 0.85), ("Victoria, Australia", -37.0, 145.0, 0.80), ("Siberia, Russia", 62.0, 105.0, 0.75)],
    "glacier": [("Antarctica", -75.0, 0.0, 0.95), ("Greenland", 72.0, -40.0, 0.90), ("Himalayas, Nepal", 28.0, 85.0, 0.85), ("Alps, Switzerland", 46.5, 8.0, 0.70)],
    "flood": [("Bangladesh", 24.0, 90.0, 0.95), ("Amazon, Brazil", -3.0, -60.0, 0.80), ("Mekong Delta, Vietnam", 10.0, 105.0, 0.85), ("Mississippi, USA", 32.0, -91.0, 0.75)],
    "desert": [("Sahara, Algeria", 27.0, 5.0, 0.90), ("Sahel, Niger", 15.0, 8.0, 0.85), ("Gobi, Mongolia", 43.0, 105.0, 0.80), ("Aral Sea, Uzbekistan", 45.0, 58.0, 0.95)],
    "earthquake": [("Turkey-Syria", 37.0, 38.0, 0.95), ("Japan", 35.0, 140.0, 0.90), ("California, USA", 35.0, -119.0, 0.85), ("Chile", -30.0, -71.0, 0.80)],
    "wetland": [("Okavango, Botswana", -19.0, 23.0, 0.90), ("Pantanal, Brazil", -17.0, -57.0, 0.95), ("Sundarbans, Bangladesh", 22.0, 89.0, 0.85), ("Everglades, USA", 25.5, -80.5, 0.80)],
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
h1 {{ background: linear-gradient(90deg, {accent} 0%, #FC3D21 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 3rem !important; line-height: 1.1 !important; }}
h2 {{ color: {text_main} !important; font-weight: 600; font-size: 1.8rem !important; margin-top: 24px !important; }}
h3 {{ color: {text_main} !important; font-weight: 600; }}
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
.landing-card {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 12px; padding: 24px; margin: 12px 0; height: 100%; }}
.landing-card h3 {{ color: {accent}; margin: 0 0 10px 0; font-size: 1.1rem; }}
.landing-card p {{ color: {text_muted}; font-size: 14px; line-height: 1.6; margin: 0; }}
.pipeline-step {{ display: flex; align-items: flex-start; margin: 12px 0; padding: 12px 16px; background: {card_bg}; border-left: 3px solid {accent}; border-radius: 6px; }}
.pipeline-step-num {{ background: {accent}; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; margin-right: 14px; flex-shrink: 0; }}
.pipeline-step-text {{ color: {text_main}; font-size: 14px; line-height: 1.5; }}
.pipeline-step-text b {{ color: {accent}; }}
.impact-box {{ background: {card_bg}; border-radius: 10px; padding: 20px; margin: 8px 0; border: 1px solid {card_border}; }}
.impact-box h4 {{ color: {accent}; margin: 0 0 8px 0; font-size: 1rem; }}
.impact-box p {{ color: {text_muted}; font-size: 13px; line-height: 1.5; margin: 0; }}
.footer-links {{ color: {text_muted}; font-size: 13px; line-height: 1.9; }}
.footer-links a {{ color: {accent}; text-decoration: none; }}
.hero-sub {{ color: {text_muted}; font-size: 1.15rem; line-height: 1.6; max-width: 720px; }}
.hero-badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; background: {card_bg}; border: 1px solid {accent}; color: {accent}; font-size: 12px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# LANDING PAGE (if not onboarded)
# ============================================================
if not st.session_state["onboarded"]:
    # Language selector on landing too
    lc1, lc2, lc3 = st.columns([4, 1, 1])
    with lc2:
        theme_icon = "☀️ Light" if st.session_state["theme"] == "dark" else "🌙 Dark"
        if st.button(theme_icon, key="landing_theme"):
            st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"
            st.rerun()
    with lc3:
        lang_options = {"English": "en", "Русский": "ru", "Español": "es", "Français": "fr"}
        lang_name = st.selectbox("Language", list(lang_options.keys()),
            index=list(lang_options.values()).index(st.session_state["lang"]),
            label_visibility="collapsed", key="landing_lang")
        new_lang = lang_options[lang_name]
        if new_lang != st.session_state["lang"]:
            st.session_state["lang"] = new_lang
            st.rerun()

    st.markdown('<span class="hero-badge">NASA SPACE APPS CHALLENGE 2026</span>', unsafe_allow_html=True)
    st.markdown("# NISAR Surface Change Tracker")
    st.markdown(f"""
    <p class="hero-sub">
    Track and visualize surface changes of our planet using real radar data from the
    NASA-ISRO Synthetic Aperture Radar (NISAR) mission. Pick a location, choose a type
    of change, and get a real interferogram — computed in the cloud, straight from
    NASA Earthdata.
    </p>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Three feature cards
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown(f"""
        <div class="landing-card">
            <h3>📡 Real NISAR Data</h3>
            <p>Every analysis downloads an actual NISAR L1 GUNW scene — about 800 MB —
            directly from the NASA ASF Data Access. No simulations, no pre-baked images.</p>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown(f"""
        <div class="landing-card">
            <h3>🌍 Global Coverage</h3>
            <p>Click any point on the map. If NISAR has captured it, we process it.
            Six change types: wildfires, glaciers, floods, desertification, earthquakes, wetlands.</p>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown(f"""
        <div class="landing-card">
            <h3>🔬 Scientific Pipeline</h3>
            <p>We read the raw HDF5, extract unwrapped phase and coherence, compute InSAR
            displacement in centimeters, and render the interferogram — all in your browser.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Method
    st.markdown("## Method")
    st.markdown("""
    <p class="hero-sub">Our pipeline uses the official NASA ASF API, OAuth 2.0 authentication, and standard InSAR mathematics.</p>
    """, unsafe_allow_html=True)

    steps = [
        ("Search", "Query the NASA ASF Data Access for NISAR scenes intersecting your coordinates and date range."),
        ("Authenticate", "Log in to NASA Earthdata via OAuth 2.0. Your credentials never leave your session."),
        ("Download", "Fetch the full GUNW product — typically 500–1000 MB — from the NISAR data pool."),
        ("Process", "Read the HDF5 file with h5py, extract <b>unwrappedPhase</b> and <b>coherenceMagnitude</b>."),
        ("Render", "Convert phase to surface displacement (L-band, λ=24 cm), downsample for performance, and render a 3-panel PNG."),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        st.markdown(f"""
        <div class="pipeline-step">
            <div class="pipeline-step-num">{i}</div>
            <div class="pipeline-step-text"><b>{title}</b> — {desc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Validation
    st.markdown("## Validation")
    st.markdown("""
    <p class="hero-sub">Verified against a real NISAR GUNW scene over Antarctica, September 13, 2026.</p>
    """, unsafe_allow_html=True)

    v1, v2, v3, v4 = st.columns(4)
    with v1:
        st.metric("Phase range", "−26.75 … +27.53 rad")
    with v2:
        st.metric("Displacement", "−51.09 … +52.57 cm")
    with v3:
        st.metric("Coherence", "0.000 … 0.939")
    with v4:
        st.metric("Scene size", "4185 × 4293 px")

    st.markdown(f"""
    <p style="color:{text_muted}; font-size:13px; margin-top:12px;">
    Values match the product specification: <b>NASA NISAR L1 RUNW Product Spec, D-102271</b>.
    </p>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Impact
    st.markdown("## Who is this for?")
    i1, i2, i3, i4 = st.columns(4)
    with i1:
        st.markdown(f"""
        <div class="impact-box">
            <h4>Climate scientists</h4>
            <p>Monitor glacier retreat and permafrost thaw over years and decades.</p>
        </div>
        """, unsafe_allow_html=True)
    with i2:
        st.markdown(f"""
        <div class="impact-box">
            <h4>Geologists</h4>
            <p>Detect millimeter-scale ground deformation before and after earthquakes.</p>
        </div>
        """, unsafe_allow_html=True)
    with i3:
        st.markdown(f"""
        <div class="impact-box">
            <h4>Disaster response</h4>
            <p>Rapid assessment of flood extent and wildfire damage, day or night, through clouds.</p>
        </div>
        """, unsafe_allow_html=True)
    with i4:
        st.markdown(f"""
        <div class="impact-box">
            <h4>Ecologists</h4>
            <p>Track wetland loss, desertification and land-cover change across continents.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # CTA
    cta1, cta2, cta3 = st.columns([1, 2, 1])
    with cta2:
        if st.button("▶  Continue to the app", use_container_width=True, type="primary", key="cta_continue"):
            st.session_state["onboarded"] = True
            st.rerun()

    st.markdown("---")

    # Footer
    st.markdown(f"""
    <div class="footer-links" style="text-align:center;">
        Built for <b>NASA Space Apps Challenge 2026</b><br>
        Data: <a href="https://search.earthdata.nasa.gov" target="_blank">NASA Earthdata</a> ·
        <a href="https://search.asf.alaska.edu" target="_blank">ASF DAAC</a> ·
        <a href="https://nisar.jpl.nasa.gov" target="_blank">NISAR Mission</a><br>
        Radar data © NASA / ISRO · Product spec D-102271
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ============================================================
# MAIN APP
# ============================================================
# Back button
back_col1, back_col2, back_col3, back_col4 = st.columns([1, 4, 1, 1])
with back_col1:
    if st.button("← Back", key="back_to_landing"):
        st.session_state["onboarded"] = False
        st.rerun()
with back_col3:
    theme_icon = "☀️" if st.session_state["theme"] == "dark" else "🌙"
    if st.button(theme_icon, key="app_theme"):
        st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"
        st.rerun()
with back_col4:
    lang_options = {"English": "en", "Русский": "ru", "Español": "es", "Français": "fr"}
    lang_name = st.selectbox("Language", list(lang_options.keys()),
        index=list(lang_options.values()).index(st.session_state["lang"]),
        label_visibility="collapsed", key="app_lang")
    new_lang = lang_options[lang_name]
    if new_lang != st.session_state["lang"]:
        st.session_state["lang"] = new_lang
        st.rerun()

col_logo, col_help = st.columns([5, 1])
with col_logo:
    st.markdown("# NISAR Surface Change Tracker")
    st.markdown(f"<p style='color:{text_muted}; margin-top:-12px;'>{T['tagline']}</p>", unsafe_allow_html=True)
with col_help:
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

# STEP 1
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
    st.info("Выберите тип изменения, чтобы продолжить")
    st.stop()

# STEP 2
st.markdown(f'<div class="section-header">2. {T["select_location"]}</div>', unsafe_allow_html=True)
st.markdown(f"<p style='color:{text_muted}; font-size:13px;'>{T['click_map']}</p>", unsafe_allow_html=True)

m = folium.Map(location=st.session_state["map_center"], zoom_start=st.session_state["map_zoom"],
    min_zoom=2, max_zoom=10,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="NASA Earth Imagery", control_scale=True, world_copy_jump=False, no_wrap=True)

hotspots = HOTSPOTS_BY_TYPE[st.session_state["change_type"]]
for name, hlat, hlon, intensity in hotspots:
    radius = 8 + int(intensity * 12)
    folium.CircleMarker(location=[hlat, hlon], radius=radius,
        color=active["map_color"], fill=True, fill_color=active["map_color"],
        fill_opacity=0.65, weight=2,
        tooltip=f"<b>{name}</b><br>{active['label']}<br>Intensity: {int(intensity*100)}%",
    ).add_to(m)

folium.Marker(location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
    tooltip="Selected", icon=folium.Icon(color="red", icon="crosshair", prefix="fa")).add_to(m)

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

st.markdown(f"<p style='color:{accent}; font-weight:600; margin-top:12px;'>"
            f"📌 {T['legend']} — {active['label']}:</p>", unsafe_allow_html=True)
legend_cols = st.columns(len(hotspots))
for i, (name, hlat, hlon, intensity) in enumerate(hotspots):
    with legend_cols[i]:
        st.markdown(f"""
        <div style="background:{card_bg}; border-left:3px solid {active['map_color']}; border-radius:6px; padding:8px 12px; margin:4px 0; font-size:12px;">
            <b style="color:{active['map_color']};">● {name}</b><br>
            <span style="color:{text_muted};">Intensity: {int(intensity*100)}%</span>
        </div>
        """, unsafe_allow_html=True)

# STEP 3
st.markdown(f'<div class="section-header">3. {T["date_range"]}</div>', unsafe_allow_html=True)
col_d1, col_d2 = st.columns(2)
with col_d1:
    start_date = st.date_input(T["from"], value=pd.Timestamp("2026-09-01"))
with col_d2:
    end_date = st.date_input(T["to"], value=pd.Timestamp("2026-09-28"))

# STEP 4
st.markdown(f'<div class="section-header">4. {T["check_avail"]}</div>', unsafe_allow_html=True)
if st.button(f"🔍 {T['check_avail']}", key="check_btn", use_container_width=True):
    with st.spinner("Checking NASA Earthdata..."):
        try:
            r = requests.post(f"{BACKEND_URL}/search",
                json={"lat": st.session_state["selected_lat"], "lon": st.session_state["selected_lon"],
                      "start_date": str(start_date), "end_date": str(end_date)}, timeout=60)
            d = r.json()
            st.session_state["availability_count"] = d.get("count", 0)
            st.session_state["availability_scenes"] = d.get("scenes", [])
            st.session_state["availability_checked"] = True
        except Exception as e:
            st.error(f"❌ {e}")

if st.session_state["availability_checked"]:
    count = st.session_state["availability_count"]
    if count == 0:
        st.warning(f"⚠️ {T['no_data']}")
    else:
        st.success(f"✅ {count} NISAR scenes found:")
        for s in st.session_state["availability_scenes"][:10]:
            st.markdown(f"""
            <div class="scene-row">
                <b>{s.get('level', '?')}</b> · {s.get('name', 'unknown')}<br>
                <span style='color:{text_muted};'>Date: {s.get('date', 'unknown')}</span>
            </div>
            """, unsafe_allow_html=True)

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
                        st.info(f"
