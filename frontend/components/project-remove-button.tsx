"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2, AlertTriangle, X, Check } from "lucide-react";

import { Button } from "@/components/chrome";
import { api, errorMessage, type ResourceId } from "@/lib/api";

export function ProjectRemoveButton({ projectId, projectName }: { projectId: ResourceId; projectName: string }) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  async function removeProject() {
    setBusy(true);
    try {
      await api.deleteProject(projectId);
      router.push("/projects");
      router.refresh();
    } catch (error) {
      alert(errorMessage(error, "Could not remove project."));
      setBusy(false);
      setConfirming(false);
    }
  }

  if (confirming) {
    return (
      <span className="inline-flex items-center gap-1">
        <span className="mr-1 inline-flex items-center gap-1 text-xs font-medium text-rose-600">
          <AlertTriangle className="h-3.5 w-3.5" />
          Sure?
        </span>
        <Button
          variant="danger"
          disabled={busy}
          onClick={removeProject}
          aria-label="Confirm remove project"
          className="px-2 py-1 text-xs"
        >
          <Check className="h-3.5 w-3.5" />
          {busy ? "Removing…" : "Yes, remove"}
        </Button>
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() => setConfirming(false)}
          aria-label="Cancel remove"
          className="px-2 py-1 text-xs"
        >
          <X className="h-3.5 w-3.5" />
          Cancel
        </Button>
      </span>
    );
  }

  return (
    <Button
      variant="danger"
      onClick={() => setConfirming(true)}
      aria-label={`Remove project ${projectName}`}
      className="px-3 py-2 text-sm"
    >
      <Trash2 className="h-4 w-4" />
  
    </Button>
  );
}