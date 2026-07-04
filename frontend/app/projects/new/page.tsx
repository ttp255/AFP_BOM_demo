import Link from "next/link";
import { ArrowLeft, FileJson, Upload } from "lucide-react";

import { PageHeader, Panel } from "@/components/chrome";
import { ProjectImportButton } from "@/components/project-import-button";

export default function NewProjectPage() {
  return (
    <>
      <PageHeader
        title="New Project"
        eyebrow="Import Revit data"
        subtitle="Create a project by uploading its exported Revit JSON file."
        actions={(
          <Link href="/projects" className="inline-flex min-h-10 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-mist">
            <ArrowLeft className="h-4 w-4" aria-hidden /> All Projects
          </Link>
        )}
      />
      <div className="p-5 lg:p-8">
        <Panel>
          <div className="grid gap-6 p-6 sm:p-8 lg:grid-cols-[1fr_auto] lg:items-center">
            <div className="flex gap-4">
              <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-blue-50 text-primary">
                <FileJson className="h-6 w-6" aria-hidden />
              </div>
              <div>
                <h2 className="text-lg font-bold text-ink">Upload Revit JSON</h2>
                <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
                  Select a JSON export to create the project, generate its paint BOM, and prepare product suggestions.
                </p>
                <div className="mt-3 flex items-center gap-2 text-xs font-medium text-slate-500">
                  <Upload className="h-3.5 w-3.5" aria-hidden /> Accepted format: .json
                </div>
              </div>
            </div>
            <ProjectImportButton />
          </div>
        </Panel>
      </div>
    </>
  );
}
