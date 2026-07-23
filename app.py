"""
GIRO Video Creator — iOS Style · Manual de Marca 2024
"""

import streamlit as st
import tempfile, os, io, time
from PIL import Image
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, vfx

# ===== BRAND =====
ROJO    = "#F32624"
ROJO_H  = "#d41f1d"
GRIS    = "#636363"
GRIS_L  = "#f5f5f7"
GRIS_B  = "#e5e5ea"
BLANCO  = "#FFFFFF"
NEGRO   = "#1d1d1f"

st.set_page_config(page_title="GIRO Video Creator", page_icon="🎬", layout="centered")

# ===== iOS DESIGN SYSTEM =====
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    * {{ font-family: 'Inter', -apple-system, sans-serif !important; }}
    
    /* Fondo iOS */
    .stApp {{ background: {GRIS_L} !important; }}
    .main {{ max-width: 480px; margin: 0 auto; }}
    
    /* Header */
    .ios-header {{
        text-align: center; padding: 40px 0 20px 0;
    }}
    .ios-logo {{
        font-size: 34px; font-weight: 800; color: {ROJO}; letter-spacing: -1px;
    }}
    .ios-subtitle {{
        font-size: 15px; color: {GRIS}; font-weight: 400; margin-top: -4px;
    }}
    
    /* Progress dots */
    .progress-dots {{
        display: flex; justify-content: center; gap: 12px; padding: 12px 0 24px 0;
    }}
    .dot {{ width: 8px; height: 8px; border-radius: 50%; background: {GRIS_B}; transition: all 0.3s; }}
    .dot.active {{ background: {ROJO}; width: 24px; border-radius: 4px; }}
    .dot.done {{ background: {ROJO}; opacity: 0.6; }}
    
    /* Cards */
    .ios-card {{
        background: {BLANCO}; border-radius: 16px; padding: 24px;
        margin: 0 0 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    
    /* Buttons */
    .stButton > button {{
        background: {ROJO} !important; color: white !important;
        border: none !important; border-radius: 10px !important;
        font-weight: 600 !important; font-size: 15px !important;
        padding: 10px 20px !important; transition: all 0.15s !important;
        letter-spacing: -0.2px !important;
    }}
    .stButton > button:hover {{ background: {ROJO_H} !important; }}
    .stButton > button:disabled {{ background: {GRIS_B} !important; color: #999 !important; }}
    
    /* Secondary button */
    .btn-secondary > button {{
        background: {GRIS_L} !important; color: {ROJO} !important;
        border: 1.5px solid {GRIS_B} !important;
    }}
    
    /* Upload zone */
    .stFileUploader > div {{ border-radius: 14px !important; }}
    
    /* Photo cards */
    .photo-mini {{
        background: {BLANCO}; border-radius: 12px; overflow: hidden;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
        text-align: center; padding-bottom: 6px;
    }}
    .photo-badge {{
        display: inline-block; background: {ROJO}; color: white;
        width: 22px; height: 22px; border-radius: 50%;
        font-size: 12px; font-weight: 700; line-height: 22px;
        margin: 6px 0 2px 0;
    }}
    
    /* Slider */
    .stSlider > div > div > div > div {{
        background: {ROJO} !important;
    }}
    
    /* Progress bar */
    .stProgress > div > div > div > div {{
        background: {ROJO} !important;
    }}
    
    /* Radio buttons */
    .stRadio > div > label > div {{ color: {NEGRO} !important; }}
    
    /* Audio player */
    .stAudio > div {{ border-radius: 12px !important; }}
    
    /* Success message */
    .stSuccess {{ border-radius: 12px !important; }}
    
    /* Captions */
    .stCaption {{ color: {GRIS} !important; }}
    
    /* Divider thinner */
    hr {{ margin: 8px 0 !important; border-color: {GRIS_B} !important; }}
    
    /* Select slider */
    .stSelectSlider > div > div > div > div {{ background: {ROJO} !important; }}
    
    /* Compact columns */
    div[data-testid="column"] {{ padding: 0 2px !important; }}
    
    /* Small icon buttons inside photo cards */
    .stButton > button > div > p {{ font-size: 11px !important; }}
</style>
""", unsafe_allow_html=True)

# ===== SESSION =====
if 'step' not in st.session_state:       st.session_state.step = 1
if 'photos' not in st.session_state:     st.session_state.photos = []
if 'music_data' not in st.session_state: st.session_state.music_data = None
if 'music_name' not in st.session_state: st.session_state.music_name = None
if 'rendered_video' not in st.session_state: st.session_state.rendered_video = None

# ===== CENTERED CONTAINER =====
_, c, _ = st.columns([1, 3, 1])

with c:
    # ===== HEADER =====
    st.markdown(f"""
    <div class="ios-header">
        <div class="ios-logo">GIRO</div>
        <div class="ios-subtitle">Video Creator</div>
    </div>
    """, unsafe_allow_html=True)

    # ===== PROGRESS DOTS =====
    dots_html = '<div class="progress-dots">'
    for i in range(1, 5):
        cls = "active" if i == st.session_state.step else ("done" if i < st.session_state.step else "")
        dots_html += f'<div class="dot {cls}"></div>'
    dots_html += '</div>'
    st.markdown(dots_html, unsafe_allow_html=True)

    # ================================================================
    # PASO 1 — FOTOS
    # ================================================================
    if st.session_state.step == 1:
        st.markdown("### 📸 Tus fotos")
        st.caption("Agregá las imágenes en el orden que aparecerán")

        uploaded = st.file_uploader("", type=["jpg","jpeg","png","webp"],
                                     accept_multiple_files=True, key="up", label_visibility="collapsed")

        if uploaded:
            for f in uploaded:
                if not any(p[0] == f.name for p in st.session_state.photos):
                    st.session_state.photos.append([f.name, f.read(), 8])

        if st.session_state.photos:
            n = len(st.session_state.photos)
            cols = st.columns(min(n, 4))
            for i in range(n):
                name, data, dur = st.session_state.photos[i]
                with cols[i]:
                    st.markdown(f'<div class="photo-badge">{i+1}</div>', unsafe_allow_html=True)
                    try:
                        img = Image.open(io.BytesIO(data))
                        st.image(img, use_container_width=True)
                    except:
                        st.warning("?")
                    st.caption(name[:14] + ("…" if len(name) > 14 else ""))

                    b1, b2 = st.columns(2, gap="small")
                    if b1.button("◀", key=f"L{i}", disabled=(i==0), use_container_width=True):
                        if i > 0:
                            st.session_state.photos[i], st.session_state.photos[i-1] = \
                                st.session_state.photos[i-1], st.session_state.photos[i]
                            st.rerun()
                    if b2.button("✕", key=f"D{i}", use_container_width=True):
                        st.session_state.photos.pop(i); st.rerun()

        if len(st.session_state.photos) >= 2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Siguiente", type="primary", use_container_width=True):
                st.session_state.step = 2; st.rerun()
        elif st.session_state.photos:
            st.caption("Mínimo 2 fotos para continuar")

    # ================================================================
    # PASO 2 — DURACIÓN
    # ================================================================
    elif st.session_state.step == 2:
        st.markdown("### ⏱️ Duración")
        st.caption("Cuánto tiempo se muestra cada foto")

        n = len(st.session_state.photos)
        for i in range(n):
            name, data, dur = st.session_state.photos[i]
            c1, c2 = st.columns([1, 3])
            with c1:
                try:
                    img = Image.open(io.BytesIO(data))
                    st.image(img, use_container_width=True)
                except:
                    st.warning("?")
            with c2:
                st.markdown(f"**Foto {i+1}**")
                st.caption(name[:25] + ("…" if len(name) > 25 else ""))
                new_dur = st.select_slider(
                    "", options=[5, 8, 10], value=dur,
                    key=f"dur_{i}", label_visibility="collapsed"
                )
                st.session_state.photos[i][2] = new_dur

        total = sum(p[2] for p in st.session_state.photos)
        trans = 0.8 * (n - 1)
        st.caption(f"Duración total: ~{int(total + trans)} segundos")

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("Atrás", key="back2", use_container_width=True):
                st.session_state.step = 1; st.rerun()
        with c2:
            if st.button("Siguiente", type="primary", use_container_width=True):
                st.session_state.step = 3; st.rerun()

    # ================================================================
    # PASO 3 — MÚSICA
    # ================================================================
    elif st.session_state.step == 3:
        st.markdown("### 🎵 Música")
        st.caption("Agregá un MP3 de fondo (opcional)")

        music_file = st.file_uploader("", type=["mp3"], key="mu", label_visibility="collapsed")
        if music_file:
            st.session_state.music_data = music_file.read()
            st.session_state.music_name = music_file.name

        if st.session_state.music_data:
            st.audio(st.session_state.music_data, format="audio/mp3")
            st.caption(f"✅ {st.session_state.music_name} · {len(st.session_state.music_data)/1024:.0f} KB")
            if st.button("Quitar música", use_container_width=True):
                st.session_state.music_data = None
                st.session_state.music_name = None
                st.rerun()
        else:
            st.info("Sin música de fondo")

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("Atrás", key="back3", use_container_width=True):
                st.session_state.step = 2; st.rerun()
        with c2:
            if st.button("Siguiente", type="primary", use_container_width=True):
                st.session_state.step = 4
                st.session_state.rendered_video = None
                st.rerun()

    # ================================================================
    # PASO 4 — EXPORTAR
    # ================================================================
    elif st.session_state.step == 4:
        if st.session_state.rendered_video:
            st.markdown("### ✅ ¡Listo!")
            size_mb = len(st.session_state.rendered_video) / (1024 * 1024)
            has_audio = " + música" if st.session_state.music_data else ""
            st.success(f"H.264 MP4{has_audio} · {size_mb:.1f} MB")
            st.video(st.session_state.rendered_video)
            st.download_button("Descargar Video", st.session_state.rendered_video,
                               f"giro_video_{int(time.time())}.mp4", "video/mp4",
                               use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Crear otro video", use_container_width=True):
                for k in ['step','photos','music_data','music_name','rendered_video']:
                    if k in st.session_state: del st.session_state[k]
                st.rerun()
        else:
            st.markdown("### 🎬 Exportar")
            total = sum(p[2] for p in st.session_state.photos)
            trans = 0.8 * (len(st.session_state.photos) - 1)
            music = st.session_state.music_name or "Sin música"
            
            st.markdown(f"""
            <div class="ios-card">
                <table style="width:100%;font-size:15px;">
                <tr><td style="color:{GRIS};">📸 Fotos</td><td style="font-weight:600;">{len(st.session_state.photos)}</td></tr>
                <tr><td style="color:{GRIS};">⏱️ Duración</td><td style="font-weight:600;">~{int(total+trans)}s</td></tr>
                <tr><td style="color:{GRIS};">🎵 Música</td><td style="font-weight:600;">{music}</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Renderizar Video", type="primary", use_container_width=True):
                tmp_files = []
                try:
                    progress_bar = st.progress(0)
                    status = st.empty()

                    photo_datas = [p[1] for p in st.session_state.photos]
                    durations = [p[2] for p in st.session_state.photos]

                    img0 = Image.open(io.BytesIO(photo_datas[0]))
                    W, H = img0.size
                    max_dim = 1280
                    if W >= H and W > max_dim: H = int(H * max_dim / W); W = max_dim
                    elif H > W and H > max_dim: W = int(W * max_dim / H); H = max_dim
                    if W % 2: W += 1
                    if H % 2: H += 1

                    clips = []
                    for i, data in enumerate(photo_datas):
                        status.text(f"Foto {i+1}/{len(photo_datas)}")
                        img = Image.open(io.BytesIO(data)).resize((W, H), Image.LANCZOS)
                        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                        tmp.close(); img.save(tmp.name); tmp_files.append(tmp.name)
                        clips.append(ImageClip(tmp.name, duration=durations[i]))
                        progress_bar.progress(int((i+1)/len(photo_datas)*25))

                    for i, c in enumerate(clips):
                        if i > 0: c = c.with_effects([vfx.CrossFadeIn(0.8)])
                        if i < len(clips)-1: c = c.with_effects([vfx.CrossFadeOut(0.8)])
                        clips[i] = c
                    progress_bar.progress(40)

                    status.text("Uniendo...")
                    video = concatenate_videoclips(clips, method="compose")
                    progress_bar.progress(60)

                    if st.session_state.music_data:
                        status.text("Agregando música...")
                        music_tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                        music_tmp.write(st.session_state.music_data); music_tmp.close()
                        tmp_files.append(music_tmp.name)
                        audio = AudioFileClip(music_tmp.name)
                        if audio.duration > video.duration:
                            audio = audio.subclipped(0, video.duration)
                        video = video.with_audio(audio)
                    progress_bar.progress(70)

                    status.text("Exportando H.264 MP4...")
                    output = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                    output.close(); tmp_files.append(output.name)
                    video.write_videofile(output.name, codec='libx264', audio_codec='aac',
                                          bitrate='2000k', fps=30, preset='medium',
                                          threads=2, logger=None)
                    progress_bar.progress(95)

                    with open(output.name, 'rb') as f:
                        st.session_state.rendered_video = f.read()

                    for fp in tmp_files:
                        try: os.unlink(fp)
                        except: pass

                    progress_bar.progress(100); status.empty()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    for fp in tmp_files:
                        try: os.unlink(fp)
                        except: pass

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Atrás", key="back4", use_container_width=True):
                st.session_state.step = 3; st.rerun()

    # ===== FOOTER =====
    st.divider()
    st.caption("GIRO · Manual de Marca 2024")
