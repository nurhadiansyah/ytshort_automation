import os
import subprocess
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import config

def get_audio_duration(audio_path: str) -> float:
    """Mendapatkan durasi audio (dalam detik) dari file WAV atau audio lainnya."""
    try:
        with wave.open(audio_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        cmd = [config.FFMPEG_EXE, "-i", audio_path, "-f", "null", "-"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        import re
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", res.stderr)
        if m:
            hours, mins, secs = float(m.group(1)), float(m.group(2)), float(m.group(3))
            return hours * 3600 + mins * 60 + secs
        return 5.0

def create_header_badge(
    title: str,
    output_path: str,
    width: int = config.VIDEO_WIDTH,
    height: int = config.VIDEO_HEIGHT,
    style: str = "clay_badge"
) -> str:
    """
    Membuat header badge / sticker pill transparan di bagian atas layar (~12-14% height).
    Menampilkan hook judul topik edukasi (seperti di video Claymation viral YouTube Shorts).
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Bersihkan title dari hashtag, suffix #Shorts, prefix klise
    clean_title = title.split("#")[0].strip()
    for prefix in ["Animasi:", "Animasi Fakta:", "Fakta Unik:", "Tahukah Kamu:", "Rahasia:"]:
        if clean_title.lower().startswith(prefix.lower()):
            clean_title = clean_title[len(prefix):].strip()

    font_candidates = [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf"
    ]
    font_size = 46
    font = None
    for fc in font_candidates:
        if Path(fc).exists():
            try:
                font = ImageFont.truetype(fc, font_size)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    words = clean_title.upper().split()
    lines = []
    curr = []
    max_w = 780
    for w in words:
        curr.append(w)
        bbox = draw.textbbox((0, 0), " ".join(curr), font=font)
        if (bbox[2] - bbox[0]) > max_w:
            curr.pop()
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    
    if len(lines) > 2:
        lines = lines[:2]
        lines[1] = lines[1] + "..."

    badge_text = "\n".join(lines)
    bbox = draw.multiline_textbbox((0, 0), badge_text, font=font, spacing=10, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x = 44
    pad_y = 20
    box_w = text_w + (pad_x * 2)
    box_h = text_h + (pad_y * 2)

    x1 = (width - box_w) // 2
    y1 = int(height * 0.125)
    x2 = x1 + box_w
    y2 = y1 + box_h
    corner_radius = 28

    # 1. Bayangan 3D Lembut
    draw.rounded_rectangle(
        [x1 + 3, y1 + 7, x2 + 3, y2 + 7],
        radius=corner_radius,
        fill=(0, 0, 0, 150)
    )

    # 2. Body Badge Plastisin Clay
    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=corner_radius,
        fill=(14, 18, 28, 235),
        outline=(255, 212, 38, 240),
        width=4
    )

    # 3. Mini Top Tag "★ EDUKASI SHORTS"
    tag_font_size = 20
    tag_font = None
    for fc in ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf"]:
        if Path(fc).exists():
            try:
                tag_font = ImageFont.truetype(fc, tag_font_size)
                break
            except Exception:
                pass
    if tag_font:
        tag_text = "★ EDUKASI SHORTS"
        tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
        tag_w = tag_bbox[2] - tag_bbox[0]
        tag_x = (width - tag_w) // 2
        tag_y = y1 - 28
        draw.rounded_rectangle(
            [tag_x - 14, tag_y - 4, tag_x + tag_w + 14, tag_y + 20],
            radius=10,
            fill=(255, 212, 38, 255)
        )
        draw.text((tag_x, tag_y), tag_text, font=tag_font, fill=(10, 14, 24, 255))

    # 4. Teks Hook
    draw.multiline_text(
        (x1 + pad_x, y1 + pad_y),
        badge_text,
        font=font,
        fill="#FFFFFF",
        stroke_width=3,
        stroke_fill="#000000",
        spacing=10,
        align="center"
    )

    img.save(output_path, "PNG")
    return output_path

def create_caption_card(
    text: str,
    output_path: str,
    width: int = config.VIDEO_WIDTH,
    height: int = config.VIDEO_HEIGHT,
    font_size: int = 64,
    highlight: bool = True,
    style: str = "clay_pop"
) -> str:
    """
    Membuat caption card transparan berformat Shorts Edukasi Modern:
    - clay_pop (Default): Gaya plastisin clay stop-motion, rounded dark backing dengan border clay yellow/white & 3D bevel.
    - kinetic_bold: Teks besar tanpa kotak kaku, stroke 9px, multi-layer drop shadow 3D (Gaya viral MrBeast / Vox).
    - neon_badge: Rounded glass badge semi-transparan dengan aksen neon yellow & teks kontras.
    - cyber_cyan: Rounded glass badge dengan aksen neon cyan futuristik.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_candidates = [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf"
    ]
    font = None
    for fc in font_candidates:
        if os.path.exists(fc):
            try:
                font = ImageFont.truetype(fc, font_size)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    words = text.strip().split()
    lines = []
    current_line = []
    max_line_width = width - 240
    
    for word in words:
        current_line.append(word)
        test_str = " ".join(current_line)
        bbox = draw.textbbox((0, 0), test_str, font=font)
        if (bbox[2] - bbox[0]) > max_line_width:
            current_line.pop()
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    full_text = "\n".join(lines).upper()
    
    bbox = draw.multiline_textbbox((0, 0), full_text, font=font, spacing=14, align="center")
    box_w = bbox[2] - bbox[0]
    box_h = bbox[3] - bbox[1]
    
    # Area Aman Shorts: 67% dari atas layar
    x = (width - box_w) // 2
    y = int(height * 0.67) - (box_h // 2)
    
    if style == "clay_pop":
        pad_x, pad_y = 42, 22
        # Drop shadow 3D
        draw.rounded_rectangle(
            [x - pad_x + 3, y - pad_y + 8, x + box_w + pad_x + 3, y + box_h + pad_y + 8],
            radius=26,
            fill=(0, 0, 0, 160)
        )
        # Clay card body
        draw.rounded_rectangle(
            [x - pad_x, y - pad_y, x + box_w + pad_x, y + box_h + pad_y],
            radius=26,
            fill=(12, 16, 26, 235),
            outline=(255, 212, 38, 240) if highlight else (255, 255, 255, 90),
            width=4
        )
        fill_color = "#FFDE21" if highlight else "#FFFFFF"
        draw.multiline_text(
            (x, y),
            full_text,
            font=font,
            fill=fill_color,
            stroke_width=7,
            stroke_fill="#000000",
            spacing=14,
            align="center"
        )
    elif style == "neon_badge":
        pad_x, pad_y = 38, 22
        draw.rounded_rectangle(
            [x - pad_x, y - pad_y, x + box_w + pad_x, y + box_h + pad_y],
            radius=24,
            fill=(10, 14, 24, 225),
            outline=(255, 232, 31, 140) if highlight else (255, 255, 255, 60),
            width=3
        )
        fill_color = "#FFE81F" if highlight else "#FFFFFF"
        draw.multiline_text(
            (x, y),
            full_text,
            font=font,
            fill=fill_color,
            stroke_width=6,
            stroke_fill="#000000",
            spacing=14,
            align="center"
        )
    elif style == "cyber_cyan":
        pad_x, pad_y = 38, 22
        draw.rounded_rectangle(
            [x - pad_x, y - pad_y, x + box_w + pad_x, y + box_h + pad_y],
            radius=24,
            fill=(8, 20, 36, 230),
            outline=(0, 240, 255, 160) if highlight else (255, 255, 255, 60),
            width=3
        )
        fill_color = "#00F5FF" if highlight else "#FFFFFF"
        draw.multiline_text(
            (x, y),
            full_text,
            font=font,
            fill=fill_color,
            stroke_width=6,
            stroke_fill="#020814",
            spacing=14,
            align="center"
        )
    else:
        # kinetic_bold: Multi-Layer 3D Drop Shadow
        shadow_offsets = [
            (-4, -4), (4, -4), (-4, 4), (4, 4),
            (0, 5), (0, -5), (5, 0), (-5, 0),
            (0, 7), (2, 7), (-2, 7)
        ]
        for sx, sy in shadow_offsets:
            draw.multiline_text(
                (x + sx, y + sy),
                full_text,
                font=font,
                fill="#000000",
                spacing=14,
                align="center"
            )
            
        fill_color = "#FFE81F" if highlight else "#FFFFFF"
        draw.multiline_text(
            (x, y),
            full_text,
            font=font,
            fill=fill_color,
            stroke_width=8,
            stroke_fill="#000000",
            spacing=14,
            align="center"
        )
    
    img.save(output_path, "PNG")
    return output_path

def render_animated_scene(
    image_path: str,
    captions: list[str] | str,
    audio_path: str,
    output_scene_path: str,
    motion_type: int = 1,
    caption_style: str = "kinetic_bold"
) -> str:
    """
    Me-render 1 adegan video animasi vertikal (MP4):
    1. Efek gerak kamera animasi dinamis dengan Lanczos upscaling berkualitas tinggi
    2. Lapisan partikel ambient mengambang (Ambient motion overlay)
    3. Subtitle berganti secara dinamis berdasarkan proporsi kata (Word-Count Proportional)
    4. Audio anti-kresek: Dilengkapi smooth fade-in/fade-out & digital silence padding (apad)
    """
    audio_duration = get_audio_duration(audio_path)
    padding_dur = 0.35
    total_duration = audio_duration + padding_dur
    total_frames = int(total_duration * config.VIDEO_FPS)
    fps = config.VIDEO_FPS
    
    # Siapkan captions
    if isinstance(captions, str):
        captions_list = [captions]
    else:
        captions_list = [c for c in captions if c.strip()]
    if not captions_list:
        captions_list = ["..."]

    # Hitung timing kemunculan tiap chunk subtitle berdasarkan proporsi jumlah kata
    total_words = sum(max(1, len(c.strip().split())) for c in captions_list)
    caption_files = []
    accum_time = 0.0
    
    for c_idx, text_chunk in enumerate(captions_list):
        c_png = str(Path(output_scene_path).with_suffix(f".cap_{c_idx}.png"))
        create_caption_card(text_chunk, c_png, highlight=(c_idx % 2 == 1 or len(captions_list) == 1), style=caption_style)
        
        words_in_chunk = max(1, len(text_chunk.strip().split()))
        chunk_dur = audio_duration * (words_in_chunk / total_words)
        
        t_start = accum_time
        t_end = min(total_duration, accum_time + chunk_dur) if (c_idx < len(captions_list) - 1) else total_duration
        accum_time = t_end
        caption_files.append((c_png, t_start, t_end))

    # 5 Pilihan Gerak Kamera Animasi Sinematik
    if motion_type == 1:
        # Smooth Cinematic Push-In dengan Organic Handheld Drift
        camera_filter = (
            f"zoompan=z='min(zoom+0.0016,1.22)':"
            f"x='iw/2-(iw/zoom/2)+sin(on/28)*16':"
            f"y='ih/2-(ih/zoom/2)+cos(on/32)*10':"
            f"d={total_frames}:s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={fps}"
        )
    elif motion_type == 2:
        # Character / Face Focus Zoom (Fokus ke sepertiga atas layar)
        camera_filter = (
            f"zoompan=z='min(zoom+0.0018,1.24)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/3-(ih/zoom/3)':"
            f"d={total_frames}:s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={fps}"
        )
    elif motion_type == 3:
        # Epic Pull-Back Reveal (Mundur mengungkap keseluruhan visual adegan)
        camera_filter = (
            f"zoompan=z='max(1.22-0.0015*on,1.02)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={fps}"
        )
    elif motion_type == 4:
        # Cinematic Horizontal Pan Sweep (Menyapu dari kiri ke kanan dengan micro-zoom)
        camera_filter = (
            f"zoompan=z='min(zoom+0.0012,1.15)':"
            f"x='(iw*0.35)-(iw/zoom/2)+(on/{total_frames})*(iw*0.25)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={fps}"
        )
    else:
        # Dramatic Upward Tilt / Rise (Gerak dari bawah ke atas)
        camera_filter = (
            f"zoompan=z='min(zoom+0.0014,1.18)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='(ih*0.62)-(ih/zoom/2)-(on/{total_frames})*(ih*0.2)':"
            f"d={total_frames}:s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={fps}"
        )

    # Cek partikel ambient overlay
    particles_path = config.ASSETS_DIR / "ambient_particles.mp4"
    has_particles = particles_path.exists()
    
    inputs = ["-loop", "1", "-i", image_path]
    current_input_idx = 1
    
    if has_particles:
        inputs.extend(["-stream_loop", "-1", "-i", str(particles_path)])
        particles_input_idx = current_input_idx
        current_input_idx += 1
    else:
        particles_input_idx = None

    # Tambahkan input gambar subtitle
    caption_input_indices = []
    for c_png, t_s, t_e in caption_files:
        inputs.extend(["-i", c_png])
        caption_input_indices.append((current_input_idx, t_s, t_e))
        current_input_idx += 1

    # Tambahkan input audio
    audio_input_idx = current_input_idx
    inputs.extend(["-i", audio_path])

    # Susun filter graph FFmpeg:
    # 1. Scale ke canvas tajam 1.5x (1620x2880) agar gerak kamera bebas jitter, lalu zoompan
    filters = []
    filters.append(
        f"[0:v]scale=1620:2880:flags=lanczos:force_original_aspect_ratio=increase,"
        f"crop=1620:2880,{camera_filter}[cam_raw]"
    )
    # Tambahkan color grading sinematik & vignette fokus visual
    filters.append(
        f"[cam_raw]eq=contrast=1.06:brightness=0.01:saturation=1.12,"
        f"vignette=angle=PI/7[cam]"
    )
    last_v = "[cam]"
    
    # 2. Blend ambient particles
    if has_particles:
        filters.append(f"[{particles_input_idx}:v]scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}[scaled_p]")
        filters.append(f"{last_v}[scaled_p]blend=all_mode='screen':all_opacity=0.35[with_p]")
        last_v = "[with_p]"

    # 3. Dynamic Subtitles overlays dengan animasi Spring Glide (Slide-up Pop 20px)
    for idx_tuple, (c_in, t_s, t_e) in enumerate(caption_input_indices):
        next_v = f"[v_sub_{idx_tuple}]"
        y_expr = f"(H*0.66-(h/2))+if(lt(t-{t_s:.2f},0.12),(1-(t-{t_s:.2f})/0.12)*20,0)"
        filters.append(f"{last_v}[{c_in}:v]overlay=x='(W-w)/2':y='{y_expr}':enable='between(t,{t_s:.2f},{t_e:.2f})'{next_v}")
        last_v = next_v

    # 4. Filter Audio Anti-Kresek (Smooth taper 35ms & apad silence padding)
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
        raise RuntimeError(f"FFmpeg render animated scene error: {res.stderr[-400:]}")
        
    return output_scene_path

def combine_scenes_to_short(
    scene_video_paths: list[str],
    final_output_path: str,
    bgm_path: str = None,
    header_badge_path: str = None,
    enable_progress_bar: bool = True,
    enable_sfx: bool = True
) -> str:
    """
    Menggabungkan seluruh video scene dengan:
    1. Transisi audio mulus (acrossfade 80ms)
    2. Header Hook Badge di bagian atas layar (~12-14%)
    3. Dynamic animated progress bar yang berjalan dari 0% ke 100%
    4. Sound FX: Pop accent pada pembuka dan Whoosh transitions antar adegan
    5. Ambient Background Music (BGM) loopable dengan audio ducking otomatis
    """
    if not scene_video_paths:
        raise ValueError("Daftar scene kosong!")

    temp_concat_output = str(config.TEMP_DIR / "combined_no_bgm.mp4")

    # 1. Hitung durasi tiap scene untuk kalkulasi timestamp transisi
    scene_durations = [get_audio_duration(p) for p in scene_video_paths]

    # Concat adegan
    if len(scene_video_paths) == 1:
        import shutil
        shutil.copy(scene_video_paths[0], temp_concat_output)
    else:
        inputs = []
        for p in scene_video_paths:
            inputs.extend(["-i", p])
            
        num_clips = len(scene_video_paths)
        filter_parts = []
        v_concat_inputs = "".join(f"[{i}:v]" for i in range(num_clips))
        filter_parts.append(f"{v_concat_inputs}concat=n={num_clips}:v=1:a=0[outv]")
        
        last_a = "[0:a]"
        for i in range(1, num_clips):
            next_a = f"[cross_a_{i}]"
            filter_parts.append(f"{last_a}[{i}:a]acrossfade=d=0.08:c1=tri:c2=tri{next_a}")
            last_a = next_a

        full_filter = ";".join(filter_parts)
        
        cmd_concat = [
            config.FFMPEG_EXE, "-y",
            *inputs,
            "-filter_complex", full_filter,
            "-map", "[outv]",
            "-map", last_a,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            temp_concat_output
        ]
        
        res = subprocess.run(cmd_concat, capture_output=True, text=True)
        if res.returncode != 0:
            concat_list_file = config.TEMP_DIR / "scenes_list.txt"
            with open(concat_list_file, "w", encoding="utf-8") as f:
                for p in scene_video_paths:
                    clean_p = str(Path(p).resolve()).replace("\\", "/")
                    f.write(f"file '{clean_p}'\n")
            cmd_demuxer = [
                config.FFMPEG_EXE, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_file),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "192k",
                temp_concat_output
            ]
            res2 = subprocess.run(cmd_demuxer, capture_output=True, text=True)
            if res2.returncode != 0:
                raise RuntimeError(f"FFmpeg concat error: {res2.stderr[-400:]}")

    # 2. Total duration
    total_duration = get_audio_duration(temp_concat_output)

    # 3. Kumpulkan input & filter untuk video embellishment (Header Badge & Progress Bar)
    # serta audio embellishment (SFX & BGM)
    embellish_inputs = ["-i", temp_concat_output]
    next_input_idx = 1
    v_filters = []
    current_v = "[0:v]"

    # Overlay Header Badge jika aktif
    if header_badge_path and os.path.exists(header_badge_path):
        embellish_inputs.extend(["-i", header_badge_path])
        badge_idx = next_input_idx
        next_input_idx += 1
        # Animasi spring slide-down dari atas di detik 0-0.22
        v_filters.append(f"{current_v}[{badge_idx}:v]overlay=x=0:y='if(lt(t,0.22),(1-(t/0.22))*(-50),0)':enable='gte(t,0)'[with_badge]")
        current_v = "[with_badge]"

    # Progress bar dinamis (0% -> 100% dari total durasi)
    if enable_progress_bar and total_duration > 0.5:
        progress_track = "drawbox=x=40:y=24:w=1000:h=8:color=white@0.25:t=fill"
        progress_fill = f"drawbox=x=40:y=24:w='1000*min(1,t/{total_duration:.2f})':h=8:color=0xFFD426@1:t=fill"
        v_filters.append(f"{current_v}{progress_track},{progress_fill}[with_prog]")
        current_v = "[with_prog]"

    # Audio mixing setup
    a_filters = [f"[0:a]aformat=channel_layouts=stereo,volume=1.0[voice_a]"]
    mix_sources = ["[voice_a]"]

    # Sound FX (Pop on opening & Whooshes at scene cuts)
    sfx_pop_path = config.ASSETS_DIR / "sfx_pop.wav"
    sfx_whoosh_path = config.ASSETS_DIR / "sfx_whoosh.wav"

    if enable_sfx and sfx_pop_path.exists():
        embellish_inputs.extend(["-i", str(sfx_pop_path)])
        pop_idx = next_input_idx
        next_input_idx += 1
        a_filters.append(f"[{pop_idx}:a]aformat=channel_layouts=stereo,adelay=100|100,volume=0.45[pop_a]")
        mix_sources.append("[pop_a]")

    if enable_sfx and sfx_whoosh_path.exists() and len(scene_durations) > 1:
        accum_t = 0.0
        for s_i in range(len(scene_durations) - 1):
            accum_t += scene_durations[s_i]
            trans_ms = max(50, int(accum_t * 1000))
            embellish_inputs.extend(["-i", str(sfx_whoosh_path)])
            whoosh_idx = next_input_idx
            next_input_idx += 1
            a_filters.append(f"[{whoosh_idx}:a]aformat=channel_layouts=stereo,adelay={trans_ms}|{trans_ms},volume=0.55[whoosh_a_{s_i}]")
            mix_sources.append(f"[whoosh_a_{s_i}]")

    # BGM mixing
    if not bgm_path:
        bgm_candidates = list(config.ASSETS_DIR.glob("*.mp3"))
        if bgm_candidates:
            bgm_path = str(bgm_candidates[0])

    if bgm_path and os.path.exists(bgm_path):
        embellish_inputs.extend(["-stream_loop", "-1", "-i", bgm_path])
        bgm_idx = next_input_idx
        next_input_idx += 1
        a_filters.append(f"[{bgm_idx}:a]aformat=channel_layouts=stereo,volume=0.10[bgm_a]")
        mix_sources.append("[bgm_a]")

    # Mix audio
    if len(mix_sources) > 1:
        inputs_str = "".join(mix_sources)
        a_filters.append(f"{inputs_str}amix=inputs={len(mix_sources)}:duration=first:dropout_transition=0[a_final]")
        final_a = "[a_final]"
    else:
        final_a = "[voice_a]"

    # Jika tidak ada video filter sama sekali
    if not v_filters:
        v_filters.append(f"[0:v]copy[v_final]")
        final_v = "[v_final]"
    else:
        final_v = current_v

    full_filter_complex = ";".join(v_filters + a_filters)

    cmd_final = [
        config.FFMPEG_EXE, "-y",
        *embellish_inputs,
        "-filter_complex", full_filter_complex,
        "-map", final_v,
        "-map", final_a,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(total_duration),
        final_output_path
    ]

    res_final = subprocess.run(cmd_final, capture_output=True, text=True)
    if res_final.returncode == 0:
        return final_output_path

    # Fallback jika embellish kompleks error
    import shutil
    shutil.copy(temp_concat_output, final_output_path)
    return final_output_path
