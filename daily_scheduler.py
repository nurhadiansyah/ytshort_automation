import os
import sys
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import threading

# Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
import youtube_uploader

DATA_DIR = config.BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
TOPICS_FILE = DATA_DIR / "topics_150.json"
SCHEDULE_FILE = DATA_DIR / "upload_schedule.json"
BATCH_STATUS_FILE = DATA_DIR / "batch_status.json"

schedule_lock = threading.Lock()

# 5 Slot Jam Tayang Prime Time YouTube Shorts (WIB = UTC+7)
# 08:00 WIB = 01:00 UTC (Pagi waktu sarapan / berangkat kerja)
# 12:00 WIB = 05:00 UTC (Siang jam istirahat makan)
# 15:30 WIB = 08:30 UTC (Sore santai / istirahat)
# 18:30 WIB = 11:30 UTC (Petang pulang kerja)
# 20:30 WIB = 13:30 UTC (Malam prime time medsos)
PRIME_TIME_SLOTS = [
    {"wib": "08:00", "utc_hour": 1, "utc_minute": 0, "label": "Pagi (08:00 WIB)"},
    {"wib": "12:00", "utc_hour": 5, "utc_minute": 0, "label": "Siang (12:00 WIB)"},
    {"wib": "15:30", "utc_hour": 8, "utc_minute": 30, "label": "Sore (15:30 WIB)"},
    {"wib": "18:30", "utc_hour": 11, "utc_minute": 30, "label": "Petang (18:30 WIB)"},
    {"wib": "20:30", "utc_hour": 13, "utc_minute": 30, "label": "Malam (20:30 WIB)"},
]

def load_topics() -> list[str]:
    if not TOPICS_FILE.exists():
        raise FileNotFoundError("File data/topics_150.json tidak ditemukan!")
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def init_or_load_schedule(start_date: datetime = None) -> dict:
    """
    Membuat atau memuat jadwal 30 hari (150 konten, 5 konten per hari).
    """
    with schedule_lock:
        if SCHEDULE_FILE.exists():
            try:
                with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        if start_date is None:
            # Default mulai hari ini atau besok jika hari ini sudah lewat jam 20:30
            start_date = datetime.now()

        topics = load_topics()
        schedule_days = []
        topic_idx = 0

        for day_num in range(1, 31):
            day_date = start_date + timedelta(days=day_num - 1)
            date_str = day_date.strftime("%Y-%m-%d")
            
            slots = []
            for slot_cfg in PRIME_TIME_SLOTS:
                if topic_idx < len(topics):
                    curr_topic = topics[topic_idx]
                else:
                    curr_topic = f"Konten Edukasi Keamanan Siber #{topic_idx + 1}"

                # Hitung waktu rilis UTC
                slot_time_utc = datetime(
                    year=day_date.year,
                    month=day_date.month,
                    day=day_date.day,
                    hour=slot_cfg["utc_hour"],
                    minute=slot_cfg["utc_minute"],
                    second=0,
                    tzinfo=timezone.utc
                )
                publish_at_iso = slot_time_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

                slots.append({
                    "video_index": topic_idx + 1,
                    "topic": curr_topic,
                    "slot_label": slot_cfg["label"],
                    "wib_time": f"{date_str} {slot_cfg['wib']} WIB",
                    "publish_at_utc": publish_at_iso,
                    "video_path": None,
                    "status": "pending", # pending, produced, uploaded, failed
                    "youtube_url": None,
                    "uploaded_at": None,
                    "error": None
                })
                topic_idx += 1

            schedule_days.append({
                "day_number": day_num,
                "date": date_str,
                "slots": slots,
                "day_status": "pending" # pending, in_progress, completed
            })

        schedule_data = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_days": 30,
            "videos_per_day": 5,
            "total_videos": 150,
            "days": schedule_days
        }

        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(schedule_data, f, indent=2, ensure_ascii=False)

        return schedule_data

