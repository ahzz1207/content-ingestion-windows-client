const form = document.getElementById("settings-form");
const statusMessage = document.getElementById("settings-status");
const apiBaseUrlInput = document.getElementById("api-base-url");
const apiTokenInput = document.getElementById("api-token");

function setStatus(message, tone = "neutral") {
  statusMessage.textContent = message || "";
  statusMessage.dataset.tone = tone;
}

async function sendMessage(message) {
  const response = await chrome.runtime.sendMessage(message);
  if (!response || !response.ok) {
    throw new Error((response && response.error) || "Request failed");
  }
  return response;
}

async function loadSettings() {
  const response = await sendMessage({ type: "get-settings" });
  apiBaseUrlInput.value = response.settings.apiBaseUrl;
  apiTokenInput.value = response.settings.apiToken;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await sendMessage({
      type: "save-settings",
      settings: {
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        apiToken: apiTokenInput.value.trim(),
      },
    });
    setStatus("Settings saved", "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

loadSettings().catch((error) => {
  setStatus(error.message, "error");
});
