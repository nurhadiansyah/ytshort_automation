// ===================================================
// AI SHORTS ANIMATOR STUDIO - CLIENT CONTROLLER
// ===================================================

let pollingInterval = null;
let currentSelectedFilename = null;

document.addEventListener("DOMContentLoaded", () => {
    initSystemStatus();
    initPresets();
    initStyleSelectors();
    initGenerateHandler();
    initGallery();
    initModal();
    initTabs();
    initBatchDashboard();
});

// 1. Cek Status Kesiapan Sistem
async function initSystemStatus() {
    try {
        const res = await fetch("/api/system-status");
        const data = await res.json();

        // Gemini
        const bgGemini = document.getElementById("badge-gemini");
        if (data.gemini_ready) {
            bgGemini.classList.add("ready");
        } else {
            bgGemini.classList.add("warning");
        }

        // FFmpeg
        const bgFFmpeg = document.getElementById("badge-ffmpeg");
        if (data.ffmpeg_ready) {
            bgFFmpeg.classList.add("ready");
        } else {
            bgFFmpeg.classList.add("warning");
        }

        // YouTube
        const bgYt = document.getElementById("badge-youtube");
        const ytText = document.getElementById("yt-status-text");
        bgYt.style.cursor = "pointer";
        bgYt.title = "Klik untuk menghubungkan atau tes login YouTube";

        const btnConnectYt = document.getElementById("btnConnectYoutube");
        if (data.youtube_authenticated) {
            bgYt.className = "status-badge ready";
            ytText.textContent = "YouTube (Terhubung)";
            if (btnConnectYt) btnConnectYt.style.display = "none";
        } else if (data.youtube_expired) {
            bgYt.className = "status-badge warning";
            ytText.textContent = "Sesi Habis (Klik Login)";
            if (btnConnectYt) btnConnectYt.style.display = "inline-flex";
        } else if (data.youtube_ready) {
            bgYt.className = "status-badge warning";
            ytText.textContent = "Klik Login YouTube";
            if (btnConnectYt) btnConnectYt.style.display = "inline-flex";
        } else {
            bgYt.className = "status-badge warning";
            ytText.textContent = "YouTube (Belum Ada Secret)";
            if (btnConnectYt) btnConnectYt.style.display = "inline-flex";
        }

        // Event klik untuk login YouTube
        bgYt.onclick = async () => {
            if (!data.youtube_ready) {
                alert("File 'client_secret.json' belum ditemukan di folder proyek. Pastikan file JSON kredensial sudah ada.");
                return;
            }

            let force = false;
            if (data.youtube_authenticated) {
                if (!confirm("Akun YouTube Anda saat ini sudah terhubung.\n\nApakah Anda ingin login ulang atau mengganti channel YouTube?")) {
                    return;
                }
                force = true;
            }

            ytText.textContent = "Membuka Browser...";
            bgYt.style.opacity = "0.7";
            try {
                const aRes = await fetch("/api/youtube-auth", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ force: force })
                });
                const aData = await aRes.json();
                if (aData.status === "success") {
                    alert(`🎉 Berhasil terhubung dengan YouTube!\nChannel: ${aData.channel_title}`);
                    initSystemStatus();
                } else {
                    alert("Gagal login YouTube: " + aData.message);
                    initSystemStatus();
                }
            } catch (err) {
                alert("Error otorisasi YouTube: " + err.message);
                initSystemStatus();
            } finally {
                bgYt.style.opacity = "1";
            }
        };
    } catch (err) {
        console.error("Gagal memeriksa status sistem:", err);
    }
}

// 2. Preset Pills & Kategori Edukasi
function initPresets() {
    const topicInput = document.getElementById("topicInput");
    const container = document.getElementById("presetTopicsContainer");
    const btnRandom = document.getElementById("btnRandomTopic");

    // Delegasi klik preset-pill
    if (container) {
        container.addEventListener("click", (e) => {
            const pill = e.target.closest(".preset-pill");
            if (pill && pill.dataset.topic) {
                topicInput.value = pill.dataset.topic;
                topicInput.focus();
            }
        });
    }

    // Tombol Acak Topik Viral
    if (btnRandom) {
        btnRandom.addEventListener("click", async () => {
            btnRandom.textContent = "🎲 Mengacak...";
            try {
                const res = await fetch("/api/random-topic");
                const data = await res.json();
                if (data.topic) {
                    topicInput.value = data.topic;
                    topicInput.focus();
                }
            } catch (err) {
                console.error("Gagal mengambil random topic:", err);
            } finally {
                btnRandom.textContent = "🎲 Acak Topik Viral";
            }
        });
    }

    // Filter Niche Pills
    const nichePills = document.querySelectorAll(".niche-pill");
    nichePills.forEach(pill => {
        pill.addEventListener("click", async () => {
            nichePills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            const nicheKey = pill.dataset.niche;

            try {
                const res = await fetch("/api/educational-niches");
                const data = await res.json();
                const cats = data.categories || {};
                
                let selectedTopics = [];
                if (nicheKey === "all") {
                    Object.values(cats).forEach(c => {
                        if (c.topics && c.topics.length > 0) selectedTopics.push(c.topics[0]);
                    });
                } else if (cats[nicheKey] && cats[nicheKey].topics) {
                    selectedTopics = cats[nicheKey].topics.slice(0, 5);
                }

                if (selectedTopics.length > 0 && container) {
                    let html = '<span class="preset-label">Ide Topik:</span>';
                    selectedTopics.forEach(t => {
                        const shortLabel = t.length > 25 ? t.substring(0, 24) + "..." : t;
                        html += `<button type="button" class="preset-pill" data-topic="${t}">${shortLabel}</button>`;
                    });
                    container.innerHTML = html;
                }
            } catch (err) {
                console.error("Gagal load niche topics:", err);
            }
        });
    });
}