def sync_schedule_with_batch():
    """
    Menyelaraskan video yang sudah selesai dibuat oleh batch_engine dengan slot jadwal.
    """
    if not SCHEDULE_FILE.exists():
        init_or_load_schedule()

    with schedule_lock:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            schedule = json.load(f)

        # Cari video yang sudah jadi di batch_status atau folder output/
        produced_map = {}
        if BATCH_STATUS_FILE.exists():
            try:
                with open(BATCH_STATUS_FILE, "r", encoding="utf-8") as bf:
                    bdata = json.load(bf)
                    for item in bdata.get("history", []):
                        if item.get("status") == "success" and item.get("video_path"):
                            produced_map[item.get("index")] = item.get("video_path")
            except Exception:
                pass

        # Periksa juga file di folder output/
        for mp4_file in config.OUTPUT_DIR.glob("Animasi_*.mp4"):
            meta_file = mp4_file.with_name(f"{mp4_file.stem}_metadata.json")
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as mf:
                        m = json.load(mf)
                        topic = m.get("title", "")
                        # Cari slot yang sesuai
                        for day in schedule.get("days", []):
                            for slot in day.get("slots", []):
                                if slot.get("topic") in topic or topic in slot.get("topic"):
                                    if not slot.get("video_path"):
                                        slot["video_path"] = str(mp4_file)
                                        if slot.get("status") in ("pending", "failed"):
                                            slot["status"] = "produced"
                                            slot["error"] = None
                except Exception:
                    pass

        # Perbarui slot berdasarkan batch map
        for day in schedule.get("days", []):
            for slot in day.get("slots", []):
                v_idx = slot.get("video_index")
                if v_idx in produced_map and not slot.get("video_path"):
                    slot["video_path"] = produced_map[v_idx]
                if slot.get("video_path") and os.path.exists(slot["video_path"]) and slot.get("status") in ("pending", "failed"):
                    slot["status"] = "produced"
                    slot["error"] = None

        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)

        return schedule

class YouTubeQuotaLimitError(Exception):
    """Exception khusus saat akun YouTube mencapai batas unggah harian (10-15 video/24 jam atau kuota API habis)."""
    pass

def is_quota_error(err: str) -> bool:
    err_lower = str(err).lower()
    return any(keyword in err_lower for keyword in [
        "uploadlimitexceeded",
        "quotaexceeded",
        "ratelimitexceeded",
        "quota exceeded",
        "video uploads per day",
        "user has exceeded the number of videos",
        "429"
    ])

