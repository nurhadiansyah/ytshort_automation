import os
import sys
import json
import time
from pathlib import Path

# Tangani encoding Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
import ai_services
import video_editor
import youtube_uploader
import veo_service

def create_short_video(
    topic: str = "Fakta Menarik Hewan Bawah Laut",
    animation_style: str = "Handcrafted Claymation Animation",
    auto_upload: bool = False,
    privacy_status: str = "unlisted",
    voice_name: str = "id-ID-ArdiNeural",
    caption_style: str = "clay_pop",
    scene_count: int = 5,
    enable_header_badge: bool = True,
    enable_progress_bar: bool = True,
    enable_sfx: bool = True
) -> dict:
    """
    Menjalankan alur lengkap produksi Video Ilustrasi Animasi YouTube Shorts:
    1. Konsep & Naskah Animasi (Gemini - 5 Adegan Cepat)
    2. Voiceover TTS Studio
    3. AI Animated Artwork (Gaya Claymation Stop-Motion)
    4. Rendering Video Animasi (Camera Motion + Dynamic Subtitles + Header Badge + Progress Bar + SFX)
    5. YouTube Upload (Opsional / Otomatis)
    """
    timestamp = int(time.time())
    run_dir = config.TEMP_DIR / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print(f"[*] MEMULAI PRODUKSI VIDEO ILUSTRASI ANIMASI")
    print(f"[*] Topik: {topic}")
    print(f"[*] Gaya Visual: {animation_style}")
    print(f"[*] Jumlah Adegan: {scene_count} Adegan (Pacing Cepat)")
    print("=" * 60)
    
    # 1. GENERATE NASKAH & SKENARIO ANIMASI
    print(f"\n[LANGKAH 1/4] Membuat Konsep & Naskah Animasi ({scene_count} Adegan) via Gemini...")
    script_data = ai_services.generate_script(topic=topic, animation_style=animation_style, scene_count=scene_count)
    
    title = script_data.get("title", f"Animasi: {topic} #Shorts")
    description = script_data.get("description", "")
    tags = script_data.get("tags", ["Shorts", "Animasi", "Fakta", "Edukasi"])
    scenes = script_data.get("scenes", [])
    
    if not scenes:
        raise ValueError("Naskah tidak menghasilkan adegan (scenes).")
        
    print(f"-> Judul: {title}")
    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).rstrip()[:40].replace(" ", "_")
    print(f"-> Total Adegan Animasi: {len(scenes)}")

    # 1.1 Buat Header Hook Badge jika diaktifkan
    header_badge_path = None
    if enable_header_badge:
        header_badge_path = str(run_dir / "header_badge.png")
        print(f"[*] Membuat Header Hook Badge di atas video...")
        video_editor.create_header_badge(title, header_badge_path)
    
    # 2. GENERATE SUARA & ILUSTRASI ANIMASI PER ADEGAN
    print("\n[LANGKAH 2/4] Menghasilkan Voiceover Studio & Ilustrasi Seni Animasi...")
    scene_videos = []
    
    visual_theme = script_data.get("visual_theme", "")
    camera_map = {"zoom_in": 1, "pan_focus": 2, "pull_back": 3, "pan_sweep": 4, "tilt_rise": 5}
    
    for idx, sc in enumerate(scenes, 1):
        print(f"\n--- Memproses Adegan Animasi {idx}/{len(scenes)} ---")
        narration = sc.get("narration", "")
        captions = sc.get("captions", [sc.get("caption", narration[:30])])
        img_prompt = sc.get("image_prompt", f"3D animation illustration of {topic}")
        
        # Audio Voiceover
        audio_file = run_dir / f"scene_{idx}_voice.wav"
        ai_services.generate_voice(narration, str(audio_file), voice_name=voice_name)
        
        # Ilustrasi Animasi (Menggunakan visual_theme agar 100% konsisten)
        image_file = run_dir / f"scene_{idx}_anim_art.jpg"
        ai_services.generate_image(img_prompt, str(image_file), visual_theme=visual_theme)
        
        # 3. GENERATE VIDEO KLIP: LANGSUNG LEMPAR KE GOOGLE VEO 3
        scene_output = run_dir / f"scene_{idx}_anim_clip.mp4"
        raw_veo_clip = run_dir / f"scene_{idx}_raw_veo.mp4"
        
        print(f"[*] Adegan {idx}: Mencoba generate klip langsung via Google Veo 3...")
        veo_ok = veo_service.generate_veo3_clip(str(image_file), img_prompt, str(raw_veo_clip))
        
        if veo_ok and raw_veo_clip.exists():
            print(f"[+] Adegan {idx}: Video berhasil dibuat langsung oleh Google Veo 3!")
            veo_service.render_veo_scene_with_subs_and_audio(
                veo_video_path=str(raw_veo_clip),
                captions=captions,
                audio_path=str(audio_file),
                output_scene_path=str(scene_output)
            )
        else:
            print(f"[*] Adegan {idx}: Menggunakan rendering animasi dinamis (Camera Motion + Subtitle Sinkron)...")
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

    # Ekspor Paket Khusus Google Veo 3 (Naskah + Prompt + Gambar)
    veo_pack_dir = config.OUTPUT_DIR / f"Veo3_Package_{safe_title}_{timestamp}"
    scene_image_paths = [str(run_dir / f"scene_{i}_anim_art.jpg") for i in range(1, len(scenes) + 1)]
    veo_service.export_veo3_package(script_data, scene_image_paths, veo_pack_dir)

    # 3. MENGGABUNGKAN SELURUH ADEGAN KE VIDEO FINAL
    print("\n[LANGKAH 3/4] Menggabungkan Seluruh Adegan Menjadi Video Final...")
    final_video_name = f"Animasi_{safe_title}_{timestamp}.mp4"
    final_video_path = config.OUTPUT_DIR / final_video_name
    
    # Cek musik BGM di assets/
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
    
    # Simpan metadata JSON di output
    meta_path = config.OUTPUT_DIR / f"Animasi_{safe_title}_{timestamp}_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n[+] VIDEO ANIMASI BERHASIL DIBUAT!")
    print(f"    File Video : {final_video_path}")
    print(f"    Paket Veo 3: {veo_pack_dir}")
    
    result = {
        "video_path": str(final_video_path),
        "title": title,
        "description": description,
        "tags": tags,
        "uploaded": False,
        "youtube_url": None
    }
    
    # 4. UPLOAD KE YOUTUBE
    if auto_upload:
        print("\n[LANGKAH 4/4] Mengunggah Otomatis ke YouTube...")
        client_secret = config.BASE_DIR / config.YOUTUBE_CLIENT_SECRET_FILE
        if not client_secret.exists():
            print(f"[!] PERHATIAN: File '{client_secret.name}' belum ada di folder proyek.")
            print("    Video telah tersimpan dengan aman di folder 'output/'.")
            print("    Silakan masukkan 'client_secret.json' dari Google Cloud Console jika ingin upload otomatis.")
        else:
            try:
                yt_url = youtube_uploader.upload_video(
                    video_path=str(final_video_path),
                    title=title,
                    description=description,
                    tags=tags,
                    privacy_status=privacy_status
                )
                result["uploaded"] = True
                result["youtube_url"] = yt_url
            except Exception as e:
                print(f"[!] Gagal upload ke YouTube: {e}")
    else:
        print("\n[*] Video animasi siap di folder 'output/'.")
        
    print("=" * 60)
    return result
