# Obsidian Plugin MVP

This plugin is the second entry surface for the local Content Ingestion API.

## Current scope

- command palette action to submit a URL
- right-side status view that lists recent jobs
- settings tab for API base URL and token
- correct Obsidian plugin persistence via whole-object `loadData()` / `saveData()`

## Build

```powershell
cd H:\demo-win\obsidian-plugin
npm install
npm run build
```

Then copy `manifest.json`, `main.js`, and `styles.css` into your Obsidian vault plugin directory.