def upload_scheduled_slot(slot: dict) -> bool:
    """
    Mengunggah satu slot video ke YouTube dengan publish_at terjadwal.
    """
    video_path = slot.get("video_path")
    if not video_path or not os.path.exists(video_path):
        slot["status"] = "failed"
        slot["error"] = "File video belum diproduksi atau tidak ditemukan."
        return False

    client_secret = config.BASE_DIR / config.YOUTUBE_CLIENT_SECRET_FILE
    if not client_secret.exists():
        fallback = config.BASE_DIR / "client_secret.json.json"
        if fallback.exists():
            client_secret = fallback
        else:
            slot["status"] = "failed"
            slot["error"] = f"File {client_secret.name} belum ada di root folder."
            return False

    topic = slot.get("topic", "Tips Keamanan Siber")
    title = f"{topic[:85]} #Shorts"
    desc = (
        f"{topic}\n\n"
        f"Lindungi privasi dan data pribadimu di era digital!\n"
        f"Subscribe untuk fakta & tips keamanan siber harian lainnya.\n\n"
        f"#Shorts #CyberSecurity #KeamananDigital #TipsTeknologi #Edukasi"
    )
    tags = ["Shorts", "CyberSecurity", "KeamananDigital", "TipsTeknologi", "Edukasi"]

    publish_at = slot.get("publish_at_utc")

    try:
        print(f"\n[*] Mengunggah slot [{slot.get('video_index')}] '{topic}'...")
        print(f"    Waktu Rilis Terjadwal: {slot.get('wib_time')} (UTC: {publish_at})")
        
        yt_url = youtube_uploader.upload_video(
            video_path=video_path,
            title=title,
            description=desc,
            tags=tags,
            privacy_status="private", # Wajib 'private' jika menggunakan publishAt
            publish_at=publish_at
        )

        slot["status"] = "uploaded"
        slot["youtube_url"] = yt_url
        slot["uploaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        slot["error"] = None
        print(f"[+] Slot [{slot.get('video_index')}] Berhasil Diunggah! URL: {yt_url}")
        return True

    except Exception as e:
        err_msg = str(e)
        if is_quota_error(err_msg):
            # Video TIDAK rusak, kuota harian sedang penuh
            slot["status"] = "produced"
            slot["error"] = "Batas unggah harian YouTube (10-15 video/24 jam) tercapai. Menunggu reset jendela kuota Google."
            print(f"[⚠️] Batas harian YouTube tercapai pada slot [{slot.get('video_index')}]. Status tetap 'produced'.")
            raise YouTubeQuotaLimitError(err_msg)
        else:
            slot["status"] = "failed"
            slot["error"] = err_msg
            print(f"[!] Gagal mengunggah slot [{slot.get('video_index')}]: {err_msg}")
            return False

def upload_next_daily_batch(limit: int = 5) -> dict:
    """
    Mengunggah antrean berikutnya sebanyak 5 video (jatah kuota aman harian YouTube API).
    """
    sync_schedule_with_batch()

    with schedule_lock:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            schedule = json.load(f)

    uploaded_count = 0
    failed_count = 0
    quota_limit_reached = False
    quota_msg = None
    results = []

    # Cari slot yang berstatus 'produced' (video sudah jadi tapi belum diupload)
    for day in schedule.get("days", []):
        if quota_limit_reached:
            break
        for slot in day.get("slots", []):
            if uploaded_count >= limit:
                break
            
            if slot.get("status") in ("produced", "pending", "failed") and slot.get("video_path") and os.path.exists(slot.get("video_path", "")):
                try:
                    ok = upload_scheduled_slot(slot)
                    if ok:
                        uploaded_count += 1
                    else:
                        failed_count += 1
                except YouTubeQuotaLimitError as qe:
                    quota_limit_reached = True
                    quota_msg = "Batas upload harian YouTube (10-15 video/24 jam) untuk channel ini telah tercapai. Auto-Pilot akan mencoba kembali saat jendela kuota terbuka."
                    results.append({
                        "video_index": slot.get("video_index"),
                        "topic": slot.get("topic"),
                        "status": "produced",
                        "error": quota_msg
                    })
                    break # Hentikan iterasi slot lainnya hari ini
                
                results.append({
                    "video_index": slot.get("video_index"),
                    "topic": slot.get("topic"),
                    "status": slot.get("status"),
                    "youtube_url": slot.get("youtube_url"),
                    "error": slot.get("error")
                })

        # Cek apakah semua slot pada hari ini sudah beres
        all_done = all(s.get("status") == "uploaded" for s in day.get("slots", []))
        if all_done:
            day["day_status"] = "completed"
        elif any(s.get("status") == "uploaded" for s in day.get("slots", [])):
            day["day_status"] = "in_progress"

        if uploaded_count >= limit or quota_limit_reached:
            break

    # Simpan kembali jadwal
    with schedule_lock:
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)

    return {
        "uploaded_count": uploaded_count,
        "failed_count": failed_count,
        "quota_limit_reached": quota_limit_reached,
        "message": quota_msg or (f"Berhasil mengunggah {uploaded_count} video!" if uploaded_count > 0 else "Tidak ada video baru untuk diunggah."),
        "results": results
    }

