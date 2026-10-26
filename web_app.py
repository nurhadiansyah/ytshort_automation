import os
import sys
import json
import time
import queue
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response, send_from_directory

# Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
import ai_services
import video_editor
import youtube_uploader
import veo_service
import shutil
import batch_engine
import daily_scheduler

app = Flask(__name__)

# State untuk live progress dan log
current_task = {
    "status": "idle", # idle, running, completed, error
    "progress": 0,
    "step": "",
    "log": [],
    "result": None,
    "error_message": None
}
task_lock = threading.Lock()

def add_log(msg: str):
    print(f"[WEB] {msg}")
    with task_lock:
        current_task["log"].append({"time": time.strftime("%H:%M:%S"), "message": msg})
        if len(current_task["log"]) > 100:
            current_task["log"].pop(0)

def set_progress(percent: int, step_name: str):
    with task_lock:
        current_task["progress"] = percent
        current_task["step"] = step_name
    add_log(f"[{percent}%] {step_name}")

def run_generation_job(
    topic: str,
    animation_style: str,
    voice_type: str,
    auto_upload: bool,
    privacy_status: str,
    caption_style: str = "clay_pop",
    scene_count: int = 5,
    enable_header_badge: bool = True,
    enable_progress_bar: bool = True,
    enable_sfx: bool = True,
    scheduled_publish_time: str = None
):
    global current_task
    try:
        with task_lock:
            current_task["status"] = "running"
            current_task["progress"] = 5
            current_task["step"] = "Memulai produksi video animasi..."
            current_task["log"] = []
            current_task["result"] = None
            current_task["error_message"] = None

        timestamp = int(time.time())
        run_dir = config.TEMP_DIR / f"web_run_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        set_progress(10, f"Merancang konsep ({scene_count} adegan) untuk '{topic}'...")
        script_data = ai_services.generate_script(topic=topic, animation_style=animation_style, scene_count=scene_count)
        
        title = script_data.get("title", f"Animasi: {topic} #Shorts")
        description = script_data.get("description", "")
        tags = script_data.get("tags", ["Shorts", "Animasi", "Edukasi", "Fakta"])
        scenes = script_data.get("scenes", [])
        
        if not scenes:
            raise ValueError("Gagal menghasilkan adegan naskah.")

        add_log(f"Naskah selesai! Judul: '{title}' ({len(scenes)} adegan)")
        set_progress(20, "Memproses adegan (Voiceover, Seni Ilustrasi, & Animasi)...")

        # Buat Header Hook Badge jika aktif
        header_badge_path = None
        if enable_header_badge:
            header_badge_path = str(run_dir / "header_badge.png")
            add_log("Membuat Header Hook Badge di bagian atas video...")
            video_editor.create_header_badge(title, header_badge_path)

        scene_videos = []
        num_scenes = len(scenes)
        
        visual_theme = script_data.get("visual_theme", "")
        camera_map = {"zoom_in": 1, "pan_focus": 2, "pull_back": 3, "pan_sweep": 4, "tilt_rise": 5}

        for idx, sc in enumerate(scenes, 1):
            base_pct = 25 + int(((idx - 1) / num_scenes) * 50)
            set_progress(base_pct, f"Adegan {idx}/{num_scenes}: Rekam suara & artwork animasi...")
            
            narration = sc.get("narration", "")
            captions = sc.get("captions", [sc.get("caption", narration[:30])])
            img_prompt = sc.get("image_prompt", f"3D Pixar illustration of {topic}")

            # 1. Voiceover (Sesuai pilihan voice_type: Ardi, Gadis, atau Google)
            audio_file = run_dir / f"scene_{idx}_voice.wav"
            add_log(f"Adegan {idx}: Membuat voiceover...")
            ai_services.generate_voice(narration, str(audio_file), voice_name=voice_type)

            # 2. Gambar Seni Ilustrasi (Sesuai tema visual & naskah cerita)
            image_file = run_dir / f"scene_{idx}_art.jpg"
            add_log(f"Adegan {idx}: Menggambar ilustrasi bertema '{narration[:35]}...'")
            ai_services.generate_image(img_prompt, str(image_file), visual_theme=visual_theme)

            # 3. Generate Video: Langsung lempar gambar & prompt ke Google Veo 3
            scene_output = run_dir / f"scene_{idx}_clip.mp4"
            raw_veo_clip = run_dir / f"scene_{idx}_raw_veo.mp4"
            
            add_log(f"Adegan {idx}: Melempar gambar & prompt ke Google Veo 3...")
            veo_ok = veo_service.generate_veo3_clip(str(image_file), img_prompt, str(raw_veo_clip))
            
            if veo_ok and raw_veo_clip.exists():
                add_log(f"Adegan {idx}: Video berhasil dibuat langsung oleh Google Veo 3 AI!")
                veo_service.render_veo_scene_with_subs_and_audio(
                    veo_video_path=str(raw_veo_clip),
                    captions=captions,
                    audio_path=str(audio_file),
                    output_scene_path=str(scene_output)
                )
            else:
                add_log(f"Adegan {idx}: Menggunakan rendering animasi dinamis (Camera Motion + Subtitle {caption_style})...")
                motion_type = camera_map.get(sc.get("camera_motion", ""), ((idx - 1) % 5) + 1)
                video_editor.render_animated_scene(
                    image_path=str(image_file),
                    captions=captions,
                    audio_path=str(audio_file),
                    output_scene_path=str(scene_output),
                    motion_type=motion_type,
                    caption_style=caption_style
                )
            scene_videos.append(str(scene_output))

        set_progress(80, "Menggabungkan semua adegan, mixing BGM, Header Badge & SFX...")
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).rstrip()[:40].replace(" ", "_")
        final_video_name = f"Animasi_{safe_title}_{timestamp}.mp4"
        final_video_path = config.OUTPUT_DIR / final_video_name

        bgm_candidates = list(config.ASSETS_DIR.glob("*.mp3"))
        bgm_path = str(bgm_candidates[0]) if bgm_candidates else None

        video_editor.combine_scenes_to_short(
            scene_video_paths=scene_videos,
            final_output_path=str(final_video_path),
            bgm_path=bgm_path,
            header_badge_path=header_badge_path,
            enable_progress_bar=enable_progress_bar,
            enable_sfx=enable_sfx
        )

        # Buat Paket Khusus Google Veo 3 (Prompt Lengkap + Gambar Setiap Adegan)
        add_log("Menyiapkan paket prompt & gambar untuk Google Veo 3...")
        veo_pack_dir = config.OUTPUT_DIR / f"Veo3_{safe_title}_{timestamp}"
        scene_img_paths = [str(run_dir / f"scene_{i}_art.jpg") for i in range(1, len(scenes) + 1)]
        veo_service.export_veo3_package(script_data, scene_img_paths, veo_pack_dir)
        
        # Buat file ZIP agar user bisa unduh 1 klik
        zip_base_name = str(config.OUTPUT_DIR / f"Veo3_{safe_title}_{timestamp}")
        shutil.make_archive(zip_base_name, 'zip', str(veo_pack_dir))
        veo_zip_filename = f"Veo3_{safe_title}_{timestamp}.zip"

        # Simpan metadata JSON
        meta_path = config.OUTPUT_DIR / f"Animasi_{safe_title}_{timestamp}_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)

        res_data = {
            "video_filename": final_video_name,
            "video_url": f"/video/{final_video_name}",
            "veo_zip_url": f"/download-veo/{veo_zip_filename}",
            "veo_zip_name": veo_zip_filename,
            "title": title,
            "description": description,
            "tags": tags,
            "scenes_count": len(scenes),
            "scenes": scenes,
            "uploaded": False,
            "youtube_url": None
        }

        # Auto Upload jika dicentang
        if auto_upload:
            set_progress(90, "Mengunggah video otomatis ke YouTube Shorts...")
            client_secret = config.BASE_DIR / config.YOUTUBE_CLIENT_SECRET_FILE
            if not client_secret.exists():
                add_log("Peringatan: client_secret.json belum disetel, upload dilewati.")
            else:
                try:
                    actual_privacy = "private" if scheduled_publish_time else privacy_status
                    if scheduled_publish_time:
                        add_log(f"Menjadwalkan tayang di YouTube Shorts pada: {scheduled_publish_time} (Status: Private Terjadwal)")
                    yt_url = youtube_uploader.upload_video(
                        video_path=str(final_video_path),
                        title=title,
                        description=description,
                        tags=tags,
                        privacy_status=actual_privacy,
                        publish_at=scheduled_publish_time
                    )
                    res_data["uploaded"] = True
                    res_data["youtube_url"] = yt_url
                    res_data["scheduled_publish_at"] = scheduled_publish_time
                    add_log(f"Upload YouTube Berhasil! {yt_url}")
                except Exception as e:
                    add_log(f"Gagal upload YouTube: {e}")

        set_progress(100, "Selesai! Video animasi siap diputar.")
        with task_lock:
            current_task["status"] = "completed"
            current_task["result"] = res_data

    except Exception as e:
        import traceback
        err_msg = str(e)
        add_log(f"ERROR: {err_msg}")
        print(traceback.format_exc())
        with task_lock:
            current_task["status"] = "error"
            current_task["error_message"] = err_msg

