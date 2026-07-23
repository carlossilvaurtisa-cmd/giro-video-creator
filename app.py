"""
GIRO Video Creator — Flask + MoviePy
=====================================
"""
import os, uuid, shutil, time, tempfile, json
from flask import Flask, render_template, request, jsonify, send_file, session
from PIL import Image
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, vfx

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'giro-dev-key-2024')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

BASE_DIR = os.path.join(tempfile.gettempdir(), 'giro_video_creator')
os.makedirs(BASE_DIR, exist_ok=True)

def get_user_dir():
    """Crea/recupera carpeta temporal del usuario"""
    if 'user_id' not in session:
        session['user_id'] = uuid.uuid4().hex[:12]
    user_dir = os.path.join(BASE_DIR, session['user_id'])
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def get_user_data():
    """Carga datos de la sesión desde JSON"""
    user_dir = get_user_dir()
    data_path = os.path.join(user_dir, 'data.json')
    if os.path.exists(data_path):
        with open(data_path, 'r') as f:
            return json.load(f)
    return {'photos': [], 'music': None, 'music_name': None}

def save_user_data(data):
    """Guarda datos de la sesión a JSON"""
    user_dir = get_user_dir()
    with open(os.path.join(user_dir, 'data.json'), 'w') as f:
        json.dump(data, f)

# ========================
# RUTAS
# ========================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload-photos', methods=['POST'])
def upload_photos():
    user_dir = get_user_dir()
    data = get_user_data()
    
    files = request.files.getlist('photos')
    for f in files:
        if f.filename:
            photo_id = uuid.uuid4().hex[:8]
            filepath = os.path.join(user_dir, f'{photo_id}.jpg')
            img = Image.open(f.stream)
            # Redimensionar para ahorrar espacio
            w, h = img.size
            if max(w, h) > 1920:
                ratio = 1920 / max(w, h)
                img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
            img.save(filepath, 'JPEG', quality=85)
            data['photos'].append({
                'id': photo_id,
                'name': f.filename,
                'duration': 8,
            })
    
    save_user_data(data)
    return jsonify({'status': 'ok', 'photos': data['photos']})

@app.route('/api/reorder-photos', methods=['POST'])
def reorder_photos():
    data = get_user_data()
    order = request.json.get('order', [])
    photo_map = {p['id']: p for p in data['photos']}
    data['photos'] = [photo_map[pid] for pid in order if pid in photo_map]
    save_user_data(data)
    return jsonify({'status': 'ok'})

@app.route('/api/remove-photo', methods=['POST'])
def remove_photo():
    user_dir = get_user_dir()
    data = get_user_data()
    photo_id = request.json.get('id')
    
    data['photos'] = [p for p in data['photos'] if p['id'] != photo_id]
    # Eliminar archivo
    filepath = os.path.join(user_dir, f'{photo_id}.jpg')
    if os.path.exists(filepath):
        os.remove(filepath)
    
    save_user_data(data)
    return jsonify({'status': 'ok', 'photos': data['photos']})

@app.route('/api/set-durations', methods=['POST'])
def set_durations():
    data = get_user_data()
    durations = request.json.get('durations', {})
    for p in data['photos']:
        if p['id'] in durations:
            p['duration'] = int(durations[p['id']])
    save_user_data(data)
    return jsonify({'status': 'ok'})

@app.route('/api/upload-music', methods=['POST'])
def upload_music():
    user_dir = get_user_dir()
    data = get_user_data()
    
    file = request.files.get('music')
    if file and file.filename:
        # Eliminar música anterior
        if data['music'] and os.path.exists(os.path.join(user_dir, data['music'])):
            os.remove(os.path.join(user_dir, data['music']))
        
        filename = f'music_{uuid.uuid4().hex[:6]}.mp3'
        filepath = os.path.join(user_dir, filename)
        file.save(filepath)
        data['music'] = filename
        data['music_name'] = file.filename
    
    save_user_data(data)
    return jsonify({'status': 'ok', 'music_name': data['music_name']})

