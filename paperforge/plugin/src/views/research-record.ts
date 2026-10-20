import { App, Modal } from "obsidian";
import { t } from "../i18n";
import type {
  PaperForgeClient,
  ResearchRecord,
  ResearchSource,
} from "../client/paperforge-client";

export class ResearchRecordCaptureModal extends Modal {
  constructor(
    app: App,
    private client: PaperForgeClient,
    private readonly paper: string,
    private readonly pdfPath: string,
    private saved: () => void
  ) {
    super(app);
  }

  onOpen() {
    const el = this.contentEl;
    el.addClass("paperforge-record-modal");
    el.createEl("h2", { text: t("record_save") });
    el.createEl("p", { text: this.paper });
    const form = el.createEl("form");
    const fields: Record<string, HTMLInputElement | HTMLTextAreaElement> = {};
    for (const name of [
      "excerpt",
      "usage",
      "section",
      "context",
      "note",
      "pdf",
      "page",
      "printed",
    ]) {
      const label = form.createEl("label", { text: t("record_" + name) });
      const input =
        name === "excerpt" ||
        name === "usage" ||
        name === "context" ||
        name === "note"
          ? label.createEl("textarea", {
              attr: { name, "aria-label": t("record_" + name) },
            })
          : label.createEl("input", {
              attr: {
                name,
                "aria-label": t("record_" + name),
                type: name === "page" ? "number" : "text",
              },
            });
      if (name === "excerpt" || name === "usage") input.required = true;
      if (name === "page") {
        input.setAttribute("min", "1");
        input.setAttribute("step", "1");
      }
      fields[name] = input;
    }
    fields.pdf.value = this.pdfPath;
    const label = form.createEl("label", { text: t("record_basis") });
    const basis = label.createEl("select", {
      attr: { name: "basis", "aria-label": t("record_basis") },
    });
    for (const value of ["recorded", "user_confirmed", "exact_text"]) {
      basis.createEl("option", { text: t("record_" + value), value });
    }
    const status = el.createEl("p", {
      attr: { role: "status", "aria-live": "polite" },
    });
    const submit = form.createEl("button", {
      text: t("record_save"),
      attr: { type: "submit" },
    });
    const close = el.createEl("button", {
      text: t("record_cancel"),
      attr: { type: "button" },
    });
    close.onclick = () => this.close();
    form.onsubmit = async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      submit.disabled = true;
      try {
        const source: ResearchSource | undefined = fields.pdf.value.trim()
          ? {
              path: fields.pdf.value.trim(),
              physical_page: Number(fields.page.value),
              printed_page: fields.printed.value,
              basis: basis.value as ResearchSource["basis"],
              anchor: fields.excerpt.value,
            }
          : undefined;
        const values = Object.fromEntries(
          Object.entries(fields).map(([key, value]) => [key, value.value])
        );
        const result = await this.client.saveReadingRecord(
          this.paper,
          values,
          source
        );
        status.setText(
          `${t("record_saved")}: ${result.id} — ${t("record_" + result.provenance.status)}`
        );
        // Keep durable identity visible, and prevent accidental duplicate submits.
        for (const field of Object.values(fields)) field.disabled = true;
        basis.disabled = true;
        this.saved();
      } catch (error) {
        status.setText(
          `${t("record_failed")}: ${error instanceof Error ? error.message : String(error)}`
        );
        submit.disabled = false;
      }
    };
    fields.excerpt.focus();
  }
}

export class ResearchRecordModal extends Modal {
  constructor(
    app: App,
    private client: PaperForgeClient,
    private record: ResearchRecord,
    private openParent: (key: string) => void,
    private changed: () => void
  ) {
    super(app);
  }

  onOpen() {
    const el = this.contentEl;
    el.empty();
    el.addClass("paperforge-record-modal");
    const record = this.record;
    el.createEl("h2", { text: record.id });
    el.createEl("p", {
      text: `${record.paper_id} — ${t("record_" + record.record_status)}`,
    });
    for (const field of [
      "excerpt",
      "usage",
      "context",
      "section",
      "note",
    ] as const) {
      el.createEl("h3", { text: t("record_" + field) });
      el.createEl("p", { text: record[field] });
    }
    el.createEl("p", { text: t("record_" + record.provenance.status) });
    if (record.source) {
      el.createEl("p", {
        text: `${record.source.path} — ${t("record_page")}: ${record.source.physical_page}; ${t("record_printed")}: ${record.source.printed_page || "—"}`,
      });
    }
    const details = el.createEl("details");
    details.createEl("summary", { text: t("record_details") });
    details.createEl("pre", {
      text: JSON.stringify(
        {
          legacy_verified: record.verified,
          source: record.source,
          current_provenance: record.provenance,
          corrections: record.corrections,
        },
        null,
        2
      ),
    });
    for (const correction of record.corrections) {
      el.createEl("p", {
        text: `${correction.id}: ${correction.correction} — ${correction.reason}`,
      });
    }
    const status = el.createEl("p", {
      attr: { role: "status", "aria-live": "polite" },
    });
    const parent = el.createEl("button", { text: t("record_parent") });
    parent.onclick = () => {
      this.openParent(record.paper_id);
      this.close();
    };
    const source = el.createEl("button", { text: t("record_open_source") });
    source.onclick = async () => {
      source.disabled = true;
      try {
        const checked = await this.client.readingRecordSource(record);
        // The backend checks canonical paper, vault containment, current hash and physical bounds.
        await this.app.workspace.openLinkText(
          `${checked.path}#page=${checked.physical_page}`,
          "",
          true
        );
        status.setText(t("record_" + checked.provenance.status));
      } catch (error) {
        status.setText(
          `${t("record_failed")}: ${error instanceof Error ? error.message : String(error)}`
        );
      } finally {
        source.disabled = false;
      }
    };
    const form = el.createEl("form");
    const correctionLabel = form.createEl("label", {
      text: t("record_correction"),
    });
    const correction = correctionLabel.createEl("textarea", {
      attr: {
        name: "correction",
        required: "",
        "aria-label": t("record_correction"),
      },
    });
    const reasonLabel = form.createEl("label", { text: t("record_reason") });
    const reason = reasonLabel.createEl("input", {
      attr: { name: "reason", "aria-label": t("record_reason") },
    });
    const submit = form.createEl("button", {
      text: t("record_append_correction"),
      attr: { type: "submit" },
    });
    form.onsubmit = async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      submit.disabled = true;
      try {
        const saved = await this.client.correctReadingRecord(
          record,
          correction.value,
          reason.value
        );
        record.record_status = "corrected";
        record.corrections.push({
          id: saved.jsonl_id,
          correction: correction.value,
          reason: reason.value,
        });
        this.changed();
        this.onOpen();
      } catch (error) {
        status.setText(
          `${t("record_failed")}: ${error instanceof Error ? error.message : String(error)}`
        );
        submit.disabled = false;
      }
    };
  }
}
