const jobsList = document.getElementById("jobs-list");
const statusMessage = document.getElementById("status-message");
const manualForm = document.getElementById("manual-form");
const manualUrlInput = document.getElementById("manual-url");

function setStatus(message, tone = "neutral") {
  statusMessage.textContent = message || "";
  statusMessage.dataset.tone = tone;
}

function renderJobs(items) {
  jobsList.innerHTML = "";
  if (!items || items.length === 0) {
    jobsList.innerHTML = '<p class="empty-state">No jobs yet.</p>';
    return;
  }

  for (const item of items) {
    const row = document.createElement("article");
    row.className = "job-row";

    const url = document.createElement("p");
    url.className = "job-url";
    url.textContent = item.source_url || item.final_url || item.job_id;

    const meta = document.createElement("p");
    meta.className = "job-meta";
    meta.textContent = `${item.status} · ${item.created_at || item.updated_at || item.job_id}`;

    row.appendChild(url);
    row.appendChild(meta);
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

refreshJobs().catch((error) => {
  setStatus(error.message, "error");
});
