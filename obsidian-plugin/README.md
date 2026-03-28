# Obsidian Plugin

This plugin is the second entry surface for the local Content Ingestion API.

## Current scope

- command palette action to submit a URL
- right-side status view that lists recent jobs through `GET /api/v1/jobs?view=result_cards`
- manual import of completed jobs into Source + Digest notes
- settings tab for API base URL, token, and the fixed source/digest output directories
- correct Obsidian plugin persistence via whole-object `loadData()` / `saveData()`

## What the import flow does

For a completed job, the plugin fetches `GET /api/v1/jobs/{job_id}/result` and writes:

- one Source note into `01 Sources/` by default
- one Digest note into `02 Digests/` by default

The importer uses `job_id` as the upsert key:

- if a note for the same `job_id` already exists in the target directory, it is updated
- if a filename collision happens for a different `job_id`, the new file gets ` - {job_id}` appended

Current v1 boundaries:

- no background sync of all completed jobs
- no claim/topic/entity note generation yet
- no attachment mirroring into the vault yet
- no auto-embed into the current editor yet

## Build

```powershell
cd H:\demo-win\obsidian-plugin
npm install
npm run build
```

Then copy `manifest.json`, `main.js`, and `styles.css` into your Obsidian vault plugin directory.

## First validation path

1. Start the local API server from this repo:

   ```powershell
   pip install -e ".[api]"
   python main.py serve
   ```

2. Install the plugin build into your vault and enable it
3. Open the plugin settings and fill in:
   - API base URL
   - API token
   - optional Source notes directory
   - optional Digest notes directory
4. Use `Submit URL to Content Ingestion` to queue a job
5. Click the ribbon icon or run `Open Content Ingestion status view` to open the status panel
6. Wait for a job to reach `completed`
7. Click `Import notes`
8. Confirm the vault now contains:
   - one note under `01 Sources/`
   - one note under `02 Digests/`
   - both notes carrying the same `job_id` in frontmatter
