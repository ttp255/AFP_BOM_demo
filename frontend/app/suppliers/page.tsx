import { Badge, PageHeader, Panel } from "@/components/chrome";
import { api } from "@/lib/api";

export default async function SuppliersPage() {
  const suppliers = await api.getSuppliers().catch(() => []);
  return (
    <>
      <PageHeader title="Suppliers" eyebrow="Pricing and delivery sources" />
      <div className="p-5 lg:p-8">
        <Panel>
          <table className="table-grid">
            <thead><tr><th>Code</th><th>Name</th><th>City</th><th>Rating</th><th>Status</th></tr></thead>
            <tbody>
              {suppliers.map((supplier) => (
                <tr key={supplier.id}>
                  <td>{supplier.supplier_code}</td>
                  <td>{supplier.supplier_name}</td>
                  <td>{supplier.city || "-"}</td>
                  <td>{supplier.rating || "-"}</td>
                  <td><Badge tone={supplier.is_active ? "success" : "issue"}>{supplier.is_active ? "active" : "inactive"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </>
  );
}
