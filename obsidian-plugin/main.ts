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

import { ApiClient } from "./api-client";
import { importCompletedResult } from "./importer";
import { DEFAULT_API_BASE_URL, DEFAULT_SETTINGS, IngestionSettings, JobResultCard } from "./types";

const VIEW_TYPE_STATUS = "content-ingestion-status";

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

    const healthEl = contentEl.createDiv({ cls: "content-ingestion-view__health" });
    const listEl = contentEl.createDiv({ cls: "content-ingestion-view__list" });

    try {
      const health = await this.plugin.apiClient.health();
      const watcherRunning = health.watcher?.running;
      const watcherLabel = watcherRunning === true ? "running" : watcherRunning === false ? "stopped" : "unknown";
      const inboxPath = health.shared_inbox_root || "unknown";
      healthEl.setText(`API: ${health.status} | Inbox: ${inboxPath} | WSL watcher: ${watcherLabel}`);

      const jobs = await this.plugin.apiClient.listJobs();
      if (!jobs.items.length) {
        listEl.createDiv({
          cls: "content-ingestion-view__empty",
          text: "No jobs yet.",
        });
        return;
      }

      for (const item of jobs.items) {
        this.renderJobRow(listEl, item);
      }
    } catch (error) {
      listEl.createDiv({
        cls: "content-ingestion-view__empty",
        text: error instanceof Error ? error.message : String(error),
      });
    }
  }

  private renderJobRow(listEl: HTMLDivElement, item: JobResultCard): void {
    const rowEl = listEl.createDiv({
      cls: `content-ingestion-job content-ingestion-job--${item.status}`,
    });

    rowEl.createDiv({
      cls: "content-ingestion-job__title",
      text: item.result_card?.headline || item.title || item.source_url || item.canonical_url || item.job_id,
    });

    rowEl.createDiv({
      cls: "content-ingestion-job__summary",
      text: summarizeJob(item),
    });

    rowEl.createDiv({
      cls: "content-ingestion-job__meta",
      text: [statusLabel(item.status), formatTimestamp(item.updated_at), item.platform].filter(Boolean).join(" | "),
    });

    const chips = rowEl.createDiv({ cls: "content-ingestion-job__chips" });
    if (item.status === "completed") {
      chips.createSpan({
        cls: `content-ingestion-chip content-ingestion-chip--${item.result_card?.verification_signal || "unavailable"}`,
        text: verificationLabel(item.result_card?.verification_signal || "unavailable"),
      });
      if ((item.result_card?.warning_count || 0) > 0) {
        chips.createSpan({
          cls: "content-ingestion-chip content-ingestion-chip--warning",
          text: `${item.result_card?.warning_count} warning${item.result_card?.warning_count === 1 ? "" : "s"}`,
        });
      }
      if (item.result_card?.coverage_warning) {
        chips.createSpan({
          cls: "content-ingestion-chip content-ingestion-chip--caution",
          text: "Coverage limited",
        });
      }
    }

    if (Array.isArray(item.result_card?.quick_takeaways) && item.result_card?.quick_takeaways.length) {
      const takeawayList = rowEl.createEl("ul", { cls: "content-ingestion-job__takeaways" });
      for (const takeaway of item.result_card.quick_takeaways) {
        takeawayList.createEl("li", { text: takeaway });
      }
    }

    const actions = rowEl.createDiv({ cls: "content-ingestion-job__actions" });
    const sourceUrl = item.source_url || item.canonical_url;
    if (sourceUrl) {
      const sourceLink = actions.createEl("a", {
        cls: "mod-button",
        href: sourceUrl,
        text: "Open source",
      });
      sourceLink.target = "_blank";
      sourceLink.rel = "noreferrer";
    }

    const copyButton = actions.createEl("button", {
      cls: "mod-button",
      text: "Copy job id",
    });
    copyButton.onclick = async () => {
      try {
        await navigator.clipboard.writeText(item.job_id);
        new Notice(`Copied ${item.job_id}`);
      } catch (error) {
        new Notice(error instanceof Error ? error.message : String(error));
      }
    };

    const archiveButton = actions.createEl("button", {
      cls: "mod-button",
      text: "Archive",
    });
    archiveButton.onclick = async () => {
      const confirmed = window.confirm(
        `Archive job ${item.job_id}? Pipeline files will be moved to the archived folder. Imported Obsidian notes will stay.`
      );
      if (!confirmed) {
        return;
      }
      archiveButton.disabled = true;
      archiveButton.setText("Archiving...");
      try {
        await this.plugin.archiveJob(item.job_id);
      } finally {
        archiveButton.disabled = false;
        archiveButton.setText("Archive");
      }
    };

    if (item.status === "completed") {
      const importButton = actions.createEl("button", {
        cls: "mod-button mod-cta",
        text: "Import notes",
      });
      importButton.onclick = async () => {
        importButton.disabled = true;
        importButton.setText("Importing...");
        try {
          await this.plugin.importCompletedJob(item.job_id);
        } finally {
          importButton.disabled = false;
          importButton.setText("Import notes");
        }
      };
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
      .setName("Source notes directory")
      .setDesc("Folder for source notes imported from completed jobs")
      .addText((text) =>
        text.setValue(this.plugin.settings.sourceNotesDir).onChange(async (value) => {
          this.plugin.settings.sourceNotesDir = value.trim() || DEFAULT_SETTINGS.sourceNotesDir;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("Digest notes directory")
      .setDesc("Folder for digest notes imported from completed jobs")
      .addText((text) =>
        text.setValue(this.plugin.settings.digestNotesDir).onChange(async (value) => {
          this.plugin.settings.digestNotesDir = value.trim() || DEFAULT_SETTINGS.digestNotesDir;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("Default tags")
      .setDesc("Comma separated tags sent with manual URL submissions")
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

  async importCompletedJob(jobId: string): Promise<void> {
    try {
      const result = await importCompletedResult(this.app, this.apiClient, this.settings, jobId);
      new Notice(`Imported ${result.sourceFile.basename} and ${result.digestFile.basename}`);
    } catch (error) {
      new Notice(error instanceof Error ? error.message : String(error));
    } finally {
      await this.refreshStatusViews();
    }
  }

  async archiveJob(jobId: string): Promise<void> {
    try {
      await this.apiClient.archiveJob(jobId);
      new Notice(`Archived ${jobId}. Imported notes were kept.`);
    } catch (error) {
      new Notice(error instanceof Error ? error.message : String(error));
    } finally {
      await this.refreshStatusViews();
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

function summarizeJob(item: JobResultCard): string {
  if (item.status === "completed") {
    return item.result_card?.one_sentence_take || item.result_card?.conclusion || item.source_url || item.job_id;
  }
  if (item.status === "failed") {
    return item.failure_card?.summary || item.failure_card?.error || "Processing failed.";
  }
  return item.source_url || item.canonical_url || "Waiting for analysis output.";
}

function formatTimestamp(value?: string): string {
  if (!value) {
    return "Unknown time";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function statusLabel(status: string): string {
  return {
    queued: "Queued",
    processing: "Processing",
    completed: "Completed",
    failed: "Failed",
  }[status] || status;
}

function verificationLabel(value: string): string {
  return {
    supported: "Verified",
    mixed: "Mixed",
    warning: "Needs review",
    unclear: "Unclear",
    unavailable: "No verification",
  }[value] || value;
}
