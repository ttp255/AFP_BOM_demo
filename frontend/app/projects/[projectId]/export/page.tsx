"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  DollarSign,
  Download,
  FileDown,
  FileSpreadsheet,
  FileText,
  PackageCheck,
  ShieldCheck,
  Sparkles,
  Upload,
  type LucideIcon,
} from "lucide-react";

import { Badge, Button, PageHeader, Panel } from "@/components/chrome";
import { ProjectTabs, refreshProjectProgress } from "@/components/project-tabs";
import { api, errorMessage, type Project } from "@/lib/api";

type ExportFormat = "excel" | "pdf" | "json";
type ExportScope = "approved_only" | "all_items";

type MetricCard = {
  label: string;
  value: string | number;
  detail: string;
  Icon: LucideIcon;
  tone: "success" | "warning" | "issue" | "primary";
};

const workflow = [
  { label: "Import Data", detail: "Upload Revit files", Icon: Download },
  { label: "Review Rooms", detail: "Verify spaces and areas", Icon: CheckCircle2 },
  { label: "Generate BOM", detail: "Create paint takeoff", Icon: FileText },
  { label: "Suggest Products", detail: "Map to catalog", Icon: PackageCheck },
  { label: "Approve", detail: "Review and confirm", Icon: ShieldCheck },
  { label: "Export", detail: "BOM and reports", Icon: FileDown },
];

const currency = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

function formatMoney(value: unknown, unit = "VND") {
  const amount = Number(value || 0);
  return amount ? `${currency.format(amount)} ${unit}` : "-";
}

function productName(suggestion: any) {
  return suggestion.product?.product_name || (suggestion.product_id ? `Product #${suggestion.product_id}` : "-");
}

function supplierName(suggestion: any) {
  return suggestion.supplier?.supplier_name || (suggestion.supplier_id ? `Supplier #${suggestion.supplier_id}` : "-");
}

