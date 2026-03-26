import {
  App,
  ItemView,
  Modal,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  WorkspaceLeaf,
} from "obsidian";

const VIEW_TYPE_STATUS = "content-ingestion-status";
const DEFAULT_API_BASE_URL = "http://127.0.0.1:19527/api/v1";

interface IngestionSettings {
  apiBaseUrl: string;
  apiToken: string;
  defaultTags: string;
  autoOpenStatusView: boolean;
}

interface JobRecord {
  job_id: string;
  status: string;
  source_url?: string;
  final_url?: string;
  created_at?: string;
  updated_at?: string;
}

interface JobListResult {
  items: JobRecord[];
  total: number;
}

const DEFAULT_SETTINGS: IngestionSettings = {
  apiBaseUrl: DEFAULT_API_BASE_URL,
  apiToken: "",
  defaultTags: "",
  autoOpenStatusView: true,
};

class ApiClient {
  constructor(private readonly getSettings: () => IngestionSettings) {}

  async ingest(url: string): Promise<JobRecord> {
    return this.request("/ingest", {
      method: "POST",
      body: JSON.stringify({
        url,
        tags: this.defaultTags(),
      }),
    });
  }

  async listJobs(): Promise<JobListResult> {
    return this.request("/jobs?status=queued,processing,completed,failed&limit=12");
  }

  async health(): Promise<{ status: string }> {
    return this.request("/health");
  }

  private defaultTags(): string[] {
    const settings = this.getSettings();
    return settings.defaultTags
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  private async request(path: string, init: RequestInit = {}): Promise<any> {
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

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `${response.status} ${response.statusText}`);
    }

    return response.json();
  }
}

class IngestUrlModal extends Modal {
  private inputEl!: HTMLInputElement;
  private submitButtonEl!: HTMLButtonElement;

  constructor(app: App, private readonly plugin: ContentIngestionPlugin) {
    super(app);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("content-ingestion-modal");
    contentEl.createEl("h2", { text: "Send URL to Content Ingestion" });

    this.inputEl = contentEl.createEl("input", {
      type: "url",
      placeholder: "https://example.com/article",
    });
    this.inputEl.addClass("content-ingestion-input");
    this.inputEl.focus();

    this.submitButtonEl = contentEl.createEl("button", {
      text: "Submit",
    });
    this.submitButtonEl.addClass("mod-cta");
    this.submitButtonEl.onclick = async () => {
      await this.submit();
    };

    this.inputEl.addEventListener("keydown", async (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        await this.submit();
      }
    });
  }

  private async submit(): Promise<void> {
    const url = this.inputEl.value.trim();
    if (!url) {
      new Notice("URL is required");
      return;
    }

    this.submitButtonEl.disabled = true;
    try {
      await this.plugin.submitUrl(url);
      this.close();
    } finally {
      this.submitButtonEl.disabled = false;
    }
  }
}

class StatusView extends ItemView {
  private listEl!: HTMLDivElement;

  constructor(leaf: WorkspaceLeaf, private readonly plugin: ContentIngestionPlugin) {
    super(leaf);
  }

  getViewType(): string {
    return VIEW_TYPE_STATUS;
  }

  getDisplayText(): string {
    return "Content Ingestion";
  }

  async onOpen(): Promise<void> {
    await this.render();
  }

  async refresh(): Promise<void> {
    await this.render();
  }

  private async render(): Promise<void> {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("content-ingestion-view");

    const headerEl = contentEl.createDiv({ cls: "content-ingestion-view__header" });
    headerEl.createEl("h2", { text: "Recent ingestion jobs" });
    const refreshButton = headerEl.createEl("button", { text: "Refresh" });
    refreshButton.onclick = async () => {
      await this.render();
    };

    this.listEl = contentEl.createDiv({ cls: "content-ingestion-view__list" });

    try {
      const health = await this.plugin.apiClient.health();
      contentEl.createDiv({
        cls: "content-ingestion-view__health",
        text: `API: ${health.status}`,
      });
      const jobs = await this.plugin.apiClient.listJobs();
      if (!jobs.items.length) {
        this.listEl.createDiv({
          cls: "content-ingestion-view__empty",
          text: "No jobs yet.",
        });
        return;
      }
      for (const item of jobs.items) {
        const rowEl = this.listEl.createDiv({ cls: "content-ingestion-job" });
        rowEl.createDiv({
          cls: "content-ingestion-job__url",
          text: item.source_url ?? item.final_url ?? item.job_id,
        });
        rowEl.createDiv({
          cls: "content-ingestion-job__meta",
          text: `${item.status} · ${item.created_at ?? item.updated_at ?? item.job_id}`,
        });
      }
    } catch (error) {
      this.listEl.createDiv({
        cls: "content-ingestion-view__empty",
        text: error instanceof Error ? error.message : String(error),
      });
    }
  }
}

