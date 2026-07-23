"""
GIRO Video Creator — Flask + MoviePy
"""
import os, uuid, shutil, time, tempfile, json, threading
from flask import Flask, render_template, request, jsonify, send_file, session
from PIL import Image

try:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, vfx
    MOVIEPY_OK = True
except Exception as e:
    print(f"WARNING: moviepy no disponible: {e}")
    MOVIEPY_OK = False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'giro-dev-key-2024')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

BASE_DIR = os.path.join(tempfile.gettempdir(), 'giro_video_creator')
os.makedirs(BASE_DIR, exist_ok=True)

# Render async
render_tasks = {}

def get_user_dir():
    if 'user_id' not in session:
        session['user_id'] = uuid.uuid4().hex[:12]
    d = os.path.join(BASE_DIR, session['user_id'])
    os.makedirs(d, exist_ok=True)
    return d

def get_user_data():
    p = os.path.join(get_user_dir(), 'data.json')
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return {'photos': [], 'music': None, 'music_name': None}

def save_user_data(data):
    with open(os.path.join(get_user_dir(), 'data.json'), 'w') as f:
        json.dump(data, f)

def _render_thread(user_dir, task_id):
    """Render en background"""
    dp = os.path.join(user_dir, 'data.json')
    with open(dp) as f: data = json.load(f)
    out = os.path.join(user_dir, 'output.mp4')
    tmp = []
    try:
        durations = [p['duration'] for p in data['photos']]
        img0 = Image.open(os.path.join(user_dir, f"{data['photos'][0]['id']}.jpg"))
        W, H = img0.size
        mx = 1280
        if W >= H and W > mx: H = int(H*mx/W); W = mx
        elif H > W and H > mx: W = int(W*mx/H); H = mx
        if W%2: W+=1
        if H%2: H+=1
        clips = []
        for i, p in enumerate(data['photos']):
            fp = os.path.join(user_dir, f"{p['id']}.jpg")
            img = Image.open(fp).resize((W,H), Image.LANCZOS)
            t = os.path.join(user_dir, f"_t{i}.png")
            img.save(t); tmp.append(t)
            clips.append(ImageClip(t, duration=durations[i]))
        for i, c in enumerate(clips):
            if i>0: c=c.with_effects([vfx.CrossFadeIn(0.8)])
            if i<len(clips)-1: c=c.with_effects([vfx.CrossFadeOut(0.8)])
            clips[i]=c
        video = concatenate_videoclips(clips, method="compose")
        if data['music']:
            mp = os.path.join(user_dir, data['music'])
            if not os.path.exists(mp) and data.get('music_source') == 'library':
                mp = os.path.join(app.static_folder, 'musica', data['music'])
            if os.path.exists(mp):
                a = AudioFileClip(mp)
                if a.duration > video.duration: a = a.subclipped(0, video.duration)
                video = video.with_audio(a)
        video.write_videofile(out, codec='libx264', audio_codec='aac',
                              bitrate='2000k', fps=30, preset='ultrafast',
                              threads=2, logger=None)
        sz = os.path.getsize(out)
        render_tasks[task_id] = {'status':'done','size_mb':round(sz/(1024*1024),1),
                                  'has_audio':bool(data['music']),'width':W,'height':H}
    except Exception as e:
        render_tasks[task_id] = {'status':'error','error':str(e)}
    finally:
        for fp in tmp:
            try: os.remove(fp)
            except: pass

# ===== ROUTES =====

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload-photos', methods=['POST'])
def upload_photos():
    user_dir = get_user_dir()
    data = get_user_data()
    for f in request.files.getlist('photos'):
        if f.filename:
            pid = uuid.uuid4().hex[:8]
            fp = os.path.join(user_dir, f'{pid}.jpg')
            img = Image.open(f.stream)
            w, h = img.size
            if max(w,h)>1920:
                r=1920/max(w,h); img=img.resize((int(w*r),int(h*r)), Image.LANCZOS)
            img.save(fp, 'JPEG', quality=85)
            data['photos'].append({'id':pid,'name':f.filename,'duration':8})
    save_user_data(data)
    return jsonify({'status':'ok','photos':data['photos']})

@app.route('/api/reorder-photos', methods=['POST'])
def reorder_photos():
    data = get_user_data()
    order = request.json.get('order',[])
    m = {p['id']:p for p in data['photos']}
    data['photos'] = [m[pid] for pid in order if pid in m]
    save_user_data(data)
    return jsonify({'status':'ok'})

@app.route('/api/remove-photo', methods=['POST'])
def remove_photo():
    user_dir = get_user_dir()
    data = get_user_data()
    pid = request.json.get('id')
    data['photos'] = [p for p in data['photos'] if p['id']!=pid]
    fp = os.path.join(user_dir, f'{pid}.jpg')
    if os.path.exists(fp): os.remove(fp)
    save_user_data(data)
    return jsonify({'status':'ok','photos':data['photos']})

