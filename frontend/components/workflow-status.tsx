import { Check, Circle, LoaderCircle, TriangleAlert } from "lucide-react";

const steps = ["Upload", "Rules", "SQL", "Vector", "Ranking", "Approve"];

export function WorkflowStatus({ currentStep, action, state = "running" }: { currentStep: number; action: string; state?: "running" | "success" | "error" }) {
  const safeStep = Math.min(Math.max(currentStep, 1), steps.length);
  const progress = state === "success" ? 100 : Math.round(((safeStep - 1) / (steps.length - 1)) * 100);

  return (
    <section className="rounded-lg border border-line bg-white px-5 py-4 shadow-panel" aria-label="Project workflow">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink" role="status" aria-live="polite">
        {state === "running" ? <LoaderCircle className="h-4 w-4 animate-spin text-primary" aria-hidden /> : null}
        {state === "success" ? <Check className="h-4 w-4 text-emerald-600" aria-hidden /> : null}
        {state === "error" ? <TriangleAlert className="h-4 w-4 text-issue" aria-hidden /> : null}
        {action}
        <span className="ml-auto whitespace-nowrap text-xs font-bold text-slate-500">{progress}% complete</span>
      </div>
      <div className="mb-3 h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label="Project creation progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
        <div className={`h-full rounded-full transition-[width] duration-500 ${state === "error" ? "bg-rose-500" : state === "success" ? "bg-emerald-500" : "bg-primary"}`} style={{ width: `${progress}%` }} />
      </div>
      <ol className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        {steps.map((label, index) => {
          const step = index + 1;
          const complete = step < safeStep || state === "success";
          const active = step === safeStep && state !== "success";
          return (
            <li key={label} className="min-w-0">
              <div className={`mb-2 h-1.5 rounded-full ${complete ? "bg-emerald-500" : active ? "bg-primary" : "bg-slate-200"}`} />
              <div className={`flex items-center gap-1.5 text-xs font-semibold ${active ? "text-primary" : complete ? "text-emerald-700" : "text-slate-400"}`}>
                {complete ? <Check className="h-3.5 w-3.5 shrink-0" aria-hidden /> : <Circle className="h-3.5 w-3.5 shrink-0" aria-hidden />}
                <span className="truncate">{label}</span>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