def upload_slot_by_index(video_index: int) -> dict:
    """
    Mengunggah satu slot tertentu berdasarkan nomor video_index dengan waktu rilis terjadwal (publishAt).
    """
    sync_schedule_with_batch()
    with schedule_lock:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            schedule = json.load(f)

    target_slot = None
    target_day = None
    for day in schedule.get("days", []):
        for slot in day.get("slots", []):
            if slot.get("video_index") == video_index:
                target_slot = slot
                target_day = day
                break
        if target_slot:
            break

    if not target_slot:
        return {"status": "error", "message": f"Slot #{video_index} tidak ditemukan di jadwal."}

    if not target_slot.get("video_path") or not os.path.exists(target_slot.get("video_path", "")):
        return {"status": "error", "message": f"File video untuk slot #{video_index} belum ada atau belum diproduksi."}

    try:
        ok = upload_scheduled_slot(target_slot)
        if ok and target_day:
            all_done = all(s.get("status") == "uploaded" for s in target_day.get("slots", []))
            if all_done:
                target_day["day_status"] = "completed"
            else:
                target_day["day_status"] = "in_progress"

        with schedule_lock:
            with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
                json.dump(schedule, f, indent=2, ensure_ascii=False)

        if ok:
            return {
                "status": "success",
                "message": f"Video #{video_index} berhasil diunggah dengan jadwal rilis: {target_slot.get('wib_time')}",
                "youtube_url": target_slot.get("youtube_url"),
                "slot": target_slot
            }
        else:
            return {"status": "error", "message": target_slot.get("error", "Gagal mengunggah")}

    except YouTubeQuotaLimitError as qe:
        return {
            "status": "error",
            "is_quota_error": True,
            "message": "Batas kuota harian upload YouTube (10-15 video/24 jam) untuk channel ini telah tercapai. Video tetap aman tersimpan untuk diunggah saat jendela kuota terbuka."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def produce_and_upload_today(limit: int = 5, animation_style: str = "Handcrafted Claymation Animation", progress_callback = None) -> dict:
    """
    Memproduksi video edukasi yang belum dibuat untuk slot hari ini dan langsung mengunggahnya
    ke YouTube Shorts dengan jadwal tayang otomatis (publishAt prime-time).
    """
    import pipeline
    sync_schedule_with_batch()
    
    with schedule_lock:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            schedule = json.load(f)
            
    processed_count = 0
    uploaded_count = 0
    failed_count = 0
    results = []
    
    for day in schedule.get("days", []):
        for slot in day.get("slots", []):
            if processed_count >= limit:
                break
                
            # Jika belum diunggah
            if slot.get("status") != "uploaded":
                topic = slot.get("topic")
                video_path = slot.get("video_path")
                
                # Jika belum ada file video atau file hilang, buat sekarang dalam gaya Claymation
                if not video_path or not os.path.exists(video_path):
                    if progress_callback:
                        progress_callback(f"Memproduksi video animasi Claymation slot [{slot.get('video_index')}]: '{topic[:40]}...'")
                    try:
                        res = pipeline.create_short_video(
                            topic=topic,
                            animation_style=animation_style,
                            scene_count=5,
                            caption_style="clay_pop",
                            enable_header_badge=True,
                            enable_progress_bar=True,
                            enable_sfx=True
                        )
                        video_path = res.get("video_path")
                        slot["video_path"] = video_path
                        slot["status"] = "produced"
                    except Exception as e:
                        slot["status"] = "failed"
                        slot["error"] = f"Gagal render video: {e}"
                        failed_count += 1
                        results.append(slot)
                        processed_count += 1
                        continue
                        
                # Upload ke YouTube terjadwal
                if progress_callback:
                    progress_callback(f"Mengunggah slot [{slot.get('video_index')}] ke YouTube ({slot.get('slot_label', slot.get('wib_time'))})...")
                    
                try:
                    ok = upload_scheduled_slot(slot)
                    if ok:
                        uploaded_count += 1
                    else:
                        failed_count += 1
                except YouTubeQuotaLimitError:
                    if progress_callback:
                        progress_callback("Batas harian channel YouTube tercapai (10-15 video/24 jam). Video aman tersimpan dan akan diunggah otomatis.")
                    results.append({
                        "video_index": slot.get("video_index"),
                        "topic": slot.get("topic"),
                        "status": "produced",
                        "wib_time": slot.get("wib_time"),
                        "error": "Batas unggah harian YouTube tercapai. Menunggu reset kuota."
                    })
                    break
                    
                processed_count += 1
                results.append({
                    "video_index": slot.get("video_index"),
                    "topic": slot.get("topic"),
                    "status": slot.get("status"),
                    "wib_time": slot.get("wib_time"),
                    "youtube_url": slot.get("youtube_url"),
                    "error": slot.get("error")
                })
                
        # Update status hari
        all_done = all(s.get("status") == "uploaded" for s in day.get("slots", []))
        if all_done:
            day["day_status"] = "completed"
        elif any(s.get("status") == "uploaded" for s in day.get("slots", [])):
            day["day_status"] = "in_progress"

        if processed_count >= limit:
            break
            
    with schedule_lock:
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)
            
    return {
        "processed_count": processed_count,
        "uploaded_count": uploaded_count,
        "failed_count": failed_count,
        "results": results
    }