@app.route('/api/remove-music', methods=['POST'])
def remove_music():
    user_dir = get_user_dir()
    data = get_user_data()
    
    if data['music']:
        filepath = os.path.join(user_dir, data['music'])
        if os.path.exists(filepath):
            os.remove(filepath)
    data['music'] = None
    data['music_name'] = None
    save_user_data(data)
    return jsonify({'status': 'ok'})

@app.route('/api/get-data', methods=['GET'])
def get_data():
    data = get_user_data()
    # Calcular duración total
    total_sec = sum(p['duration'] for p in data['photos'])
    trans_sec = 0.8 * max(0, len(data['photos']) - 1)
    return jsonify({
        'photos': data['photos'],
        'music_name': data['music_name'],
        'total_duration': int(total_sec + trans_sec),
        'photo_count': len(data['photos']),
    })

@app.route('/api/photo/<photo_id>.jpg')
def serve_photo(photo_id):
    user_dir = get_user_dir()
    filepath = os.path.join(user_dir, f'{photo_id}.jpg')
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    return '', 404

@app.route('/api/render', methods=['POST'])
def render_video():
    user_dir = get_user_dir()
    data = get_user_data()
    
    if len(data['photos']) < 2:
        return jsonify({'error': 'Necesitás al menos 2 fotos'}), 400
    
    output_path = os.path.join(user_dir, 'output.mp4')
    tmp_files = []
    
    try:
        durations = [p['duration'] for p in data['photos']]
        
        # Tamaño de salida (basado en primera foto)
        img0 = Image.open(os.path.join(user_dir, f"{data['photos'][0]['id']}.jpg"))
        W, H = img0.size
        max_dim = 1280
        if W >= H and W > max_dim:
            H = int(H * max_dim / W); W = max_dim
        elif H > W and H > max_dim:
            W = int(W * max_dim / H); H = max_dim
        if W % 2: W += 1
        if H % 2: H += 1
        
        # Crear clips
        clips = []
        for i, p in enumerate(data['photos']):
            filepath = os.path.join(user_dir, f"{p['id']}.jpg")
            img = Image.open(filepath).resize((W, H), Image.LANCZOS)
            tmp = os.path.join(user_dir, f"_tmp_{i}.png")
            img.save(tmp)
            tmp_files.append(tmp)
            clips.append(ImageClip(tmp, duration=durations[i]))
        
        # Transiciones fade
        for i, c in enumerate(clips):
            if i > 0:
                c = c.with_effects([vfx.CrossFadeIn(0.8)])
            if i < len(clips) - 1:
                c = c.with_effects([vfx.CrossFadeOut(0.8)])
            clips[i] = c
        
        video = concatenate_videoclips(clips, method="compose")
        
        # Audio
        if data['music']:
            music_path = os.path.join(user_dir, data['music'])
            if os.path.exists(music_path):
                audio = AudioFileClip(music_path)
                if audio.duration > video.duration:
                    audio = audio.subclipped(0, video.duration)
                video = video.with_audio(audio)
        
        # Exportar
        video.write_videofile(
            output_path, codec='libx264', audio_codec='aac',
            bitrate='2000k', fps=30, preset='medium', threads=2, logger=None,
        )
        
        # Limpiar temporales
        for fp in tmp_files:
            try: os.remove(fp)
            except: pass
        
        # Datos del resultado
        file_size = os.path.getsize(output_path)
        has_audio = bool(data['music'] and os.path.exists(os.path.join(user_dir, data['music'])))
        
        return jsonify({
            'status': 'ok',
            'filename': 'output.mp4',
            'size_mb': round(file_size / (1024 * 1024), 1),
            'has_audio': has_audio,
            'width': W,
            'height': H,
        })
    
    except Exception as e:
        for fp in tmp_files:
            try: os.remove(fp)
            except: pass
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/output.mp4')
def download_video():
    user_dir = get_user_dir()
    filepath = os.path.join(user_dir, 'output.mp4')
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='video/mp4',
                        download_name=f'giro_video_{int(time.time())}.mp4',
                        as_attachment=True)
    return '', 404

@app.route('/api/reset', methods=['POST'])
def reset():
    user_dir = get_user_dir()
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
    session.pop('user_id', None)
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
