import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileDown,
  FolderKanban,
  PackageCheck,
  Plus,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import { Badge, PageHeader, Panel } from "@/components/chrome";
import { api, type Project, type ProductSuggestion } from "@/lib/api";

type ProjectOverview = {
  project: Project;
  bom: Array<Record<string, unknown>>;
  suggestions: ProductSuggestion[];
  exports: Array<Record<string, unknown>>;
  approvedItems: number;
};

type WorkflowState = {
  label: string;
  detail: string;
  href: string;
  tone: "neutral" | "success" | "warning" | "issue";
  progress: number;
};

function workflowState({ project, bom, suggestions, exports, approvedItems }: ProjectOverview): WorkflowState {
  const base = `/projects/${project.id}`;
  if (!bom.length) {
    return { label: "BOM pending", detail: "Generate the bill of materials", href: `${base}/bom`, tone: "warning", progress: 20 };
  }
  if (!suggestions.length) {
    return { label: "Products pending", detail: "Generate product matches", href: `${base}/suggestions`, tone: "warning", progress: 45 };
  }
  if (approvedItems < bom.length) {
    return {
      label: "Review products",
      detail: `${approvedItems} of ${bom.length} BOM items approved`,
      href: `${base}/suggestions`,
      tone: "issue",
      progress: 70,
    };
  }
  if (!exports.length) {
    return { label: "Ready to export", detail: "All products are approved", href: `${base}/export`, tone: "success", progress: 90 };
  }
  return { label: "Exported", detail: `${exports.length} export${exports.length === 1 ? "" : "s"} created`, href: `${base}/export`, tone: "success", progress: 100 };
}

