"""
AUTO-PILOT HARIAN YOUTUBE SHORTS UPLOADER
============================================================
Skrip otomatis yang menjalankan penjadwalan harian 5 video per hari,
memantau batas kuota YouTube secara otomatis, dan memperbarui
status video di antrean YouTube Shorts.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

import config
import daily_scheduler

def run_autopilot_cli():
    print("============================================================")
    print("🤖 AUTO-PILOT PENJADWALAN HARIAN YOUTUBE SHORTS")
    print("============================================================")
    
    # 1. Selaraskan seluruh video yang ada di output/
    daily_scheduler.reorganize_and_schedule_all_videos()
    summary = daily_scheduler.get_schedule_summary()
    
    print(f"[*] Total Video Terjadwal: {summary['total_videos']} Video")
    print(f"[*] Video Sudah Terunggah : {summary['uploaded_count']} Video")
    print(f"[*] Video Siap Diunggah   : {summary['ready_to_upload_count']} Video")
    print(f"[*] Slot Pending           : {summary['pending_count']} Slot")
    print("------------------------------------------------------------")
    print("[*] Slot Prime-Time Rilis: 08:00, 12:00, 15:30, 18:30, 20:30 WIB")
    print("[*] Batas Aman Kuota     : 5 Video / Hari (8.000 / 10.000 Unit)")
    print("============================================================\n")

    while True:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now_str}] 🚀 Memeriksa antrean upload hari ini...")
        
        try:
            res = daily_scheduler.upload_next_daily_batch(limit=5)
            up_count = res.get("uploaded_count", 0)
            fail_count = res.get("failed_count", 0)
            
            quota_hit = res.get("quota_limit_reached", False)
            if not quota_hit:
                for r in res.get("results", []):
                    err = str(r.get("error", ""))
                    if "uploadLimitExceeded" in err or "quotaExceeded" in err:
                        quota_hit = True
                        break
                        
            if quota_hit:
                print(f"\n[⚠️] Batas harian upload YouTube channel tercapai (10-15 video/24 jam).")
                print(f"[*] Sistem Auto-Pilot akan istirahat dan mencoba lagi otomatis saat jendela kuota terbuka.\n")
            elif up_count > 0:
                print(f"\n[🎉] BERHASIL! {up_count} video YouTube Shorts telah diunggah & dijadwalkan!")
            else:
                print(f"[*] Semua slot untuk hari ini sudah terunggah.")
                
        except Exception as e:
            print(f"[!] Error pengecekan batch: {e}")
            
        print("[*] Tidur 30 menit sebelum pengecekan berkala berikutnya... (Tekan Ctrl+C untuk berhenti)")
        try:
            time.sleep(1800) # Cek setiap 30 menit
        except KeyboardInterrupt:
            print("\n[!] Auto-Pilot dihentikan oleh pengguna.")
            break

if __name__ == "__main__":
    run_autopilot_cli()
