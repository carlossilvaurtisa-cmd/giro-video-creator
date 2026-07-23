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
GRIS_CLARO = "#f0f0f0"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp {{ font-family: 'Inter', 'Century Gothic', sans-serif; }}
    
    /* Botones primarios */
    .stButton > button {{
        background-color: {ROJO} !important; color: white !important;
        border: none !important; font-weight: 600 !important;
        border-radius: 6px !important; transition: all 0.2s !important;
    }}
    .stButton > button:hover {{ background-color: #d41f1d !important; transform: translateY(-1px); }}
    
    /* Botones secundarios (volver) */
    .stButton > button:not(:has(span)) {{ }}
    
    /* Steps */
    .step-active {{ background:{ROJO}; color:white; padding:6px 14px; border-radius:16px;
        font-weight:600; font-size:13px; display:inline-block; }}
    .step-done {{ background:#22c55e; color:white; padding:6px 14px; border-radius:16px;
        font-weight:600; font-size:13px; display:inline-block; }}
    .step-pending {{ background:#e5e5e5; color:#888; padding:6px 14px; border-radius:16px;
        font-weight:600; font-size:13px; display:inline-block; }}
    
    /* Timeline card */
    .timeline-card {{
        background: white; border: 2px solid #e0e0e0; border-radius: 8px;
        overflow: hidden; text-align: center; position: relative;
    }}
    .timeline-card.active {{ border-color: {ROJO}; }}
    .timeline-number {{
        position: absolute; top: 4px; left: 4px;
        background: {ROJO}; color: white; width: 20px; height: 20px;
        border-radius: 50%; font-size: 11px; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
        z-index: 2;
    }}
    .timeline-duration {{
        position: absolute; bottom: 4px; right: 4px;
        background: rgba(0,0,0,0.7); color: white; font-size: 10px;
        padding: 1px 6px; border-radius: 3px; font-weight: 500;
    }}
    
    /* Timeline track */
    .timeline-track {{
        background: #1a1a2e; border-radius: 6px; padding: 12px;
        display: flex; gap: 2px; overflow-x: auto;
        align-items: flex-end; min-height: 100px;
    }}
    .timeline-clip {{
        background: {ROJO}; border-radius: 4px 4px 2px 2px;
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 10px; font-weight: 600;
        cursor: pointer; transition: all 0.15s;
        min-width: 40px; position: relative;
    }}
    .timeline-clip:hover {{ filter: brightness(1.2); }}
    .timeline-gap {{
        width: 6px; background: #2d2d4a; border-radius: 2px;
        flex-shrink: 0;
    }}
</style>
""", unsafe_allow_html=True)

# ===== SESSION STATE =====
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'photos' not in st.session_state:
    st.session_state.photos = []
if 'music_data' not in st.session_state:
    st.session_state.music_data = None
if 'music_name' not in st.session_state:
    st.session_state.music_name = None
if 'rendered_video' not in st.session_state:
    st.session_state.rendered_video = None

# ===== HEADER =====
st.markdown(f"""
<h1 style='color:{ROJO};margin-bottom:0;font-size:26px;'>GIRO
<span style='color:{GRIS};font-size:17px;font-weight:400;margin-left:8px;'>Video Creator</span></h1>
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
# PASO 1: FOTOS — Timeline estilo Premiere
# ================================================================
if st.session_state.step == 1:
    st.subheader("📸 Línea de tiempo")

    uploaded = st.file_uploader(
        "Arrastrá imágenes aquí", type=["jpg","jpeg","png","webp"],
        accept_multiple_files=True, key="uploader",
        label_visibility="collapsed"
    )

    if uploaded:
        for f in uploaded:
            if not any(p[0] == f.name for p in st.session_state.photos):
                st.session_state.photos.append([f.name, f.read(), 8])

    if st.session_state.photos:
        n = len(st.session_state.photos)

        # --- Timeline visual (estilo Premiere) ---
        st.caption("Orden de aparición →")
        
        # Timeline track
        total_dur = sum(p[2] for p in st.session_state.photos)
        max_width_pct = 100

        timeline_html = '<div class="timeline-track">'
        for i, photo in enumerate(st.session_state.photos):
            dur = photo[2]
            width_pct = max(3, (dur / max(total_dur, 1)) * 80)
            timeline_html += f'<div class="timeline-clip" style="width:{width_pct}%;" title="Foto {i+1}: {photo[0]} ({dur}s)">{i+1}</div>'
            if i < n - 1:
                timeline_html += '<div class="timeline-gap"></div>'
        timeline_html += '</div>'
        st.markdown(timeline_html, unsafe_allow_html=True)

        # --- Miniaturas con controles ---
        cols = st.columns(min(n, 8))
        for i in range(n):
            name, data, dur = st.session_state.photos[i]
            with cols[i]:
                # Tarjeta compacta
                st.markdown(f"""
                <div style='position:relative;'>
                    <div style='position:absolute;top:4px;left:4px;background:{ROJO};color:white;
                    width:20px;height:20px;border-radius:50%;font-size:11px;font-weight:700;
                    display:flex;align-items:center;justify-content:center;z-index:2;'>{i+1}</div>
                    <div style='position:absolute;bottom:4px;right:4px;background:rgba(0,0,0,0.7);
                    color:white;font-size:10px;padding:1px 6px;border-radius:3px;'>{dur}s</div>
                </div>
                """, unsafe_allow_html=True)
                try:
                    img = Image.open(io.BytesIO(data))
                    st.image(img, use_container_width=True)
                except:
                    st.warning("?")
                st.caption(name[:18] + ("…" if len(name) > 18 else ""))

                # Controles compactos
                bc1, bc2, bc3 = st.columns([1, 1, 1], gap="small")
                if bc1.button("◀", key=f"l_{i}", help="Izquierda", disabled=(i==0),
                              use_container_width=True):
                    if i > 0:
                        st.session_state.photos[i], st.session_state.photos[i-1] = \
                            st.session_state.photos[i-1], st.session_state.photos[i]
                        st.rerun()
                if bc2.button("✕", key=f"d_{i}", help="Eliminar",
                              use_container_width=True):
                    st.session_state.photos.pop(i)
                    st.rerun()
                if bc3.button("▶", key=f"r_{i}", help="Derecha", disabled=(i==n-1),
                              use_container_width=True):
                    if i < n - 1:
                        st.session_state.photos[i], st.session_state.photos[i+1] = \
                            st.session_state.photos[i+1], st.session_state.photos[i]
                        st.rerun()

        st.divider()
        if n >= 2:
            if st.button("Siguiente → Duración", type="primary", use_container_width=True):
                st.session_state.step = 2
                st.rerun()
        else:
            st.info("⚠️ Necesitás al menos 2 fotos para continuar.")
    else:
        st.info("Subí tus fotos para comenzar. Se aceptan JPG, PNG y WebP.")

# ================================================================
# PASO 2: DURACIÓN
# ================================================================
elif st.session_state.step == 2:
    st.subheader("⏱️ Duración de cada clip")

    # Timeline visual de duraciones
    n = len(st.session_state.photos)
    total_dur = sum(p[2] for p in st.session_state.photos)
    
    timeline_html = '<div class="timeline-track" style="align-items:center;">'
    for i, photo in enumerate(st.session_state.photos):
        dur = photo[2]
        width_pct = max(4, (dur / 10) * 60)  # 10s max reference
        timeline_html += f'<div class="timeline-clip" style="width:{width_pct}%;" title="Foto {i+1}: {dur}s">{i+1}<br/><small>{dur}s</small></div>'
        if i < n - 1:
            timeline_html += '<div class="timeline-gap"></div>'
    timeline_html += '</div>'
    st.markdown(timeline_html, unsafe_allow_html=True)

    # Miniaturas con selector de duración
    cols = st.columns(min(n, 6))
    for i in range(n):
        name, data, dur = st.session_state.photos[i]
        with cols[i]:
            try:
                img = Image.open(io.BytesIO(data))
                st.image(img, use_container_width=True)
            except:
                st.warning("?")
            
            st.markdown(f"**{i+1}.** {name[:15]}…" if len(name)>15 else f"**{i+1}.** {name}")
            
            new_dur = st.select_slider(
                "Segundos", options=[5, 8, 10], value=dur,
                key=f"dur_{i}", label_visibility="collapsed"
            )
            st.session_state.photos[i][2] = new_dur

    # Duración total
    total = sum(p[2] for p in st.session_state.photos)
    trans = 0.8 * (n - 1)
    st.info(f"⏱️ Duración total: **{int(total + trans)} segundos** ({n} fotos × {total}s + {trans:.1f}s transiciones)")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Volver", use_container_width=True):
            st.session_state.step = 1; st.rerun()
    with c2:
        if st.button("Siguiente → Música", type="primary", use_container_width=True):
            st.session_state.step = 3; st.rerun()

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

    if st.session_state.music_data:
        st.success(f"✅ **{st.session_state.music_name}** ({len(st.session_state.music_data)/1024:.0f} KB)")
        st.audio(st.session_state.music_data, format="audio/mp3")
        if st.button("🗑️ Quitar música", use_container_width=True):
            st.session_state.music_data = None
            st.session_state.music_name = None
            st.rerun()
    else:
        st.info("Sin música. El video se generará sin audio de fondo.")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Volver", use_container_width=True):
            st.session_state.step = 2; st.rerun()
    with c2:
        if st.button("Siguiente → Exportar", type="primary", use_container_width=True):
            st.session_state.step = 4
            st.session_state.rendered_video = None
            st.rerun()

# ================================================================
# PASO 4: EXPORTAR
# ================================================================
elif st.session_state.step == 4:
    st.subheader("🎬 Exportar Video")

    total = sum(p[2] for p in st.session_state.photos)
    trans = 0.8 * (len(st.session_state.photos) - 1)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Fotos", len(st.session_state.photos))
    c2.metric("Duración", f"{int(total + trans)}s")
    c3.metric("Música", st.session_state.music_name or "Sin música")

    if st.session_state.rendered_video:
        file_size_mb = len(st.session_state.rendered_video) / (1024 * 1024)
        has_audio = " + música" if st.session_state.music_data else ""
        st.success(f"✅ ¡Video listo! H.264 MP4{has_audio} • {file_size_mb:.1f} MB")
        st.video(st.session_state.rendered_video)
        st.download_button(
            "⬇️ Descargar Video", st.session_state.rendered_video,
            file_name=f"giro_video_{int(time.time())}.mp4",
            mime="video/mp4", use_container_width=True,
        )
        st.divider()
        if st.button("🔄 Crear otro video", use_container_width=True):
            for key in ['step', 'photos', 'music_data', 'music_name', 'rendered_video']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    else:
        if st.button("🎬 Renderizar Video", type="primary", use_container_width=True):
            tmp_files = []
            try:
                progress_bar = st.progress(0)
                status = st.empty()

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

                status.text("Aplicando transiciones...")
                for i, c in enumerate(clips):
                    if i > 0:
                        c = c.with_effects([vfx.CrossFadeIn(0.8)])
                    if i < len(clips) - 1:
                        c = c.with_effects([vfx.CrossFadeOut(0.8)])
                    clips[i] = c
                progress_bar.progress(40)

                status.text("Uniendo clips...")
                video = concatenate_videoclips(clips, method="compose")
                progress_bar.progress(60)

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

                status.text("Exportando H.264 MP4 (2 Mbps)...")
                output = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                output.close()
                tmp_files.append(output.name)
                video.write_videofile(
                    output.name, codec='libx264', audio_codec='aac',
                    bitrate='2000k', fps=30, preset='medium', threads=2, logger=None,
                )
                progress_bar.progress(95)

                status.text("Preparando descarga...")
                with open(output.name, 'rb') as f:
                    st.session_state.rendered_video = f.read()

                for fpath in tmp_files:
                    try: os.unlink(fpath)
                    except: pass

                progress_bar.progress(100)
                status.empty()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
                for fpath in tmp_files:
                    try: os.unlink(fpath)
                    except: pass

    st.divider()
    if st.button("← Volver a Música", use_container_width=True):
        st.session_state.step = 3; st.rerun()

st.divider()
st.caption("GIRO Video Creator · Streamlit + MoviePy · H.264 + AAC")