// 3. Pilihan Gaya Animasi
function initStyleSelectors() {
    const styleOptions = document.querySelectorAll(".style-option");
    styleOptions.forEach(opt => {
        opt.addEventListener("click", () => {
            styleOptions.forEach(o => o.classList.remove("selected"));
            opt.classList.add("selected");
            const radio = opt.querySelector("input[type='radio']");
            if (radio) radio.checked = true;
        });
    });
}

// Helper untuk menghitung waktu tayang terjadwal ISO UTC
function getScheduledPublishISO(slotChoice) {
    if (slotChoice === "instant" || !slotChoice) return null;
    
    const now = new Date();
    const primeSlots = {
        "08:00": { hour: 8, minute: 0, utch: 1, utcm: 0 },
        "12:00": { hour: 12, minute: 0, utch: 5, utcm: 0 },
        "15:30": { hour: 15, minute: 30, utch: 8, utcm: 30 },
        "18:30": { hour: 18, minute: 30, utch: 11, utcm: 30 },
        "20:30": { hour: 20, minute: 30, utch: 13, utcm: 30 }
    };
    
    let targetSlot = primeSlots[slotChoice];
    let scheduleDate = new Date(now);
    
    if (slotChoice === "next_slot" || !targetSlot) {
        const wibHours = (now.getUTCHours() + 7) % 24;
        const wibMinutes = now.getUTCMinutes();
        const currentMins = wibHours * 60 + wibMinutes;
        
        const sortedSlots = [
            { key: "08:00", mins: 8 * 60 },
            { key: "12:00", mins: 12 * 60 },
            { key: "15:30", mins: 15 * 60 + 30 },
            { key: "18:30", mins: 18 * 60 + 30 },
            { key: "20:30", mins: 20 * 60 + 30 }
        ];
        
        let found = sortedSlots.find(s => s.mins > currentMins + 20);
        if (found) {
            targetSlot = primeSlots[found.key];
        } else {
            // Sudah lewat malam ini, jadwalkan slot pagi besok
            targetSlot = primeSlots["08:00"];
            scheduleDate.setUTCDate(scheduleDate.getUTCDate() + 1);
        }
    }
    
    const targetUTC = new Date(Date.UTC(
        scheduleDate.getUTCFullYear(),
        scheduleDate.getUTCMonth(),
        scheduleDate.getUTCDate(),
        targetSlot.utch,
        targetSlot.utcm,
        0
    ));
    return targetUTC.toISOString();
}

// 4. Form Submission & Polling Progress
function initGenerateHandler() {
    const btnGenerate = document.getElementById("btnGenerate");
    const autoUploadCheck = document.getElementById("autoUploadCheck");
    const scheduleUploadBox = document.getElementById("scheduleUploadBox");

    if (autoUploadCheck && scheduleUploadBox) {
        autoUploadCheck.addEventListener("change", () => {
            scheduleUploadBox.style.display = autoUploadCheck.checked ? "block" : "none";
        });
    }

    btnGenerate.addEventListener("click", async () => {
        const topic = document.getElementById("topicInput").value.trim();
        const animStyle = document.querySelector("input[name='animStyle']:checked").value;
        const voiceType = document.getElementById("voiceType").value;
        const captionStyle = document.getElementById("captionStyle") ? document.getElementById("captionStyle").value : "clay_pop";
        const autoUpload = autoUploadCheck ? autoUploadCheck.checked : false;
        const privacy = document.getElementById("privacyStatus").value;

        const sceneCount = document.getElementById("sceneCountSelect") ? parseInt(document.getElementById("sceneCountSelect").value) : 5;
        const enableHeaderBadge = document.getElementById("chkHeaderBadge") ? document.getElementById("chkHeaderBadge").checked : true;
        const enableProgressBar = document.getElementById("chkProgressBar") ? document.getElementById("chkProgressBar").checked : true;
        const enableSFX = document.getElementById("chkSFX") ? document.getElementById("chkSFX").checked : true;

        let scheduledPublishTime = null;
        if (autoUpload) {
            const slotSelect = document.getElementById("scheduleSlotSelect");
            const slotChoice = slotSelect ? slotSelect.value : "next_slot";
            scheduledPublishTime = getScheduledPublishISO(slotChoice);
        }

        if (!topic) {
            alert("Harap masukkan topik video animasi edukasi terlebih dahulu!");
            return;
        }

        // Kunci tombol & alihkan ke state progress
        btnGenerate.disabled = true;
        btnGenerate.querySelector(".btn-text").textContent = "Sedang Memproses Claymation...";

        showProgressState();

        try {
            const res = await fetch("/api/start-generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    topic: topic,
                    animation_style: animStyle,
                    voice_type: voiceType,
                    caption_style: captionStyle,
                    scene_count: sceneCount,
                    enable_header_badge: enableHeaderBadge,
                    enable_progress_bar: enableProgressBar,
                    enable_sfx: enableSFX,
                    auto_upload: autoUpload,
                    privacy_status: privacy,
                    scheduled_publish_time: scheduledPublishTime
                })
            });
            const data = await res.json();
            if (res.ok) {
                startPolling();
            } else {
                alert(data.message || "Gagal memulai proses!");
                resetGenerateButton();
            }
        } catch (err) {
            alert("Error jaringan saat menghubungi server!");
            resetGenerateButton();
        }
    });
}

