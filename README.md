# 🚀 AI Shorts Animator Studio (Web GUI Lokal)

Aplikasi otomasi berbasis AI untuk memproduksi **Video Ilustrasi Animasi YouTube Shorts (9:16)** secara otomatis dari topik apapun dan mengunggahnya langsung ke **YouTube** dengan tampilan antarmuka web modern (**Web GUI Lokal**).

---

## 🌐 Cara Menjalankan Web GUI (Paling Mudah)

Anda **tidak perlu pusing mengetik perintah di terminal / kernel**:
1. Cukup **klik dua kali (double click)** file:
   👉 **[`start_web_ui.bat`](file:///f:/gabut/short_automation/start_web_ui.bat)**
2. Browser Anda akan terbuka otomatis di alamat:
   👉 **`http://127.0.0.1:5000`**

*(Atau jalankan perintah `python web_app.py` di terminal).*

---

## ✨ Fitur-Fitur Web GUI

1. **Input Topik & Quick Idea Pills**:
   * Ketik topik apa saja secara bebas, atau klik tombol ide cepat (Gurita 3 Jantung, Misteri Lubang Hitam, Saturnus, dll).

2. **Pilihan Gaya Ilustrasi Animasi**:
   * 🌟 **3D Pixar Animation** (Karakter 3D ekspresif, warna cerah sinematik - Paling Viral)
   * 🌸 **Studio Ghibli Anime** (Ilustrasi anime estetis & pemandangan magis)
   * 💥 **Modern Motion Comic** (Gaya komik modern dinamis)

3. **Pilihan Suara (Voiceover)**:
   * Google AI Studio TTS (Puck - Narasi cerah)
   * Microsoft Neural Voice (Ardi / Gadis - Bahasa Indonesia jernih tanpa batas kuota)

4. **Live Monitor & Real-Time Progress**:
   * Tampilan progres persentase (0% - 100%).
   * Checklist tahapan otomatis (Naskah -> Voiceover -> Ilustrasi Seni -> Render Video).
   * Live Terminal Log ticker.

5. **Integrated Video Player (9:16 Shorts)**:
   * Putar dan tinjau langsung video animasi yang baru saja dibuat di browser.
   * Tombol unduh video (.mp4).

6. **1-Click Upload ke YouTube**:
   * Upload langsung dari browser dengan pilihan privasi (`Unlisted`, `Private`, atau `Public`).

7. **Galeri Video Tersimpan**:
   * Daftar semua video animasi yang pernah dibuat di folder `output/`.
   * Bisa diputar ulang kapan saja atau di-upload ulang ke YouTube.

---

## 📁 Struktur Direktori

```
short_automation/
├── start_web_ui.bat         # Klik 2x untuk membuka Web GUI
├── web_app.py               # Server web lokal (Flask)
├── templates/
│   └── index.html           # Tampilan antarmuka Web GUI
├── static/
│   ├── css/style.css        # Desain futuristik dark mode & glassmorphism
│   └── js/app.js            # Logika interaktif & live progress
├── output/                  # Hasil video final (.mp4)
├── assets/                  # Partikel animasi & musik BGM (.mp3)
├── config.py                # Konfigurasi sistem
├── ai_services.py           # Modul AI (Naskah, Suara TTS, Ilustrasi Seni)
├── video_editor.py          # Render kamera dinamis, subtitle, & partikel
├── youtube_uploader.py      # Upload otomatis YouTube OAuth2
├── pipeline.py              # Orkestrasi alur otomatisasi
├── .env                     # File konfigurasi API Key
└── client_secret.json       # Kredensial OAuth YouTube
```
