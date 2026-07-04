"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FlaskConical, Upload } from "lucide-react";

import { Button, PageHeader, Panel } from "@/components/chrome";
import { ProjectTabs, refreshProjectProgress } from "@/components/project-tabs";
import { WorkflowStatus } from "@/components/workflow-status";
import { api, errorMessage, type ImportResult } from "@/lib/api";

const IS_DEV = process.env.NODE_ENV === "development";

export default function ImportPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = use(params);
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [step, setStep] = useState(1);
  const [action, setAction] = useState("Ready to upload project JSON");

  useEffect(() => {
    if (!busy) return;
    const bomTimer = window.setTimeout(() => {
      setStep(3);
      setAction("Building paint BOM…");
    }, 700);
    const suggestionTimer = window.setTimeout(() => {
      setStep(4);
      setAction("Matching and ranking products…");
    }, 1600);
    return () => {
      window.clearTimeout(bomTimer);
      window.clearTimeout(suggestionTimer);
    };
  }, [busy]);

  // Show the generated product suggestions as soon as the import succeeds.
  useEffect(() => {
    if (!result) return;
    router.replace(`/projects/${projectId}/suggestions`);
  }, [result, projectId, router]);

  async function upload() {
    if (!file) return;
    setError("");
    setResult(null);
    setStep(2);
    setAction("Uploading project JSON…");
    setBusy(true);
    try {
      const importResult = await api.uploadRevitJson(file, projectId);
      setResult(importResult);
      setStep(5);
      setAction(
        importResult.suggestions_generated > 0
          ? `${importResult.suggestions_generated} product suggestions ready`
          : "Import complete; product suggestions need attention",
      );
      refreshProjectProgress();
    } catch (uploadError) {
      const message = errorMessage(uploadError, "The file could not be imported.");
      setError(message);
      setAction(message);
    } finally {
      setBusy(false);
    }
  }

  /** DEV-ONLY: simulate a successful import to test status bar → success → forward */
  function simulateSuccess() {
    setError("");
    setBusy(false);
    setStep(5);
    setAction("[TEST] 12 product suggestions ready");
    setResult({
      project_id: projectId,
      project_code: "TEST",
      status: "completed",
      rooms_imported: 0,
      surfaces_imported: 0,
      bom_items_generated: 8,
      suggestions_generated: 12,
      warnings: [],
    });
  }

  return (
    <>
      <PageHeader title="Import Revit JSON" eyebrow="Project data intake" />
      <ProjectTabs projectId={projectId} />
      <div className="grid gap-5 p-5 lg:p-8">
        {(busy || error || result) ? (
          <div>
            <WorkflowStatus
              currentStep={step}
              action={action}
              state={error ? "error" : result ? "success" : "running"}
            />
          </div>
        ) : null}
        <Panel>
          <div className="grid gap-4 p-5">
            <input className="w-full rounded-md border border-line bg-white p-3" type="file" accept="application/json,.json" onChange={(event) => setFile(event.target.files?.[0] || null)} />
            <div className="flex flex-wrap gap-2">
              <Button disabled={!file || busy} onClick={upload}>
                <Upload className="h-4 w-4" /> {busy ? "Importing" : "Upload JSON"}
              </Button>
              {IS_DEV ? (
                <Button
                  id="dom-test-simulate-success"
                  variant="secondary"
                  onClick={simulateSuccess}
                  title="DOM test: simulate success state and auto-forward to suggestions"
                >
                  <FlaskConical className="h-4 w-4" /> Test Success
                </Button>
              ) : null}
            </div>
            {error ? <p className="text-sm font-medium text-issue" role="alert">{error}</p> : null}
          </div>
        </Panel>
        {result ? (
          <Panel>
            <div className="p-5">
              <h2 className="text-base font-bold">Import Result</h2>
              {result.warnings?.map((warning) => (
                <p key={warning} className="mt-3 rounded-md bg-amber-50 p-3 text-sm text-warning" role="status">{warning}</p>
              ))}
              <pre className="mt-3 overflow-auto rounded-md bg-slate-950 p-4 text-sm text-white">{JSON.stringify(result, null, 2)}</pre>
            </div>
          </Panel>
        ) : null}
      </div>
    </>
  );
}