function showProgressState() {
    document.getElementById("idleState").classList.add("hidden");
    document.getElementById("playerState").classList.add("hidden");
    document.getElementById("progressState").classList.remove("hidden");
    
    document.getElementById("taskStatusBadge").textContent = "Sedang Merender...";
    document.getElementById("taskStatusBadge").className = "badge-status active";

    // Reset steps
    document.querySelectorAll(".step-item").forEach(s => s.className = "step-item");
    document.getElementById("step-script").classList.add("active");
    
    // Clear log
    document.getElementById("terminalLogs").innerHTML = "";
}

function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(checkProgress, 1200);
}

async function checkProgress() {
    try {
        const res = await fetch("/api/progress");
        const data = await res.json();

        // Update percent & step text
        const pct = data.progress || 0;
        document.getElementById("progressFill").style.width = `${pct}%`;
        document.getElementById("progressPercent").textContent = `${pct}%`;
        document.getElementById("currentStepText").textContent = data.step || "Memproses...";

        // Update checklist highlights
        if (pct >= 10) markStep("step-script", pct >= 25);
        if (pct >= 25) markStep("step-voice", pct >= 50);
        if (pct >= 40) markStep("step-art", pct >= 75);
        if (pct >= 75) markStep("step-render", pct >= 100);

        // Update terminal logs
        const terminal = document.getElementById("terminalLogs");
        if (data.log && data.log.length > 0) {
            terminal.innerHTML = data.log.map(item => `
                <div class="log-line">
                    <span class="text-muted">[${item.time}]</span> ${escapeHtml(item.message)}
                </div>
            `).join("");
            terminal.scrollTop = terminal.scrollHeight;
        }

        // Selesai
        if (data.status === "completed") {
            clearInterval(pollingInterval);
            resetGenerateButton();
            showCompletedState(data.result);
            initGallery(); // Refresh galeri
        } else if (data.status === "error") {
            clearInterval(pollingInterval);
            resetGenerateButton();
            alert("Terjadi kesalahan: " + (data.error_message || "Unknown error"));
            document.getElementById("taskStatusBadge").textContent = "Error";
            document.getElementById("taskStatusBadge").className = "badge-status";
        }
    } catch (err) {
        console.error("Gagal memeriksa progress:", err);
    }
}

function markStep(stepId, isDone) {
    const el = document.getElementById(stepId);
    if (!el) return;
    if (isDone) {
        el.className = "step-item done";
    } else {
        el.className = "step-item active";
    }
}

function resetGenerateButton() {
    const btn = document.getElementById("btnGenerate");
    btn.disabled = false;
    btn.querySelector(".btn-text").textContent = "Generate Video Animasi Claymation";
}