@app.route('/api/set-durations', methods=['POST'])
def set_durations():
    data = get_user_data()
    durs = request.json.get('durations',{})
    for p in data['photos']:
        if p['id'] in durs: p['duration'] = int(durs[p['id']])
    save_user_data(data)
    return jsonify({'status':'ok'})

@app.route('/api/music-library')
def music_library():
    """Lista los MP3 disponibles en static/musica/"""
    lib_dir = os.path.join(app.static_folder, 'musica')
    tracks = []
    if os.path.exists(lib_dir):
        for f in sorted(os.listdir(lib_dir)):
            if f.endswith('.mp3'):
                name = f.replace('.mp3','').replace('_',' ').replace('-',' ')
                tracks.append({'filename': f, 'name': name.title()})
    return jsonify({'tracks': tracks})

@app.route('/api/select-library-music', methods=['POST'])
def select_library_music():
    """Selecciona un tema de la biblioteca"""
    data = get_user_data()
    filename = request.json.get('filename')
    lib_path = os.path.join(app.static_folder, 'musica', filename)
    if not os.path.exists(lib_path):
        return jsonify({'error': 'Tema no encontrado'}), 404
    
    # Si había música subida, eliminarla
    user_dir = get_user_dir()
    if data['music'] and os.path.exists(os.path.join(user_dir, data['music'])):
        os.remove(os.path.join(user_dir, data['music']))
    
    data['music'] = filename
    data['music_name'] = '🎵 ' + filename.replace('.mp3','').replace('_',' ').replace('-',' ').title()
    data['music_source'] = 'library'
    save_user_data(data)
    return jsonify({'status': 'ok', 'music_name': data['music_name']})
@app.route('/api/upload-music', methods=['POST'])
def upload_music():
    user_dir = get_user_dir()
    data = get_user_data()
    f = request.files.get('music')
    if f and f.filename:
        if data['music'] and data.get('music_source') != 'library' and \
           os.path.exists(os.path.join(user_dir, data['music'])):
            os.remove(os.path.join(user_dir, data['music']))
        fn = f'music_{uuid.uuid4().hex[:6]}.mp3'
        f.save(os.path.join(user_dir, fn))
        data['music'] = fn; data['music_name'] = f.filename
        data['music_source'] = 'upload'
    save_user_data(data)
    return jsonify({'status':'ok','music_name':data['music_name']})

@app.route('/api/remove-music', methods=['POST'])
def remove_music():
    user_dir = get_user_dir()
    data = get_user_data()
    if data['music'] and data.get('music_source') != 'library':
        fp = os.path.join(user_dir, data['music'])
        if os.path.exists(fp): os.remove(fp)
    data['music'] = None; data['music_name'] = None
    data.pop('music_source', None)
    save_user_data(data)
    return jsonify({'status':'ok'})

@app.route('/api/get-data')
def get_data():
    data = get_user_data()
    t = sum(p['duration'] for p in data['photos'])
    tr = 0.8*max(0,len(data['photos'])-1)
    return jsonify({'photos':data['photos'],'music_name':data['music_name'],
                    'total_duration':int(t+tr),'photo_count':len(data['photos'])})

@app.route('/api/photo/<photo_id>.jpg')
def serve_photo(photo_id):
    fp = os.path.join(get_user_dir(), f'{photo_id}.jpg')
    if os.path.exists(fp): return send_file(fp, mimetype='image/jpeg')
    return '',404

@app.route('/api/render', methods=['POST'])
def render_video():
    if not MOVIEPY_OK:
        return jsonify({'error':'MoviePy no disponible'}),500
    data = get_user_data()
    if len(data['photos'])<2:
        return jsonify({'error':'Necesitás al menos 2 fotos'}),400
    
    task_id = uuid.uuid4().hex[:8]
    render_tasks[task_id] = {'status':'processing'}
    t = threading.Thread(target=_render_thread, args=(get_user_dir(), task_id))
    t.start()
    return jsonify({'status':'processing','task_id':task_id})

@app.route('/api/render-status/<task_id>')
def render_status(task_id):
    task = render_tasks.get(task_id)
    if not task: return jsonify({'status':'not_found'}),404
    return jsonify(task)

@app.route('/api/download/output.mp4')
def download_video():
    fp = os.path.join(get_user_dir(), 'output.mp4')
    if os.path.exists(fp):
        return send_file(fp, mimetype='video/mp4',
                        download_name=f'giro_video_{int(time.time())}.mp4',
                        as_attachment=True)
    return '',404

@app.route('/api/reset', methods=['POST'])
def reset():
    d = get_user_dir()
    if os.path.exists(d): shutil.rmtree(d)
    session.pop('user_id', None)
    return jsonify({'status':'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
