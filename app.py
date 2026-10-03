"""
NISAR Surface Change Tracker — v6.1
- All strings via translations (no hardcode)
- Removed manual "Check availability" button
- Clickable legend hotspots → map markers
- Selected scene stays highlighted with 🎯 + tooltip shows address
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

defaults = {
    "lang": "en", "change_type": None,
    "selected_lat": -75.0, "selected_lon": 0.0, "selected_address": "",
    "scene_lat": None, "scene_lon": None, "scene_name": None, "scene_address": None,
    "show_help": False, "job_id": None, "theme": "dark",
    "availability_checked": False, "availability_count": None, "availability_scenes": [],
    "onboarded": False,
    "regions_results": [], "auto_check_done_for": None,
    "hotspot_lat": None, "hotspot_lon": None, "hotspot_name": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def toggle_theme(): st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"
def toggle_help(): st.session_state["show_help"] = not st.session_state["show_help"]
def go_to_app(): st.session_state["onboarded"] = True
def go_to_landing(): st.session_state["onboarded"] = False

def set_change_type(key):
    if st.session_state["change_type"] != key:
        st.session_state["change_type"] = key
        st.session_state["availability_checked"] = False
        st.session_state["availability_count"] = None
        st.session_state["availability_scenes"] = []
        st.session_state["regions_results"] = []
        st.session_state["auto_check_done_for"] = None
        st.session_state["scene_lat"] = None
        st.session_state["scene_lon"] = None
        st.session_state["scene_name"] = None
        st.session_state["hotspot_lat"] = None
        st.session_state["hotspot_lon"] = None
        st.session_state["hotspot_name"] = None
        st.session_state["job_id"] = None

def select_scene(name, lat, lon):
    st.session_state["scene_name"] = name
    st.session_state["scene_lat"] = lat
    st.session_state["scene_lon"] = lon
    try:
        geolocator = Nominatim(user_agent="nisar_tracker")
        loc = geolocator.reverse(f"{lat}, {lon}", timeout=5)
        st.session_state["scene_address"] = loc.address if loc else "Remote area"
    except Exception:
        st.session_state["scene_address"] = f"{lat:.3f}, {lon:.3f}"

def select_hotspot(name, lat, lon):
    st.session_state["hotspot_name"] = name
    st.session_state["hotspot_lat"] = lat
    st.session_state["hotspot_lon"] = lon

# LANGUAGE
lang_options = {"English": "en", "Русский": "ru", "Español": "es", "Français": "fr"}
lang_name = st.selectbox("🌐 Language", list(lang_options.keys()),
    index=list(lang_options.values()).index(st.session_state["lang"]),
    key="lang_selector", label_visibility="collapsed")
T = TEXTS[st.session_state["lang"]]

# CHANGE TYPES
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
    "earthquake": [("Turkey-Syria", 37.