function showCompletedState(result) {
    document.getElementById("progressState").classList.add("hidden");
    const playerState = document.getElementById("playerState");
    playerState.classList.remove("hidden");

    document.getElementById("taskStatusBadge").textContent = "Selesai 100%";
    document.getElementById("taskStatusBadge").className = "badge-status success";

    if (result) {
        const video = document.getElementById("videoPlayer");
        video.src = result.video_url;
        video.load();
        video.play().catch(() => {});

        document.getElementById("playerVideoTitle").textContent = result.title;
        document.getElementById("btnDownload").href = result.video_url;

        const btnVeo = document.getElementById("btnDownloadVeo");
        if (result.veo_zip_url) {
            btnVeo.href = result.veo_zip_url;
            btnVeo.setAttribute("download", result.veo_zip_name || "Veo3_Package.zip");
            btnVeo.classList.remove("hidden");
        } else {
            btnVeo.classList.add("hidden");
        }

        // Button upload di player
        currentSelectedFilename = result.video_filename;
        const ytBox = document.getElementById("ytUploadResult");
        if (result.uploaded && result.youtube_url) {
            ytBox.classList.remove("hidden");
            ytBox.innerHTML = `🎉 Video telah tayang di YouTube: <a href="${result.youtube_url}" target="_blank" style="color: #6EE7B7; font-weight: bold;">Tonton di YouTube Shorts</a>`;
        } else {
            ytBox.classList.add("hidden");
        }

        // Render Scene Visualizer Timeline jika ada
        const timelineContainer = document.getElementById("sceneTimelineContainer");
        const cardsGrid = document.getElementById("sceneCardsGrid");
        const countBadge = document.getElementById("timelineCountBadge");
        if (result.scenes && result.scenes.length > 0 && cardsGrid) {
            timelineContainer.classList.remove("hidden");
            countBadge.textContent = `${result.scenes.length} Adegan`;
            cardsGrid.innerHTML = result.scenes.map((sc, i) => {
                const scNum = sc.scene_number || (i + 1);
                const motion = sc.camera_motion || "zoom_in";
                const caps = sc.captions || [];
                return `
                    <div class="scene-card-item">
                        <div class="scene-card-header">
                            <span class="scene-card-badge">Adegan ${scNum}</span>
                            <span class="scene-card-motion">🎥 ${motion}</span>
                        </div>
                        <p class="scene-card-narration">${escapeHtml(sc.narration || "")}</p>
                        <div class="scene-card-captions">
                            ${caps.map(c => `<span class="scene-chip">💬 ${escapeHtml(c)}</span>`).join("")}
                        </div>
                    </div>
                `;
            }).join("");
        } else if (timelineContainer) {
            timelineContainer.classList.add("hidden");
        }
    }
}

