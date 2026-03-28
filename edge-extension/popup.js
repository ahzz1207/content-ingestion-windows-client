const jobsList = document.getElementById("jobs-list");
const statusMessage = document.getElementById("status-message");
const inboxStatus = document.getElementById("inbox-status");
const manualForm = document.getElementById("manual-form");
const manualUrlInput = document.getElementById("manual-url");

function setStatus(message, tone = "neutral") {
  statusMessage.textContent = message || "";
  statusMessage.dataset.tone = tone;
}

function formatTimestamp(value) {
  if (!value) {
    return "Unknown time";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusLabel(status) {
  return {
    queued: "Queued",
    processing: "Processing",
    completed: "Completed",
    failed: "Failed",
  }[status] || status;
}

function verificationLabel(value) {
  return {
    supported: "Verified",
    mixed: "Mixed",
    warning: "Needs review",
    unclear: "Unclear",
    unavailable: "No verification",
  }[value] || value;
}

function jobUrl(item) {
  return item.source_url || item.canonical_url || "";
}

function openSourceUrl(item) {
  const url = jobUrl(item);
  if (!url) {
    setStatus("No source URL is available for this job.", "error");
    return;
  }
  chrome.tabs.create({ url });
}

async function copyJobId(item) {
  try {
    await navigator.clipboard.writeText(item.job_id);
    setStatus(`Copied ${item.job_id}`, "success");
  } catch (error) {
    setStatus(error.message || "Failed to copy job id", "error");
  }
}

async function archiveJob(item) {
  const confirmed = window.confirm(
    `Archive job ${item.job_id}? Pipeline files will be moved to the archived folder. Imported Obsidian notes will stay.`
  );
  if (!confirmed) {
    return;
  }
  await sendMessage({ type: "archive-job", jobId: item.job_id });
  setStatus(`Archived ${item.job_id}`, "success");
  await refreshJobs();
}

function appendMeta(row, item) {
  const meta = document.createElement("p");
  meta.className = "job-meta";
  const parts = [statusLabel(item.status), formatTimestamp(item.updated_at)];
  if (item.platform) {
    parts.push(item.platform);
  }
  meta.textContent = parts.filter(Boolean).join(" | ");
  row.appendChild(meta);
}

function appendActions(row, item) {
  const actions = document.createElement("div");
  actions.className = "job-actions";

  if (jobUrl(item)) {
    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "mini-button";
    openButton.textContent = "Open source";
    openButton.addEventListener("click", () => openSourceUrl(item));
    actions.appendChild(openButton);
  }

  const copyButton = document.createElement("button");
  copyButton.type = "button";
  copyButton.className = "mini-button";
  copyButton.textContent = "Copy job id";
  copyButton.addEventListener("click", async () => {
    await copyJobId(item);
  });
  actions.appendChild(copyButton);

  const archiveButton = document.createElement("button");
  archiveButton.type = "button";
  archiveButton.className = "mini-button";
  archiveButton.textContent = "Archive";
  archiveButton.addEventListener("click", async () => {
    try {
      await archiveJob(item);
    } catch (error) {
      setStatus(error.message || "Failed to archive job", "error");
    }
  });
  actions.appendChild(archiveButton);

  row.appendChild(actions);
}

function renderQueuedOrProcessing(row, item) {
  const title = document.createElement("p");
  title.className = "job-title";
  title.textContent = item.title || jobUrl(item) || item.job_id;
  row.appendChild(title);

  const summary = document.createElement("p");
  summary.className = "job-summary";
  summary.textContent = jobUrl(item) || "Waiting for analysis output.";
  row.appendChild(summary);
}

function renderCompleted(row, item) {
  const card = item.result_card || {};
  const title = document.createElement("p");
  title.className = "job-title";
  title.textContent = card.headline || item.title || item.job_id;
  row.appendChild(title);

  const summary = document.createElement("p");
  summary.className = "job-summary";
  summary.textContent = card.one_sentence_take || jobUrl(item) || "Completed.";
  row.appendChild(summary);

  const chips = document.createElement("div");
  chips.className = "job-chips";

  const verificationChip = document.createElement("span");
  verificationChip.className = `job-chip tone-${card.verification_signal || "unavailable"}`;
  verificationChip.textContent = verificationLabel(card.verification_signal || "unavailable");
  chips.appendChild(verificationChip);

  if (Number(card.warning_count || 0) > 0) {
    const warningChip = document.createElement("span");
    warningChip.className = "job-chip tone-warning";
    warningChip.textContent = `${card.warning_count} warning${card.warning_count === 1 ? "" : "s"}`;
    chips.appendChild(warningChip);
  }

  if (card.coverage_warning) {
    const coverageChip = document.createElement("span");
    coverageChip.className = "job-chip tone-caution";
    coverageChip.textContent = "Coverage limited";
    chips.appendChild(coverageChip);
  }

  if (chips.childElementCount > 0) {
    row.appendChild(chips);
  }

  if (Array.isArray(card.quick_takeaways) && card.quick_takeaways.length > 0) {
    const takeawayList = document.createElement("ul");
    takeawayList.className = "takeaway-list";
    for (const takeaway of card.quick_takeaways) {
      const itemEl = document.createElement("li");
      itemEl.textContent = takeaway;
      takeawayList.appendChild(itemEl);
    }
    row.appendChild(takeawayList);
  }
}

function renderFailed(row, item) {
  const card = item.failure_card || {};
  const title = document.createElement("p");
  title.className = "job-title";
  title.textContent = item.title || jobUrl(item) || item.job_id;
  row.appendChild(title);

  const summary = document.createElement("p");
  summary.className = "job-summary";
  summary.textContent = card.summary || card.error || "Processing failed.";
  row.appendChild(summary);
}

function renderJobs(items) {
  jobsList.innerHTML = "";
  if (!items || items.length === 0) {
    jobsList.innerHTML = '<p class="empty-state">No jobs yet.</p>';
    return;
  }

  for (const item of items) {
    const row = document.createElement("article");
    row.className = `job-card is-${item.status}`;

    if (item.status === "completed") {
      renderCompleted(row, item);
    } else if (item.status === "failed") {
      renderFailed(row, item);
    } else {
      renderQueuedOrProcessing(row, item);
    }

    appendMeta(row, item);
    appendActions(row, item);
    jobsList.appendChild(row);
  }
}

async function sendMessage(message) {
  const response = await chrome.runtime.sendMessage(message);
  if (!response || !response.ok) {
    throw new Error((response && response.error) || "Request failed");
  }
  return response;
}

async function refreshInboxStatus() {
  try {
    const response = await sendMessage({ type: "health" });
    const health = response.health || {};
    const inboxPath = health.shared_inbox_root || "unknown";
    const watcherRunning = health.watcher?.running;
    const watcherLabel = watcherRunning === true ? "running" : watcherRunning === false ? "stopped" : "unknown";
    inboxStatus.textContent = `Inbox: ${inboxPath} | WSL: ${watcherLabel}`;
    inboxStatus.dataset.tone = watcherRunning === true ? "ok" : "warn";
  } catch {
    inboxStatus.textContent = "";
  }
}

async function refreshJobs() {
  const response = await sendMessage({ type: "list-jobs" });
  renderJobs(response.jobs.items || []);
}

document.getElementById("submit-current-tab").addEventListener("click", async () => {
  try {
    setStatus("Submitting current tab...");
    const response = await sendMessage({ type: "submit-current-tab" });
    setStatus(`Queued ${response.job.job_id}`, "success");
    await refreshJobs();
  } catch (error) {
    setStatus(error.message, "error");
  }
});

manualForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setStatus("Submitting URL...");
    const response = await sendMessage({ type: "submit-url", url: manualUrlInput.value.trim() });
    manualUrlInput.value = "";
    setStatus(`Queued ${response.job.job_id}`, "success");
    await refreshJobs();
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.getElementById("refresh-jobs").addEventListener("click", async () => {
  try {
    setStatus("Refreshing jobs...");
    await refreshJobs();
    setStatus("Jobs updated", "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.getElementById("open-options").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

refreshInboxStatus().catch(() => {});
refreshJobs().catch((error) => {
  setStatus(error.message, "error");
});