class ContentIngestionSettingTab extends PluginSettingTab {
  constructor(app: App, private readonly plugin: ContentIngestionPlugin) {
    super(app, plugin);
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl("h2", { text: "Content Ingestion" });

    new Setting(containerEl)
      .setName("API base URL")
      .setDesc("Local HTTP API base URL")
      .addText((text) =>
        text
          .setPlaceholder(DEFAULT_API_BASE_URL)
          .setValue(this.plugin.settings.apiBaseUrl)
          .onChange(async (value) => {
            this.plugin.settings.apiBaseUrl = value.trim() || DEFAULT_API_BASE_URL;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("API token")
      .setDesc("Bearer token used by the local API server")
      .addText((text) => {
        text.inputEl.type = "password";
        text
          .setPlaceholder("Paste token")
          .setValue(this.plugin.settings.apiToken)
          .onChange(async (value) => {
            this.plugin.settings.apiToken = value.trim();
            await this.plugin.saveSettings();
          });
      });

    new Setting(containerEl)
      .setName("Default tags")
      .setDesc("Comma separated tags for future use")
      .addText((text) =>
        text
          .setPlaceholder("research, article")
          .setValue(this.plugin.settings.defaultTags)
          .onChange(async (value) => {
            this.plugin.settings.defaultTags = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Auto open status view after submit")
      .addToggle((toggle) =>
        toggle.setValue(this.plugin.settings.autoOpenStatusView).onChange(async (value) => {
          this.plugin.settings.autoOpenStatusView = value;
          await this.plugin.saveSettings();
        })
      );
  }
}

export default class ContentIngestionPlugin extends Plugin {
  settings: IngestionSettings = DEFAULT_SETTINGS;
  apiClient: ApiClient = new ApiClient(() => this.settings);

  async onload(): Promise<void> {
    await this.loadSettings();
    this.apiClient = new ApiClient(() => this.settings);

    this.registerView(VIEW_TYPE_STATUS, (leaf) => new StatusView(leaf, this));

    this.addCommand({
      id: "submit-url",
      name: "Submit URL to Content Ingestion",
      callback: () => {
        new IngestUrlModal(this.app, this).open();
      },
    });

    this.addCommand({
      id: "open-status-view",
      name: "Open Content Ingestion status view",
      callback: async () => {
        await this.activateStatusView();
      },
    });

    this.addRibbonIcon("inbox", "Content Ingestion", async () => {
      await this.activateStatusView();
    });

    this.addSettingTab(new ContentIngestionSettingTab(this.app, this));
  }

  async onunload(): Promise<void> {
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_STATUS);
  }

  async submitUrl(url: string): Promise<void> {
    try {
      const job = await this.apiClient.ingest(url);
      new Notice(`Queued ${job.job_id}`);
      if (this.settings.autoOpenStatusView) {
        await this.activateStatusView();
      }
      await this.refreshStatusViews();
    } catch (error) {
      new Notice(error instanceof Error ? error.message : String(error));
    }
  }

  async loadSettings(): Promise<void> {
    const data = await this.loadData();
    this.settings = Object.assign({}, DEFAULT_SETTINGS, data ?? {});
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
    this.apiClient = new ApiClient(() => this.settings);
    await this.refreshStatusViews();
  }

  async activateStatusView(): Promise<void> {
    const leaf = this.app.workspace.getRightLeaf(false);
    if (!leaf) {
      return;
    }
    await leaf.setViewState({
      type: VIEW_TYPE_STATUS,
      active: true,
    });
    this.app.workspace.revealLeaf(leaf);
  }

  async refreshStatusViews(): Promise<void> {
    const leaves = this.app.workspace.getLeavesOfType(VIEW_TYPE_STATUS);
    for (const leaf of leaves) {
      const view = leaf.view;
      if (view instanceof StatusView) {
        await view.refresh();
      }
    }
  }
}