export default async function DashboardPage() {
  const projects = await api.getProjects().catch(() => []);
  const overview: ProjectOverview[] = await Promise.all(
    projects.map(async (project) => {
      const [bom, suggestions, exports] = await Promise.all([
        api.getBom(project.id).catch(() => []),
        api.getSuggestions(project.id).catch(() => []),
        api.getExports(project.id).catch(() => []),
      ]);
      const approvedItems = new Set(
        suggestions
          .filter((suggestion) => suggestion.suggestion_status === "approved")
          .map((suggestion) => String(suggestion.bom_item_id)),
      ).size;
      return { project, bom, suggestions, exports, approvedItems };
    }),
  );

  const pendingBom = overview.filter(({ bom }) => !bom.length).length;
  const needReview = overview.filter(({ bom, suggestions, approvedItems }) =>
    bom.length > 0 && suggestions.length > 0 && approvedItems < bom.length
  ).length;
  const exportCount = overview.reduce((total, item) => total + item.exports.length, 0);
  const readyToExport = overview.filter(({ bom, approvedItems, exports }) =>
    bom.length > 0 && approvedItems === bom.length && !exports.length
  ).length;

  const cards: Array<{
    label: string;
    value: number;
    detail: string;
    Icon: LucideIcon;
    iconClass: string;
    iconBg: string;
  }> = [
    { label: "Total projects", value: projects.length, detail: "Active Revit jobs", Icon: FolderKanban, iconClass: "text-blue-600", iconBg: "bg-blue-50" },
    { label: "Pending BOM", value: pendingBom, detail: pendingBom ? "Projects need a BOM" : "All BOMs generated", Icon: AlertTriangle, iconClass: "text-amber-600", iconBg: "bg-amber-50" },
    { label: "Need product review", value: needReview, detail: needReview ? "Approval is required" : "No reviews waiting", Icon: PackageCheck, iconClass: "text-violet-600", iconBg: "bg-violet-50" },
    { label: "Exports created", value: exportCount, detail: readyToExport ? `${readyToExport} ready to export` : "Across all projects", Icon: FileDown, iconClass: "text-emerald-600", iconBg: "bg-emerald-50" },
  ];

  const actionItems = overview
    .map((item) => ({ ...item, state: workflowState(item) }))
    .filter(({ state }) => state.progress < 100)
    .sort((a, b) => a.state.progress - b.state.progress)
    .slice(0, 4);

  return (
    <>
      <PageHeader
        title="Dashboard"
        eyebrow="Workflow control"
        subtitle="Track every Revit project from import through product approval and export."
        actions={(
          <Link href="/projects/new" className="inline-flex min-h-10 items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" aria-hidden /> New project
          </Link>
        )}
      />
      <div className="grid gap-6 p-5 lg:p-8">
        <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-600 p-6 text-white shadow-[0_18px_40px_rgba(37,99,235,0.18)] lg:p-8">
          <div className="relative z-[1] max-w-2xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold uppercase tracking-wide">
              <Sparkles className="h-3.5 w-3.5" aria-hidden /> AFP workspace
            </div>
            <h2 className="text-2xl font-bold sm:text-3xl">Keep the BOM workflow moving</h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-blue-100">
              {actionItems.length
                ? `${actionItems.length} project${actionItems.length === 1 ? " needs" : "s need"} your attention. Open the next task and continue where you left off.`
                : "Everything is up to date. Start a new project whenever you are ready."}
            </p>
          </div>
          <div className="absolute -right-12 -top-20 h-64 w-64 rounded-full bg-white/10" />
          <div className="absolute -bottom-24 right-28 h-52 w-52 rounded-full bg-indigo-300/10" />
        </section>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {cards.map(({ label, value, detail, Icon, iconClass, iconBg }) => (
            <Panel key={label}>
              <div className="flex items-start justify-between gap-4 p-5">
                <div>
                  <div className="text-sm font-medium text-slate-500">{label}</div>
                  <div className="mt-2 text-3xl font-bold text-slate-950">{value}</div>
                  <div className="mt-1 text-xs text-slate-500">{detail}</div>
                </div>
                <div className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl ${iconBg}`}>
                  <Icon className={`h-5 w-5 ${iconClass}`} aria-hidden />
                </div>
              </div>
            </Panel>
          ))}
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,0.8fr)]">
          <Panel>
            <div className="flex items-center justify-between border-b border-line p-5">
              <div>
                <h2 className="text-base font-bold">Recent projects</h2>
                <p className="mt-1 text-xs text-slate-500">Live status across the complete BOM workflow</p>
              </div>
              <Link href="/projects" className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:text-blue-700">
                View all <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </div>
            <div className="overflow-x-auto">
              <table className="table-grid">
                <thead><tr><th>Project</th><th>Workflow</th><th>Progress</th><th><span className="sr-only">Open</span></th></tr></thead>
                <tbody>
                  {overview.slice(0, 6).map((item) => {
                    const state = workflowState(item);
                    return (
                      <tr key={item.project.id}>
                        <td>
                          <Link className="font-semibold text-slate-900 hover:text-primary" href={`/projects/${item.project.id}`}>
                            {item.project.project_name}
                          </Link>
                          <div className="mt-1 text-xs text-slate-500">{item.project.project_code} · {item.project.location || "No location"}</div>
                        </td>
                        <td><Badge tone={state.tone}>{state.label}</Badge><div className="mt-1.5 text-xs text-slate-500">{state.detail}</div></td>
                        <td className="min-w-40">
                          <div className="mb-1 flex justify-between text-xs text-slate-500"><span>Completion</span><span>{state.progress}%</span></div>
                          <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-primary" style={{ width: `${state.progress}%` }} /></div>
                        </td>
                        <td className="text-right"><Link href={state.href} className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-line text-slate-600 hover:border-blue-200 hover:bg-blue-50 hover:text-primary" aria-label={`Open ${item.project.project_name}`}><ArrowRight className="h-4 w-4" /></Link></td>
                      </tr>
                    );
                  })}
                  {!overview.length ? <tr><td colSpan={4} className="py-10 text-center text-slate-500">No projects yet. Create a project to begin.</td></tr> : null}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel>
            <div className="border-b border-line p-5">
              <h2 className="text-base font-bold">Next actions</h2>
              <p className="mt-1 text-xs text-slate-500">Projects that need attention first</p>
            </div>
            <div className="divide-y divide-line">
              {actionItems.map(({ project, state }) => (
                <Link key={project.id} href={state.href} className="group flex items-center gap-3 p-4 hover:bg-blue-50/60">
                  <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-100 text-sm font-bold text-slate-700 group-hover:bg-blue-100 group-hover:text-primary">
                    {project.project_name.slice(0, 1).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-semibold text-slate-900">{project.project_name}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">{state.detail}</div>
                  </div>
                  <ArrowRight className="h-4 w-4 shrink-0 text-slate-400 group-hover:text-primary" aria-hidden />
                </Link>
              ))}
              {!actionItems.length ? (
                <div className="p-8 text-center">
                  <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-emerald-50"><CheckCircle2 className="h-6 w-6 text-emerald-600" /></div>
                  <div className="mt-3 text-sm font-semibold">You are all caught up</div>
                  <div className="mt-1 text-xs text-slate-500">There are no pending workflow tasks.</div>
                </div>
              ) : null}
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}