// 5. Galeri Video Tersimpan
async function initGallery() {
    const grid = document.getElementById("videoGrid");
    try {
        const res = await fetch("/api/videos");
        const videos = await res.json();

        if (videos.length === 0) {
            grid.innerHTML = `<div class="text-muted" style="grid-column: 1/-1; text-align: center; padding: 30px;">Belum ada video tersimpan. Buat video pertama Anda di atas!</div>`;
            return;
        }

        grid.innerHTML = videos.map(v => `
            <div class="video-card">
                <div class="video-card-thumb" onclick="playInMainPlayer('${v.url}', '${escapeHtml(v.title)}', '${v.filename}')">
                    <video src="${v.url}#t=0.5" preload="metadata"></video>
                    <div class="thumb-play-overlay">▶</div>
                </div>
                <div class="video-card-title" title="${escapeHtml(v.title)}">${escapeHtml(v.title)}</div>
                <div class="video-card-meta">
                    <span>📅 ${v.created_at}</span>
                    <span>💾 ${v.size_mb} MB</span>
                </div>
                <div class="video-card-actions">
                    <a href="${v.url}" download>📥 Unduh</a>
                    <button type="button" onclick="openUploadModal('${v.filename}')">🚀 Upload YT</button>
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Gagal memuat galeri:", err);
    }
}

document.getElementById("btnRefreshGallery").addEventListener("click", initGallery);

function playInMainPlayer(url, title, filename) {
    document.getElementById("idleState").classList.add("hidden");
    document.getElementById("progressState").classList.add("hidden");
    const playerState = document.getElementById("playerState");
    playerState.classList.remove("hidden");

    const video = document.getElementById("videoPlayer");
    video.src = url;
    video.load();
    video.play().catch(() => {});

    document.getElementById("playerVideoTitle").textContent = title;
    document.getElementById("btnDownload").href = url;
    currentSelectedFilename = filename;
    document.getElementById("ytUploadResult").classList.add("hidden");

    window.scrollTo({ top: 120, behavior: "smooth" });
}

// 6. Modal Upload ke YouTube
function initModal() {
    const modal = document.getElementById("uploadModal");
    const btnUploadNow = document.getElementById("btnUploadNow");
    const btnCancel = document.getElementById("btnCancelModal");
    const btnConfirm = document.getElementById("btnConfirmUpload");
    const schedulePreset = document.getElementById("modalSchedulePreset");
    const customTimeBox = document.getElementById("modalCustomTimeBox");
    const customTimeInput = document.getElementById("modalScheduleTime");

    if (schedulePreset) {
        schedulePreset.addEventListener("change", () => {
            const val = schedulePreset.value;
            if (val === "custom") {
                customTimeBox.classList.remove("hidden");
            } else {
                customTimeBox.classList.add("hidden");
            }
        });
    }

    btnUploadNow.addEventListener("click", () => {
        if (!currentSelectedFilename) return;
        openUploadModal(currentSelectedFilename);
    });

    btnCancel.addEventListener("click", () => {
        modal.classList.add("hidden");
    });

    btnConfirm.addEventListener("click", async () => {
        const privacy = document.getElementById("modalPrivacy").value;
        const presetVal = schedulePreset ? schedulePreset.value : "";
        let publishAtIso = null;

        if (presetVal) {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            let targetHour = 8;
            let targetMinute = 0;

            if (presetVal === "besok_pagi") {
                targetHour = 8; targetMinute = 0;
            } else if (presetVal === "besok_siang") {
                targetHour = 12; targetMinute = 0;
            } else if (presetVal === "besok_sore") {
                targetHour = 15; targetMinute = 30;
            } else if (presetVal === "besok_petang") {
                targetHour = 18; targetMinute = 30;
            } else if (presetVal === "besok_malam") {
                targetHour = 20; targetMinute = 30;
            } else if (presetVal === "custom" && customTimeInput.value) {
                const userDt = new Date(customTimeInput.value);
                if (!isNaN(userDt.getTime())) {
                    publishAtIso = userDt.toISOString();
                }
            }

            if (!publishAtIso && presetVal !== "custom") {
                // Set WIB (UTC+7) -> kurangi 7 jam untuk UTC
                const dtWib = new Date(Date.UTC(tomorrow.getFullYear(), tomorrow.getMonth(), tomorrow.getDate(), targetHour - 7, targetMinute, 0));
                publishAtIso = dtWib.toISOString();
            }
        }

        btnConfirm.disabled = true;
        btnConfirm.textContent = "Mengunggah & Menjadwalkan...";

        try {
            const res = await fetch("/api/upload-video", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    filename: currentSelectedFilename,
                    privacy: privacy,
                    publish_at: publishAtIso
                })
            });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                modal.classList.add("hidden");
                alert(`🎉 ${data.message}\nLink YouTube: ${data.youtube_url}`);
                const ytBox = document.getElementById("ytUploadResult");
                ytBox.classList.remove("hidden");
                ytBox.innerHTML = `🎉 Video berhasil diunggah: <a href="${data.youtube_url}" target="_blank" style="color: #6EE7B7; font-weight: bold;">Buka di YouTube Shorts</a> ${publishAtIso ? `<span style="display:block; font-size:0.8rem; color:#94A3B8;">Jadwal Rilis: ${publishAtIso}</span>` : ''}`;
            } else if (data.is_quota_error) {
                alert(`⚠️ Batas Kuota Harian YouTube Tercapai:\n${data.message}`);
            } else if (data.is_auth_error || (data.message && (data.message.includes("invalid_grant") || data.message.includes("expired or revoked")))) {
                alert(`🔑 Sesi YouTube Kedaluwarsa:\n${data.message || 'Token kedaluwarsa atau dicabut'}\n\nSilakan klik status 'YouTube' di header atas untuk login ulang.`);
                initSystemStatus();
            } else {
                alert("Gagal upload: " + (data.message || "Terjadi kesalahan"));
            }
        } catch (err) {
            alert("Error jaringan saat upload: " + err.message);
        } finally {
            btnConfirm.disabled = false;
            btnConfirm.textContent = "🚀 Upload & Jadwalkan";
        }
    });
}

function openUploadModal(filename) {
    currentSelectedFilename = filename;
    document.getElementById("modalVideoName").textContent = `File: ${filename}`;
    const schedulePreset = document.getElementById("modalSchedulePreset");
    if (schedulePreset) schedulePreset.value = "";
    const customTimeBox = document.getElementById("modalCustomTimeBox");
    if (customTimeBox) customTimeBox.classList.add("hidden");
    document.getElementById("uploadModal").classList.remove("hidden");
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>"']/g, m => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[m]);
}

// 7. Tab Navigation
function initTabs() {
    const tabBtns = document.querySelectorAll(".tab-nav-btn");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.dataset.target;
            tabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            document.querySelectorAll(".tab-pane").forEach(pane => {
                pane.classList.add("hidden");
                pane.classList.remove("active");
            });

            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.remove("hidden");
                targetPane.classList.add("active");
            }

            if (targetId === "batchView") {
                fetchBatchStatus();
                fetchSchedule();
            }
        });
    });
}

// 8. Batch Dashboard & 30-Day Scheduler
let batchPollTimer = null;

function initBatchDashboard() {
    const btnConnectYt = document.getElementById("btnConnectYoutube");
    const btnStart = document.getElementById("btnStartBatch");
    const btnPause = document.getElementById("btnPauseBatch");
    const btnReset = document.getElementById("btnResetBatch");
    const btnUploadToday = document.getElementById("btnUploadTodayBatch");
    const btnRefreshSchedule = document.getElementById("btnRefreshSchedule");

    if (btnConnectYt) {
        btnConnectYt.addEventListener("click", async () => {
            btnConnectYt.disabled = true;
            btnConnectYt.innerHTML = `<span class="btn-icon">⏳</span><span>Membuka Browser Login...</span>`;
            try {
                const aRes = await fetch("/api/youtube-auth", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ force: true })
                });
                const aData = await aRes.json();
                if (aData.status === "success") {
                    alert(`🎉 Berhasil terhubung dengan YouTube!\nChannel: ${aData.channel_title}`);
                    initSystemStatus();
                } else {
                    alert("Gagal login YouTube: " + aData.message);
                }
            } catch (err) {
                alert("Error otorisasi YouTube: " + err.message);
            } finally {
                btnConnectYt.disabled = false;
                btnConnectYt.innerHTML = `<span class="btn-icon">🔑</span><span>Hubungkan Akun YouTube</span>`;
            }
        });
    }

    if (btnStart) {
        btnStart.addEventListener("click", async () => {
            if (!confirm("Mulai otomatisasi pabrik video untuk 1 bulan penuh (150 video)? Proses akan berjalan di latar belakang (background).")) return;
            try {
                btnStart.disabled = true;
                const res = await fetch("/api/batch-start", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ total: 150 })
                });
                const data = await res.json();
                alert(data.message);
                startBatchPolling();
            } catch (e) {
                alert("Error memulai batch: " + e.message);
            } finally {
                btnStart.disabled = false;
            }
        });
    }

    if (btnPause) {
        btnPause.addEventListener("click", async () => {
            try {
                const res = await fetch("/api/batch-pause", { method: "POST" });
                const data = await res.json();
                alert(data.message);
                fetchBatchStatus();
            } catch (e) {
                alert("Error jeda batch: " + e.message);
            }
        });
    }

    if (btnReset) {
        btnReset.addEventListener("click", async () => {
            if (!confirm("Apakah Anda yakin ingin mereset antrean batch ke 0?")) return;
            try {
                const res = await fetch("/api/batch-reset", { method: "POST" });
                const data = await res.json();
                alert(data.message);
                fetchBatchStatus();
                fetchSchedule();
            } catch (e) {
                alert("Error reset batch: " + e.message);
            }
        });
    }

    const btnProduceAndUpload = document.getElementById("btnProduceAndUploadToday");
    if (btnProduceAndUpload) {
        btnProduceAndUpload.addEventListener("click", async () => {
            if (!confirm("Jalankan Auto-Pilot untuk memproduksi & mengunggah 5 video terjadwal hari ini (Handcrafted Claymation Animation)?")) return;
            btnProduceAndUpload.disabled = true;
            btnProduceAndUpload.innerHTML = `<span class="btn-icon">⏳</span><span>Auto-Pilot Berjalan...</span>`;
            try {
                const res = await fetch("/api/schedule-produce-and-upload-today", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ limit: 5, animation_style: "Handcrafted Claymation Animation" })
                });
                const data = await res.json();
                alert(data.message || "Auto-Pilot berhasil dijalankan di background!");
                fetchBatchStatus();
                fetchSchedule();
            } catch (e) {
                alert("Error Auto-Pilot: " + e.message);
            } finally {
                btnProduceAndUpload.disabled = false;
                btnProduceAndUpload.innerHTML = `<span class="btn-icon">⚡</span><span>Auto-Pilot: Buat & Upload 5 Video Hari Ini</span>`;
            }
        });
    }

    const btnReorganize = document.getElementById("btnReorganizeSchedule");
    if (btnReorganize) {
        btnReorganize.addEventListener("click", async () => {
            btnReorganize.disabled = true;
            btnReorganize.innerHTML = `<span class="btn-icon">⏳</span><span>Menata Jadwal...</span>`;
            try {
                const res = await fetch("/api/schedule/reorganize", { method: "POST" });
                const data = await res.json();
                alert(data.message || "Semua video berhasil dijadwalkan!");
                fetchSchedule();
                fetchBatchStatus();
            } catch (e) {
                alert("Error menyusun jadwal: " + e.message);
            } finally {
                btnReorganize.disabled = false;
                btnReorganize.innerHTML = `<span class="btn-icon">📅</span><span>Jadwalkan Semua Video Jadi (41 Video)</span>`;
            }
        });
    }

    const btnToggleAutopilot = document.getElementById("btnToggleAutopilot");
    if (btnToggleAutopilot) {
        btnToggleAutopilot.addEventListener("click", async () => {
            const isCurrentlyActive = btnToggleAutopilot.dataset.active === "true";
            const endpoint = isCurrentlyActive ? "/api/autopilot/stop" : "/api/autopilot/start";
            try {
                const res = await fetch(endpoint, { method: "POST" });
                const data = await res.json();
                alert(data.message);
                fetchAutopilotStatus();
            } catch (e) {
                alert("Error mengubah status Auto-Pilot: " + e.message);
            }
        });
    }

    if (btnUploadToday) {
        btnUploadToday.addEventListener("click", async () => {
            if (!confirm("Unggah video yang sudah selesai dibuat untuk jadwal hari ini ke YouTube Shorts? (Jatah aman 5 video/hari)")) return;
            btnUploadToday.disabled = true;
            btnUploadToday.innerHTML = `<span class="btn-icon">⏳</span><span>Memproses Upload...</span>`;
            try {
                const res = await fetch("/api/schedule-upload-today", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ limit: 5 })
                });
                const data = await res.json();
                if (data.quota_limit_reached) {
                    alert(`⚠️ Info Batas Kuota YouTube:\n${data.message}\n\nSeluruh video tetap aman tersimpan & Auto-Pilot harian akan otomatis mengunggah segera setelah jendela kuota 24 jam dibuka kembali oleh Google.`);
                } else {
                    alert(`Hasil Upload: ${data.uploaded_count} berhasil diunggah & dijadwalkan!\n${data.message || ""}`);
                }
                fetchBatchStatus();
                fetchSchedule();
                fetchAutopilotStatus();
            } catch (e) {
                alert("Error upload jadwal: " + e.message);
            } finally {
                btnUploadToday.disabled = false;
                btnUploadToday.innerHTML = `<span class="btn-icon">📤</span><span>Upload Batch Hari Ini</span>`;
            }
        });
    }

    if (btnRefreshSchedule) {
        btnRefreshSchedule.addEventListener("click", () => {
            fetchSchedule();
            fetchBatchStatus();
            fetchAutopilotStatus();
        });
    }

    // Ambil status awal
    fetchBatchStatus();
    fetchSchedule();
    fetchAutopilotStatus();
    startBatchPolling();
}

async function fetchAutopilotStatus() {
    try {
        const res = await fetch("/api/autopilot/status");
        if (!res.ok) return;
        const data = await res.json();
        const active = data.active;
        
        const btnToggle = document.getElementById("btnToggleAutopilot");
        const btnText = document.getElementById("autopilotBtnText");
        const dot = document.getElementById("autopilotStatusDot");
        const title = document.getElementById("autopilotStatusTitle");
        const msg = document.getElementById("autopilotStatusMsg");
        const lastRun = document.getElementById("autopilotLastRun");
        const nextRun = document.getElementById("autopilotNextRun");
        
        if (btnToggle) {
            btnToggle.dataset.active = active ? "true" : "false";
            btnToggle.style.background = active 
                ? "linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)" 
                : "linear-gradient(135deg, #10b981 0%, #047857 100%)";
            if (btnText) btnText.textContent = active ? "Hentikan Auto-Pilot" : "Aktifkan Auto-Pilot Harian";
        }
        
        if (dot) dot.style.background = active ? "#10b981" : "#64748b";
        if (title) title.textContent = active ? "Auto-Pilot Harian: 🟢 AKTIF & BERJALAN" : "Auto-Pilot Harian: ⚪ Nonaktif";
        if (msg && data.last_message) msg.textContent = data.last_message;
        if (lastRun) lastRun.textContent = data.last_run || "-";
        if (nextRun) nextRun.textContent = active ? (data.next_run || "-") : "-";
    } catch (e) {
        console.error("Gagal mengambil status autopilot:", e);
    }
}

function startBatchPolling() {
    if (batchPollTimer) clearInterval(batchPollTimer);
    batchPollTimer = setInterval(() => {
        fetchBatchStatus();
        fetchAutopilotStatus();
    }, 4000);
}

async function fetchBatchStatus() {
    try {
        const res = await fetch("/api/batch-status");
        if (!res.ok) return;
        const data = await res.json();
        const batch = data.batch || {};
        const sched = data.schedule || {};

        const total = batch.total_target || 150;
        const currentIdx = batch.current_index || 0;
        const successful = batch.successful || 0;
        const status = batch.status || "idle";
        const currentTopic = batch.current_topic || "Antrean siap dijalankan";
        const uploadedCount = sched.uploaded_count || 0;
        const producedCount = sched.produced_count || successful;

        // Update Metrik
        const metricTotal = document.getElementById("metricTotal");
        if (metricTotal) metricTotal.textContent = `${total} Video`;

        const metricProduced = document.getElementById("metricProduced");
        if (metricProduced) metricProduced.textContent = `${producedCount} / ${total}`;

        const metricPct = document.getElementById("metricPct");
        const pct = Math.round((producedCount / total) * 100);
        if (metricPct) metricPct.textContent = `${pct}% Terpenuhi`;

        const metricUploaded = document.getElementById("metricUploaded");
        if (metricUploaded) metricUploaded.textContent = `${uploadedCount} / ${total}`;

        // Update Tracker
        const badge = document.getElementById("batchStateBadge");
        if (badge) {
            badge.className = "tracker-badge " + status;
            badge.textContent = status === "running" ? "Sedang Berjalan" : (status === "paused" ? "Dijeda" : (status === "completed" ? "Selesai 100%" : "Siap"));
        }

        const titleEl = document.getElementById("batchCurrentTopicTitle");
        if (titleEl) {
            titleEl.textContent = status === "running" ? `Sedang Memproduksi: "${currentTopic}"` : currentTopic;
        }

        const fracEl = document.getElementById("batchFractionText");
        if (fracEl) fracEl.textContent = `${currentIdx} / ${total} Video`;

        const progressFill = document.getElementById("batchProgressFill");
        if (progressFill) progressFill.style.width = `${Math.min(100, Math.round((currentIdx / total) * 100))}%`;

    } catch (e) {
        console.error("Gagal mengambil batch status:", e);
    }
}

async function fetchSchedule() {
    const container = document.getElementById("scheduleDaysContainer");
    if (!container) return;

    try {
        const res = await fetch("/api/schedule");
        if (!res.ok) return;
        const data = await res.json();
        const days = data.days || [];

        if (days.length === 0) {
            container.innerHTML = `<div class="schedule-loading">Belum ada jadwal yang dimuat.</div>`;
            return;
        }

        let html = "";
        days.forEach(day => {
            const dayNum = day.day_number;
            const dateStr = day.date;
            const dayStatus = day.day_status || "pending";
            const slots = day.slots || [];
            
            const uploadedInDay = slots.filter(s => s.status === "uploaded").length;
            const producedInDay = slots.filter(s => s.status === "produced" || s.status === "uploaded").length;

            html += `
            <div class="day-box">
                <div class="day-box-header" onclick="this.nextElementSibling.classList.toggle('hidden')">
                    <div class="day-title-grp">
                        <span class="day-tag">HARI ${dayNum}</span>
                        <span class="day-date">${dateStr}</span>
                        <span class="day-status-pill ${dayStatus}">${uploadedInDay === 5 ? "✅ 5/5 Terunggah" : `${producedInDay}/5 Siap (${uploadedInDay} Terunggah)`}</span>
                    </div>
                    <span style="color: var(--text-dim); font-size: 0.85rem; cursor: pointer;">▼ Detail 5 Jam Tayang</span>
                </div>
                <div class="day-slots-list">
                    ${slots.map(slot => {
                        const hasVideo = Boolean(slot.video_path);
                        const isUploaded = slot.status === "uploaded";
                        const vFilename = hasVideo ? slot.video_path.split(/[/\\]/).pop() : "";
                        
                        let statusClass = slot.status || "pending";
                        let statusLabel = "⏳ Antrean";
                        
                        if (isUploaded) {
                            statusClass = "uploaded";
                            statusLabel = "✅ Terunggah ke YouTube";
                        } else if (hasVideo) {
                            statusClass = "produced";
                            statusLabel = "🎬 Terjadwal Siap Upload";
                        } else if (slot.status === "failed") {
                            statusClass = "failed";
                            statusLabel = "⚠️ Perlu Ditinjau";
                        }

                        return `
                        <div class="slot-card">
                            <div class="slot-time-badge">
                                <span class="slot-time">${escapeHtml(slot.slot_label || slot.wib_time)}</span>
                                <span class="slot-status ${statusClass}">${statusLabel}</span>
                            </div>
                            <div class="slot-topic">${escapeHtml(slot.topic)}</div>
                            <div class="slot-action" style="display: flex; gap: 10px; align-items: center; justify-content: flex-end; margin-top: 6px;">
                                ${hasVideo ? `<a href="javascript:void(0)" onclick="loadExistingVideo('${escapeHtml(vFilename)}', '${escapeHtml(slot.topic)}')" style="color: #60A5FA; font-size: 0.78rem; text-decoration: none;">▶ Putar Video</a>` : ''}
                                ${hasVideo && !isUploaded ? `<a href="javascript:void(0)" onclick="uploadScheduledSlotDirect(${slot.video_index}, '${escapeHtml(slot.topic)}')" style="color: #F59E0B; font-size: 0.78rem; text-decoration: none; font-weight: 600;">🚀 Upload Terjadwal</a>` : ''}
                                ${slot.youtube_url ? `<a href="${slot.youtube_url}" target="_blank" style="color: #34D399; font-size: 0.78rem; text-decoration: none; font-weight: 600;">🔗 Buka YouTube Shorts</a>` : `<span style="font-size: 0.72rem; color: var(--text-dim);">${hasVideo ? `📅 Rilis: ${escapeHtml(slot.wib_time || '')}` : "Menunggu Antrean"}</span>`}
                            </div>
                        </div>
                        `;
                    }).join("")}
                </div>
            </div>
            `;
        });

        container.innerHTML = html;

    } catch (e) {
        container.innerHTML = `<div class="schedule-loading text-danger">Gagal memuat jadwal: ${e.message}</div>`;
    }
}

async function uploadScheduledSlotDirect(videoIndex, topic) {
    if (!confirm(`Unggah video #${videoIndex}: "${topic}" sekarang ke YouTube Shorts dengan jadwal rilis otomatis?`)) return;
    try {
        const res = await fetch("/api/schedule/upload-slot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_index: videoIndex })
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
            alert(`🎉 ${data.message}\nLink YouTube: ${data.youtube_url}`);
        } else if (data.is_quota_error) {
            alert(`⚠️ Batas Kuota Harian YouTube Tercapai:\n${data.message}`);
        } else if (data.is_auth_error || (data.message && (data.message.includes("invalid_grant") || data.message.includes("expired or revoked")))) {
            alert(`🔑 Sesi YouTube Kedaluwarsa:\n${data.message || 'Token kedaluwarsa atau dicabut'}\n\nSilakan klik status 'YouTube' di header atas untuk login ulang.`);
            initSystemStatus();
        } else {
            alert("Gagal upload: " + (data.message || "Terjadi kesalahan"));
        }
        fetchSchedule();
        fetchBatchStatus();
    } catch (err) {
        alert("Error jaringan: " + err.message);
    }
}

