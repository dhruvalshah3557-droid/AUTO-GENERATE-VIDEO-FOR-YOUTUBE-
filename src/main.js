import { translations } from "./i18n.js";

const $ = (id) => document.getElementById(id);
const state = {
  lang: localStorage.getItem("mpt_lang") || "en",
  voiceMode: "auto",
};

function t(key) {
  return translations[state.lang]?.[key] || translations.en[key] || key;
}

function applyI18n() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
}

function errorMessage(data, fallback) {
  const detail = data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => item.msg || item.message || JSON.stringify(item))
      .join("; ");
  }
  if (data?.message) return data.message;
  if (data?.error) return data.error;
  return fallback;
}

async function api(path, options = {}) {
  const res = await fetch(`/api${path}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(errorMessage(data, `Request failed: ${res.status}`));
  }
  return data;
}

function formPayload() {
  return {
    video_subject: $("video-subject").value.trim(),
    video_language: $("script-language").value,
    paragraph_number: Number($("paragraph-number").value),
    video_script_prompt: $("script-prompt").value.trim(),
    video_script: $("video-script").value.trim(),
    video_terms: $("video-terms").value.trim(),
    video_style: $("video-style").value,
    source_url: $("source-url").value.trim(),
    article_text: $("article-text").value.trim(),
    video_source: $("video-source").value,
    video_concat_mode: $("concat-mode").value,
    match_materials_to_script: $("match-script").checked,
    video_transition_mode: $("transition-mode").value,
    video_aspect: $("aspect-ratio").value,
    video_clip_duration: Number($("clip-duration").value),
    video_count: Number($("video-count").value),
    voice_mode: state.voiceMode,
    voice_name: $("voice-name").value,
    voice_volume: Number($("voice-volume").value),
    voice_rate: Number($("voice-rate").value),
    bgm_type: $("bgm-type").value,
    bgm_volume: Number($("bgm-volume").value),
    subtitle_enabled: $("subtitle-enabled").checked,
    font_name: $("font-name").value,
    subtitle_position: $("subtitle-position").value,
    text_fore_color: $("text-color").value,
    font_size: Number($("font-size").value),
    stroke_color: $("stroke-color").value,
    stroke_width: Number($("stroke-width").value),
    text_background_color: $("subtitle-bg").checked ? $("subtitle-bg-color").value : false,
    rounded_subtitle_background: $("rounded-bg").checked,
  };
}

function setVoiceMode(mode) {
  state.voiceMode = mode;
  document.querySelectorAll("#voice-mode .seg").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
  $("auto-voice-fields").hidden = mode !== "auto";
  $("upload-voice-fields").hidden = mode !== "upload";
}

async function loadVoices() {
  const data = await api("/voices");
  const select = $("voice-name");
  select.innerHTML = "";
  for (const voice of data.voices) {
    const option = document.createElement("option");
    option.value = voice.id;
    option.textContent = voice.label;
    select.appendChild(option);
  }
  const preferred = data.voices.find((v) => v.id.includes("Xiaoxiao")) || data.voices[0];
  if (preferred) select.value = preferred.id;
}

async function loadSettings() {
  const cfg = await api("/settings");
  $("cfg-pexels").value = cfg.pexels_api_key || "";
  $("cfg-pixabay").value = cfg.pixabay_api_key || "";
  $("cfg-llm-provider").value = cfg.llm_provider || "builtin";
  $("cfg-llm-base").value = cfg.llm_base_url || "";
  $("cfg-llm-key").value = cfg.llm_api_key || "";
  $("cfg-llm-model").value = cfg.llm_model || "";
}

async function saveSettings() {
  await api("/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pexels_api_key: $("cfg-pexels").value.trim(),
      pixabay_api_key: $("cfg-pixabay").value.trim(),
      llm_provider: $("cfg-llm-provider").value,
      llm_base_url: $("cfg-llm-base").value.trim(),
      llm_api_key: $("cfg-llm-key").value.trim(),
      llm_model: $("cfg-llm-model").value.trim(),
    }),
  });
  $("settings-modal").hidden = true;
}

function renderTasks(tasks) {
  const box = $("task-list");
  if (!tasks.length) {
    box.innerHTML = `<p class="muted">${t("noTasks")}</p>`;
    return;
  }
  box.innerHTML = tasks
    .map((task) => {
      const statusClass = task.state === 1 ? "ok" : task.state === -1 ? "fail" : "run";
      const statusText = task.state === 1 ? "done" : task.state === -1 ? "failed" : `${task.progress || 0}%`;
      return `<div class="task-row">
        <span class="task-status ${statusClass}">${statusText}</span>
        <span>${task.subject || task.task_id}</span>
        <span>${task.progress || 0}%</span>
        <span>${(task.task_id || "").slice(0, 8)}</span>
      </div>`;
    })
    .join("");
}

async function refreshTasks() {
  const data = await api("/tasks");
  renderTasks(data.tasks || []);
}

function showProgress(text, percent) {
  $("result-panel").hidden = false;
  $("progress-text").textContent = text;
  $("progress-fill").style.width = `${percent}%`;
}

function showVideos(videos) {
  const box = $("result-videos");
  box.innerHTML = videos
    .map((src) => `<video src="${src}" controls playsinline></video>`)
    .join("");
}

async function pollTask(taskId) {
  for (;;) {
    const data = await api(`/tasks/${taskId}`);
    const task = data.data || data;
    showProgress(task.message || t("generating"), task.progress || 0);
    if (task.state === 1) {
      showProgress(t("done"), 100);
      showVideos(task.videos || []);
      await refreshTasks();
      return;
    }
    if (task.state === -1) {
      showProgress(`${t("failed")}: ${task.error || ""}`, task.progress || 0);
      await refreshTasks();
      throw new Error(task.error || t("failed"));
    }
    await new Promise((r) => setTimeout(r, 1200));
  }
}

async function generateScript() {
  const payload = formPayload();
  if (!payload.video_subject && !payload.source_url && !payload.article_text) {
    $("video-subject").focus();
    return;
  }
  const data = await api("/scripts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  $("video-script").value = data.video_script || "";
  if (data.video_terms) $("video-terms").value = data.video_terms.join(", ");
  if (data.article_text) $("article-text").value = data.article_text;
  if (data.article_title && !$("video-subject").value.trim()) {
    $("video-subject").value = data.article_title;
  }
}

async function fetchArticle() {
  const url = $("source-url").value.trim();
  if (!url) {
    $("source-url").focus();
    return;
  }
  const data = await api("/url-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  $("article-text").value = data.content || "";
  if (data.title && !$("video-subject").value.trim()) $("video-subject").value = data.title;
  if (data.url) $("source-url").value = data.url;
}

function renderHotItems(items) {
  const box = $("hot-items");
  if (!items.length) {
    box.innerHTML = `<p class="muted">${t("noTasks")}</p>`;
    return;
  }
  box.innerHTML = items
    .map((item, index) => {
      const title = item.title || item.name || "";
      const url = item.url || item.link || "";
      const hot = item.hot || item.hotval || "";
      return `<button type="button" class="hot-item" data-index="${index}" data-title="${title.replace(/"/g, "&quot;")}" data-url="${url.replace(/"/g, "&quot;")}">
        <span class="hot-rank">${item.index || index + 1}</span>
        <span class="hot-title">${title}</span>
        <span class="hot-meta">${hot}</span>
      </button>`;
    })
    .join("");
  box.querySelectorAll(".hot-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("video-subject").value = btn.dataset.title || "";
      if (btn.dataset.url) $("source-url").value = btn.dataset.url;
      $("hotlist-modal").hidden = true;
    });
  });
}

async function openHotlist() {
  const data = await api("/hotlist");
  const sources = data.data || [];
  const select = $("hot-source");
  select.innerHTML = "";
  for (const source of sources) {
    const option = document.createElement("option");
    option.value = source.name;
    option.textContent = source.name;
    select.appendChild(option);
  }
  const apply = () => {
    const current = sources.find((item) => item.name === select.value) || sources[0];
    renderHotItems(current?.data || []);
  };
  select.onchange = apply;
  apply();
  $("hotlist-modal").hidden = false;
}

async function generateTerms() {
  const payload = formPayload();
  if (!payload.video_script && !payload.video_subject) return;
  const data = await api("/terms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  $("video-terms").value = (data.video_terms || []).join(", ");
}

async function previewVoice() {
  const payload = formPayload();
  const sample = payload.video_script || payload.video_subject || "MoneyPrinterTurbo voice preview.";
  const res = await fetch("/api/voice-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: sample, voice_name: payload.voice_name, voice_rate: payload.voice_rate }),
  });
  if (!res.ok) throw new Error("Voice preview failed");
  const blob = await res.blob();
  const audio = $("preview-audio");
  audio.src = URL.createObjectURL(blob);
  await audio.play();
}

async function generateVideo() {
  const payload = formPayload();
  if (!payload.video_subject && !payload.video_script && !payload.source_url && !payload.article_text) {
    $("video-subject").focus();
    return;
  }
  const btn = $("generate-btn");
  btn.disabled = true;
  showProgress(t("generating"), 4);
  showVideos([]);
  try {
    const form = new FormData();
    form.append("payload", JSON.stringify(payload));
    const file = $("custom-audio").files[0];
    if (payload.voice_mode === "upload" && file) form.append("custom_audio", file);
    const res = await fetch("/api/videos", { method: "POST", body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(errorMessage(data, "create failed"));
    const taskId = data.data?.task_id || data.task_id;
    if (!taskId) throw new Error("task id missing");
    await pollTask(taskId);
  } catch (err) {
    showProgress(`${t("failed")}: ${err.message}`, 0);
  } finally {
    btn.disabled = false;
  }
}

function restoreSubtitles() {
  $("subtitle-enabled").checked = true;
  $("font-name").selectedIndex = 0;
  $("subtitle-position").value = "bottom";
  $("text-color").value = "#ffffff";
  $("font-size").value = 60;
  $("font-size-val").textContent = "60";
  $("stroke-color").value = "#000000";
  $("stroke-width").value = 1.5;
  $("stroke-width-val").textContent = "1.50";
  $("subtitle-bg").checked = true;
  $("subtitle-bg-color").value = "#000000";
  $("rounded-bg").checked = false;
}

function bindUi() {
  $("lang-select").value = state.lang;
  $("lang-select").addEventListener("change", () => {
    state.lang = $("lang-select").value;
    localStorage.setItem("mpt_lang", state.lang);
    applyI18n();
  });
  $("font-size").addEventListener("input", () => {
    $("font-size-val").textContent = $("font-size").value;
  });
  $("stroke-width").addEventListener("input", () => {
    $("stroke-width-val").textContent = Number($("stroke-width").value).toFixed(2);
  });
  document.querySelectorAll("#voice-mode .seg").forEach((btn) => {
    btn.addEventListener("click", () => setVoiceMode(btn.dataset.mode));
  });
  $("task-manager-btn").addEventListener("click", async () => {
    const pop = $("task-popover");
    pop.hidden = !pop.hidden;
    if (!pop.hidden) await refreshTasks();
  });
  $("refresh-tasks").addEventListener("click", refreshTasks);
  $("settings-btn").addEventListener("click", async () => {
    await loadSettings();
    $("settings-modal").hidden = false;
  });
  $("close-settings").addEventListener("click", () => ($("settings-modal").hidden = true));
  $("cancel-settings").addEventListener("click", () => ($("settings-modal").hidden = true));
  $("save-settings").addEventListener("click", () => saveSettings().catch((e) => alert(e.message)));
  $("gen-script-btn").addEventListener("click", () => generateScript().catch((e) => alert(e.message)));
  $("fetch-url-btn").addEventListener("click", () => fetchArticle().catch((e) => alert(e.message)));
  $("hotlist-btn").addEventListener("click", () => openHotlist().catch((e) => alert(e.message)));
  $("close-hotlist").addEventListener("click", () => ($("hotlist-modal").hidden = true));
  $("gen-terms-btn").addEventListener("click", () => generateTerms().catch((e) => alert(e.message)));
  $("preview-voice-btn").addEventListener("click", () => previewVoice().catch((e) => alert(e.message)));
  $("restore-subtitle-btn").addEventListener("click", restoreSubtitles);
  $("generate-btn").addEventListener("click", generateVideo);
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".popover-wrap")) $("task-popover").hidden = true;
  });
}

applyI18n();
bindUi();
loadVoices().catch(() => {});
refreshTasks().catch(() => {});
