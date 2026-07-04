"use client";

import { use, useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

import { Badge, Button, PageHeader, Panel } from "@/components/chrome";
import { ProjectTabs, refreshProjectProgress } from "@/components/project-tabs";
import { api } from "@/lib/api";

export default function BomPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId: projectIdParam } = use(params);
  const projectId = projectIdParam;
  const [items, setItems] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setItems(await api.getBom(projectId).catch(() => []));
  }, [projectId]);

  async function generate() {
    setBusy(true);
    try {
      await api.generateBom(projectId);
      await load();
      refreshProjectProgress();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <PageHeader title="BOM Items" eyebrow="Paint quantities" actions={<Button disabled={busy} onClick={generate}><RefreshCw className="h-4 w-4" /> Generate BOM</Button>} />
      <ProjectTabs projectId={projectIdParam} />
      <div className="p-5 lg:p-8">
        <Panel>
          <table className="table-grid">
            <thead><tr><th>Item</th><th>Surface</th><th>Finish</th><th>Area</th><th>Waste</th><th>Quantity</th><th>Status</th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.item_name}</td>
                  <td>{item.surface}</td>
                  <td>{item.finish_type}</td>
                  <td>{item.net_area_m2} m2</td>
                  <td>{item.waste_factor}</td>
                  <td>{item.quantity} {item.unit}</td>
                  <td><Badge tone={item.suggestion_status === "approved" ? "success" : "warning"}>{item.suggestion_status}</Badge></td>
                </tr>
              ))}
              {!items.length ? (
                <tr><td colSpan={7} className="text-slate-500">Generate BOM after importing Revit room and surface data.</td></tr>
              ) : null}
            </tbody>
          </table>
        </Panel>
      </div>
    </>
  );
}