def reorganize_and_schedule_all_videos(start_date: datetime = None) -> dict:
    """
    Menyelaraskan seluruh video yang sudah diproduksi di output/ dan belum terunggah
    ke slot prime time hari-hari mendatang (5 video/hari) secara teratur.
    """
    with schedule_lock:
        uploaded_map = {}
        if SCHEDULE_FILE.exists():
            try:
                with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                for day in old_data.get("days", []):
                    for slot in day.get("slots", []):
                        if slot.get("status") == "uploaded" and slot.get("video_path"):
                            vname = Path(slot["video_path"]).name
                            uploaded_map[vname] = slot
            except Exception:
                pass

        all_videos = sorted(list(config.OUTPUT_DIR.glob("Animasi_*.mp4")), key=lambda x: x.stat().st_mtime)
        unuploaded_videos = []

        for v in all_videos:
            if v.name not in uploaded_map:
                meta_f = v.with_name(f"{v.stem}_metadata.json")
                title = v.stem.replace("Animasi_", "").replace("_", " ")
                if meta_f.exists():
                    try:
                        with open(meta_f, "r", encoding="utf-8") as mf:
                            m = json.load(mf)
                            title = m.get("title", title)
                    except Exception:
                        pass
                unuploaded_videos.append({
                    "path": str(v),
                    "title": title
                })

        now = datetime.now()
        if start_date is None:
            # Default mulai besok agar seluruh 5 slot per hari terpenuhi penuh
            start_date = datetime(now.year, now.month, now.day) + timedelta(days=1)

        new_days = []
        video_index = 1
        unuploaded_idx = 0

        # Hari-hari lampau yang sudah uploaded dipertahankan
        uploaded_list = list(uploaded_map.values())
        up_idx = 0
        day_num = 1

        while up_idx < len(uploaded_list):
            past_date = start_date - timedelta(days=int((len(uploaded_list) - up_idx) / 5) + 1)
            date_str = past_date.strftime("%Y-%m-%d")
            slots = []
            for slot_cfg in PRIME_TIME_SLOTS:
                if up_idx < len(uploaded_list):
                    s = uploaded_list[up_idx]
                    s["video_index"] = video_index
                    s["slot_label"] = slot_cfg["label"]
                    slots.append(s)
                    up_idx += 1
                    video_index += 1
                else:
                    break
            new_days.append({
                "day_number": day_num,
                "date": date_str,
                "slots": slots,
                "day_status": "completed"
            })
            day_num += 1

        # Jadwalkan seluruh video yang belum terunggah ke hari-hari mendatang (5 video per hari)
        target_day_count = 30
        curr_future_date = start_date
        topics = load_topics()

        while len(new_days) < target_day_count:
            date_str = curr_future_date.strftime("%Y-%m-%d")
            slots = []
            for slot_cfg in PRIME_TIME_SLOTS:
                slot_time_utc = datetime(
                    year=curr_future_date.year,
                    month=curr_future_date.month,
                    day=curr_future_date.day,
                    hour=slot_cfg["utc_hour"],
                    minute=slot_cfg["utc_minute"],
                    second=0,
                    tzinfo=timezone.utc
                )
                publish_at_iso = slot_time_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

                if unuploaded_idx < len(unuploaded_videos):
                    v_info = unuploaded_videos[unuploaded_idx]
                    slots.append({
                        "video_index": video_index,
                        "topic": v_info["title"],
                        "slot_label": slot_cfg["label"],
                        "wib_time": f"{date_str} {slot_cfg['wib']} WIB",
                        "publish_at_utc": publish_at_iso,
                        "video_path": v_info["path"],
                        "status": "produced",
                        "youtube_url": None,
                        "uploaded_at": None,
                        "error": None
                    })
                    unuploaded_idx += 1
                else:
                    topic_name = topics[video_index - 1] if (video_index - 1) < len(topics) else f"Konten Edukasi #{video_index}"
                    slots.append({
                        "video_index": video_index,
                        "topic": topic_name,
                        "slot_label": slot_cfg["label"],
                        "wib_time": f"{date_str} {slot_cfg['wib']} WIB",
                        "publish_at_utc": publish_at_iso,
                        "video_path": None,
                        "status": "pending",
                        "youtube_url": None,
                        "uploaded_at": None,
                        "error": None
                    })
                video_index += 1

            has_prod = any(s["status"] == "produced" for s in slots)
            new_days.append({
                "day_number": day_num,
                "date": date_str,
                "slots": slots,
                "day_status": "ready" if has_prod else "pending"
            })
            day_num += 1
            curr_future_date += timedelta(days=1)

        schedule_data = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_days": len(new_days),
            "videos_per_day": 5,
            "total_videos": video_index - 1,
            "days": new_days
        }

        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(schedule_data, f, indent=2, ensure_ascii=False)

        print(f"[+] Jadwal berhasil diselaraskan: {len(uploaded_list)} terunggah, {len(unuploaded_videos)} video siap terjadwal!")
        return schedule_data

# ================= BACKGROUND AUTO-PILOT DAEMON =================
autopilot_lock = threading.Lock()
autopilot_state = {
    "active": False,
    "last_run": None,
    "next_run": None,
    "last_message": "Auto-Pilot belum diaktifkan",
    "stop_event": threading.Event()
}

