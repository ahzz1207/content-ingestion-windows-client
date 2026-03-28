import { JobResultDetail } from "./types";

export function buildNoteBaseName(detail: JobResultDetail): string {
  const datePrefix = buildDatePrefix(detail);
  const rawTitle = detail.title || getSummary(detail)?.headline || detail.job_id || "Untitled";
  return `${datePrefix} ${sanitizeFileComponent(rawTitle)}`.trim();
}

export function buildSourceNote(
  detail: JobResultDetail,
  refs: {
    digestLink: string;
    ingestionDate?: string;
    tags?: string[];
  }
): string {
  const title = detail.title || detail.job_id;
  const metadata = detail.source_metadata || {};
  const lines: string[] = [
    frontmatter({
      type: "source",
      job_id: detail.job_id,
      source_url: detail.source_url || "",
      canonical_url: detail.canonical_url || "",
      platform: detail.platform || "",
      title,
      author: detail.author || "",
      published_at: detail.published_at || "",
      captured_at: getString(metadata.captured_at),
      content_shape: getString(metadata.content_shape),
      ingestion_date: refs.ingestionDate || new Date().toISOString().slice(0, 10),
      tags: refs.tags ?? [],
      status: detail.status,
    }),
    `# ${title}`,
    "",
  ];

  if (detail.source_url) {
    lines.push(`Source URL: [${detail.source_url}](${detail.source_url})`, "");
  }
  if (detail.canonical_url && detail.canonical_url !== detail.source_url) {
    lines.push(`Canonical URL: [${detail.canonical_url}](${detail.canonical_url})`, "");
  }

  lines.push("## Capture Context", "");
  lines.push(`- Platform: ${detail.platform || "unknown"}`);
  lines.push(`- Author: ${detail.author || "unknown"}`);
  lines.push(`- Published At: ${detail.published_at || "unknown"}`);
  lines.push(`- Captured At: ${getString(metadata.captured_at) || "unknown"}`);
  lines.push(`- Content Shape: ${getString(metadata.content_shape) || "unknown"}`);
  lines.push(`- Digest Note: ${refs.digestLink}`);
  lines.push("");
  return lines.join("\n");
}

export function buildDigestNote(
  detail: JobResultDetail,
  refs: {
    sourceLink: string;
    insightCardEmbed?: string | null;
  }
): string {
  const summary = getSummary(detail);
  const structuredResult = asRecord(detail.structured_result);
  const synthesis = asRecord(structuredResult.synthesis);
  const keyPoints = getArray(structuredResult.key_points);
  const verificationItems = getArray(structuredResult.verification_items);
  const lines: string[] = [
    frontmatter({
      type: "digest",
      job_id: detail.job_id,
      source_ref: refs.sourceLink,
      platform: detail.platform || "",
      title: detail.title || detail.job_id,
      author: detail.author || "",
      published_at: detail.published_at || "",
      status: detail.status,
      verification_status: deriveVerificationStatus(verificationItems),
      key_point_count: String(keyPoints.length),
      analysis_model: getString(asRecord(detail.source_metadata || {}).analysis_model),
    }),
    `# ${summary?.headline || detail.title || detail.job_id}`,
    "",
    `Source note: ${refs.sourceLink}`,
    "",
  ];

  if (refs.insightCardEmbed) {
    lines.push("## Visual Summary", "", refs.insightCardEmbed, "");
  }

  pushSection(lines, "Summary", summary?.short_text || detail.title || "");
  pushObjectList(lines, "Key Points", getArray(structuredResult.key_points), "title", "details");
  pushObjectList(lines, "Analysis", getArray(structuredResult.analysis_items), "statement", "why_it_matters", "kind");
  pushVerification(lines, getArray(structuredResult.verification_items));
  pushSection(lines, "Bottom Line", getString(synthesis.final_answer) || getString(asRecord(detail.insight_brief).synthesis_conclusion) || "");
  pushStringList(lines, "Questions & Next Steps", [
    ...getStringArray(synthesis.open_questions),
    ...getStringArray(synthesis.next_steps),
  ]);

  return lines.join("\n").trimEnd() + "\n";
}

