import { PageHeader, Panel } from "@/components/chrome";
import { ProjectTabs } from "@/components/project-tabs";
import { api } from "@/lib/api";

export default async function RoomsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId: projectIdParam } = await params;
  const rooms = await api.getRooms(projectIdParam).catch(() => []);
  return (
    <>
      <PageHeader title="Rooms" eyebrow="Room requirements" />
      <ProjectTabs projectId={projectIdParam} />
      <div className="p-5 lg:p-8">
        <Panel>
          <table className="table-grid">
            <thead><tr><th>Room</th><th>Level</th><th>Area</th><th>Height</th><th>Requirements</th></tr></thead>
            <tbody>
              {rooms.map((room) => (
                <tr key={room.id}>
                  <td>{room.room_name}</td>
                  <td>{room.level_name || "-"}</td>
                  <td>{room.area_m2 || "-"} m2</td>
                  <td>{room.height_m || "-"} m</td>
                  <td><code>{JSON.stringify(room.requirements || {})}</code></td>
                </tr>
              ))}
              {!rooms.length ? (
                <tr><td colSpan={5} className="text-slate-500">No rooms found for this project yet.</td></tr>
              ) : null}
            </tbody>
          </table>
        </Panel>
      </div>
    </>
  );
}
