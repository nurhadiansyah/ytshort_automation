import json
import re
import time
import wave
import random
import subprocess
import urllib.parse
import requests
from pathlib import Path
from PIL import Image, ImageDraw
from google import genai
from google.genai import types

import config

def get_client() -> genai.Client:
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY belum disetel! Harap periksa file .env Anda.")
    return genai.Client(api_key=config.GEMINI_API_KEY)

def generate_script(
    topic: str = "Fakta Menarik Sains Luar Angkasa",
    animation_style: str = "Handcrafted Claymation Animation",
    scene_count: int = 5
) -> dict:
    """
    Menghasilkan Storyboard Terpadu Video Shorts Edukasi Viral (High-Retention Educational Shorts):
    - Hook Rasa Penasaran (Curiosity Gap) di detik awal tanpa basa-basi
    - Pacing cepat dengan 4-5 adegan berdurasi 5-6 detik per adegan
    - Penjelasan analogi ilmiah/sejarah yang mudah divisualisasikan
    - Kontinuitas karakter tanah liat (Claymation) konsisten di setiap adegan
    - Subtitle dinamis (kinetic captions) per adegan
    - Call to action berupa pertanyaan pemicu interaksi komentar (Call to Debate)
    """
    client = get_client()

    is_clay = any(k in animation_style.lower() for k in ["clay", "plastisin", "claymation", "stop-motion"])
    clay_instruction = """
PANDUAN KHUSUS GAYA CLAYMATION (ANIMASI TANAH LIAT / PLASTISIN):
- Seluruh subjek, karakter, dan benda harus terbuat dari tanah liat plastisin buatan tangan (sculpted plasticine clay).
- Tekstur visual: terlihat guratan tangan halus, sidik jari (subtle fingerprints), dan tekstur matte/glossy khas Play-Doh / Plasticine.
- Karakter utama konsisten: Buat figur maskot tanah liat lucu 'Pico' (a friendly curious clay character) atau karakter plastisin yang sesuai dengan topik, dan pertahankan figur ini di SETIAP adegan!
- Suasana: Miniatur meja diorama (tabletop miniature diorama set) dengan pencahayaan studio makro (macro photography lighting) dan kedalaman bidang dangkal (shallow depth of field).
""" if is_clay else ""

    scenes_structure = f"""
STRUKTUR {scene_count} ADEGAN CEPAT (HIGH-RETENTION SHORTS):
- Adegan 1 (Detik 0-5: The Hook): Buka langsung dengan fakta paradoks atau pertanyaan mengejutkan tanpa salam pembuka klise.
- Adegan 2 (Detik 5-10: Analogi Sederhana): Jelaskan konsepnya dengan analogi visual yang sangat mudah dibayangkan.
- Adegan 3 (Detik 10-15: Mekanisme Inti): Perlihatkan cara kerja atau visual mendalamnya.
- Adegan 4 (Detik 15-20: Fakta Bikin Kaget / Twist): Tambahkan satu fakta pemungkas yang jarang diketahui orang.
- Adegan 5 (Detik 20-25: Call to Debate): Lempar pertanyaan seru yang memicu penonton berdebat di kolom komentar Shorts!
""" if scene_count == 5 else f"""
STRUKTUR {scene_count} ADEGAN:
- Adegan 1: Hook pembuka yang memicu rasa ingin tahu.
- Adegan 2: Analogi & mekanisme ilmiah/sejarah inti.
- Adegan 3: Fakta twist pemungkas & pertanyaan diskusi komentar.
"""

    prompt = f"""
Kamu adalah sutradara animasi stop-motion dan kreator konten YouTube Shorts Edukasi viral kelas dunia.
Tugasmu adalah merancang SATU KESATUAN STORYBOARD VIDEO SHORTS EDUKASI LENGKAP untuk topik: "{topic}".
Total Adegan yang diinginkan: {scene_count} ADEGAN.

PENTING - FORMULA SHORTS EDUKASI VIRAL (HIGH-RETENTION):
1. DILARANG KERAS menggunakan sapaan klise pembuka seperti "Halo teman-teman", "Kembali lagi", dll. Penonton akan langsung scroll pergi!
{scenes_structure}
2. KONSISTENSI VISUAL: Karakter/subjek utama, palet warna, dan gaya "{animation_style}" harus kohesif dan bersambung dari adegan 1 sampai {scene_count}.
{clay_instruction}
3. Narasi menggunakan Bahasa Indonesia yang memukau, ekspresif, dan santai (gaya kreator animasi viral).
4. Setiap adegan memiliki narasi ringkas (12-18 kata) yang dibagi menjadi 2 atau 3 potongan subtitle (`captions`) pendek (3-5 kata per caption) untuk ritme bicara yang sangat dinamis.
5. Setiap adegan memiliki `image_prompt` (dalam Bahasa Inggris) yang SANGAT DETAIL, SPESIFIK, dan SESUAI GAYA VISUAL:
   - Format wajib: Rasio 9:16 vertikal (portrait), pencahayaan sinematik dramatis, detail 8k, tanpa teks watermark.

Format Output WAJIB berupa JSON murni persis seperti ini:
{{
  "title": "Judul Edukasi Bombastis Bikin Melongo #Shorts #Edukasi #Sains",
  "description": "Deskripsi lengkap video edukasi dengan hashtag populer",
  "tags": ["shorts", "edukasi", "sains", "fakta unik", "animasi"],
  "visual_theme": "Deskripsi singkat konsistensi karakter utama dan tema warna dunia animasi",
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "Pernah kebayang gak, ada robot yang bisa mikir dan kerja sendiri tanpa disuruh?",
      "captions": [
        "Pernah kebayang gak...",
        "Robot yang bisa mikir,",
        "Dan kerja sendiri!"
      ],
      "camera_motion": "zoom_in",
      "image_prompt": "Handcrafted claymation stop-motion of a cute expressive plasticine clay robot named Pico sitting on a miniature wooden work desk surrounded by tiny sculpted plasticine books and glowing clay lightbulb above its head, macro studio lighting, visible clay thumbprint textures, vertical 9:16 aspect ratio, 8k render"
    }}
  ]
}}
"""
    candidate_models = [config.TEXT_MODEL, "gemini-3.8-flash", "gemini-3-flash", "gemini-flash-latest"]
    response = None
    last_err = None
    
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                print(f"[*] Merancang naskah shorts edukasi via Gemini ({model_name}) untuk topik: '{topic}'...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                if response and response.text:
                    break
            except Exception as e:
                last_err = e
                print(f"[!] Info model {model_name} (percobaan {attempt+1}): {e}")
                time.sleep(2)
        if response and response.text:
            break
            
    if not response or not response.text:
        raise RuntimeError(f"Gagal menghasilkan naskah animasi setelah mencoba semua model: {last_err}")
    
    text = response.text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        script_data = json.loads(text)
        print(f"[+] Master Storyboard Edukasi Berhasil Dibuat!")
        print(f"    Judul       : '{script_data.get('title')}'")
        print(f"    Tema Visual : {script_data.get('visual_theme', '3D Pixar')}")
        print(f"    Total Adegan: {len(script_data.get('scenes', []))}")
        return script_data
    except Exception as e:
        print(f"[-] Gagal parse JSON: {e}")
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise

def generate_voice(text: str, output_path: str, voice_name: str = "id-ID-ArdiNeural") -> str:
    """
    Menghasilkan voiceover edukasi berkualitas tinggi 24kHz.
    Mendukung Microsoft Neural Voice (Ardi / Gadis) instan tanpa batas kuota,
    serta Google AI Studio TTS jika dipilih.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[*] Menghasilkan audio voiceover untuk: '{text[:40]}...' (Voice: {voice_name})")
    
    # 1. Jika voice adalah Edge-TTS (Ardi / Gadis), langsung eksekusi tanpa delay
    is_edge = any(k in voice_name.lower() for k in ["edge", "ardi", "gadis", "neural", "id-id"])
    if is_edge:
        try:
            import asyncio
            import edge_tts
            
            edge_voice = "id-ID-GadisNeural" if "gadis" in voice_name.lower() else "id-ID-ArdiNeural"
            
            async def _run_edge():
                communicate = edge_tts.Communicate(text, edge_voice, rate="+6%")
                temp_mp3 = Path(output_path).with_suffix(".temp.mp3")
                await communicate.save(str(temp_mp3))
                
                cmd = [
                    config.FFMPEG_EXE, "-y",
                    "-i", str(temp_mp3),
                    "-ar", "24000",
                    "-ac", "1",
                    str(output_file)
                ]
                subprocess.run(cmd, capture_output=True)
                if temp_mp3.exists():
                    temp_mp3.unlink()
                    
            asyncio.run(_run_edge())
            if output_file.exists() and output_file.stat().st_size > 1000:
                print(f"[+] Audio voiceover ({edge_voice}) disimpan di: {output_file}")
                return str(output_file)
        except Exception as edge_err:
            print(f"[!] Info Edge-TTS error, mencoba alternatif: {edge_err}")

    # 2. Coba Google AI Studio TTS
    client = get_client()
    tts_models = [config.TTS_MODEL, "gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview"]
    pcm_bytes = None
    last_err = None
    
    for model_name in tts_models:
        for attempt in range(2):
            try:
                google_voice = voice_name if voice_name in ["Puck", "Charon", "Kore", "Fenrir", "Aoede"] else "Puck"
                response = client.models.generate_content(
                    model=model_name,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=google_voice
                                )
                            )
                        )
                    )
                )
                for cand in response.candidates:
                    if cand.content and cand.content.parts:
                        for part in cand.content.parts:
                            if part.inline_data and part.inline_data.data:
                                pcm_bytes = part.inline_data.data
                                break
                if pcm_bytes:
                    break
            except Exception as e:
                last_err = e
                time.sleep(1.5)
        if pcm_bytes:
            break
            
    if pcm_bytes:
        with wave.open(str(output_file), "wb") as wav_file:
            wav_file.setnchannels(1)      # Mono
            wav_file.setsampwidth(2)      # 16-bit
            wav_file.setframerate(24000)  # 24 kHz
            wav_file.writeframes(pcm_bytes)
        print(f"[+] Audio voiceover (Google TTS 24kHz) disimpan di: {output_file}")
        return str(output_file)

    # 3. Fallback cerdas ke Microsoft Neural Voice jika Google gagal
    print("[*] Fallback ke Microsoft Neural Voice (id-ID-ArdiNeural)...")
    try:
        import asyncio
        import edge_tts
        
        async def _run_fallback_edge():
            communicate = edge_tts.Communicate(text, "id-ID-ArdiNeural", rate="+6%")
            temp_mp3 = Path(output_path).with_suffix(".temp.mp3")
            await communicate.save(str(temp_mp3))
            
            cmd = [
                config.FFMPEG_EXE, "-y",
                "-i", str(temp_mp3),
                "-ar", "24000",
                "-ac", "1",
                str(output_file)
            ]
            subprocess.run(cmd, capture_output=True)
            if temp_mp3.exists():
                temp_mp3.unlink()
                
        asyncio.run(_run_fallback_edge())
        if output_file.exists() and output_file.stat().st_size > 1000:
            print(f"[+] Audio voiceover (Neural Voice Fallback) disimpan di: {output_file}")
            return str(output_file)
    except Exception as edge_err:
        print(f"[!] Error Fallback Edge-TTS: {edge_err}")

    raise RuntimeError(f"Gagal menghasilkan audio voiceover: {last_err}")

def create_emergency_backdrop(output_file: Path, prompt_hint: str = ""):
    """
    Menghasilkan ilustrasi claymation berkualitas tinggi dari aset master claymation
    jika API pihak ketiga mengalami pembatasan kuota atau penagihan.
    Menghilangkan sama sekali latar bintang/luar angkasa.
    """
    from PIL import Image, ImageOps
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    clay_dir = config.BASE_DIR / "assets" / "claymation"
    hint_lower = prompt_hint.lower()
    
    selected_asset = None
    if clay_dir.exists():
        # Pencocokan tema cerdas
        if any(k in hint_lower for k in ["paus", "whale", "ikan", "jantung", "laut", "ocean", "golf"]):
            target = clay_dir / "whale_golfcart.jpg"
            if target.exists(): selected_asset = target
        elif any(k in hint_lower for k in ["cyber", "keamanan", "hacker", "siber", "sandi", "kabel", "charger", "data", "firewall"]):
            target = clay_dir / "cyber_security.jpg"
            if target.exists(): selected_asset = target
        elif any(k in hint_lower for k in ["tiket", "liburan", "koper", "travel", "bandara", "asisten", "scene 2", "scene_2"]):
            target = clay_dir / "scene_2_travel.jpg"
            if target.exists(): selected_asset = target
        elif any(k in hint_lower for k in ["otak", "gear", "persepsi", "pikiran", "mata", "tangan", "mekanisme", "scene 3", "scene_3"]):
            target = clay_dir / "scene_3_mind.jpg"
            if target.exists(): selected_asset = target
        elif any(k in hint_lower for k in ["kota", "town", "gosip", "kafe", "ramai", "banyak", "komunitas", "scene 4", "scene_4"]):
            target = clay_dir / "scene_4_city.jpg"
            if target.exists(): selected_asset = target
        elif any(k in hint_lower for k in ["tanya", "pertanyaan", "malas", "jenius", "question", "manusia", "scene 5", "scene_5"]):
            target = clay_dir / "scene_5_question.jpg"
            if target.exists(): selected_asset = target
        elif any(k in hint_lower for k in ["desk", "meja", "kerja", "otonom", "chatgpt", "scene 1", "scene_1"]):
            target = clay_dir / "scene_1_desk.jpg"
            if target.exists(): selected_asset = target
            
        # Jika belum ada yang cocok, gunakan file yang ada di assets/claymation
        if not selected_asset:
            clay_files = list(clay_dir.glob("*.jpg"))
            if clay_files:
                # Pilih berdasarkan hash prompt agar konsisten untuk prompt yang sama
                idx = abs(hash(prompt_hint)) % len(clay_files)
                selected_asset = clay_files[idx]
                
    if selected_asset and selected_asset.exists():
        try:
            with Image.open(selected_asset) as img:
                # Crop & scale pas ke 1080x1920 (9:16 vertikal YouTube Shorts)
                img_fitted = ImageOps.fit(img, (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), method=Image.Resampling.LANCZOS)
                img_fitted.save(str(output_file), "JPEG", quality=95)
                print(f"[+] Berhasil memuat visual Claymation Otentik ({selected_asset.name}) -> {output_file.name}")
                return
        except Exception as e:
            print(f"[!] Gagal fit clay asset: {e}")
            
    # Fallback murni jika folder assets hilang: Buat tekstur meja kayu claymation hangat (Bukan Bintang/Luar Angkasa)
    img = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), (180, 140, 100))
    img.save(str(output_file), "JPEG", quality=90)

def generate_image_huggingface(prompt: str, output_file: Path, is_clay: bool = True) -> bool:
    """
    Cadangan AI: Menghasilkan gambar via Hugging Face Inference API (FLUX.1-schnell / SDXL).
    Hanya aktif jika HUGGINGFACE_API_KEY disetel di file .env.
    """
    hf_token = getattr(config, "HUGGINGFACE_API_KEY", "") or os.getenv("HF_TOKEN", "")
    if not hf_token:
        return False

    extra_tokens = (
        "handcrafted claymation stop-motion style, cute expressive plasticine clay characters, realistic clay texture with subtle fingerprints, miniature tabletop diorama set, warm macro studio lighting, shallow depth of field, tilt-shift lens blur, vibrant colorful clay, vertical 9:16 portrait, masterpiece, 8k render"
        if is_clay else
        "vertical 9:16 portrait, vibrant rich colors, cinematic lighting, masterpiece, 8k render"
    )
    clean_p = prompt.replace("'", " ").replace('"', ' ').replace("\n", " ").strip()
    full_prompt = f"{clean_p}, {extra_tokens}"[:500]

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0"
    ]

    for model_id in models:
        for api_url in [
            f"https://api-inference.huggingface.co/models/{model_id}",
            f"https://router.huggingface.co/hf-inference/models/{model_id}"
        ]:
            try:
                print(f"[*] [Cadangan HF] Menghubungi Hugging Face ({model_id})...")
                payload = {
                    "inputs": full_prompt,
                    "parameters": {"width": 720, "height": 1280}
                }
                resp = requests.post(api_url, headers=headers, json=payload, timeout=25)
                if resp.status_code == 200 and len(resp.content) > 3000:
                    with open(str(output_file), "wb") as f:
                        f.write(resp.content)
                    print(f"[+] BERHASIL! Gambar AI dibuat via Hugging Face ({model_id}): {output_file.name}")
                    return True
                elif resp.status_code == 503:
                    print(f"[!] Hugging Face ({model_id}) sedang proses loading model (503)...")
                elif resp.status_code == 401:
                    print(f"[!] Token Hugging Face tidak valid (HTTP 401). Memeriksa cadangan berikutnya...")
                    return False
                else:
                    print(f"[!] Hugging Face info ({resp.status_code}): {resp.text[:80]}")
            except Exception as e:
                print(f"[!] Info Hugging Face ({model_id}): {e}")
    return False

def generate_image(prompt: str, output_path: str, visual_theme: str = "") -> str:
    """
    Menghasilkan ilustrasi animasi resolusi tinggi 9:16 vertikal.
    Menerapkan sistem multi-tier generator gambar:
    1. Google AI Studio (Gemini Image Models)
    2. Cadangan 1: Hugging Face (FLUX.1-schnell) jika token diisi
    3. Cadangan 2: Pollinations.ai (FLUX / Sana Engine - 100% Free tanpa API key)
    4. Cadangan Darurat: Master Handcrafted Claymation Assets
    """
    client = get_client()
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    is_clay = any(k in (prompt + visual_theme).lower() for k in ["clay", "plastisin", "claymation", "stop-motion"])

    # 1. ENGINE UTAMA: Google AI Studio (Gemini Image Models)
    google_image_models = [
        config.IMAGE_MODEL,
        "gemini-3.1-flash-image",
        "gemini-3.1-flash-lite-image",
        "gemini-3-pro-image-preview",
        "gemini-2.5-flash-image"
    ]
    
    google_prompt = (
        f"Handcrafted Claymation stop-motion style illustration: {prompt}. "
        f"Plasticine clay figures with subtle fingerprints, miniature tabletop diorama, macro photography lighting, shallow depth of field, vertical 9:16 aspect ratio, 8k render."
        if is_clay else
        f"High quality animated illustration: {prompt}. Vertical 9:16 aspect ratio, vibrant colors, 8k digital render."
    )

    for g_model in google_image_models:
        try:
            print(f"[*] [Utama] Menghubungi Google AI Studio ({g_model}) untuk generate gambar...")
            resp = client.models.generate_content(
                model=g_model,
                contents=google_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"]
                )
            )
            for cand in resp.candidates:
                if cand.content and cand.content.parts:
                    for part in cand.content.parts:
                        if part.inline_data and part.inline_data.data:
                            with open(str(output_file), "wb") as f:
                                f.write(part.inline_data.data)
                            print(f"[+] BERHASIL! Gambar dibuat langsung oleh Google AI Studio ({g_model}): {output_file}")
                            return str(output_file)
        except Exception as g_err:
            err_msg = str(g_err)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                print(f"[!] Info Google AI Studio ({g_model}): Kuota gambar akun Google Free Tier berbatas 0 (memerlukan billing Pay-As-You-Go).")
                break # Jika akun belum billing, lewati model Google lainnya agar proses cepat
            else:
                print(f"[!] Info Google AI Studio ({g_model}): {g_err}")

    # 2. ENGINE CADANGAN 1: Hugging Face FLUX.1-schnell (Jika HUGGINGFACE_API_KEY disetel di .env)
    if getattr(config, "HUGGINGFACE_API_KEY", ""):
        hf_ok = generate_image_huggingface(prompt, output_file, is_clay=is_clay)
        if hf_ok and output_file.exists():
            return str(output_file)

    # 3. ENGINE CADANGAN 2 (FLUX.1 & Turbo Engine Tanpa Batas Kuota - 100% Free):
    if is_clay:
        extra_tokens = "handcrafted claymation stop-motion style, cute expressive plasticine clay characters, realistic clay texture with subtle fingerprints, miniature tabletop diorama set, warm macro studio lighting, shallow depth of field, tilt-shift lens blur, vibrant colorful clay, vertical 9:16 portrait, masterpiece, 8k render"
    else:
        extra_tokens = "vertical 9:16 portrait, vibrant rich colors, cinematic lighting, masterpiece, 8k render"
        
    # Bersihkan kutip dan batasi panjang teks agar URL selalu valid dan cepat di-generate
    clean_p = prompt.replace("'", " ").replace('"', ' ').replace("\n", " ").strip()
    full_prompt = f"{clean_p}, {extra_tokens}"[:500]
    encoded_prompt = urllib.parse.quote(full_prompt)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    models_to_try = ["flux", "sana", ""]
    pollen_gated = False
    for model_name in models_to_try:
        if pollen_gated:
            break
        for attempt in range(1):
            seed = random.randint(100000, 9999999)
            model_query = f"&model={model_name}" if model_name else ""
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=720&height=1280&nologo=true&seed={seed}{model_query}"
            try:
                print(f"[*] Menghubungi AI Image Engine (Pollinations {model_name or 'standard'})...")
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code == 200 and len(resp.content) > 3000:
                    with open(str(output_file), "wb") as f:
                        f.write(resp.content)
                    print(f"[+] Gambar AI berhasil dibuat & disimpan ({len(resp.content)//1024} KB): {output_file}")
                    return str(output_file)
                elif resp.status_code == 402:
                    print(f"[!] Pollinations memerlukan kredit berbayar (HTTP 402). Mengalihkan ke Master Clay Diorama...")
                    pollen_gated = True
                    break
            except Exception as pe:
                print(f"[!] Info image engine ({model_name or 'standard'}): {pe}")
            
    # 4. ENGINE CADANGAN DARURAT: Visual Clay Diorama Otentik
    print("[*] Menggunakan ilustrasi visual Master Handcrafted Claymation...")
    create_emergency_backdrop(output_file, prompt)
    return str(output_file)