function formatDate(value: unknown) {
  if (!value) return "Not exported yet";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function statusTone(status: string | undefined) {
  return status === "approved" || status === "created" || status === "completed" ? "success" : "warning";
}

export default function ExportPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId: projectIdParam } = use(params);
  const projectId = projectIdParam;
  const [project, setProject] = useState<Project | null>(null);
  const [bom, setBom] = useState<any[]>([]);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [exports, setExports] = useState<any[]>([]);
  const [scope, setScope] = useState<ExportScope>("approved_only");
  const [format, setFormat] = useState<ExportFormat>("excel");
  const [busy, setBusy] = useState(false);
  const [exportError, setExportError] = useState("");
  const [exportSuccess, setExportSuccess] = useState("");

  const load = useCallback(async () => {
    const [projectData, bomData, suggestionData, exportData] = await Promise.all([
      api.getProject(projectId).catch(() => null),
      api.getBom(projectId).catch(() => []),
      api.getSuggestions(projectId).catch(() => []),
      api.getExports(projectId).catch(() => []),
    ]);
    setProject(projectData);
    setBom(bomData);
    setSuggestions(suggestionData);
    setExports(exportData.filter((item) => String(item.project_id) === String(projectId)));
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  async function runExport() {
    setBusy(true);
    setExportError("");
    setExportSuccess("");
    try {
      await api.exportProject(projectId, format, scope);
      await load();
      refreshProjectProgress();
      setExportSuccess(format.toUpperCase() + " BOM export created successfully.");
    } catch (error) {
      setExportError(errorMessage(error, "Unable to export the BOM. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  const summary = useMemo(() => {
    const approved = suggestions.filter((item) => item.suggestion_status === "approved");
    const needReview = bom.filter((item) => item.suggestion_status !== "approved").length + suggestions.filter((item) => item.suggestion_status !== "approved").length;
    const missingPrice = suggestions.filter((item) => !Number(item.estimated_total_cost)).length;
    const missingSupplier = suggestions.filter((item) => !item.supplier_id).length;
    const totalApprovedCost = approved.reduce((sum, item) => sum + Number(item.estimated_total_cost || 0), 0);

    return { approved, needReview, missingPrice, missingSupplier, totalApprovedCost };
  }, [bom, suggestions]);

  const metrics: MetricCard[] = [
    { label: "Approved Items", value: summary.approved.length, detail: `${bom.length} BOM items`, Icon: ShieldCheck, tone: "success" },
    { label: "Need Review", value: summary.needReview, detail: "Pending approval", Icon: AlertTriangle, tone: "warning" },
    { label: "Missing Price", value: summary.missingPrice, detail: "Exported blank", Icon: DollarSign, tone: "issue" },
    { label: "Exported File", value: exports.length ? 1 : 0, detail: "Latest file for project", Icon: FileDown, tone: "primary" },
  ];

  const previewRows = summary.approved.slice(0, 5).map((suggestion) => {
    const item = bom.find((row) => row.id === suggestion.bom_item_id) || {};
    return { suggestion, item };
  });
  const latestExport = [...exports].sort(
    (left, right) => new Date(right.exported_at || 0).getTime() - new Date(left.exported_at || 0).getTime(),
  )[0];

  return (
    <>
      <PageHeader
        title="Export BOM"
        eyebrow="Exports > Export BOM"
        subtitle="Review and export the approved paint Bill of Materials."
      />
      <ProjectTabs projectId={projectIdParam} />
      <div className="grid gap-5 p-5 xl:grid-cols-[1fr_360px] lg:p-8">
        <div className="grid min-w-0 gap-5">
          <div className="flex flex-wrap items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-lg bg-blue-100 text-primary">
              <FileSpreadsheet className="h-6 w-6" aria-hidden />
            </div>
            <div>
              <div className="text-lg font-bold text-ink">{project?.project_name || "Project"}</div>
              <div className="text-sm text-slate-500">{project?.project_code || `Project ${projectId}`} {project?.location ? `- ${project.location}` : ""}</div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {metrics.map(({ label, value, detail, Icon, tone }) => (
              <Panel key={label}>
                <div className="flex items-center gap-4 p-5">
                  <div className={`grid h-14 w-14 shrink-0 place-items-center rounded-full ${tone === "success" ? "bg-emerald-100 text-emerald-600" : tone === "warning" ? "bg-amber-100 text-amber-600" : tone === "issue" ? "bg-rose-100 text-rose-600" : "bg-blue-100 text-primary"}`}>
                    <Icon className="h-7 w-7" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-slate-600">{label}</div>
                    <div className="mt-1 text-3xl font-bold text-ink">{value}</div>
                    <div className="mt-1 text-xs text-slate-500">{detail}</div>
                  </div>
                </div>
              </Panel>
            ))}
          </div>

          <Panel>
            <div className="p-5">
              <h2 className="text-base font-bold">Export Workflow Progress</h2>
              <div className="mt-5 grid gap-3 md:grid-cols-6">
                {workflow.map(({ label, detail, Icon }, index) => {
                  const active = index <= 5 && (index < 2 || bom.length || suggestions.length || exports.length);
                  return (
                    <div key={label} className="relative grid gap-3 text-center">
                      <div className={`mx-auto grid h-14 w-14 place-items-center rounded-full border ${active ? "border-primary bg-blue-50 text-primary" : "border-line bg-white text-slate-400"}`}>
                        <Icon className="h-6 w-6" aria-hidden />
                      </div>
                      <div>
                        <div className="mx-auto mb-1 grid h-5 w-5 place-items-center rounded-full bg-slate-600 text-xs font-bold text-white">{index + 1}</div>
                        <div className="text-sm font-bold text-ink">{label}</div>
                        <div className="text-xs text-slate-500">{detail}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </Panel>

          <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
            <Panel>
              <div className="border-b border-line p-5">
                <h2 className="text-base font-bold">Export Checklist</h2>
              </div>
              <div className="grid gap-1 p-4">
                <ChecklistRow ok label={`${summary.approved.length} items approved`} detail="Approved suggestions are ready for export" />
                <ChecklistRow ok={summary.needReview === 0} label={`${summary.needReview} items need review`} detail="Review recommended before exporting all" />
                <ChecklistRow ok={summary.missingPrice === 0} label={`${summary.missingPrice} products missing price`} detail="These items export with blank cost" />
                <ChecklistRow ok={summary.missingSupplier === 0} label={`${summary.missingSupplier} suppliers missing`} detail="Supplier assignment affects ordering" />
                <div className="mt-3 flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-700">
                  <CheckCircle2 className="h-5 w-5" aria-hidden />
                  <div>
                    <div className="text-sm font-bold">Ready to export</div>
                    <div className="text-xs">{formatMoney(summary.totalApprovedCost)} approved value</div>
                  </div>
                </div>
              </div>
            </Panel>

            <Panel>
              <div className="border-b border-line p-5">
                <h2 className="text-base font-bold">Export Options</h2>
              </div>
              <div className="grid gap-4 p-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <OptionCard selected={scope === "approved_only"} onClick={() => setScope("approved_only")} title="Export Approved Items Only" detail="Use approved product matches" Icon={PackageCheck} />
                  <OptionCard selected={scope === "all_items"} onClick={() => setScope("all_items")} title="Export All Items" detail="Include rending BOM rows" Icon={Sparkles} />
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <FormatButton selected={format === "excel"} onClick={() => setFormat("excel")} label="Excel" Icon={FileSpreadsheet} />
                  <FormatButton selected={format === "pdf"} onClick={() => setFormat("pdf")} label="PDF" Icon={FileText} />
                  <FormatButton selected={format === "json"} onClick={() => setFormat("json")} label="JSON" Icon={FileDown} />
                </div>
                <Button className="w-full" disabled={busy || (scope === "approved_only" && summary.approved.length === 0)} onClick={runExport}>
                  <Download className="h-4 w-4" aria-hidden />
                  {busy ? "Exporting..." : `Export ${scope === "approved_only" ? "Approved Items Only" : "All Items"}`}
                </Button>
                {exportError ? (
                  <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                    <span>{exportError}</span>
                  </div>
                ) : null}
                {exportSuccess ? (
                  <div role="status" className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                    <span>{exportSuccess}</span>
                  </div>
                ) : null}
              </div>
            </Panel>
          </div>

          <Panel>
            <div className="border-b border-line p-5">
              <h2 className="text-base font-bold">Approved BOM Preview <span className="font-normal text-slate-500">({summary.approved.length} items)</span></h2>
            </div>
            <div className="overflow-x-auto">
              <table className="table-grid">
                <thead><tr><th>BOM</th><th>Material</th><th>Product</th><th>Order Qty</th><th>Supplier</th><th>Unit Price</th><th>Total Price</th></tr></thead>
                <tbody>
                  {previewRows.map(({ suggestion, item }) => (
                    <tr key={suggestion.id}>
                      <td>{item.bom_code || suggestion.bom_item_id}</td>
                      <td>{item.material_name || item.item_name || "Paint"}</td>
                      <td>{productName(suggestion)}</td>
                      <td>{suggestion.estimated_required_package_qty || item.quantity || "-"}</td>
                      <td>{supplierName(suggestion)}</td>
                      <td>{formatMoney(suggestion.offer?.unit_price, suggestion.currency)}</td>
                      <td>{formatMoney(suggestion.estimated_total_cost, suggestion.currency)}</td>
                    </tr>
                  ))}
                  {!previewRows.length ? <tr><td colSpan={7} className="text-slate-500">Approve product suggestions before exporting approved-only BOM data.</td></tr> : null}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        <aside className="grid content-start gap-5">
          <Panel>
            <div className="border-b border-line p-5">
              <h2 className="text-base font-bold">Latest Export</h2>
            </div>
            <div className="grid gap-1 p-4">
              {latestExport ? (
                <div className="flex items-center gap-3 rounded-lg p-3 hover:bg-mist">
                  <FileSpreadsheet className="h-7 w-7 shrink-0 text-emerald-600" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-bold">{latestExport.file_name || latestExport.export_code}</div>
                    <div className="text-xs text-slate-500">{formatDate(latestExport.exported_at)}</div>
                  </div>
                  <Badge tone={statusTone(latestExport.export_status)}>{latestExport.export_status}</Badge>
                </div>
              ) : (
                <div className="p-3 text-sm text-slate-500">No exports created yet.</div>
              )}
            </div>
          </Panel>

          <Panel>
            <div className="flex items-center justify-between border-b border-line p-5">
              <h2 className="text-base font-bold">Missing Data</h2>
              <span className="text-sm font-semibold text-primary">View all</span>
            </div>
            <div className="grid gap-1 p-4">
              <MissingDataRow value={summary.missingPrice} label="items missing price" detail="May export blank cost" />
              <MissingDataRow value={summary.missingSupplier} label="items missing supplier" detail="Needs supplier assignment" />
              <MissingDataRow value={summary.needReview} label="items need approval" detail="May affect export scope" />
              <div className="mt-3 flex items-center justify-center gap-2 border-t border-line pt-4 text-sm font-bold text-primary">
                Go to Need Review <ChevronRight className="h-4 w-4" aria-hidden />
              </div>
            </div>
          </Panel>
        </aside>
      </div>
    </>
  );
}

function ChecklistRow({ ok, label, detail }: { ok: boolean; label: string; detail: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg p-3">
      {ok ? <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden /> : <AlertTriangle className="h-5 w-5 text-amber-500" aria-hidden />}
      <div className="min-w-0 flex-1">
        <div className="text-sm font-bold text-ink">{label}</div>
        <div className="text-xs text-slate-500">{detail}</div>
      </div>
      {ok ? <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden /> : <AlertTriangle className="h-5 w-5 text-amber-500" aria-hidden />}
    </div>
  );
}

function OptionCard({ selected, onClick, title, detail, Icon }: { selected: boolean; onClick: () => void; title: string; detail: string; Icon: LucideIcon }) {
  return (
    <button onClick={onClick} className={`min-h-28 rounded-lg border p-4 text-left ${selected ? "border-primary bg-blue-50" : "border-line bg-white hover:bg-mist"}`}>
      <div className="flex items-start gap-3">
        <span className={`mt-1 h-4 w-4 rounded-full border ${selected ? "border-primary bg-primary shadow-[inset_0_0_0_4px_white]" : "border-slate-300"}`} />
        <div>
          <div className="font-bold text-ink">{title}</div>
          <div className="mt-1 text-xs text-slate-500">{detail}</div>
          <Icon className="mt-4 h-6 w-6 text-primary" aria-hidden />
        </div>
      </div>
    </button>
  );
}

function FormatButton({ selected, onClick, label, Icon }: { selected: boolean; onClick: () => void; label: string; Icon: LucideIcon }) {
  return (
    <button onClick={onClick} className={`flex min-h-16 items-center gap-3 rounded-lg border px-4 text-left ${selected ? "border-primary bg-blue-50" : "border-line bg-white hover:bg-mist"}`}>
      <Icon className={label === "PDF" ? "h-6 w-6 text-rose-500" : "h-6 w-6 text-emerald-600"} aria-hidden />
      <span className="text-sm font-bold">Download {label}</span>
    </button>
  );
}

function MissingDataRow({ value, label, detail }: { value: number; label: string; detail: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg p-3">
      <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-rose-100 text-rose-600">
        <DollarSign className="h-5 w-5" aria-hidden />
      </div>
      <div>
        <div className="text-sm font-bold">{value} {label}</div>
        <div className="text-xs text-slate-500">{detail}</div>
      </div>
    </div>
  );
}
