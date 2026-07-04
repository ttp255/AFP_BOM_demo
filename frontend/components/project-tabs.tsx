"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ProjectProgress } from "@/components/project-progress";
import { api, type Project } from "@/lib/api";

export const PROJECT_PROGRESS_REFRESH_EVENT = "afp:project-progress-refresh";

export function refreshProjectProgress() {
  window.dispatchEvent(new Event(PROJECT_PROGRESS_REFRESH_EVENT));
}

const tabs = [
  ["Overview", ""],
  ["Rooms", "rooms"],
  ["BOM Items", "bom"],
  ["Product Suggestions", "suggestions"],
  ["Export", "export"],
];

export function ProjectTabs({ projectId }: { projectId: string }) {
  const [progress, setProgress] = useState({
    imported: false,
    bomItems: 0,
    suggestions: 0,
    approvedBomItems: 0,
    exports: 0,
  });

  const loadProgress = useCallback(async () => {
    const [project, rooms, elements, bom, suggestions, exports] = await Promise.all([
      api.getProject(projectId).catch(() => null as Project | null),
      api.getRooms(projectId).catch(() => []),
      api.getElements(projectId).catch(() => []),
      api.getBom(projectId).catch(() => []),
      api.getSuggestions(projectId).catch(() => []),
      api.getExports(projectId).catch(() => []),
    ]);
    const approvedBomItemIds = new Set<string | number>();
    bom.forEach((item) => {
      if (item.suggestion_status === "approved") approvedBomItemIds.add(item.id);
    });
    suggestions.forEach((item) => {
      if (item.suggestion_status === "approved" && item.bom_item_id) approvedBomItemIds.add(item.bom_item_id);
    });

    const projectExports = exports.filter((item) => String(item.project_id) === String(projectId));

    setProgress({
      imported: project?.status === "imported" || rooms.length > 0 || elements.length > 0,
      bomItems: bom.length,
      suggestions: suggestions.length,
      approvedBomItems: approvedBomItemIds.size,
      exports: projectExports.length,
    });
  }, [projectId]);

  useEffect(() => {
    setProgress({ imported: false, bomItems: 0, suggestions: 0, approvedBomItems: 0, exports: 0 });
    loadProgress();

    const handleProgressRefresh = () => {
      void loadProgress();
    };

    window.addEventListener(PROJECT_PROGRESS_REFRESH_EVENT, handleProgressRefresh);
    window.addEventListener("focus", handleProgressRefresh);

    return () => {
      window.removeEventListener(PROJECT_PROGRESS_REFRESH_EVENT, handleProgressRefresh);
      window.removeEventListener("focus", handleProgressRefresh);
    };
  }, [loadProgress]);

  return (
    <>
      <div className="flex gap-1 overflow-x-auto border-b border-line bg-white px-5 lg:px-8">
        {tabs.map(([label, suffix]) => (
          <Link key={label} href={`/projects/${projectId}${suffix ? `/${suffix}` : ""}`} className="whitespace-nowrap border-b-2 border-transparent px-3 py-3 text-sm font-semibold text-slate-600 hover:border-primary hover:text-primary">
            {label}
          </Link>
        ))}
      </div>
      <ProjectProgress {...progress} />
    </>
  );
}
