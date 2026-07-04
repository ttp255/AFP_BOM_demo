"use client";

import { use, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, RefreshCw, Sparkles, Wand2, X } from "lucide-react";

import { Badge, Button, PageHeader, Panel } from "@/components/chrome";
import { ProjectTabs, refreshProjectProgress } from "@/components/project-tabs";
import { api, errorMessage, type ProductSuggestion } from "@/lib/api";

function calculateTotalCost(suggestions: ProductSuggestion[]): number {
  return suggestions
    .filter((suggestion) => suggestion.suggestion_status === "approved")
    .reduce((total, suggestion) => {
      const cost = Number(suggestion.estimated_total_cost);
      return Number.isFinite(cost) ? total + cost : total;
    }, 0);
}

function normalizeExplanationText(value?: string): string {
  return (value || "").toLocaleLowerCase("vi").replace(/[.,;:!?()[\]{}"']/g, "").replace(/\s+/g, " ").trim();
}
function explanationRepeats(value: string | undefined, previousValues: (string | undefined)[]): boolean {
  const normalized = normalizeExplanationText(value);
  if (!normalized) return false;
  const words = new Set(normalized.split(" "));

  return previousValues.some((previousValue) => {
    const previous = normalizeExplanationText(previousValue);
    if (!previous) return false;
    if (normalized === previous || normalized.includes(previous) || previous.includes(normalized)) return true;

    const previousWords = new Set(previous.split(" "));
    const sharedWords = [...words].filter((word) => previousWords.has(word)).length;
    return words.size >= 4 && previousWords.size >= 4
      && sharedWords / Math.min(words.size, previousWords.size) >= 0.8;
  });
}
export default function SuggestionsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const router = useRouter();
  const { projectId: projectIdParam } = use(params);
  const projectId = projectIdParam;
  const [suggestions, setSuggestions] = useState<ProductSuggestion[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [approvingId, setApprovingId] = useState<string | number | null>(null);
  const [rejectingId, setRejectingId] = useState<string | number | null>(null);

  const load = useCallback(async () => {
    try {
      setSuggestions(await api.getSuggestions(projectId));
      setError("");
    } catch (cause) {
      setError(errorMessage(cause, "Could not load suggestions"));
    }
  }, [projectId]);

  async function suggest() {
    setBusy(true);
    try {
      await api.suggestProducts(projectId);
      await load();
      refreshProjectProgress();
    } catch (cause) {
      setError(errorMessage(cause, "Could not generate suggestions"));
    } finally {
      setBusy(false);
    }
  }

  async function approve(id: string | number) {
    const target = suggestions.find((suggestion) => String(suggestion.id) === String(id));
    const isReplacement = target
      ? suggestions.some(
          (suggestion) =>
            String(suggestion.bom_item_id) === String(target.bom_item_id)
            && suggestion.suggestion_status === "approved",
        )
      : false;

    setApprovingId(id);
    try {
      await api.approveSuggestion(id);
      const [updatedSuggestions, bomItems] = await Promise.all([
        api.getSuggestions(projectId),
        api.getBom(projectId),
      ]);
      setSuggestions(updatedSuggestions);
      setError("");
      refreshProjectProgress();
      const approvedBomItemIds = new Set(
        updatedSuggestions
          .filter((suggestion) => suggestion.suggestion_status === "approved")
          .map((suggestion) => String(suggestion.bom_item_id)),
      );
      if (
        !isReplacement
        &&
        bomItems.length > 0
        && bomItems.every((item) => approvedBomItemIds.has(String(item.id)))
      ) {
        router.push(`/projects/${projectId}/export`);
      }
    } catch (cause) {
      setError(errorMessage(cause, "Could not approve suggestion"));
    } finally {
      setApprovingId(null);
    }
  }

  async function reject(id: string | number) {
    setRejectingId(id);
    try {
      await api.rejectSuggestion(id);
      await load();
      refreshProjectProgress();
    } catch (cause) {
      setError(errorMessage(cause, "Could not reject suggestion"));
    } finally {
      setRejectingId(null);
    }
  }

  useEffect(() => {
    load();
  }, [load]);

  const orderedSuggestions = [...suggestions].sort((a, b) =>
    String(a.bom_item_id).localeCompare(String(b.bom_item_id)) || (a.rank_no - b.rank_no)
  );
  const totalCost = calculateTotalCost(suggestions);
  const currency = suggestions.find(
    (suggestion) => suggestion.suggestion_status === "approved" && suggestion.currency
  )?.currency || "VND";
  const approvedBomItemIds = new Set(
    suggestions
      .filter((suggestion) => suggestion.suggestion_status === "approved")
      .map((suggestion) => String(suggestion.bom_item_id)),
  );

  return (
    <>
      <PageHeader title="Product Suggestions" eyebrow="BIM context builds requirements, SQL filters, vector finds, ranking chooses, LLM explains" actions={<Button disabled={busy} onClick={suggest}><Wand2 className="h-4 w-4" /> {busy ? "Finding products..." : "Suggest Products"}</Button>} />
      <ProjectTabs projectId={projectIdParam} />
      <div className="p-5 lg:p-8">
        {error ? <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
        {suggestions.length ? (
          <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-sm font-medium text-slate-500">Approved total cost</div>
            <div className="mt-1 text-2xl font-semibold text-slate-950">
              {totalCost.toLocaleString()} {currency}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              Calculated from the approved suggestion for each BOM item
            </div>
          </div>
        ) : null}
        <Panel>
          <table className="table-grid">
            <thead><tr><th>BOM item</th><th>Rank</th><th>Product</th><th>Why effective</th><th>Price</th><th>Quantity</th><th>Cost</th><th>Supplier</th><th>Score</th><th>Status</th><th>Decision</th></tr></thead>
            <tbody>
              {orderedSuggestions.map((suggestion) => {
                const isApproved = suggestion.suggestion_status === "approved";
                const isReplacement = !isApproved && approvedBomItemIds.has(String(suggestion.bom_item_id));
                const actionLabel = isApproved
                  ? "Approved"
                  : approvingId === suggestion.id
                    ? "Saving..."
                    : isReplacement
                      ? "Use replacement"
                      : suggestion.rank_no === 1
                        ? "Approve"
                        : "Use replacement";

                return (
                <tr
                  key={suggestion.id}
                  className={
                    isApproved
                      ? "bg-emerald-50/70"
                      : suggestion.rank_no === 1
                        ? "bg-blue-50/60"
                        : "transition-colors hover:bg-slate-50"
                  }
                >
                  <td>
                    <div className="font-medium">{suggestion.bom_item?.item_name || `BOM #${suggestion.bom_item_id}`}</div>
                    <div className="text-xs text-slate-500">{suggestion.element?.revit_element_id || `Element #${suggestion.bom_item?.revit_element_id || "-"}`}</div>
                    <div className="mt-1 text-xs text-slate-400">Area: {suggestion.bom_item?.quantity || "-"} m² {suggestion.bom_item?.waste_factor ? `(waste ${suggestion.bom_item.waste_factor})` : ""}</div>
                  </td>
                  <td><Badge tone={suggestion.rank_no === 1 ? "success" : "neutral"}>#{suggestion.rank_no}</Badge></td>
                  <td>
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <div className="text-base font-bold text-slate-950">{suggestion.product?.product_name || `Product #${suggestion.product_id}`}</div>
                      {suggestion.rank_no === 1 ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-[11px] font-bold uppercase tracking-wide text-blue-700">
                          <Sparkles className="h-3 w-3" aria-hidden /> Best match
                        </span>
                      ) : null}
                    </div>
                    <div className="text-xs text-slate-500">{suggestion.product?.product_type || "-"}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {suggestion.product?.package_area_m2 && Number(suggestion.product.package_area_m2) > 0 ? (
                        <span>Coverage: {suggestion.product.package_area_m2} m²/pkg</span>
                      ) : (
                        <>
                          Coverage: {suggestion.product?.coverage_m2_per_liter || "-"} m²/L · Pkg: {suggestion.product?.package_size || "-"} {suggestion.product?.package_unit || "L"}
                          {suggestion.product?.coverage_m2_per_liter && suggestion.product?.package_size && (
                            <span className="text-slate-400"> ({Number(suggestion.product.coverage_m2_per_liter) * Number(suggestion.product.package_size)} m²/pkg)</span>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                  <td className="max-w-md whitespace-normal text-sm text-slate-600">
                    {suggestion.explanation ? (
                      <div className={`space-y-3 rounded-xl border p-3 ${
                        suggestion.rank_no === 1
                          ? "border-blue-200 bg-gradient-to-br from-blue-50 to-white shadow-sm"
                          : "border-slate-200 bg-white"
                      }`}>
                        <div className="flex items-start gap-2">
                          <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-emerald-100 text-emerald-700">
                            <Check className="h-3.5 w-3.5" aria-hidden />
                          </span>
                          <p className="font-semibold leading-6 text-slate-900">{suggestion.explanation.summary}</p>
                        </div>
                        <ul className="space-y-1.5">
                          {(suggestion.explanation.main_reasons || [])
                            .filter((reason, index, reasons) => reasons.findIndex((value) => normalizeExplanationText(value) === normalizeExplanationText(reason)) === index)
                            .map((reason, index) => (
                              <li key={index} className="flex items-start gap-2 rounded-lg bg-emerald-50/70 px-2.5 py-2 text-emerald-950">
                                <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden />
                                <span>{reason}</span>
                              </li>
                            ))}
                        </ul>
                        {!(suggestion.explanation.main_reasons || []).some(
                          (reason) => normalizeExplanationText(reason) === normalizeExplanationText(suggestion.explanation!.explanation),
                        ) ? <p>{suggestion.explanation.explanation}</p> : null}
                        {suggestion.explanation.not_needed_products ? <p className="text-slate-500">{suggestion.explanation.not_needed_products}</p> : null}
                        {!explanationRepeats(suggestion.explanation.approval_recommendation, [
                          suggestion.explanation.summary,
                          suggestion.explanation.explanation,
                          ...(suggestion.explanation.main_reasons || []),
                        ]) ? <p className="font-medium">{suggestion.explanation.approval_recommendation}</p> : null}
                      </div>
                    ) : suggestion.note || "Effectiveness explanation unavailable."}
                  </td>
                  <td className="text-sm">
                    <div className="font-medium text-slate-900">
                      {suggestion.offer?.unit_price !== null && suggestion.offer?.unit_price !== undefined ? Number(suggestion.offer.unit_price).toLocaleString() : "-"} {suggestion.currency}
                    </div>
                    {suggestion.offer?.min_order_qty ? <div className="text-xs text-slate-500">Min order: {suggestion.offer.min_order_qty}</div> : null}
                  </td>
                  <td className="text-sm">
                    <div className="font-medium text-slate-700">
                      Painted Area: {suggestion.required_painted_area !== null && suggestion.required_painted_area !== undefined ? `${suggestion.required_painted_area} m²` : "-"}
                      <span className="font-normal text-slate-400"> ({suggestion.product?.recommended_coats || 2} coats)</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-600">
                      <span className="font-semibold text-slate-800">{suggestion.estimated_required_package_qty || "-"} packages</span>
                      <span className="text-slate-400"> (stock {suggestion.offer?.stock_qty ?? "unknown"} · {suggestion.offer?.delivery_days ?? "?"} days)</span>
                    </div>
                  </td>
                  <td className="font-semibold text-primary">
                    {suggestion.estimated_total_cost !== null && suggestion.estimated_total_cost !== "" && Number.isFinite(Number(suggestion.estimated_total_cost)) ? Number(suggestion.estimated_total_cost).toLocaleString() : "-"} {suggestion.currency}
                  </td>
                  <td className="text-sm">
                    <div className="font-medium text-slate-900">{suggestion.supplier?.supplier_name || `Supplier #${suggestion.supplier_id}`}</div>
                  </td>
                  <td>
                    <div className="font-medium">{Number(suggestion.final_score).toFixed(1)}</div>
                    <div className="text-xs text-slate-500">Semantic {Number(suggestion.semantic_score || 0).toFixed(1)} · Features {Number(suggestion.feature_score || 0).toFixed(1)}</div>
                  </td>
                  <td><Badge tone={suggestion.suggestion_status === "approved" ? "success" : "neutral"}>{suggestion.suggestion_status}</Badge></td>
                  <td><div className="flex flex-wrap gap-2">
                    <Button variant="secondary" disabled={approvingId !== null || isApproved} onClick={() => approve(suggestion.id)}>
                      {isReplacement ? <RefreshCw className="h-4 w-4" /> : <Check className="h-4 w-4" />} {actionLabel}
                    </Button>
                    <Button variant="secondary" disabled={rejectingId !== null || suggestion.suggestion_status !== "suggested"} onClick={() => reject(suggestion.id)}>
                      <X className="h-4 w-4" /> {rejectingId === suggestion.id ? "Rejecting..." : "Reject"}
                    </Button>
                  </div>
                  </td>
                </tr>
                );
              })}
              {!suggestions.length ? (
                <tr><td colSpan={11} className="text-slate-500">Generate product suggestions after BOM items are ready.</td></tr>
              ) : null}
            </tbody>
          </table>
        </Panel>
      </div>
    </>
  );
}






