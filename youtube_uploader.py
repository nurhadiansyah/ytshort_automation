import os
import sys
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

import config

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

def check_auth_status() -> dict:
    """
    Cek status otentikasi YouTube tanpa membuka browser popup.
    Mengembalikan dict dengan status koneksi YouTube & validitas token.
    Jika token expired dan tidak bisa di-refresh, token.json akan otomatis dibersihkan.
    """
    token_file = config.BASE_DIR / "token.json"
    client_secret_file = config.BASE_DIR / config.YOUTUBE_CLIENT_SECRET_FILE
    if not client_secret_file.exists():
        fallback = config.BASE_DIR / "client_secret.json.json"
        if fallback.exists():
            client_secret_file = fallback
        else:
            return {
                "ready": False,
                "authenticated": False,
                "expired": False,
                "message": f"Kredensial '{config.YOUTUBE_CLIENT_SECRET_FILE}' tidak ditemukan."
            }

    if not token_file.exists() or token_file.stat().st_size <= 10:
        return {
            "ready": True,
            "authenticated": False,
            "expired": False,
            "message": "Belum terhubung ke YouTube."
        }

    try:
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(token_file, "w") as token:
                        token.write(creds.to_json())
                    return {
                        "ready": True,
                        "authenticated": True,
                        "expired": False,
                        "message": "Token YouTube aktif (berhasil diperbarui)."
                    }
                except Exception as e:
                    # Token revoked atau expired (invalid_grant)
                    print(f"[*] check_auth_status: Refresh token gagal ({e}), menghapus token.json usang...")
                    token_file.unlink(missing_ok=True)
                    return {
                        "ready": True,
                        "authenticated": False,
                        "expired": True,
                        "message": "Sesi token YouTube kedaluwarsa atau dicabut oleh Google (invalid_grant)."
                    }
            else:
                token_file.unlink(missing_ok=True)
                return {
                    "ready": True,
                    "authenticated": False,
                    "expired": True,
                    "message": "Token YouTube tidak valid."
                }

        return {
            "ready": True,
            "authenticated": True,
            "expired": False,
            "message": "Token YouTube aktif."
        }
    except Exception as e:
        print(f"[*] check_auth_status error: {e}")
        token_file.unlink(missing_ok=True)
        return {
            "ready": True,
            "authenticated": False,
            "expired": True,
            "message": f"Format token tidak valid: {e}"
        }

def get_authenticated_service(force_reauth: bool = False):
    """
    Melakukan otentikasi OAuth2 ke YouTube Data API v3.
    Token akses akan disimpan di token.json agar login browser hanya dilakukan sekali.
    Jika force_reauth=True atau token kedaluwarsa/revoked, akan menghapus token lama
    dan membuka browser untuk login ulang.
    """
    creds = None
    token_file = config.BASE_DIR / "token.json"
    client_secret_file = config.BASE_DIR / config.YOUTUBE_CLIENT_SECRET_FILE
    if not client_secret_file.exists():
        fallback = config.BASE_DIR / "client_secret.json.json"
        if fallback.exists():
            client_secret_file = fallback
        else:
            raise FileNotFoundError(
                f"File kredensial YouTube '{client_secret_file.name}' tidak ditemukan di folder proyek!\n"
                f"Silakan unduh OAuth Client JSON dari Google Cloud Console dan simpan sebagai '{client_secret_file.name}'."
            )

    if force_reauth and token_file.exists():
        print("[*] Permintaan login ulang: Menghapus token.json lama...")
        token_file.unlink(missing_ok=True)

    if not force_reauth and token_file.exists():
        try:
            if token_file.stat().st_size > 10:
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
            else:
                token_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"[!] Gagal membaca token.json ({e}). Menghapus token rusak...")
            token_file.unlink(missing_ok=True)
            creds = None

    if not creds or not creds.valid:
        refreshed = False
        if creds and creds.expired and creds.refresh_token:
            print("[*] Memperbarui sesi token YouTube yang kedaluwarsa...")
            try:
                creds.refresh(Request())
                refreshed = True
                print("[+] Token YouTube berhasil diperbarui secara otomatis.")
            except Exception as e:
                print(f"[!] Gagal refresh token YouTube: {e}")
                print("[!] Token lama telah kedaluwarsa atau dicabut Google (invalid_grant).")
                print("[!] Menghapus token.json dan membuka browser untuk otorisasi login ulang...")
                token_file.unlink(missing_ok=True)
                creds = None

        if not refreshed or not creds or not creds.valid:
            print("[*] Membuka browser untuk otorisasi login akun YouTube Anda...")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())
            print("[+] Token login berhasil disimpan di token.json.")

    return build("youtube", "v3", credentials=creds)

def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] = None,
    privacy_status: str = "unlisted", # Default 'unlisted' untuk keamanan & review
    category_id: str = "27", # 27 = Education, 28 = Science & Technology
    publish_at: str = None # ISO 8601 UTC string (contoh: '2026-10-08T09:00:00.000Z') untuk upload terjadwal
) -> str:
    """
    Mengunggah video ke YouTube via YouTube Data API v3 Resumable Upload.
    Mendukung penjadwalan tayang otomatis (publishAt).
    Mengembalikan Video ID dan URL video YouTube.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File video tidak ditemukan: {video_path}")

    youtube = get_authenticated_service()

    body_status = {
        "privacyStatus": privacy_status,
        "selfDeclaredMadeForKids": False
    }

    # Jika dijadwalkan, YouTube mewajibkan status private + publishAt
    if publish_at:
        body_status["privacyStatus"] = "private"
        body_status["publishAt"] = publish_at

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or ["Shorts", "Fakta"],
            "categoryId": category_id
        },
        "status": body_status
    }

    print(f"\n[*] Mengunggah video ke YouTube: '{title}'...")
    print(f"    Status Privasi: {privacy_status.upper()}")
    
    media = MediaFileUpload(
        video_path,
        chunksize=1024 * 1024 * 4, # 4MB chunks
        resumable=True
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"    Progress Upload: {progress}%...")

    video_id = response.get("id")
    video_url = f"https://www.youtube.com/shorts/{video_id}"
    print(f"\n[+] BERHASIL! Video telah terunggah ke YouTube:")
    print(f"    URL: {video_url}")
    return video_url
