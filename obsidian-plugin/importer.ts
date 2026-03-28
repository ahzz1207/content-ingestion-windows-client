import { promises as fs } from "fs";

import { App, TFile, normalizePath } from "obsidian";

import { ApiClient } from "./api-client";
import { buildDigestNote, buildNoteBaseName, buildSourceNote } from "./note-builders";
import { IngestionSettings, JobArtifact, JobResultDetail } from "./types";

export async function importCompletedResult(
  app: App,
  apiClient: ApiClient,
  settings: IngestionSettings,
  jobId: string
): Promise<{ sourceFile: TFile; digestFile: TFile }> {
  const detail = await apiClient.getJobResult(jobId);
  if (detail.status !== "completed") {
    throw new Error(`Only completed jobs can be imported. Current status: ${detail.status}`);
  }

  await ensureFolder(app, settings.sourceNotesDir);
  await ensureFolder(app, settings.digestNotesDir);

  const baseName = buildNoteBaseName(detail);
  const sourceTarget = await resolveTargetFile(app, settings.sourceNotesDir, baseName, detail);
  const digestTarget = await resolveTargetFile(app, settings.digestNotesDir, baseName, detail);

  const sourceLink = `[[${sourceTarget.basename}]]`;
  const digestLink = `[[${digestTarget.basename}]]`;
  const insightCardEmbed = await importInsightCard(app, settings.digestNotesDir, detail);

  const ingestionDate = new Date().toISOString().slice(0, 10);
  const tags = settings.defaultTags
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
  const sourceContent = buildSourceNote(detail, { digestLink, ingestionDate, tags });
  const digestContent = buildDigestNote(detail, { sourceLink, insightCardEmbed });

  const sourceFile = await upsertFile(app, sourceTarget.path, sourceContent);
  const digestFile = await upsertFile(app, digestTarget.path, digestContent);
  return { sourceFile, digestFile };
}

async function importInsightCard(
  app: App,
  digestNotesDir: string,
  detail: JobResultDetail
): Promise<string | null> {
  const artifact = findArtifact(detail.available_artifacts || [], "insight_card");
  if (!artifact?.path) {
    return null;
  }

  const sourcePath = artifact.path;
  const bytes = await fs.readFile(sourcePath);
  const assetDir = normalizePath(`${digestNotesDir}/_assets`);
  const extension = inferImageExtension(sourcePath, artifact.media_type);
  const suffix = artifact.kind === "thumbnail" ? "thumbnail" : "insight_card";
  const assetPath = normalizePath(`${assetDir}/${detail.job_id}-${suffix}.${extension}`);
  await ensureFolder(app, assetDir);
  const binary = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  await app.vault.adapter.writeBinary(assetPath, binary);
  return `![[${assetPath}]]`;
}

async function resolveTargetFile(
  app: App,
  rootDir: string,
  baseName: string,
  detail: JobResultDetail
): Promise<{ path: string; basename: string }> {
  const existing = findExistingByJobId(app, rootDir, detail.job_id);
  if (existing) {
    return {
      path: existing.path,
      basename: existing.basename,
    };
  }

  const normalizedDir = normalizePath(rootDir);
  const preferred = normalizePath(`${normalizedDir}/${baseName}.md`);
  const preferredFile = app.vault.getAbstractFileByPath(preferred);
  if (!(preferredFile instanceof TFile)) {
    return {
      path: preferred,
      basename: baseName,
    };
  }

  const preferredJobId = getJobId(app, preferredFile);
  if (preferredJobId === detail.job_id) {
    return {
      path: preferredFile.path,
      basename: preferredFile.basename,
    };
  }

  let suffix = ` - ${detail.job_id}`;
  let candidate = normalizePath(`${normalizedDir}/${baseName}${suffix}.md`);
  let attempt = 2;
  while (true) {
    const file = app.vault.getAbstractFileByPath(candidate);
    if (!(file instanceof TFile)) {
      return {
        path: candidate,
        basename: `${baseName}${suffix}`,
      };
    }
    if (getJobId(app, file) === detail.job_id) {
      return {
        path: file.path,
        basename: file.basename,
      };
    }
    suffix = ` - ${detail.job_id} (${attempt})`;
    candidate = normalizePath(`${normalizedDir}/${baseName}${suffix}.md`);
    attempt += 1;
  }
}

function findExistingByJobId(app: App, rootDir: string, jobId: string): TFile | null {
  const normalizedDir = normalizePath(rootDir);
  for (const file of app.vault.getMarkdownFiles()) {
    if (!file.path.startsWith(`${normalizedDir}/`)) {
      continue;
    }
    if (getJobId(app, file) === jobId) {
      return file;
    }
  }
  return null;
}

function getJobId(app: App, file: TFile): string | null {
  const frontmatter = app.metadataCache.getFileCache(file)?.frontmatter;
  const value = frontmatter?.job_id;
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

async function upsertFile(app: App, path: string, content: string): Promise<TFile> {
  const existing = app.vault.getAbstractFileByPath(path);
  if (existing instanceof TFile) {
    await app.vault.modify(existing, content);
    return existing;
  }
  return app.vault.create(path, content);
}

async function ensureFolder(app: App, folderPath: string): Promise<void> {
  const normalized = normalizePath(folderPath);
  if (!normalized || normalized === ".") {
    return;
  }
  const segments = normalized.split("/");
  let current = "";
  for (const segment of segments) {
    current = current ? `${current}/${segment}` : segment;
    if (app.vault.getAbstractFileByPath(current)) {
      continue;
    }
    await app.vault.createFolder(current);
  }
}

function findArtifact(artifacts: JobArtifact[], kind: string): JobArtifact | null {
  for (const artifact of artifacts) {
    if (artifact.kind === kind) {
      return artifact;
    }
  }
  return null;
}

function inferImageExtension(path: string, mediaType?: string): string {
  const normalized = path.toLowerCase();
  if (normalized.endsWith(".png")) {
    return "png";
  }
  if (normalized.endsWith(".webp")) {
    return "webp";
  }
  if (normalized.endsWith(".jpeg")) {
    return "jpeg";
  }
  if (normalized.endsWith(".jpg")) {
    return "jpg";
  }
  const type = (mediaType || "").toLowerCase();
  if (type === "image/png") {
    return "png";
  }
  if (type === "image/webp") {
    return "webp";
  }
  if (type === "image/jpeg") {
    return "jpg";
  }
  return "png";
}
