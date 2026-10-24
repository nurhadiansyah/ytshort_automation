import os
import sys
import json
import time
import threading
from pathlib import Path

# Tangani encoding console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
import pipeline

DATA_DIR = config.BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
TOPICS_FILE = DATA_DIR / "topics_150.json"
BATCH_STATUS_FILE = DATA_DIR / "batch_status.json"

batch_lock = threading.Lock()
stop_flag = threading.Event()

def load_topics() -> list[str]:
    if not TOPICS_FILE.exists():
        raise FileNotFoundError("File data/topics_150.json tidak ditemukan!")
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_status() -> dict:
    if not BATCH_STATUS_FILE.exists():
        return {
            "status": "idle", # idle, running, paused, completed
            "current_index": 0,
            "total_target": 150,
            "successful": 0,
            "failed": 0,
            "current_topic": "",
            "history": []
        }
    try:
        with open(BATCH_STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"status": "idle", "current_index": 0, "total_target": 150, "successful": 0, "failed": 0, "history": []}

def save_status(data: dict):
    with batch_lock:
        with open(BATCH_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def run_batch_worker(total_to_generate: int = 150, animation_style: str = "Handcrafted Claymation Animation"):
    topics = load_topics()
    status_data = load_status()
    
    total = min(total_to_generate, len(topics))
    start_idx = status_data.get("current_index", 0)

    # Jika antrean sebelumnya sudah selesai (mencapai batas total), reset otomatis dari indeks 0
    if start_idx >= total:
        print(f"[*] Antrean sebelumnya telah mencapai batas ({start_idx}/{total}). Me-reset otomatis ke indeks 0...")
        start_idx = 0
        status_data["successful"] = 0
        status_data["failed"] = 0
        status_data["history"] = []

    status_data["status"] = "running"
    status_data["total_target"] = total
    status_data["current_index"] = start_idx
    save_status(status_data)

    print(f"\n=======================================================")
    print(f"🏭 PABRIK KONTEN 1 BULAN DIMULAI: Target {total} Video")
    print(f"📌 Mulai dari antrean indeks: {start_idx + 1}/{total}")
    print(f"=======================================================\n")

    stop_flag.clear()

    for idx in range(start_idx, total):
        if stop_flag.is_set():
            print("\n[!] Batch generation dijeda (paused) oleh pengguna.")
            status_data = load_status()
            status_data["status"] = "paused"
            save_status(status_data)
            return

        topic = topics[idx]
        print(f"\n[{idx + 1}/{total}] 🎬 Memproduksi Video: '{topic}'...")

        status_data = load_status()
        status_data["current_index"] = idx
        status_data["current_topic"] = topic
        status_data["status"] = "running"
        save_status(status_data)

        try:
            # Jalankan pipeline penuh untuk topik ini
            result = pipeline.create_short_video(
                topic=topic,
                animation_style=animation_style,
                auto_upload=False # Upload dikelola terjadwal oleh daily_scheduler
            )
            
            status_data = load_status()
            status_data["successful"] = status_data.get("successful", 0) + 1
            status_data["history"].append({
                "index": idx + 1,
                "topic": topic,
                "video_path": result.get("video_path"),
                "status": "success",
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            status_data["current_index"] = idx + 1
            save_status(status_data)
            print(f"[+] Selesai {idx + 1}/{total}: '{topic}'")

            # Jeda istirahat tipis antar video untuk stabilitas API & sinkronisasi jadwal
            try:
                import daily_scheduler
                daily_scheduler.sync_schedule_with_batch()
            except Exception:
                pass
            time.sleep(3)

        except Exception as e:
            print(f"[!] Error saat memproduksi '{topic}': {e}")
            status_data = load_status()
            status_data["failed"] = status_data.get("failed", 0) + 1
            status_data["history"].append({
                "index": idx + 1,
                "topic": topic,
                "status": "failed",
                "error": str(e),
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            status_data["current_index"] = idx + 1
            save_status(status_data)
            time.sleep(5)

    status_data = load_status()
    status_data["status"] = "completed"
    status_data["current_topic"] = "Semua video batch telah selesai diproduksi!"
    save_status(status_data)
    print("\n🎉 SEMUA VIDEO BATCH 1 BULAN TELAH SELESAI DIPRODUKSI!")

active_thread = None

def is_running() -> bool:
    global active_thread
    return active_thread is not None and active_thread.is_alive()

def start_batch_in_background(total: int = 150, animation_style: str = "3D Pixar Animation"):
    global active_thread
    if is_running():
        return active_thread
    active_thread = threading.Thread(target=run_batch_worker, args=(total, animation_style), daemon=True)
    active_thread.start()
    return active_thread

def pause_batch():
    stop_flag.set()

def reset_batch():
    stop_flag.set()
    time.sleep(0.5)
    save_status({
        "status": "idle",
        "current_index": 0,
        "total_target": 150,
        "successful": 0,
        "failed": 0,
        "current_topic": "",
        "history": []
    })

if __name__ == "__main__":
    run_batch_worker(total_to_generate=150)
