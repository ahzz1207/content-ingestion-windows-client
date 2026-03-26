# Chrome Extension MVP

This extension is the first external consumer for the local Content Ingestion HTTP API.

## What it does

- sends the current tab into `POST /api/v1/ingest`
- sends a page or link from the context menu
- lists the most recent jobs from `GET /api/v1/jobs`
- refreshes the browser action badge from `status=queued,processing`
- stores API base URL and token locally

## Load it in Chrome

1. Start the local API server from this repo:

   ```powershell
   pip install -e ".[api]"
   python main.py serve
   ```

2. Open `chrome://extensions`
3. Enable Developer Mode
4. Click `Load unpacked`
5. Select [`H:\demo-win\chrome-extension`](H:\demo-win\chrome-extension)
6. Open the extension options page and paste the API token from `%USERPROFILE%\.content-ingestion\api_token`

## First validation path

1. Open any article page in Chrome
2. Click `Send current tab`
3. Confirm the popup shows a queued job
4. Confirm the badge reflects queued or processing jobs
5. Let the WSL watcher consume the job and verify it moves into `processed/`