def autopilot_worker_loop():
    """
    Loop latar belakang yang memantau jam tayang dan otomatis mengunggah video
    sesuai jadwal setiap hari secara mandiri.
    """
    print("[*] Auto-Pilot Harian YouTube Shorts AKTIF dan berjalan di latar belakang.")
    while not autopilot_state["stop_event"].is_set():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        autopilot_state["last_run"] = now_str
        
        try:
            print(f"\n[*] [Auto-Pilot Harian - {now_str}] Memeriksa antrean upload hari ini...")
            res = upload_next_daily_batch(limit=5)
            up_count = res.get("uploaded_count", 0)
            fail_count = res.get("failed_count", 0)
            
            # Cek apakah ada error limit harian
            quota_hit = res.get("quota_limit_reached", False)
            if not quota_hit:
                for r in res.get("results", []):
                    err = str(r.get("error", ""))
                    if is_quota_error(err):
                        quota_hit = True
                        break
                    
            if quota_hit:
                msg = "Batas kuota upload harian YouTube (10-15 video/24 jam) tercapai. Auto-Pilot akan otomatis mencoba kembali saat jendela kuota terbuka."
            elif up_count > 0:
                msg = f"Berhasil mengunggah & menjadwalkan {up_count} video YouTube Shorts!"
            else:
                msg = f"Semua slot siap untuk batch ini sudah terunggah atau belum ada video baru."
                
            autopilot_state["last_message"] = msg
            print(f"[+] [Auto-Pilot Harian] {msg}")
            
        except Exception as e:
            err_msg = f"Error Auto-Pilot: {e}"
            autopilot_state["last_message"] = err_msg
            print(f"[!] [Auto-Pilot Harian] {err_msg}")
            
        # Perbarui next_run (cek setiap 30 menit)
        next_dt = datetime.now() + timedelta(minutes=30)
        autopilot_state["next_run"] = next_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Tidur selama 30 menit (bisa diinterupsi oleh stop_event)
        autopilot_state["stop_event"].wait(timeout=1800)

def start_autopilot():
    with autopilot_lock:
        if autopilot_state["active"]:
            return False, "Auto-Pilot sudah aktif!"
        autopilot_state["active"] = True
        autopilot_state["stop_event"].clear()
        t = threading.Thread(target=autopilot_worker_loop, daemon=True)
        t.start()
        return True, "Auto-Pilot Harian berhasil diaktifkan!"

def stop_autopilot():
    with autopilot_lock:
        if not autopilot_state["active"]:
            return False, "Auto-Pilot sedang tidak aktif."
        autopilot_state["active"] = False
        autopilot_state["stop_event"].set()
        return True, "Auto-Pilot Harian dihentikan."

def get_autopilot_status():
    with autopilot_lock:
        return {
            "active": autopilot_state["active"],
            "last_run": autopilot_state["last_run"],
            "next_run": autopilot_state["next_run"],
            "last_message": autopilot_state["last_message"]
        }

def get_schedule_summary() -> dict:
    """
    Mengambil ringkasan data jadwal untuk ditampilkan di GUI Web.
    """
    schedule = sync_schedule_with_batch()
    
    total_slots = 0
    produced_slots = 0
    uploaded_slots = 0
    pending_slots = 0
    failed_slots = 0

    for day in schedule.get("days", []):
        for slot in day.get("slots", []):
            total_slots += 1
            st = slot.get("status")
            if st == "uploaded":
                uploaded_slots += 1
            elif st == "produced":
                produced_slots += 1
            elif st == "failed":
                failed_slots += 1
            else:
                pending_slots += 1

    return {
        "total_days": len(schedule.get("days", [])),
        "total_videos": total_slots,
        "produced_count": produced_slots + uploaded_slots,
        "uploaded_count": uploaded_slots,
        "ready_to_upload_count": produced_slots,
        "pending_count": pending_slots,
        "failed_count": failed_slots,
        "days": schedule.get("days", [])
    }

if __name__ == "__main__":
    print("Membuat / memuat jadwal 30 hari YouTube Shorts...")
    reorganize_and_schedule_all_videos()
    summary = get_schedule_summary()
    print(f"Total Video   : {summary['total_videos']}")
    print(f"Sudah Diproduksi : {summary['produced_count']}")
    print(f"Sudah Terunggah: {summary['uploaded_count']}")
    print(f"Siap Diunggah : {summary['ready_to_upload_count']}")