function buildDatePrefix(detail: JobResultDetail): string {
  const value =
    detail.published_at ||
    getString((detail.source_metadata || {}).captured_at) ||
    detail.updated_at ||
    new Date().toISOString();
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toISOString().slice(0, 10);
  }
  return new Date().toISOString().slice(0, 10);
}

function frontmatter(values: Record<string, string | string[]>): string {
  const lines = ["---"];
  for (const [key, value] of Object.entries(values)) {
    if (Array.isArray(value)) {
      if (value.length === 0) {
        lines.push(`${key}: []`);
      } else {
        lines.push(`${key}:`);
        for (const item of value) {
          lines.push(`  - ${quoteYaml(item)}`);
        }
      }
    } else {
      lines.push(`${key}: ${quoteYaml(value)}`);
    }
  }
  lines.push("---", "");
  return lines.join("\n");
}

function deriveVerificationStatus(items: unknown[]): string {
  const rows = items.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
  if (!rows.length) {
    return "unavailable";
  }
  const statuses = rows.map((r) => getString(r.status)).filter(Boolean);
  if (!statuses.length) {
    return "unavailable";
  }
  if (statuses.every((s) => s === "supported")) {
    return "supported";
  }
  if (statuses.some((s) => s === "warning")) {
    return "warning";
  }
  return "mixed";
}

function quoteYaml(value: string): string {
  return JSON.stringify(value || "");
}

function sanitizeFileComponent(value: string): string {
  const cleaned = value
    .replace(/[\\/:*?"<>|]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned || "Untitled";
}

function pushSection(lines: string[], heading: string, body: string): void {
  if (!body.trim()) {
    return;
  }
  lines.push(`## ${heading}`, "", body.trim(), "");
}

function pushStringList(lines: string[], heading: string, items: string[]): void {
  const filtered = items.map((item) => item.trim()).filter(Boolean);
  if (!filtered.length) {
    return;
  }
  lines.push(`## ${heading}`, "");
  for (const item of filtered) {
    lines.push(`- ${item}`);
  }
  lines.push("");
}

function pushObjectList(
  lines: string[],
  heading: string,
  items: unknown[],
  primaryKey: string,
  secondaryKey: string,
  tertiaryKey?: string
): void {
  const rows = items.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
  if (!rows.length) {
    return;
  }
  lines.push(`## ${heading}`, "");
  for (const row of rows) {
    const primary = getString(row[primaryKey]);
    const secondary = getString(row[secondaryKey]);
    const tertiary = tertiaryKey ? getString(row[tertiaryKey]) : "";
    const labelParts = [primary, tertiary ? `(${tertiary})` : ""].filter(Boolean);
    if (!labelParts.length && !secondary) {
      continue;
    }
    lines.push(`- ${labelParts.join(" ") || secondary}`);
    if (secondary && secondary !== primary) {
      lines.push(`  ${secondary}`);
    }
  }
  lines.push("");
}

function pushVerification(lines: string[], items: unknown[]): void {
  const rows = items.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
  if (!rows.length) {
    return;
  }
  lines.push("## Verification", "");
  for (const row of rows) {
    const claim = getString(row.claim);
    const status = getString(row.status) || "unknown";
    const rationale = getString(row.rationale);
    if (!claim) {
      continue;
    }
    lines.push(`- [${status}] ${claim}`);
    if (rationale) {
      lines.push(`  ${rationale}`);
    }
  }
  lines.push("");
}

function getSummary(detail: JobResultDetail): { headline?: string; short_text?: string } | null {
  const structuredResult = asRecord(detail.structured_result);
  const summary = asRecord(structuredResult.summary);
  if (!Object.keys(summary).length) {
    return null;
  }
  return {
    headline: getString(summary.headline) || undefined,
    short_text: getString(summary.short_text) || undefined,
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

function getArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function getString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function getStringArray(value: unknown): string[] {
  return getArray(value)
    .map((item) => (typeof item === "string" ? item : ""))
    .filter(Boolean);
}
