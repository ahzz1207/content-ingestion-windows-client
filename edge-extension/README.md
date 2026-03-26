# Edge Extension MVP

This Edge extension is the same local HTTP API consumer as the Chrome extension, packaged as a separate load target for Microsoft Edge.

## What it does

- sends the current tab into `POST /api/v1/ingest`
- sends a page or link from the context menu
- lists the most recent jobs from `GET /api/v1/jobs`
- refreshes the browser action badge from `status=queued,processing`
- stores API base URL and token locally

## Load it in Edge

1. Start the local API server from this repo:

   ```powershell
   pip install -e ".[api]"
   python main.py serve
   ```

2. Open `edge://extensions`
3. Enable `Developer mode`
4. Click `Load unpacked`
5. Select [`H:\demo-win\edge-extension`](H:/demo-win/edge-extension)
6. Open the extension options page and paste the API token from [`C:\Users\Administrator\.content-ingestion\api_token`](C:/Users/Administrator/.content-ingestion/api_token)

## First validation path

1. Open any article or video page in Edge
2. Click `Send current tab`
3. Confirm the popup shows a queued job
4. Confirm the badge reflects queued or processing jobs
5. Let the WSL watcher consume the job and verify it moves into `processed/`
