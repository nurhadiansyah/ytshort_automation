import os
import time
import json
import shutil
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

import config
import video_editor

def get_client():
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY belum disetel!")
    return genai.Client(api_key=config.GEMINI_API_KEY)

def export_veo3_package(script_data: dict, scene_image_paths: list[str], output_package_dir: Path) -> Path:
    """
    Menyatukan semua naskah, prompt, dan gambar ke dalam folder paket rapi
    yang siap dilempar ke Google Veo 3 / VideoFX / Google Labs.
    """
    output_package_dir.mkdir(parents=True, exist_ok=True)
    
    title = script_data.get("title", "Veo3_Project")
    scenes = script_data.get("scenes", [])
    
    readme_content = f"""============================================================
🎬 PAKET PROMPT & GAMBAR UNTUK GOOGLE VEO 3 (IMAGE-TO-VIDEO)
============================================================
Judul: {title}
Tema Visual: {script_data.get('visual_theme', '')}

PETUNJUK PENGGUNAAN DI GOOGLE VEO 3 / VIDEOFX:
1. Buka Google Veo 3 / VideoFX (https://labs.google/fx/tools/video-fx) atau Google AI Studio.
2. Di setiap adegan:
   - Upload file gambar (misal: scene_1_image.jpg)
   - Copy-paste teks prompt dari file .txt yang sesuai (misal: scene_1_prompt.txt)
   - Klik Generate Video!
3. Google Veo 3 akan menganimasikan gambar sesuai prompt adegan tersebut.
============================================================
"""
    with open(output_package_dir / "README_PETUNJUK_VEO3.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)

    with open(output_package_dir / "storyboard_veo3.json", "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=2, ensure_ascii=False)

    for idx, sc in enumerate(scenes, 1):
        if idx - 1 < len(scene_image_paths):
            src_img = Path(scene_image_paths[idx - 1])
            dest_img = output_package_dir / f"scene_{idx}_image.jpg"
            if src_img.exists():
                shutil.copy(src_img, dest_img)

        prompt_file = output_package_dir / f"scene_{idx}_prompt.txt"
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(f"PROMPT GOOGLE VEO 3 - ADEGAN {idx}:\n")
            f.write(f"{sc.get('image_prompt', '')}\n\n")
            f.write(f"NARASI VOICE:\n{sc.get('narration', '')}\n")

    print(f"[+] Paket Google Veo 3 berhasil diekspor ke: {output_package_dir}")
    return output_package_dir

_veo_available = None

def generate_veo3_clip(image_path: str, prompt: str, output_clip_path: str) -> bool:
    """
    Menghasilkan klip video animasi asli langsung dari Google Veo 3 API (Image-to-Video).
    Mencoba model veo-3.1-fast-generate-preview dan veo-3.1-generate-preview.
    Mengembalikan True jika sukses mendownload klip MP4, False jika akun Free Tier (belum ada Billing).
    """
    global _veo_available
    if _veo_available is False:
        return False

    client = get_client()
    veo_models = [
        "veo-3.1-fast-generate-preview",
        "veo-3.1-generate-preview",
        "veo-3.1-lite-generate-preview"
    ]
    
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    for model_name in veo_models:
        try:
            print(f"[*] Menghubungi Google Veo 3 ({model_name}) untuk generate video...")
            operation = client.models.generate_videos(
                model=model_name,
                prompt=f"{prompt}, high quality 3D animated continuous video, smooth fluid motion, cinematic lighting, 9:16 vertical",
                image=types.Image(image_bytes=img_bytes, mime_type="image/jpeg"),
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16"
                )
            )
            
            print(f"[*] Operasi Google Veo 3 dimulai: {operation.name}. Menunggu rendering AI...")
            max_wait = 240 # Tunggu max 4 menit per scene
            start_time = time.time()
            
            while not operation.done:
                if time.time() - start_time > max_wait:
                    print("[!] Timeout menunggu Google Veo 3.")
                    return False
                time.sleep(10)
                operation = client.operations.get(operation)
                print(f"    [Veo 3] Sedang me-render video AI di cloud Google...")

            if operation.response and operation.response.generated_videos:
                video_obj = operation.response.generated_videos[0]
                with open(output_clip_path, "wb") as f:
                    f.write(video_obj.video.video_bytes)
                print(f"[+] BERHASIL! Video asli dari Google Veo 3 didownload: {output_clip_path}")
                _veo_available = True
                return True
                
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                print(f"[!] Info Google Veo 3 ({model_name}): Memerlukan akun Google Cloud Billing Pay-As-You-Go. Melewati Veo 3.")
                _veo_available = False
                break
            else:
                print(f"[!] Info Veo 3 ({model_name}): {e}")
                
    return False

def render_veo_scene_with_subs_and_audio(
    veo_video_path: str,
    captions: list[str] | str,
    audio_path: str,
    output_scene_path: str
) -> str:
    """
    Menggabungkan klip video asli dari Google Veo 3 dengan audio voiceover
    dan subtitle proporsional yang bebas bunyi kresek-kresek.
    """
    audio_duration = video_editor.get_audio_duration(audio_path)
    padding_dur = 0.35
    total_duration = audio_duration + padding_dur

    if isinstance(captions, str):
        captions_list = [captions]
    else:
        captions_list = [c for c in captions if c.strip()]
    if not captions_list:
        captions_list = ["..."]

    total_words = sum(max(1, len(c.strip().split())) for c in captions_list)
    caption_files = []
    accum_time = 0.0

    for c_idx, text_chunk in enumerate(captions_list):
        c_png = str(Path(output_scene_path).with_suffix(f".veo_cap_{c_idx}.png"))
        video_editor.create_caption_card(text_chunk, c_png, highlight=(c_idx % 2 == 1 or len(captions_list) == 1))
        
        words_in_chunk = max(1, len(text_chunk.strip().split()))
        chunk_dur = audio_duration * (words_in_chunk / total_words)
        
        t_start = accum_time
        t_end = min(total_duration, accum_time + chunk_dur) if (c_idx < len(captions_list) - 1) else total_duration
        accum_time = t_end
        caption_files.append((c_png, t_start, t_end))

    inputs = ["-i", veo_video_path]
    current_input_idx = 1

    caption_input_indices = []
    for c_png, t_s, t_e in caption_files:
        inputs.extend(["-i", c_png])
        caption_input_indices.append((current_input_idx, t_s, t_e))
        current_input_idx += 1

    audio_input_idx = current_input_idx
    inputs.extend(["-i", audio_path])

    filters = []
    # 1. Scale Veo video ke 1080x1920 dan clone frame jika durasi video Veo sedikit lebih pendek dari narasi
    filters.append(
        f"[0:v]scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:flags=lanczos:force_original_aspect_ratio=increase,"
        f"crop={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},tpad=stop_mode=clone:stop_duration=2.0[v_base]"
    )
    last_v = "[v_base]"

    # 2. Dynamic Subtitle overlays
    for idx_tuple, (c_in, t_s, t_e) in enumerate(caption_input_indices):
        next_v = f"[v_sub_{idx_tuple}]"
        filters.append(f"{last_v}[{c_in}:v]overlay=0:0:enable='between(t,{t_s:.2f},{t_e:.2f})'{next_v}")
        last_v = next_v

    # 3. Audio Anti-Kresek
    fade_out_st = max(0.1, audio_duration - 0.04)
    audio_clean_filter = (
        f"[{audio_input_idx}:a]afade=t=in:ss=0:d=0.03,"
        f"afade=t=out:st={fade_out_st:.2f}:d=0.04,"
        f"apad=pad_dur={padding_dur:.2f}[clean_a]"
    )
    filters.append(audio_clean_filter)

    filter_complex_str = ";".join(filters)

    cmd = [
        config.FFMPEG_EXE, "-y",
        *inputs,
        "-filter_complex", filter_complex_str,
        "-map", last_v,
        "-map", "[clean_a]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(total_duration),
        output_scene_path
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg render veo scene error: {res.stderr[-400:]}")

    return output_scene_path
