import { ApiHealth, DeleteJobResponse, IngestionSettings, JobListResult, JobResultCard, JobResultDetail } from "./types";

export class ApiClient {
  constructor(private readonly getSettings: () => IngestionSettings) {}

  async ingest(url: string): Promise<{ job_id: string; status: string }> {
    return this.request("/ingest", {
      method: "POST",
      body: JSON.stringify({
        url,
        tags: this.defaultTags(),
      }),
    });
  }

  async listJobs(): Promise<JobListResult<JobResultCard>> {
    return this.request("/jobs?status=queued,processing,completed,failed&limit=12&view=result_cards");
  }

  async getJobResult(jobId: string): Promise<JobResultDetail> {
    return this.request(`/jobs/${jobId}/result`);
  }

  async archiveJob(jobId: string): Promise<DeleteJobResponse> {
    return this.request(`/jobs/${jobId}`, { method: "DELETE" });
  }

  async health(): Promise<ApiHealth> {
    return this.request("/health");
  }

  private defaultTags(): string[] {
    const settings = this.getSettings();
    return settings.defaultTags
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const settings = this.getSettings();
    const headers = new Headers(init.headers ?? {});
    headers.set("Accept", "application/json");
    if (settings.apiToken) {
      headers.set("Authorization", `Bearer ${settings.apiToken}`);
    }
    if (init.body) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(`${settings.apiBaseUrl.replace(/\/+$/, "")}${path}`, {
      ...init,
      headers,
    });

    const text = await response.text();
    const data = text ? safeJsonParse(text) : {};
    if (!response.ok) {
      const detail =
        data && typeof data === "object" && typeof (data as { detail?: unknown }).detail === "string"
          ? (data as { detail: string }).detail
          : `${response.status} ${response.statusText}`;
      throw new Error(detail);
    }

    return data as T;
  }
}

function safeJsonParse(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return { raw: value };
  }
}
