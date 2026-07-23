"""
GIRO Video Creator — Wizard paso a paso
=========================================
"""

import streamlit as st
import tempfile
import os
import io
import time
from PIL import Image
from moviepy import (
    ImageClip, AudioFileClip, concatenate_videoclips, vfx,
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
        font-weight: 700 !important;
    }}
    .stButton > button:hover {{ background-color: #d41f1d !important; }}
    .step-active {{
        background-color: {ROJO}; color: white; padding: 8px 16px; border-radius: 20px;
        font-weight: 700; font-size: 14px; display: inline-block;
    }}
    .step-done {{
        background-color: #22c55e; color: white; padding: 8px 16px; border-radius: 20px;
        font-weight: 700; font-size: 14px; display: inline-block;
    }}
    .step-pending {{
        background-color: #e0e0e0; color: #666; padding: 8px 16px; border-radius: 20px;
        font-weight: 700; font-size: 14px; display: inline-block;
    }}
    .photo-grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
</style>
""", unsafe_allow_html=True)

# ===== SESSION STATE =====
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'photos' not in st.session_state:
    st.session_state.photos = []  # list of (name, data, duration)
if 'music_data' not in st.session_state:
    st.session_state.music_data = None
if 'music_name' not in st.session_state:
    st.session_state.music_name = None
if 'rendered_video' not in st.session_state:
    st.session_state.rendered_video = None

# ===== HEADER =====
st.markdown(f"""
<h1 style='color:{ROJO};margin-bottom:0;font-size:28px;'>GIRO <span style='color:{GRIS};font-size:18px;font-weight:400;'>Video Creator</span></h1>
""", unsafe_allow_html=True)

# ===== STEP INDICATOR =====
steps = ["1️⃣ Fotos", "2️⃣ Duración", "3️⃣ Música", "4️⃣ Exportar"]
cols = st.columns(4)
for i, (col, label) in enumerate(zip(cols, steps)):
    with col:
        if i + 1 < st.session_state.step:
            st.markdown(f"<span class='step-done'>✓ {label}</span>", unsafe_allow_html=True)
        elif i + 1 == st.session_state.step:
            st.markdown(f"<span class='step-active'>{label}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='step-pending'>{label}</span>", unsafe_allow_html=True)

st.divider()

# ================================================================
# PASO 1: SUBIR Y ORDENAR FOTOS
# ================================================================
if st.session_state.step == 1:
    st.subheader("📸 Subí tus fotos")
    st.caption("Las fotos aparecerán en el video en el orden en que las organices.")

    uploaded = st.file_uploader(
        "Arrastrá imágenes aquí", type=["jpg","jpeg","png","webp"],
        accept_multiple_files=True, key="uploader",
        label_visibility="collapsed"
    )

    if uploaded:
        for f in uploaded:
            if not any(p[0] == f.name for p in st.session_state.photos):
                st.session_state.photos.append([f.name, f.read(), 8])

    # Mostrar fotos en orden horizontal (izquierda → derecha) con numeración clara
    if st.session_state.photos:
        st.caption(f"**{len(st.session_state.photos)} fotos** — orden de aparición en el video:")

        # Galería horizontal con números grandes
        n = len(st.session_state.photos)
        cols = st.columns(min(n, 8))

        for i in range(n):
            name, data, dur = st.session_state.photos[i]
            with cols[i]:
                # Número bien visible
                st.markdown(f"""
                <div style='background:{ROJO};color:white;width:28px;height:28px;
                border-radius:50%;display:flex;align-items:center;justify-content:center;
                font-weight:700;font-size:14px;margin:0 auto 4px auto;'>{i+1}</div>
                """, unsafe_allow_html=True)

                try:
                    img = Image.open(io.BytesIO(data))
                    st.image(img, use_container_width=True)
                except:
                    st.warning("?")
                st.caption(name[:20] + ("…" if len(name) > 20 else ""))

                # Botones de reorden
                bc1, bc2, bc3 = st.columns([1, 1, 1])
                with bc1:
                    if i > 0:
                        if st.button("◀", key=f"left_{i}", help="Mover a la izquierda"):
                            st.session_state.photos[i], st.session_state.photos[i-1] = \
                                st.session_state.photos[i-1], st.session_state.photos[i]
                            st.rerun()
                with bc2:
                    if st.button("✕", key=f"del_{i}", help="Eliminar"):
                        st.session_state.photos.pop(i)
                        st.rerun()
                with bc3:
                    if i < n - 1:
                        if st.button("▶", key=f"right_{i}", help="Mover a la derecha"):
                            st.session_state.photos[i], st.session_state.photos[i+1] = \
                                st.session_state.photos[i+1], st.session_state.photos[i]
                            st.rerun()

        # Botón siguiente
        st.divider()
        if len(st.session_state.photos) >= 2:
            if st.button("Siguiente → Duración", type="primary", use_container_width=True):
                st.session_state.step = 2
                st.rerun()
        else:
            st.info("⚠️ Necesitás al menos 2 fotos para continuar.")
    else:
        st.info("Subí tus fotos para empezar.")

# ================================================================
# PASO 2: DURACIÓN
# ================================================================
elif st.session_state.step == 2:
    st.subheader("⏱️ Duración de cada foto")

    # Duración global
    global_dur = st.radio(
        "Duración para todas las fotos:",
        [5, 8, 10], horizontal=True,
        index=1 if st.session_state.photos[0][2] == 8 else 0,
        format_func=lambda x: f"{x} segundos"
    )

    # Aplicar a todas
    for photo in st.session_state.photos:
        photo[2] = global_dur

    # Mostrar timeline con duraciones individuales
    st.caption("Duración individual (opcional):")
    for i, photo in enumerate(st.session_state.photos):
        name, data, dur = photo
        c1, c2 = st.columns([4, 1])
        with c1:
            try:
                img = Image.open(io.BytesIO(data))
                st.image(img, width=120)
                st.caption(f"**{i+1}.** {name}")
            except:
                st.caption(f"**{i+1}.** {name}")
        with c2:
            individual = st.selectbox(
                "", [5, 8, 10],
                index=[5,8,10].index(dur),
                key=f"ind_dur_{i}",
                label_visibility="collapsed"
            )
            st.session_state.photos[i][2] = individual

    # Calcular duración total estimada
    total_sec = sum(p[2] for p in st.session_state.photos)
    trans_sec = 0.8 * (len(st.session_state.photos) - 1)
    st.info(f"⏱️ Duración estimada del video: **{int(total_sec + trans_sec)} segundos**")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Volver a Fotos", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with c2:
        if st.button("Siguiente → Música", type="primary", use_container_width=True):
            st.session_state.step = 3
            st.rerun()

# ================================================================
# PASO 3: MÚSICA
# ================================================================
elif st.session_state.step == 3:
    st.subheader("🎵 Música de fondo")

    music_file = st.file_uploader(
        "Subí un archivo MP3", type=["mp3"],
        key="music_step3", label_visibility="collapsed"
    )

    if music_file:
        st.session_state.music_data = music_file.read()
        st.session_state.music_name = music_file.name
        st.success(f"✅ **{music_file.name}** cargado ({len(st.session_state.music_data)/1024:.0f} KB)")
        # Preview
        st.audio(st.session_state.music_data, format="audio/mp3")
    elif st.session_state.music_data and st.session_state.music_name:
        st.success(f"✅ **{st.session_state.music_name}** cargado")
        st.audio(st.session_state.music_data, format="audio/mp3")
    else:
        st.info("Sin música — el video se generará sin audio.")

    if st.button("🗑️ Quitar música"):
        st.session_state.music_data = None
        st.session_state.music_name = None
        st.rerun()

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Volver a Duración", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with c2:
        if st.button("Siguiente → Exportar", type="primary", use_container_width=True):
            st.session_state.step = 4
            st.session_state.rendered_video = None  # Reset
            st.rerun()

# ================================================================
# PASO 4: EXPORTAR
# ================================================================
elif st.session_state.step == 4:
    st.subheader("🎬 Exportar Video")

    # Resumen
    total_sec = sum(p[2] for p in st.session_state.photos)
    trans_sec = 0.8 * (len(st.session_state.photos) - 1)
    dur_str = f"{int(total_sec + trans_sec)}s"
    music_str = st.session_state.music_name or "Sin música"

    c1, c2, c3 = st.columns(3)
    c1.metric("Fotos", len(st.session_state.photos))
    c2.metric("Duración", dur_str)
    c3.metric("Música", music_str)

    st.divider()

    if not st.session_state.rendered_video:
        if st.button("🎬 Renderizar Video", type="primary", use_container_width=True):
            tmp_files = []
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

                # --- Transiciones fade ---
                status.text("Aplicando transiciones...")
                for i, c in enumerate(clips):
                    if i > 0:
                        c = c.with_effects([vfx.CrossFadeIn(0.8)])
                    if i < len(clips) - 1:
                        c = c.with_effects([vfx.CrossFadeOut(0.8)])
                    clips[i] = c
                progress_bar.progress(40)

                # --- Concatenar ---
                status.text("Uniendo clips...")
                video = concatenate_videoclips(clips, method="compose")
                progress_bar.progress(60)

                # --- Audio ---
                if st.session_state.music_data:
                    status.text("Agregando música...")
                    music_tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                    music_tmp.write(st.session_state.music_data)
                    music_tmp.close()
                    tmp_files.append(music_tmp.name)

                    audio = AudioFileClip(music_tmp.name)
                    if audio.duration > video.duration:
                        audio = audio.subclipped(0, video.duration)
                    video = video.with_audio(audio)
                progress_bar.progress(70)

                # --- Exportar ---
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
                    st.session_state.rendered_video = f.read()

                # Limpiar
                for fpath in tmp_files:
                    try:
                        os.unlink(fpath)
                    except:
                        pass

                progress_bar.progress(100)
                status.empty()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
                for fpath in tmp_files:
                    try:
                        os.unlink(fpath)
                    except:
                        pass

    # Mostrar resultado
    if st.session_state.rendered_video:
        file_size_mb = len(st.session_state.rendered_video) / (1024 * 1024)
        has_audio = " + música" if st.session_state.music_data else ""
        st.success(f"✅ ¡Video listo! H.264 MP4{has_audio} • {file_size_mb:.1f} MB")

        st.video(st.session_state.rendered_video)

        st.download_button(
            "⬇️ Descargar Video",
            st.session_state.rendered_video,
            file_name=f"giro_video_{int(time.time())}.mp4",
            mime="video/mp4",
            use_container_width=True,
        )

        if st.button("🔄 Reiniciar (crear otro video)", use_container_width=True):
            st.session_state.step = 1
            st.session_state.photos = []
            st.session_state.music_data = None
            st.session_state.music_name = None
            st.session_state.rendered_video = None
            st.rerun()

    # Volver
    st.divider()
    if st.button("← Volver a Música", use_container_width=True):
        st.session_state.step = 3
        st.rerun()

st.divider()
st.caption("GIRO Video Creator · H.264 + AAC garantizado · Streamlit + MoviePy")
