import { PageHeader, Panel } from "@/components/chrome";
import { api } from "@/lib/api";

export default async function ProductsPage() {
  const products = await api.getProducts().catch(() => []);
  return (
    <>
      <PageHeader title="Product Catalog" eyebrow="Paint & More catalog" />
      <div className="p-5 lg:p-8">
        <Panel>
          <table className="table-grid">
            <thead><tr><th>SKU</th><th>Name</th><th>Type</th><th>Usage</th><th>Coverage</th><th>Package</th></tr></thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id}>
                  <td>{product.sku}</td>
                  <td>{product.product_name}</td>
                  <td>{product.product_type}</td>
                  <td>{(product.usage_areas || []).join(", ")}</td>
                  <td>{product.coverage_m2_per_liter} m2/L</td>
                  <td>{product.package_size} {product.package_unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </>
  );
}
