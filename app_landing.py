import streamlit as st

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="EARTH IS ALIVE · NISAR Observatory",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- СТИЛИ (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

    /* Глобальный фон - глубокий космос */
    .stApp {
        background: radial-gradient(circle at 50% 50%, #0a0e1a 0%, #000000 100%);
        color: #e8ecf5;
        font-family: 'Space Grotesk', sans-serif;
    }

    /* Убираем стандартные отступы Streamlit */
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        max-width: 100%;
    }

    /* Анимация появления */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .hero-section {
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        background-image: url('https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/The_Earth_seen_from_Apollo_17.jpg/1200px-The_Earth_seen_from_Apollo_17.jpg');
        background-size: cover;
        background-position: center;
        position: relative;
        animation: fadeIn 2s ease-out;
    }

    /* Затемнение фона, чтобы текст читался */
    .hero-section::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0, 0, 0, 0.6);
        z-index: 1;
    }

    .hero-content {
        position: relative;
        z-index: 2;
        max-width: 800px;
        padding: 20px;
    }

    .hero-title {
        font-size: 4rem;
        font-weight: 700;
        line-height: 1.1;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #4a9eff 0%, #FC3D21 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }

    .hero-subtitle {
        font-size: 1.5rem;
        color: #c8d0e0;
        margin-bottom: 2rem;
        font-weight: 300;
    }

    .hero-cta {
        font-size: 1.1rem;
        padding: 15px 40px;
        background: linear-gradient(90deg, #0B3D91 0%, #FC3D21 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
        box-shadow: 0 0 20px rgba(74, 158, 255, 0.4);
    }

    .hero-cta:hover {
        transform: scale(1.05);
        box-shadow: 0 0 30px rgba(252, 61, 33, 0.6);
    }

    /* Секции ниже */
    .info-section {
        padding: 80px 20px;
        max-width: 1000px;
        margin: 0 auto;
    }

    .info-title {
        font-size: 2.5rem;
        color: #4a9eff;
        margin-bottom: 1.5rem;
        text-align: center;
    }

    .info-text {
        font-size: 1.1rem;
        line-height: 1.8;
        color: #a0a8b8;
        text-align: center;
        max-width: 800px;
        margin: 0 auto;
    }

    /* Карточки */
    .card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 20px;
        margin-top: 40px;
    }

    .feature-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(74, 158, 255, 0.2);
        border-radius: 12px;
        padding: 30px;
        transition: transform 0.3s, border-color 0.3s;
    }

    .feature-card:hover {
        transform: translateY(-5px);
        border-color: #4a9eff;
        background: rgba(74, 158, 255, 0.05);
    }

    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 15px;
    }

    .feature-title {
        font-size: 1.3rem;
        color: #ffffff;
        margin-bottom: 10px;
    }

    .feature-desc {
        font-size: 0.95rem;
        color: #8892a6;
        line-height: 1.6;
    }

    /* Футер */
    .footer {
        text-align: center;
        padding: 40px;
        color: #5a6478;
        font-size: 0.9rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)

# --- ГЛАВНЫЙ ЭКРАН (HERO) ---
st.markdown("""
<div class="hero-section">
    <div class="hero-content">
        <h1 class="hero-title">EARTH IS ALIVE.<br>WE ARE LISTENING.</h1>
    <p class="hero-subtitle">Discover how our planet changes through the eyes of NISAR.</p>
    <p style="color: #8892a6; margin-bottom: 30px;">Welcome to the Earth Observatory. Explore real satellite radar observations and discover how scientists detect changes on our planet.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Кнопка входа (Streamlit-кнопка, стилизованная через CSS)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("ENTER THE OBSERVATORY", use_container_width=True, type="primary"):
        st.switch_page("app.py") # Переход на основной рабочий сайт

# --- СЕКЦИЯ: МИССИЯ ---
st.markdown("""
<div class="info-section">
    <h2 class="info-title">What is this mission?</h2>
    <p class="info-text">
        Earth is constantly changing. Earthquakes shift the ground, glaciers flow, floods reshape landscapes, and soil moisture varies. 
        The NISAR (NASA-ISRO Synthetic Aperture Radar) mission uses advanced radar to observe these changes from space. 
        This platform allows you to explore real NISAR data and understand how our planet is evolving.
    </p>
</div>
""", unsafe_allow_html=True)

# --- СЕКЦИЯ: ЧТО МЫ МОЖЕМ ОБНАРУЖИТЬ ---
st.markdown("""
<div class="info-section">
    <h2 class="info-title">What can we discover?</h2>
    <div class="card-grid">
        <div class="feature-card">
            <div class="feature-icon">🌍</div>
            <h3 class="feature-title">Earthquakes</h3>
            <p class="feature-desc">Measure ground deformation along the radar line of sight (LOS). Detects centimeter-scale shifts caused by seismic events.</p>
            <p style="color: #27ae60; font-size: 0.8rem; margin-top: 15px; font-weight: 600;">● LIVE</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon">❄️</div>
            <h3 class="feature-title">Glaciers</h3>
            <p class="feature-desc">Track the movement of ice sheets and glaciers over time. Radar penetrates clouds and darkness to monitor polar regions.</p>
            <p style="color: #c98a00; font-size: 0.8rem; margin-top: 15px; font-weight: 600;">● COMING SOON</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🌊</div>
            <h3 class="feature-title">Floods & Wetlands</h3>
            <p class="feature-desc">Detect changes in water extent and soil moisture. Radar backscatter is highly sensitive to the presence of water.</p>
            <p style="color: #c98a00; font-size: 0.8rem; margin-top: 15px; font-weight: 600;">● COMING SOON</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- СЕКЦИЯ: КАК ЭТО РАБОТАЕТ ---
st.markdown("""
<div class="info-section">
    <h2 class="info-title">How does it work?</h2>
    <div style="display: flex; justify-content: space-around; text-align: center; margin-top: 40px; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 200px; padding: 20px;">
            <div style="font-size: 2rem; color: #4a9eff;">01</div>
            <h4 style="color: #fff;">Select Region</h4>
            <p style="color: #8892a6; font-size: 0.9rem;">Choose a location on the map.</p>
        </div>
        <div style="flex: 1; min-width: 200px; padding: 20px;">
            <div style="font-size: 2rem; color: #4a9eff;">02</div>
            <h4 style="color: #fff;">Find Data</h4>
            <p style="color: #8892a6; font-size: 0.9rem;">We search NASA ASF for available NISAR observations.</p>
        </div>
        <div style="flex: 1; min-width: 200px; padding: 20px;">
            <div style="font-size: 2rem; color: #4a9eff;">03</div>
            <h4 style="color: #fff;">Process</h4>
            <p style="color: #8892a6; font-size: 0.9rem;">Our backend downloads and analyzes the radar data.</p>
        </div>
        <div style="flex: 1; min-width: 200px; padding: 20px;">
            <div style="font-size: 2rem; color: #4a9eff;">04</div>
            <h4 style="color: #fff;">Explore</h4>
            <p style="color: #8892a6; font-size: 0.9rem;">View interferograms and quality metrics.</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- ФУТЕР ---
st.markdown("""
<div class="footer">
    <p>An independent project for NASA Space Apps Challenge 2026.</p>
    <p>Data source: NASA / ISRO NISAR Mission via ASF DAAC.</p>
    <p style="font-size: 0.8rem; color: #3a4256; margin-top: 20px;">
        "You call it home. We call it a fascinating living planet." — ZORI, Extraterrestrial Research Team
    </p>
</div>
""", unsafe_allow_html=True)
