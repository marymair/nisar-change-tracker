import streamlit as st
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import io
from translations import TEXTS

try:
    from streamlit_folium import st_folium
    import folium
    HAS_MAP = True
except ImportError:
    HAS_MAP = False

st.set_page_config(page_title="NISAR Change Tracker", page_icon="🛰️", layout="wide")

lang_options = {"English": "en", "Русский": "ru", "Español": "es", "Français": "fr"}
with st.sidebar:
    lang_name = st.selectbox("🌐 Language / Язык / Idioma / Langue", list(lang_options.keys()))
    lang = lang_options[lang_name]

T = TEXTS[lang]

st.title(T["title"])
st.caption(T["subtitle"])
st.warning(T["warning"])

with st.sidebar:
    st.header(T["settings"])
    change_type = st.selectbox(
        T["change_type"],
        [T["fire"], T["glacier"], T["flood"], T["desert"], T["wetland"], T["earthquake"]]
    )
    st.subheader(T["dates"])
    date_from = st.date_input(T["date_from"])
    date_to = st.date_input(T["date_to"])
    palette = st.selectbox(T["palette"], ["seismic", "RdYlGn_r", "coolwarm", "viridis"])
    threshold = st.slider(T["threshold"], 0, 100, 15)
    show_stats = st.checkbox(T["show_stats"], value=True)

# ============ КАРТА ============
st.subheader(T["map_title"])
st.caption(T["map_hint"])

if HAS_MAP:
    m = folium.Map(
        location=[45.0, 58.5],
        zoom_start=4,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="NASA Earth Imagery / Esri"
    )
    folium.Marker([45.0, 58.5], tooltip="Aral Sea (example)").add_to(m)
    map_data = st_folium(m, height=400, use_container_width=True, key="world_map")

    if map_data and map_data.get("last_clicked"):
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]
        st.success(f"{T['selected_coords']}: {lat:.4f}, {lon:.4f}")
else:
    st.info("Install streamlit-folium to enable the interactive map.")

st.divider()

# ============ ЗАГРУЗКА ФАЙЛОВ ============
st.subheader(T["upload_section"])
col1, col2 = st.columns(2)
with col1:
    f1 = st.file_uploader(T["upload_1"], type=["jpg", "jpeg", "png"])
with col2:
    f2 = st.file_uploader(T["upload_2"], type=["jpg", "jpeg", "png"])

# ============ АНАЛИЗ ============
if f1 and f2:
    img_before = np.array(Image.open(f1).convert("L"), dtype=np.float32)
    img_after = np.array(Image.open(f2).convert("L"), dtype=np.float32)

    h = min(img_before.shape[0], img_after.shape[0])
    w = min(img_before.shape[1], img_after.shape[1])
    a = img_before[:h, :w]
    b = img_after[:h, :w]

    diff = b - a
    max_abs = np.max(np.abs(diff)) or 1.0
    change = diff / max_abs

    st.subheader(T["results"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.image(a, caption=T["date_1"], clamp=True, use_container_width=True)
    with c2:
        st.image(b, caption=T["date_2"], clamp=True, use_container_width=True)
    with c3:
        fig, ax = plt.subplots()
        im = ax.imshow(change, cmap=palette, vmin=-1, vmax=1)
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.046)
        st.pyplot(fig)

    if show_stats:
        mask = np.abs(change) > (threshold / 100.0)
        pct = (mask.sum() / mask.size) * 100
        s1, s2, s3 = st.columns(3)
        s1.metric(T["changed_area"], f"{pct:.1f}%")
        s2.metric(T["mean_change"], f"{change.mean():.3f}")
        s3.metric(T["max_change"], f"{change.max:.3f}")

    buf = io.BytesIO()
    plt.imsave(buf, change, cmap=palette, format="png")
    st.download_button(T["download"], buf.getvalue(), "change_map.png", "image/png")

else:
    st.info(T["info"])

st.divider()
st.caption(T["footer"])