# ================= ROUTES =================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/system-status")
def system_status():
    has_gemini = bool(config.GEMINI_API_KEY)
    yt_status = youtube_uploader.check_auth_status()
    has_ffmpeg = bool(config.FFMPEG_EXE and os.path.exists(config.FFMPEG_EXE))

    return jsonify({
        "gemini_ready": has_gemini,
        "youtube_ready": yt_status.get("ready", False),
        "youtube_authenticated": yt_status.get("authenticated", False),
        "youtube_expired": yt_status.get("expired", False),
        "youtube_message": yt_status.get("message", ""),
        "ffmpeg_ready": has_ffmpeg
    })

@app.route("/api/youtube-auth", methods=["POST"])
def trigger_youtube_auth():
    try:
        data = request.json or {}
        force = bool(data.get("force", False))
        service = youtube_uploader.get_authenticated_service(force_reauth=force)
        req = service.channels().list(part="snippet", mine=True)
        res = req.execute()
        title = "Akun YouTube"
        if res.get("items"):
            title = res["items"][0].get("snippet", {}).get("title", title)
        return jsonify({"status": "success", "channel_title": title})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/youtube/import-token", methods=["POST"])
def import_youtube_token():
    try:
        data = request.json or {}
        token_content = data.get("token_content", "").strip()
        if not token_content:
            return jsonify({"status": "error", "message": "Konten token JSON tidak boleh kosong."}), 400
        
        # Validasi format JSON
        try:
            parsed = json.loads(token_content)
            if not isinstance(parsed, dict) or ("token" not in parsed and "refresh_token" not in parsed):
                return jsonify({"status": "error", "message": "Format token.json tidak valid (harus berisi field 'token' atau 'refresh_token')."}), 400
        except Exception as je:
            return jsonify({"status": "error", "message": f"Format JSON tidak valid: {je}"}), 400

        token_file = config.BASE_DIR / "token.json"
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(token_content)

        # Tes koneksi dengan token baru
        service = youtube_uploader.get_authenticated_service()
        req = service.channels().list(part="snippet,statistics", mine=True)
        res = req.execute()
        title = "Akun YouTube"
        sub_count = "0"
        vid_count = "0"
        if res.get("items"):
            item = res["items"][0]
            title = item.get("snippet", {}).get("title", title)
            sub_count = item.get("statistics", {}).get("subscriberCount", "0")
            vid_count = item.get("statistics", {}).get("videoCount", "0")

        return jsonify({
            "status": "success",
            "message": f"Token YouTube berhasil diimpor! Terhubung ke channel: '{title}' ({sub_count} subs, {vid_count} video).",
            "channel_title": title
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal mengimpor token: {e}"}), 500

@app.route("/api/start-generate", methods=["POST"])
def start_generate():
    global current_task
    with task_lock:
        if current_task["status"] == "running":
            return jsonify({"status": "error", "message": "Proses pembuatan video sedang berjalan!"}), 400

    data = request.json or {}
    topic = data.get("topic", "").strip() or "Fakta Menarik Sains Luar Angkasa"
    animation_style = data.get("animation_style", "Handcrafted Claymation Animation")
    voice_type = data.get("voice_type", "edge-ardi")
    auto_upload = bool(data.get("auto_upload", False))
    privacy_status = data.get("privacy_status", "unlisted")
    caption_style = data.get("caption_style", "clay_pop")
    scene_count = int(data.get("scene_count", 5))
    enable_header_badge = bool(data.get("enable_header_badge", True))
    enable_progress_bar = bool(data.get("enable_progress_bar", True))
    enable_sfx = bool(data.get("enable_sfx", True))
    scheduled_publish_time = data.get("scheduled_publish_time", None)

    t = threading.Thread(
        target=run_generation_job,
        args=(topic, animation_style, voice_type, auto_upload, privacy_status, caption_style, scene_count, enable_header_badge, enable_progress_bar, enable_sfx, scheduled_publish_time),
        daemon=True
    )
    t.start()

    return jsonify({"status": "success", "message": "Proses dimulai!"})

@app.route("/api/educational-niches")
def get_educational_niches():
    niche_file = config.BASE_DIR / "data" / "educational_niches.json"
    if niche_file.exists():
        try:
            with open(niche_file, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"categories": {}})

@app.route("/api/random-topic")
def get_random_topic():
    niche_file = config.BASE_DIR / "data" / "educational_niches.json"
    if niche_file.exists():
        try:
            with open(niche_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                import random
                cats = list(data.get("categories", {}).values())
                if cats:
                    c = random.choice(cats)
                    top = random.choice(c.get("topics", ["Misteri Luar Angkasa"]))
                    return jsonify({"topic": top, "category": c.get("name", "Edukasi")})
        except Exception:
            pass
    return jsonify({"topic": "Kenapa Paus Biru Punya Jantung Sebesar Mobil Golf?", "category": "Sains & Alam"})

@app.route("/api/generate-ai-topic")
def generate_ai_topic():
    """Menghasilkan 1 topik baru segar dan unik menggunakan Gemini AI secara instan."""
    niche = request.args.get("niche", "all")
    try:
        fresh_topics = ai_services.generate_fresh_topics(count=1, niche=niche)
        if fresh_topics:
            return jsonify({
                "status": "success",
                "topic": fresh_topics[0],
                "source": "gemini-ai"
            })
    except Exception as e:
        print(f"[!] Error generate_ai_topic: {e}")
    # Fallback jika terjadi limit / offline
    return get_random_topic()


@app.route("/api/progress")
def get_progress():
    with task_lock:
        return jsonify(current_task)

@app.route("/api/videos")
def list_videos():
    videos = []
    for f in config.OUTPUT_DIR.glob("*.mp4"):
        st = f.stat()
        meta_file = f.with_name(f"{f.stem}_metadata.json")
        title = f.stem.replace("_", " ")
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as m:
                    mdata = json.load(m)
                    title = mdata.get("title", title)
            except Exception:
                pass

        videos.append({
            "filename": f.name,
            "title": title,
            "size_mb": round(st.st_size / (1024 * 1024), 2),
            "created_at": time.strftime("%d/%m/%Y %H:%M", time.localtime(st.st_mtime)),
            "mtime": st.st_mtime,
            "url": f"/video/{f.name}"
        })

    videos.sort(key=lambda x: x["mtime"], reverse=True)
    return jsonify(videos)

@app.route("/video/<path:filename>")
def serve_video(filename):
    return send_from_directory(str(config.OUTPUT_DIR), filename, mimetype="video/mp4")

@app.route("/download-veo/<path:filename>")
def download_veo(filename):
    return send_from_directory(str(config.OUTPUT_DIR), filename, as_attachment=True)

@app.route("/api/upload-video", methods=["POST"])
def upload_existing_video():
    data = request.json or {}
    filename = data.get("filename")
    privacy = data.get("privacy", "unlisted")
    publish_at = data.get("publish_at", None)

    if not filename:
        return jsonify({"status": "error", "message": "Nama file video tidak diberikan"}), 400

    video_path = config.OUTPUT_DIR / filename
    if not video_path.exists():
        return jsonify({"status": "error", "message": "File video tidak ditemukan"}), 404

    # Ambil judul dari metadata jika ada
    title = video_path.stem.replace("_", " ") + " #Shorts"
    desc = "Video animasi fakta menarik! Jangan lupa like dan subscribe. #Shorts #Animasi"
    tags = ["Shorts", "Animasi", "Fakta"]
    meta_file = video_path.with_name(f"{video_path.stem}_metadata.json")
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as m:
                mdata = json.load(m)
                title = mdata.get("title", title)
                desc = mdata.get("description", desc)
                tags = mdata.get("tags", tags)
        except Exception:
            pass

    actual_privacy = "private" if publish_at else privacy

    try:
        url = youtube_uploader.upload_video(
            video_path=str(video_path),
            title=title,
            description=desc,
            tags=tags,
            privacy_status=actual_privacy,
            publish_at=publish_at
        )
        return jsonify({
            "status": "success",
            "youtube_url": url,
            "publish_at": publish_at,
            "message": f"Video berhasil diunggah{' dengan jadwal rilis: ' + publish_at if publish_at else ''}!"
        })
    except Exception as e:
        err_str = str(e)
        from daily_scheduler import is_quota_error
        if is_quota_error(err_str):
            return jsonify({
                "status": "error",
                "is_quota_error": True,
                "message": "Batas kuota harian upload YouTube (10-15 video/24 jam) untuk channel ini telah tercapai. Google akan mereset kuota dalam siklus 24 jam."
            }), 429
        if "invalid_grant" in err_str or "expired or revoked" in err_str:
            (config.BASE_DIR / "token.json").unlink(missing_ok=True)
            return jsonify({
                "status": "error",
                "is_auth_error": True,
                "message": "Sesi token YouTube kedaluwarsa atau dicabut Google. Sesi lama telah dibersihkan. Silakan klik tombol 'YouTube' di bar atas untuk login ulang akun YouTube Anda."
            }), 401
        return jsonify({"status": "error", "message": err_str}), 500

@app.route("/api/schedule/upload-slot", methods=["POST"])
def upload_slot_endpoint():
    data = request.json or {}
    video_index = data.get("video_index")
    if not video_index:
        return jsonify({"status": "error", "message": "video_index wajib diisi"}), 400
    res = daily_scheduler.upload_slot_by_index(int(video_index))
    status_code = 429 if res.get("is_quota_error") else (200 if res.get("status") == "success" else 400)
    return jsonify(res), status_code

# ================= BATCH & 30-DAY SCHEDULER ROUTES =================

@app.route("/api/batch-status")
def get_batch_status():
    b_status = batch_engine.load_status()
    s_summary = daily_scheduler.get_schedule_summary()
    return jsonify({
        "batch": b_status,
        "schedule": s_summary
    })

@app.route("/api/batch-start", methods=["POST"])
def start_batch():
    data = request.json or {}
    total = int(data.get("total", 150))
    style = data.get("animation_style", "3D Pixar Animation")
    use_ai_topics = bool(data.get("use_ai_topics", True))

    if batch_engine.is_running():
        return jsonify({"status": "warning", "message": "Pabrik batch sudah berjalan!"})

    batch_engine.start_batch_in_background(total=total, animation_style=style, use_ai_topics=use_ai_topics)
    mode_text = "Topik Baru dari Gemini AI" if use_ai_topics else "Daftar Statis 150"
    return jsonify({"status": "success", "message": f"Pabrik batch dimulai untuk {total} video (Mode: {mode_text})!"})

@app.route("/api/batch-pause", methods=["POST"])
def pause_batch():
    batch_engine.pause_batch()
    return jsonify({"status": "success", "message": "Instruksi jeda (pause) dikirim."})

@app.route("/api/batch-reset", methods=["POST"])
def reset_batch():
    batch_engine.reset_batch()
    return jsonify({"status": "success", "message": "Antrean batch berhasil direset."})

@app.route("/api/schedule")
def get_full_schedule():
    sched = daily_scheduler.sync_schedule_with_batch()
    return jsonify(sched)

@app.route("/api/schedule-upload-today", methods=["POST"])
def upload_today():
    data = request.json or {}
    limit = int(data.get("limit", 5))
    res = daily_scheduler.upload_next_daily_batch(limit=limit)
    return jsonify(res)

@app.route("/api/schedule-produce-and-upload-today", methods=["POST"])
def produce_and_upload_today_endpoint():
    data = request.json or {}
    limit = int(data.get("limit", 5))
    style = data.get("animation_style", "Handcrafted Claymation Animation")

    def _run_auto_pilot():
        def _cb(msg):
            add_log(f"[Auto-Pilot] {msg}")
            print(f"[Auto-Pilot] {msg}")
        try:
            add_log(f"[Auto-Pilot] Memulai auto-pilot: produksi & jadwal rilis {limit} video hari ini...")
            res = daily_scheduler.produce_and_upload_today(
                limit=limit,
                animation_style=style,
                progress_callback=_cb
            )
            add_log(f"[Auto-Pilot] Selesai! {res['uploaded_count']} video diunggah terjadwal, {res['failed_count']} gagal.")
        except Exception as e:
            add_log(f"[Auto-Pilot] Error: {e}")

    t = threading.Thread(target=_run_auto_pilot, daemon=True)
    t.start()
    return jsonify({
        "status": "success",
        "message": f"Auto-Pilot produksi dan jadwal upload {limit} video Shorts telah dijalankan di background!"
    })

@app.route("/api/schedule/reorganize", methods=["POST"])
def reorganize_schedule():
    sched = daily_scheduler.reorganize_and_schedule_all_videos()
    return jsonify({
        "status": "success",
        "message": "Seluruh video yang sudah diproduksi berhasil dipetakan ke jadwal harian!",
        "schedule": sched
    })

@app.route("/api/autopilot/start", methods=["POST"])
def start_autopilot_endpoint():
    ok, msg = daily_scheduler.start_autopilot()
    return jsonify({"status": "success" if ok else "warning", "message": msg})

@app.route("/api/autopilot/stop", methods=["POST"])
def stop_autopilot_endpoint():
    ok, msg = daily_scheduler.stop_autopilot()
    return jsonify({"status": "success" if ok else "warning", "message": msg})

@app.route("/api/autopilot/status")
def autopilot_status_endpoint():
    return jsonify(daily_scheduler.get_autopilot_status())

def wait_and_open_browser(port: int):
    """Menunggu server Flask benar-benar aktif (HTTP 200) sebelum membuka browser agar tidak ada error connection refused."""
    import time
    import urllib.request
    import webbrowser
    for _ in range(35):
        time.sleep(0.35)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/system-status", timeout=1) as resp:
                if resp.status == 200:
                    print(f"[*] Server siap! Membuka browser ke http://127.0.0.1:{port}...")
                    webbrowser.open(f"http://127.0.0.1:{port}")
                    return
        except Exception:
            pass
    # Fallback jika polling tidak selesai
    webbrowser.open(f"http://127.0.0.1:{port}")

if __name__ == "__main__":
    import socket
    # Gunakan port dari environment jika ada (Hugging Face Spaces default 7860) atau 5000 untuk lokal
    default_port = 7860 if os.environ.get("SPACE_ID") else 5000
    port = int(os.environ.get("PORT", default_port))

    # Cek port hanya jika di lingkungan lokal
    if not os.environ.get("SPACE_ID") and not os.environ.get("PORT"):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) == 0:
                print(f"[!] Port {port} sedang digunakan. Mengalihkan ke port 5001...")
                port = 5001

    print(f"\n=======================================================")
    print(f"🚀 SERVER GUI WEB BERJALAN DI:")
    print(f"👉 Port: {port}")
    print(f"👉 http://127.0.0.1:{port}")
    print(f"👉 http://localhost:{port}")
    print(f"=======================================================\n")
    
    # Buka browser otomatis hanya jika di lingkungan lokal (bukan di Cloud/Docker)
    if not os.environ.get("SPACE_ID") and not os.environ.get("DOCKER_CONTAINER"):
        threading.Thread(target=wait_and_open_browser, args=(port,), daemon=True).start()

    app.run(host="0.0.0.0", port=port, debug=False)
