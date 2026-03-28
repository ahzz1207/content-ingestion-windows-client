# Chrome Extension MVP

This extension is the first external consumer for the local Content Ingestion HTTP API.

## What it does

- sends the current tab into `POST /api/v1/ingest`
- sends a page or link from the context menu
- lists the most recent jobs from `GET /api/v1/jobs?view=result_cards`
- refreshes the browser action badge from `status=queued,processing`
- renders lightweight result cards for `queued`, `processing`, `completed`, and `failed`
- shows completed-job headline, one-line take, verification signal, warning count, and coverage hint when available
- shows failed-job summary and error context when available
- allows `Open source` and `Copy job id` actions from the popup
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
2. Click `Resubmit current tab`
3. Confirm the popup first shows the job as `queued` or `processing`
4. Confirm the badge reflects queued or processing jobs
5. Let the WSL watcher consume the job and confirm the popup refreshes into a completed or failed result card
6. For a completed job, confirm the popup shows a headline, one-line take, and verification chip
7. Use `Open source` or `Copy job id` to confirm the lightweight actions work

## API assumptions

- the extension expects `GET /api/v1/jobs?view=result_cards`
- the extension still uses lightweight polling only; it does not fetch full result payloads
- the popup is intentionally not a second workspace and does not render long-form structured analysis
