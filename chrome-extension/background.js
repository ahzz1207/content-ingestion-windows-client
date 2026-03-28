const DEFAULT_API_BASE_URL = "http://127.0.0.1:19527/api/v1";
const BADGE_ALARM_NAME = "refreshBadge";
const CONTEXT_MENU_ID = "send-to-content-ingestion";
const API_TIMEOUT_MS = 20000;

async function getSettings() {
  const stored = await chrome.storage.local.get({
    apiBaseUrl: DEFAULT_API_BASE_URL,
    apiToken: "",
  });
  return {
    apiBaseUrl: normalizeApiBaseUrl(stored.apiBaseUrl || DEFAULT_API_BASE_URL),
    apiToken: stored.apiToken || "",
  };
}

function normalizeApiBaseUrl(value) {
  return String(value || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

async function saveSettings(nextSettings) {
  const current = await getSettings();
  const merged = {
    apiBaseUrl: normalizeApiBaseUrl(nextSettings.apiBaseUrl || current.apiBaseUrl),
    apiToken: nextSettings.apiToken ?? current.apiToken,
  };
  await chrome.storage.local.set(merged);
  await updateBadge();
  return merged;
}

async function apiRequest(path, options = {}) {
  const settings = await getSettings();
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  if (settings.apiToken) {
    headers.set("Authorization", `Bearer ${settings.apiToken}`);
  }
  const init = {
    ...options,
    headers,
  };
  if (options.body && typeof options.body !== "string") {
    headers.set("Content-Type", "application/json");
    init.body = JSON.stringify(options.body);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  init.signal = controller.signal;

  try {
    const response = await fetch(`${settings.apiBaseUrl}${path}`, init);
    const text = await response.text();
    const data = text ? safeJsonParse(text) : {};
    if (!response.ok) {
      const detail = data && typeof data.detail === "string" ? data.detail : response.statusText;
      throw new Error(`API ${response.status}: ${detail}`);
    }
    return data;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("API request timed out. The page may still be queued shortly.");
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

function safeJsonParse(value) {
  try {
    return JSON.parse(value);
  } catch {
    return { raw: value };
  }
}

async function submitUrl(url) {
  return apiRequest("/ingest", {
    method: "POST",
    body: {
      url,
    },
  });
}

async function listRecentJobs() {
  return apiRequest("/jobs?status=queued,processing,completed,failed&limit=10&view=result_cards");
}

async function archiveJob(jobId) {
  return apiRequest(`/jobs/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
  });
}

async function updateBadge() {
  try {
    const data = await apiRequest("/jobs?status=queued,processing&limit=50");
    const count = Number(data.total || 0);
    await chrome.action.setBadgeBackgroundColor({ color: "#2E6DA4" });
    await chrome.action.setBadgeText({ text: count > 0 ? String(count) : "" });
  } catch (error) {
    await chrome.action.setBadgeBackgroundColor({ color: "#A94442" });
    await chrome.action.setBadgeText({ text: "!" });
  }
}

async function getCurrentTabUrl() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url || tab.url.startsWith("chrome://")) {
    throw new Error("Current tab URL is not available");
  }
  return tab.url;
}

chrome.runtime.onInstalled.addListener(async () => {
  chrome.contextMenus.create({
    id: CONTEXT_MENU_ID,
    title: "Send to Content Ingestion",
    contexts: ["page", "link"],
  });
  chrome.alarms.create(BADGE_ALARM_NAME, { periodInMinutes: 1 });
  await updateBadge();
});

chrome.runtime.onStartup.addListener(async () => {
  chrome.alarms.create(BADGE_ALARM_NAME, { periodInMinutes: 1 });
  await updateBadge();
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === BADGE_ALARM_NAME) {
    await updateBadge();
  }
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  const url = info.linkUrl || info.pageUrl;
  if (!url) {
    return;
  }
  try {
    await submitUrl(url);
    await updateBadge();
  } catch (error) {
    console.error("Failed to submit URL from context menu", error);
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    if (message.type === "get-settings") {
      sendResponse({ ok: true, settings: await getSettings() });
      return;
    }
    if (message.type === "save-settings") {
      const settings = await saveSettings(message.settings || {});
      sendResponse({ ok: true, settings });
      return;
    }
    if (message.type === "submit-current-tab") {
      const url = await getCurrentTabUrl();
      const job = await submitUrl(url);
      await updateBadge();
      sendResponse({ ok: true, job });
      return;
    }
    if (message.type === "submit-url") {
      const job = await submitUrl(String(message.url || ""));
      await updateBadge();
      sendResponse({ ok: true, job });
      return;
    }
    if (message.type === "list-jobs") {
      const jobs = await listRecentJobs();
      sendResponse({ ok: true, jobs });
      return;
    }
    if (message.type === "archive-job") {
      const archived = await archiveJob(String(message.jobId || ""));
      await updateBadge();
      sendResponse({ ok: true, archived });
      return;
    }
    if (message.type === "health") {
      const health = await apiRequest("/health");
      sendResponse({ ok: true, health });
      return;
    }
    sendResponse({ ok: false, error: "Unknown message type" });
  })().catch((error) => {
    sendResponse({ ok: false, error: error.message || String(error) });
  });
  return true;
});
