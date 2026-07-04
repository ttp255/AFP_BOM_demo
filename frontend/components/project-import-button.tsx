"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload } from "lucide-react";

import { Button } from "@/components/chrome";
import { WorkflowStatus } from "@/components/workflow-status";
import { api, errorMessage, type ImportResult } from "@/lib/api";

export function ProjectImportButton() {
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [step, setStep] = useState(1);
  const [action, setAction] = useState("Ready to create a new project");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [warning, setWarning] = useState("");

  useEffect(() => {
    if (!busy || result || error) return;
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
  }, [busy, result, error]);


  async function importFile(file: File | null | undefined) {
    if (!file) return;
    setError("");
    setWarning("");
    setResult(null);
    setStep(2);
    setAction("Uploading project JSON…");
    setBusy(true);
    try {
      const importResult = await api.uploadRevitJson(file);
      setResult(importResult);
      setWarning(importResult.warnings?.join(" ") || "");
      setStep(5);
      setAction(
        importResult.suggestions_generated > 0
          ? `Project created — ${importResult.suggestions_generated} product suggestions ready`
          : importResult.warnings?.length
            ? "Project and BOM created; product suggestions need attention"
            : "Project created — no matching products were found",
      );
      router.replace(`/projects/${importResult.project_id}/suggestions`);
    } catch (uploadError) {
      const message = errorMessage(uploadError, "The file could not be imported.");
      setError(message);
      setAction(message);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <>
      <input ref={inputRef} className="hidden" type="file" accept="application/json,.json" onChange={(event) => importFile(event.target.files?.[0])} />
      <Button disabled={busy} onClick={() => inputRef.current?.click()}>
        <Upload className="h-4 w-4" /> {busy ? "Importing" : "Import JSON"}
      </Button>
      {(busy || error || result) ? (
        <div className="fixed inset-x-0 top-20 z-20 border-b border-line bg-[#f7f9fc]/95 p-3 shadow-md backdrop-blur" aria-label="Project processing status">
          <div className="mx-auto w-full max-w-5xl">
            <WorkflowStatus currentStep={step} action={action} state={error ? "error" : result ? "success" : "running"} />
            {warning ? <p className="px-2 pt-2 text-xs font-medium text-amber-700" role="alert">{warning}</p> : null}
            {error ? <p className="px-2 pt-2 text-xs font-medium text-issue" role="alert">{error}</p> : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
