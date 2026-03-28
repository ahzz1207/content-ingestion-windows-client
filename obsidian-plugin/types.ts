export const DEFAULT_API_BASE_URL = "http://127.0.0.1:19527/api/v1";

export interface IngestionSettings {
  apiBaseUrl: string;
  apiToken: string;
  defaultTags: string;
  autoOpenStatusView: boolean;
  sourceNotesDir: string;
  digestNotesDir: string;
}

export interface JobResultCardPayload {
  headline?: string;
  one_sentence_take?: string;
  quick_takeaways?: string[];
  conclusion?: string;
  verification_signal?: string;
  warning_count?: number;
  coverage_warning?: string | null;
}

export interface JobFailureCardPayload {
  summary?: string;
  error?: string;
}

export interface JobResultCard {
  job_id: string;
  status: string;
  updated_at?: string;
  analysis_state?: string;
  title?: string;
  author?: string;
  published_at?: string;
  platform?: string;
  source_url?: string;
  canonical_url?: string;
  result_card?: JobResultCardPayload;
  failure_card?: JobFailureCardPayload;
}

export interface JobListResult<TItem = JobResultCard> {
  items: TItem[];
  total: number;
  limit?: number;
  statuses?: string[];
}

export interface ApiHealth {
  status: string;
  version?: string;
  shared_inbox_root?: string;
  watcher?: {
    running: boolean;
    pid?: string;
    shared_root?: string;
    log_path?: string;
    started_at?: string;
    error?: string;
  };
}

export interface JobResultDetail {
  job_id: string;
  status: string;
  analysis_state?: string;
  updated_at?: string;
  source_url?: string;
  canonical_url?: string;
  title?: string;
  author?: string;
  published_at?: string;
  platform?: string;
  source_metadata?: Record<string, unknown>;
  normalized_markdown?: string;
  structured_result?: Record<string, unknown>;
  insight_brief?: Record<string, unknown>;
  coverage?: Record<string, unknown> | null;
  warnings?: unknown[];
  available_artifacts?: JobArtifact[];
  error?: string;
}

export interface JobArtifact {
  kind?: string;
  path?: string;
  description?: string;
  media_type?: string;
}

export interface DeleteJobResponse {
  job_id: string;
  archived: boolean;
  previous_status?: string;
}

export const DEFAULT_SETTINGS: IngestionSettings = {
  apiBaseUrl: DEFAULT_API_BASE_URL,
  apiToken: "",
  defaultTags: "",
  autoOpenStatusView: true,
  sourceNotesDir: "01 Sources",
  digestNotesDir: "02 Digests",
};
