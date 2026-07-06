const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
const UPLOAD_TIMEOUT_MS = 120_000;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (!headers.has("Content-Type") && options?.body) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    cache: "no-store",
    headers,
  });

  if (!res.ok) {
    const detail = await readError(res);
    throw new Error(`API ${res.status} ${res.statusText}${detail ? `: ${detail}` : ""}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`API returned invalid JSON for ${path}`);
  }
}

async function readError(res: Response) {
  const contentType = res.headers.get("content-type") || "";
  try {
    if (contentType.includes("application/json")) {
      const body = await res.json();
      if (typeof body.detail === "string") return body.detail;
      if (Array.isArray(body.detail)) {
        return body.detail.map((item: { msg?: string }) => item.msg || JSON.stringify(item)).join("; ");
      }
      return JSON.stringify(body);
    }
    return await res.text();
  } catch {
    return "";
  }
}

export type Project = {
  id: ResourceId;
  project_code: string;
  project_name: string;
  status: string;
  created_at?: string;
  revit_file_name?: string;
  location?: string;
};

export type ProductSuggestion = {
  id: ResourceId;
  bom_item_id: ResourceId;
  product_id: ResourceId;
  supplier_id: ResourceId;
  rank_no: number;
  is_best_option: boolean;
  hard_filter_pass: boolean;
  suggestion_status: "suggested" | "approved" | "rejected";
  estimated_required_package_qty?: number | string;
  estimated_total_cost?: number | string;
  required_painted_area?: number | string;
  currency: string;
  semantic_score: number;
  feature_score: number;
  price_score: number;
  stock_score: number;
  delivery_score: number;
  supplier_score: number;
  final_score: number;
  note?: string;
  explanation?: {
    summary: string;
    explanation?: string;
    main_reasons?: string[];
    not_needed_products?: string;
    approval_recommendation: string;
  };
  bom_item?: Record<string, any>;
  element?: Record<string, any>;
  product?: Record<string, any>;
  supplier?: Record<string, any>;
  offer?: Record<string, any>;
};
export type ImportResult = {
  project_id: string;
  project_code: string;
  status: string;
  created_at?: string;
  rooms_imported: number;
  surfaces_imported: number;
  bom_items_generated: number;
  suggestions_generated: number;
  warnings?: string[];
};

export type ResourceId = string;

export type SearchResult = {
  id: ResourceId;
  title: string;
  subtitle: string;
  href: string;
};

export type SearchResponse = {
  projects: SearchResult[];
  rooms: SearchResult[];
  products: SearchResult[];
};

export function errorMessage(error: unknown, fallback = "Something went wrong") {
  if (error instanceof TypeError && /fetch/i.test(error.message)) {
    return "Cannot reach the API. Check that the backend is running and try again.";
  }
  return error instanceof Error && error.message ? error.message : fallback;
}

export const api = {
  getProjects: () => request<Project[]>("/api/projects"),
  getProject: (projectId: ResourceId) => request<Project>(`/api/projects/${projectId}`),
  deleteProject: (projectId: ResourceId) => request<void>(`/api/projects/${projectId}`, { method: "DELETE" }),
  getRooms: (projectId: ResourceId) => request<any[]>(`/api/projects/${projectId}/rooms`),
  getElements: (projectId: ResourceId) => request<any[]>(`/api/projects/${projectId}/elements`),
  getBom: (projectId: ResourceId) => request<any[]>(`/api/bom/projects/${projectId}`),
  getSuggestions: (projectId: ResourceId) => request<ProductSuggestion[]>(`/api/suggestions/projects/${projectId}`),
  getProducts: () => request<any[]>("/api/catalog/products"),
  getSuppliers: () => request<any[]>("/api/catalog/suppliers"),
  getExports: (projectId: ResourceId) => request<any[]>(`/api/exports/projects/${projectId}`),
  search: (query: string) => request<SearchResponse>(`/api/search?q=${encodeURIComponent(query)}`),

  uploadRevitJson: async (file: File, projectId?: ResourceId): Promise<ImportResult> => {
    const formData = new FormData();
    formData.append("file", file);
    const path = projectId ? `/api/import/projects/${projectId}/revit-json` : "/api/import/revit-json";
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);
    try {
      const res = await fetch(`${API_URL}${path}`, { method: "POST", body: formData, signal: controller.signal });
      if (!res.ok) {
        const detail = await readError(res);
        throw new Error(detail || `Upload failed (HTTP ${res.status})`);
      }
      return res.json();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new Error("Upload timed out. The file may be too large; please try again.");
      }
      throw error;
    } finally {
      window.clearTimeout(timeout);
    }
  },

  generateBom: (projectId: ResourceId) =>
    request(`/api/bom/projects/${projectId}/generate`, { method: "POST" }),
  suggestProducts: (projectId: ResourceId) =>
    request(`/api/suggestions/projects/${projectId}/suggest`, { method: "POST" }),
  approveSuggestion: (suggestionId: ResourceId) =>
    request(`/api/suggestions/${suggestionId}/approve`, { method: "POST" }),
  rejectSuggestion: (suggestionId: ResourceId) =>
    request(`/api/suggestions/${suggestionId}/reject`, { method: "POST" }),
  exportProject: async (projectId: ResourceId, exportType: string, scope: string) => {
    const res = await fetch(
      `${API_URL}/api/exports/projects/${projectId}/${exportType}?scope=${encodeURIComponent(scope)}`,
      { method: "POST" },
    );
    if (!res.ok) {
      const detail = await readError(res);
      throw new Error(`Export failed (HTTP ${res.status})${detail ? `: ${detail}` : ""}`);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || `bom.${exportType}`;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};



