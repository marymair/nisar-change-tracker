"""
NISAR Surface Change Tracker — Streamlit frontend.
3D globe, filters, backend integration via Railway API.
"""
import streamlit as st
import pydeck as pdk
import pandas as pd
import requests
import time
from PIL import Image
from io import BytesIO

# ============================================================
# CONFIG
# ============================================================
BACKEND_URL = "https://nisar-backend-production-feb6.up.railway.app"

st.set_page_config(
    page_title="NISAR Surface Change Tracker",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CUSTOM CSS — NASA style + Space Grotesk
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: #0a0e1a;
    color: #e8ecf5;
}

.stApp {
    background: linear-gradient(180deg, #0a0e1a 0%, #0f1424 50%, #0a0e1a 100%);
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    letter-spacing: -0.02em;
}

h1 {
    background: linear-gradient(90deg, #4a9eff 0%, #FC3D21 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5rem !important;
}

.stButton > button {
    background: linear-gradient(90deg, #0B3D91 0%, #FC3D21 100%);
    color: white;
    border: none;
    padding: 14px 32px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 16px;
    border-radius: 8px;
    box-shadow: 0 0 20px rgba(74, 158, 255, 0.3);
    transition: all 0.3s ease;
    width: 100%;
}

.stButton > button:hover {
    box-shadow: 0 0 30px rgba(252, 61, 33, 0.5);
    transform: translateY(-2px);
}

.stSelectbox label, .stDateInput label, .stSlider label {
    color: #8892a6 !important;
    font-size: 13px !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

div[data-testid="stMetricValue"] {
    font-family: 'Space Grotesk', sans-serif;
    color: #4a9eff;
    font-size: 1.8rem;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
col_logo, col_lang = st.columns([4, 1])
with col_logo:
    st.markdown("# 🛰️ NISAR Surface Change Tracker")
    st.markdown("<p style='color:#8892a6; margin-top:-15px;'>NASA-ISRO SAR Mission · Real-time surface change analysis</p>", unsafe_allow_html=True)
with col_lang:
    lang = st.selectbox("🌐 Language", ["English", "Русский", "Español", "Français"], label_visibility="collapsed")

# ============================================================
# FILTERS — Type of change
# ============================================================
st.markdown("### 🎯 Type of change")
CHANGE_TYPES = [
    ("🔥", "Wildfires"),
    ("🏔️", "Glaciers"),
    ("🌊", "Floods"),
    ("🏜️", "Desertification"),
    ("🌍", "Earthquakes"),
    ("🌿", "Wetlands"),
]

cols = st.columns(6)
selected_type = None
for i, (icon, name) in enumerate(CHANGE_TYPES):
    with cols[i]:
        if st.button(f"{icon} {name}", key=f"type_{name}", use_container_width=True):
            st.session_state["change_type"] = name

if "change_type" not in st.session_state:
    st.session_state["change_type"] = "Glaciers"

st.markdown(f"<p style='color:#4a9eff; text-align:center;'>Selected: <b>{st.session_state['change_type']}</b></p>", unsafe_allow_html=True)

# ============================================================
# 3D GLOBE
# ============================================================
st.markdown("### 🌍 Select a location")

# Initialize selected coordinates
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = -75.0
    st.session_state["selected_lon"] = 0.0

# Sample reference points (where NISAR has known data)
REFERENCE_POINTS = pd.DataFrame({
    "name": ["Antarctica", "Himalayas", "Amazon", "California", "Greenland"],
    "lat": [-75.0, 28.0, -3.0, 38.0, 72.0],
    "lon": [0.0, 85.0, -60.0, -120.0, -40.0],
    "color": [[74, 158, 255]] * 5,
})

# Build the globe with pydeck
view_state = pdk.ViewState(
    latitude=20,
    longitude=0,
    zoom=1.5,
    pitch=0,
)

scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=REFERENCE_POINTS,
    get_position=["lon", "lat"],
    get_color="color",
    get_radius=200000,
    pickable=True,
)

r = pdk.Deck(
    layers=[scatter_layer],
    initial_view_state=view_state,
    map_style=None,
    tooltip={"text": "{name}"},
)

# Show globe (2D projection as fallback for now)
st.pydeck_chart(r, use_container_width=True)

# Manual coordinate input as fallback
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    lat = st.number_input("Latitude", value=st.session_state["selected_lat"], format="%.2f")
with col2:
    lon = st.number_input("Longitude", value=st.session_state["selected_lon"], format="%.2f")
with col3:
    st.markdown("**Quick select:**")
    quick_cols = st.columns(5)
    for i, row in REFERENCE_POINTS.iterrows():
        with quick_cols[i]:
            if st.button(row["name"][:8], key=f"quick_{row['name']}"):
                st.session_state["selected_lat"] = row["lat"]
                st.session_state["selected_lon"] = row["lon"]
                st.rerun()

# ============================================================
# DATE RANGE
# ============================================================
st.markdown("### 📅 Date range")
col_d1, col_d2 = st.columns(2)
with col_d1:
    start_date = st.date_input("From", value=pd.Timestamp("2026-09-01"))
with col_d2:
    end_date = st.date_input("To", value=pd.Timestamp("2026-09-28"))

# ============================================================
# ANALYZE BUTTON
# ============================================================
st.markdown("---")
if st.button("▶️  ANALYZE THIS LOCATION", use_container_width=True):
    with st.spinner("🔎 Searching NISAR scenes on NASA Earthdata..."):
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
                job_id = data.get("job_id")
                scene_name = data.get("scene_name", "")
                st.session_state["job_id"] = job_id
                st.session_state["scene_name"] = scene_name
                st.success(f"✅ Job started: `{job_id}`")
                st.info(f"📡 Scene: {scene_name}")
        except Exception as e:
            st.error(f"❌ Backend connection failed: {e}")

# ============================================================
# RESULT PANEL
# ============================================================
if "job_id" in st.session_state:
    job_id = st.session_state["job_id"]

    st.markdown("### ⏳ Processing...")
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Poll status
    for i in range(60):  # up to 5 minutes
        try:
            status_resp = requests.get(f"{BACKEND_URL}/status/{job_id}", timeout=10)
            status_data = status_resp.json()
            status = status_data.get("status", "unknown")

            if status == "processing":
                progress_bar.progress(min((i + 1) * 2, 95))
                status_text.text(f"⏳ {status_data.get('scene_name', 'Processing...')}")
                time.sleep(5)
            elif status == "done":
                progress_bar.progress(100)
                status_text.text("✅ Analysis complete!")
                break
            elif status == "error":
                st.error(f"❌ Error: {status_data.get('error', 'unknown')}")
                break
        except Exception as e:
            st.warning(f"Polling error: {e}")
            time.sleep(5)

    # Show result image
    if status == "done":
        st.markdown("### 🖼️ Result")
        try:
            img_resp = requests.get(f"{BACKEND_URL}/image/{job_id}", timeout=30)
            if img_resp.status_code == 200:
                img = Image.open(BytesIO(img_resp.content))
                st.image(img, use_container_width=True)

                st.download_button(
                    "⬇️  Download PNG",
                    data=img_resp.content,
                    file_name=f"nisar_{job_id}.png",
                    mime="image/png",
                )

                stats = status_data.get("stats", {})
                if stats:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Phase min", f"{stats.get('phase_min', 0):.2f} rad")
                    c2.metric("Phase max", f"{stats.get('phase_max', 0):.2f} rad")
                    c3.metric("Displacement min", f"{stats.get('disp_min_cm', 0):.2f} cm")
                    c4.metric("Displacement max", f"{stats.get('disp_max_cm', 0):.2f} cm")
            else:
                st.error(f"Could not fetch image: {img_resp.status_code}")
        except Exception as e:
            st.error(f"Image fetch failed: {e}")

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#8892a6; font-size:12px;'>"
    "Built for NASA Space Apps Challenge · Data: NISAR L1 GUNW · Powered by NASA Earthdata"
    "</p>",
    unsafe_allow_html=True,
)
