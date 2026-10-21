import sys
import os
from pathlib import Path

# Tangani encoding Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
import pipeline
import youtube_uploader

def print_banner():
    print("""
============================================================
   *** CREATOR VIDEO ILUSTRASI ANIMASI YOUTUBE SHORTS ***
         Powered by Google AI Studio & Gemini
============================================================
    """)

def check_env():
    if not config.GEMINI_API_KEY:
        print("[!] ERROR: GEMINI_API_KEY belum disetel di file .env!")
        print("    Harap buka file .env dan masukkan API Key dari Google AI Studio.")
        return False
    return True

def list_output_videos():
    videos = list(config.OUTPUT_DIR.glob("*.mp4"))
    return sorted(videos, key=lambda x: x.stat().st_mtime, reverse=True)

def choose_animation_style():
    print("\nPilih Gaya Ilustrasi Animasi:")
    print("1. 3D Pixar / Disney Animation (Karakter 3D ekspresif, warna cerah sinematik - Rekomendasi Viral)")
    print("2. Anime / Studio Ghibli Style (Ilustrasi anime estetis, pemandangan magis)")
    print("3. Modern Comic / Motion Graphic (Gaya komik modern dinamis)")
    choice = input("Pilihan (1/2/3, default 1): ").strip()
    style_map = {
        "1": "3D Pixar Animation",
        "2": "Studio Ghibli Anime Illustration",
        "3": "Modern Dynamic Comic Animation"
    }
    return style_map.get(choice, "3D Pixar Animation")

def main():
    print_banner()
    if not check_env():
        sys.exit(1)

    while True:
        print("\nPilih Menu:")
        print("1. Buat Video Ilustrasi Animasi Baru (Simpan ke folder output)")
        print("2. Buat Video Animasi dan Langsung Upload ke YouTube")
        print("3. Upload Video yang Sudah Ada ke YouTube")
        print("4. Tes Koneksi Google AI Studio")
        print("5. Keluar")

        choice = input("\nMasukkan pilihan (1-5): ").strip()

        if choice == "1":
            topic = input("\nMasukkan topik video (Contoh: 'Fakta Hewan Gurita', 'Misteri Lubang Hitam'): ").strip()
            if not topic:
                topic = "Fakta Menarik Hewan Bawah Laut"
            anim_style = choose_animation_style()
            try:
                pipeline.create_short_video(topic=topic, animation_style=anim_style, auto_upload=False)
            except Exception as e:
                print(f"\n[!] Terjadi error saat pembuatan video animasi: {e}")

        elif choice == "2":
            topic = input("\nMasukkan topik video: ").strip()
            if not topic:
                topic = "Fakta Menarik Alam Semesta"
            anim_style = choose_animation_style()
            
            print("\nPilih status privasi video di YouTube:")
            print("1. Unlisted (Hanya yang punya link bisa nonton - Rekomendasi)")
            print("2. Private (Hanya Anda yang bisa nonton)")
            print("3. Public (Langsung tayang ke publik)")
            p_choice = input("Pilihan (1/2/3, default 1): ").strip()
            status_map = {"1": "unlisted", "2": "private", "3": "public"}
            privacy = status_map.get(p_choice, "unlisted")
            
            try:
                pipeline.create_short_video(topic=topic, animation_style=anim_style, auto_upload=True, privacy_status=privacy)
            except Exception as e:
                print(f"\n[!] Terjadi error: {e}")

        elif choice == "3":
            videos = list_output_videos()
            if not videos:
                print("\n[!] Belum ada video .mp4 di folder 'output/'. Silakan buat video dulu (Menu 1).")
                continue
            
            print("\nDaftar Video di Folder Output:")
            for idx, v in enumerate(videos, 1):
                print(f"{idx}. {v.name}")
            
            v_idx = input(f"\nPilih nomor video (1-{len(videos)}): ").strip()
            try:
                selected_video = videos[int(v_idx) - 1]
            except Exception:
                print("[!] Pilihan nomor video tidak valid.")
                continue
            
            title = input(f"Masukkan judul video (Tekan Enter untuk '{selected_video.stem}'): ").strip()
            if not title:
                title = f"{selected_video.stem} #Shorts"
            
            desc = input("Masukkan deskripsi video (Tekan Enter untuk default): ").strip()
            if not desc:
                desc = "Tonton video animasi fakta menarik ini sampai habis! Jangan lupa like dan subscribe. #Shorts #Animasi #FaktaUnik"
                
            p_choice = input("Privasi upload (1: Unlisted, 2: Private, 3: Public, default 1): ").strip()
            status_map = {"1": "unlisted", "2": "private", "3": "public"}
            privacy = status_map.get(p_choice, "unlisted")
            
            try:
                youtube_uploader.upload_video(
                    video_path=str(selected_video),
                    title=title,
                    description=desc,
                    privacy_status=privacy
                )
            except Exception as e:
                print(f"\n[!] Gagal upload: {e}")

        elif choice == "4":
            print("\n[*] Menjalankan diagnosa Google AI Studio...")
            try:
                import ai_services
                script = ai_services.generate_script("Fakta Singkat Gurita", "3D Pixar Animation")
                print("[+] Script & Concept generator: OK!")
                v_file = ai_services.generate_voice("Ini adalah tes suara animasi Google AI Studio", str(config.TEMP_DIR / "diag_voice.wav"))
                print(f"[+] Google TTS Voiceover: OK! ({v_file})")
                img_file = ai_services.generate_image("A cute cartoon octopus floating in glowing water", str(config.TEMP_DIR / "diag_image.jpg"))
                print(f"[+] AI Animated Artwork: OK! ({img_file})")
                print("\n[+] Semua layanan AI siap digunakan!")
            except Exception as e:
                print(f"[!] Diagnosa gagal: {e}")

        elif choice == "5":
            print("\nSampai jumpa!")
            break
        else:
            print("[!] Pilihan tidak dikenali.")

if __name__ == "__main__":
    main()
