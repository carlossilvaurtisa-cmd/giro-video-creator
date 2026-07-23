"""
GIRO Video Creator — Streamlit + MoviePy
=========================================
Crea videos con transiciones fade y música. H.264 MP4 garantizado.
"""

import streamlit as st
import tempfile
import os
import io
import time
from PIL import Image
from moviepy import (
    ImageClip, AudioFileClip, concatenate_videoclips, vfx, afx,
)

# ===== CONFIG =====
st.set_page_config(page_title="GIRO | Video Creator", page_icon="🎬", layout="wide")

ROJO = "#F32624"
GRIS = "#636363"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp {{ font-family: 'Inter', 'Century Gothic', sans-serif; }}
    .stButton > button {{
        background-color: {ROJO} !important; color: white !important; border: none !important;
        font-weight: 700 !important; padding: 12px 40px !important; font-size: 16px !important;
    }}
    .stButton > button:hover {{ background-color: #d41f1d !important; }}
</style>
""", unsafe_allow_html=True)

# ===== SESSION STATE =====
if 'photos' not in st.session_state:
    st.session_state.photos = []

# ===== HEADER =====
st.markdown(f"""
<h1 style='color:{ROJO};margin-bottom:0;font-size:32px;'>GIRO</h1>
<p style='color:{GRIS};font-size:16px;border-left:3px solid {ROJO};padding-left:12px;'>Video Creator</p>
""", unsafe_allow_html=True)
st.divider()

# ===== 1. FOTOS =====
st.subheader("📸 Fotos")
uploaded = st.file_uploader(
    "Arrastrá tus fotos aquí o hacé clic", type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True, key="photo_uploader", label_visibility="collapsed"
)

if uploaded:
    for f in uploaded:
        if not any(p[0] == f.name for p in st.session_state.photos):
            st.session_state.photos.append([f.name, f.read(), 8])

if st.session_state.photos:
    st.caption(f"{len(st.session_state.photos)} foto(s) cargadas")
    cols = st.columns(min(len(st.session_state.photos), 6))
    for i, photo in enumerate(st.session_state.photos):
        name, data, dur = photo
        with cols[i % 6]:
            try:
                img = Image.open(io.BytesIO(data))
                st.image(img, use_container_width=True)
            except:
                st.warning(f"No se pudo leer: {name}")
            new_dur = st.selectbox(
                "Duración", [5, 8, 10],
                index=[5,8,10].index(dur) if dur in [5,8,10] else 1,
                key=f"dur_{i}", label_visibility="collapsed"
            )
            st.session_state.photos[i][2] = new_dur
            if st.button("✕", key=f"del_{i}"):
                st.session_state.photos.pop(i)
                st.rerun()
else:
    st.info("Subí al menos 2 fotos para comenzar.")

st.divider()

# ===== 2. AJUSTES =====
st.subheader("⚙️ Ajustes")
c1, c2 = st.columns(2)
with c1:
    trans_dur = st.selectbox("Duración de transición", [0.5, 0.8, 1.2],
                             index=1, format_func=lambda x: f"{x}s")
with c2:
    st.caption("Transición: Fade (fundido cruzado)")

st.divider()

# ===== 3. MÚSICA =====
st.subheader("🎵 Música de fondo")
music_file = st.file_uploader("Subí un MP3 (opcional)", type=["mp3"], key="music_uploader",
                               label_visibility="collapsed")
music_data = music_file.read() if music_file else None
if music_data:
    st.caption(f"✅ {music_file.name} — {len(music_data)/1024:.0f} KB")
else:
    st.caption("Sin música. El video se generará sin audio.")

st.divider()

# ===== 4. RENDER =====
can_render = len(st.session_state.photos) >= 2

st.subheader("🎬 Renderizar")

if st.button("Crear Video", disabled=not can_render, type="primary", use_container_width=True):
    if not can_render:
        st.error("Necesitás al menos 2 fotos.")
    else:
        tmp_files = []  # Para limpiar después
        try:
            progress_bar = st.progress(0)
            status = st.empty()

            # --- Preparar imágenes ---
            status.text("Preparando imágenes...")
            photo_datas = [p[1] for p in st.session_state.photos]
            durations = [p[2] for p in st.session_state.photos]

            img0 = Image.open(io.BytesIO(photo_datas[0]))
            W, H = img0.size
            max_dim = 1280
            if W >= H and W > max_dim:
                H = int(H * max_dim / W); W = max_dim
            elif H > W and H > max_dim:
                W = int(W * max_dim / H); H = max_dim
            if W % 2: W += 1
            if H % 2: H += 1

            clips = []
            for i, data in enumerate(photo_datas):
                img = Image.open(io.BytesIO(data)).resize((W, H), Image.LANCZOS)
                tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                tmp.close()
                img.save(tmp.name)
                tmp_files.append(tmp.name)
                clip = ImageClip(tmp.name, duration=durations[i])
                clips.append(clip)
                progress_bar.progress(int((i+1)/len(photo_datas)*25))

            # --- Aplicar fade-in/fade-out en cada clip ---
            status.text("Aplicando transiciones...")
            for i, c in enumerate(clips):
                if i > 0:
                    c = c.with_effects([vfx.CrossFadeIn(trans_dur)])
                if i < len(clips) - 1:
                    c = c.with_effects([vfx.CrossFadeOut(trans_dur)])
                clips[i] = c
            progress_bar.progress(40)

            # --- Concatenar ---
            status.text("Uniendo clips...")
            video = concatenate_videoclips(clips, method="compose")
            progress_bar.progress(60)

            # --- Audio ---
            if music_data:
                status.text("Agregando música...")
                music_tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                music_tmp.write(music_data)
                music_tmp.close()
                tmp_files.append(music_tmp.name)

                audio = AudioFileClip(music_tmp.name)
                if audio.duration > video.duration:
                    audio = audio.subclipped(0, video.duration)
                audio = audio.with_effects([afx.fadeout(2.5)])
                video = video.with_audio(audio)
            progress_bar.progress(70)

            # --- Exportar H.264 ---
            status.text("Exportando H.264 MP4 (2 Mbps)...")
            output = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            output.close()
            tmp_files.append(output.name)

            video.write_videofile(
                output.name,
                codec='libx264',
                audio_codec='aac',
                bitrate='2000k',
                fps=30,
                preset='medium',
                threads=2,
                logger=None,
            )
            progress_bar.progress(95)

            # --- Leer resultado ---
            status.text("Preparando descarga...")
            with open(output.name, 'rb') as f:
                video_bytes = f.read()

            # Limpiar
            for fpath in tmp_files:
                try:
                    os.unlink(fpath)
                except:
                    pass

            progress_bar.progress(100)
            status.empty()

            # --- Mostrar ---
            file_size_mb = len(video_bytes) / (1024 * 1024)
            has_audio = " + música" if music_data else ""
            st.success(f"✅ ¡Video creado! H.264 MP4{has_audio} • {W}×{H} • {file_size_mb:.1f} MB")

            st.download_button(
                "⬇️ Descargar Video",
                video_bytes,
                file_name=f"giro_video_{int(time.time())}.mp4",
                mime="video/mp4",
                use_container_width=True,
            )

            st.video(video_bytes)

        except Exception as e:
            st.error(f"Error al renderizar: {e}")
            # Limpiar temp files en caso de error
            for fpath in tmp_files:
                try:
                    os.unlink(fpath)
                except:
                    pass

st.divider()
st.caption("GIRO Video Creator · Streamlit + MoviePy · H.264 + AAC garantizado")
