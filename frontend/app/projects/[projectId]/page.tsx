import Link from "next/link";
import { Upload, Trash2 } from "lucide-react";

import { Button, PageHeader, Panel } from "@/components/chrome";
import { ProjectTabs } from "@/components/project-tabs";
import { ProjectRemoveButton } from "@/components/project-remove-button";
import { api } from "@/lib/api";

export default async function ProjectOverview({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId: projectIdParam } = await params;
  const projectId = projectIdParam;
  const [project, rooms, elements, bom, suggestions] = await Promise.all([
    api.getProject(projectId).catch(() => null),
    api.getRooms(projectId).catch(() => []),
    api.getElements(projectId).catch(() => []),
    api.getBom(projectId).catch(() => []),
    api.getSuggestions(projectId).catch(() => []),
  ]);

  return (
    <>
      <PageHeader
        title={project?.project_name || "Project"}
        eyebrow={project?.project_code || "Overview"}
        actions={
          <div className="flex gap-2">
            <Link href={`/projects/${projectId}/import`}><Button><Upload className="h-4 w-4" /> Import JSON</Button></Link>
            {project ? <ProjectRemoveButton projectId={project.id} projectName={project.project_name} /> : null}
          </div>
        }
      />
      <ProjectTabs projectId={projectIdParam} />
      <div className="grid gap-5 p-5 lg:p-8">
        <div className="grid gap-4 md:grid-cols-4">
          {[
            ["Rooms", rooms.length],
            ["Paint Elements", elements.length],
            ["BOM Items", bom.length],
            ["Suggestions", suggestions.length],
          ].map(([label, value]) => (
            <Panel key={label}>
              <div className="p-5">
                <div className="text-sm text-slate-500">{label}</div>
                <div className="mt-2 text-3xl font-bold">{value}</div>
              </div>
            </Panel>
          ))}
        </div>
        <Panel>
          <div className="p-5">
            <h2 className="text-base font-bold">Workflow</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-4">
              {["Import JSON", "Generate BOM", "Suggest products", "Approve and export"].map((step, index) => (
                <div key={step} className="rounded-md border border-line bg-mist p-4">
                  <div className="text-xs font-bold text-slate-500">Ster {index + 1}</div>
                  <div className="mt-1 font-semibold">{step}</div>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}
