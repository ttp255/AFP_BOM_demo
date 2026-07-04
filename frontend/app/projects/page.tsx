import Link from "next/link";
import { Plus } from "lucide-react";

import { Badge, PageHeader, Panel } from "@/components/chrome";
import { ProjectRemoveButton } from "@/components/project-remove-button";
import { api } from "@/lib/api";

export default async function ProjectsPage() {
  const projects = await api.getProjects().catch(() => []);
  const sortedProjects = [...projects].sort((a, b) => {
    const aTime = a.created_at ? Date.parse(a.created_at) : 0;
    const bTime = b.created_at ? Date.parse(b.created_at) : 0;
    return bTime - aTime;
  });
  return (
    <>
      <PageHeader
        title="All Projects"
        eyebrow="Imported Revit jobs"
        actions={(
          <Link href="/projects/new" className="inline-flex min-h-10 items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" aria-hidden /> New Project
          </Link>
        )}
      />
      <div className="p-5 lg:p-8">
        <Panel>
          <table className="table-grid">
            <thead>
              <tr>
                <th>Project</th>
                <th>Revit File</th>
                <th>Location</th>
                <th>Created</th>
                <th>Status</th>
                <th><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {sortedProjects.map((project) => (
                <tr key={project.id}>
                  <td>
                    <Link className="font-semibold text-primary" href={`/projects/${project.id}`}>
                      {project.project_code} - {project.project_name}
                    </Link>
                  </td>
                  <td>{project.revit_file_name || "-"}</td>
                  <td>{project.location || "-"}</td>
                  <td>
                    {project.created_at
                      ? new Intl.DateTimeFormat("en-GB", {
                          dateStyle: "medium",
                          timeStyle: "short",
                          timeZone: "Asia/Bangkok",
                        }).format(new Date(project.created_at))
                      : "-"}
                  </td>
                  <td><Badge tone="success">{project.status}</Badge></td>
                  <td className="text-right"><ProjectRemoveButton projectId={project.id} projectName={project.project_name} /></td>
                </tr>
              ))}
              {!sortedProjects.length ? <tr><td colSpan={6} className="text-slate-500">Upload a Revit JSON file to create the first project.</td></tr> : null}
            </tbody>
          </table>
        </Panel>
      </div>
    </>
  );
}


