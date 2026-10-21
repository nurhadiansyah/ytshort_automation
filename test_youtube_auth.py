import os
import sys
from pathlib import Path

# Tangani encoding console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
import youtube_uploader

def test_connection():
    print("=" * 60)
    print("🔐 TES SAMBUNGAN AKUN YOUTUBE DATA API v3")
    print("=" * 60)

    client_secret = config.BASE_DIR / config.YOUTUBE_CLIENT_SECRET_FILE
    token_file = config.BASE_DIR / "token.json"

    if not client_secret.exists():
        print(f"\n[!] FILE BELUM ADA: '{client_secret.name}' tidak ditemukan di:")
        print(f"    {config.BASE_DIR}")
        print("\nSilakan ikuti panduan berikut:")
        print("1. Buka Google Cloud Console: https://console.cloud.google.com/")
        print("2. Aktifkan 'YouTube Data API v3'")
        print("3. Buat Kredensial -> OAuth client ID -> Desktop App")
        print("4. Unduh JSON kredensial dan simpan sebagai 'client_secret.json' di folder proyek.")
        return False

    print(f"\n[+] File kredensial ditemukan: '{client_secret.name}'")
    print("[*] Melakukan otentikasi login YouTube...")
    print("    (Jendela browser akan terbuka jika ini pertama kali Anda login)")

    try:
        service = youtube_uploader.get_authenticated_service()
        
        # Ambil info channel untuk memverifikasi sambungan
        request = service.channels().list(
            part="snippet,statistics",
            mine=True
        )
        response = request.execute()

        items = response.get("items", [])
        if items:
            ch = items[0]
            title = ch.get("snippet", {}).get("title", "Tidak diketahui")
            subs = ch.get("statistics", {}).get("subscriberCount", "0")
            vids = ch.get("statistics", {}).get("videoCount", "0")

            print("\n" + "=" * 60)
            print("🎉 BERHASIL TERHUBUNG DENGAN CHANNEL YOUTUBE ANDA!")
            print(f"   Nama Channel   : {title}")
            print(f"   Subscribers    : {subs}")
            print(f"   Total Video    : {vids}")
            print(f"   Status File    : token.json tersimpan dengan aman.")
            print("=" * 60)
            print("\nKini sistem sudah siap 100% untuk mengunggah 5 video terjadwal per hari!")
            return True
        else:
            print("[+] Login berhasil, namun tidak ditemukan channel YouTube di akun Google ini.")
            return True

    except Exception as e:
        print(f"\n[!] Gagal otentikasi YouTube: {e}")
        return False

if __name__ == "__main__":
    test_connection()
