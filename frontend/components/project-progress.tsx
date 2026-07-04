import { Check, Circle } from "lucide-react";

type ProjectProgressProps = {
  imported: boolean;
  bomItems: number;
  suggestions: number;
  approvedBomItems: number;
  exports: number;
};

export function ProjectProgress({ imported, bomItems, suggestions, approvedBomItems, exports }: ProjectProgressProps) {
  const approvalComplete = bomItems > 0 && approvedBomItems >= bomItems;
  const steps = [
    { label: "Import data", detail: imported ? "Revit data imported" : "Upload project JSON", complete: imported },
    { label: "Build BOM", detail: bomItems ? `${bomItems} items created` : "Generate paint quantities", complete: bomItems > 0 },
    // { label: "Rules", detail: suggestions ? "Product types decided" : "Decide product type", complete: suggestions > 0 },
    // { label: "SQL + vector", detail: suggestions ? `${suggestions} valid matches` : "Filter and match products", complete: suggestions > 0 },
    { label: "Rank + explain", detail: suggestions ? "Best options explained" : "Score valid options", complete: suggestions > 0 },
    {
      label: "Approve",
      detail: approvedBomItems ? `${approvedBomItems} of ${bomItems} items approved` : "Review suggestions",
      complete: approvalComplete,
    },
    {
      label: "Export",
      detail: !approvalComplete
        ? "Approve all BOM items first"
        : exports
          ? `${exports} ${exports === 1 ? "file" : "files"} created`
          : "Create final file",
      complete: approvalComplete && exports > 0,
    },
  ];
  const completed = steps.filter((step) => step.complete).length;
  const progress = Math.round((completed / steps.length) * 100);
  const activeIndex = steps.findIndex((step) => !step.complete);

  return (
    <section className="border-b border-line bg-white px-5 py-4 lg:px-8" aria-labelledby="project-progress-title">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="project-progress-title" className="text-sm font-bold">Project progress</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {activeIndex === -1 ? "Project workflow complete" : `Next: ${steps[activeIndex].label}`}
          </p>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-primary">{progress}%</div>
          <div className="text-[11px] font-semibold text-slate-500">{completed} of {steps.length} stages complete</div>
        </div>
      </div>

      <div
        className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-200"
        role="progressbar"
        aria-label="Overall project progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress}
        aria-valuetext={`${completed} of ${steps.length} stages complete`}
      >
        <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${progress}%` }} />
      </div>

      <ol className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-7">
        {steps.map((step, index) => {
          const active = index === activeIndex;
          return (
            <li key={step.label} className="min-w-0" aria-current={active ? "step" : undefined}>
              <div className="flex items-center gap-1.5">
                <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full ${
                  step.complete ? "bg-emerald-600 text-white" : active ? "bg-primary text-white" : "bg-slate-200 text-slate-500"
                }`}>
                  {step.complete ? <Check className="h-3.5 w-3.5" aria-hidden /> : <Circle className="h-3 w-3" aria-hidden />}
                </span>
                <span className={`truncate text-xs font-bold ${step.complete ? "text-emerald-700" : active ? "text-primary" : "text-slate-500"}`}>
                  {step.label}
                </span>
              </div>
              <p className="mt-1 truncate pl-6 text-[11px] text-slate-500">{step.detail}</p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}