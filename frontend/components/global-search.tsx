"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Box, ClipboardList, DoorOpen, LoaderCircle, Search, X } from "lucide-react";

import { api, SearchResponse, SearchResult } from "@/lib/api";

const emptyResults: SearchResponse = { projects: [], rooms: [], products: [] };
const groups = [
  { key: "projects" as const, label: "Projects", icon: ClipboardList },
  { key: "rooms" as const, label: "Rooms", icon: DoorOpen },
  { key: "products" as const, label: "Products", icon: Box },
];

export function GlobalSearch() {
  const router = useRouter();
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResponse>(emptyResults);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const flatResults = useMemo(() => groups.flatMap((group) => results[group.key]), [results]);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || target.isContentEditable;
      if ((event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) || (event.key.toLowerCase() === "k" && !typing)) {
        event.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    };
    const handleOutsideClick = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("keydown", handleShortcut);
    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      window.removeEventListener("keydown", handleShortcut);
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, []);

  useEffect(() => {
    const normalized = query.trim();
    setActiveIndex(-1);
    if (!normalized) {
      setResults(emptyResults);
      setLoading(false);
      return;
    }
    let current = true;
    setLoading(true);
    const timer = window.setTimeout(async () => {
      try {
        const nextResults = await api.search(normalized);
        if (current) setResults(nextResults);
      } catch {
        if (current) setResults(emptyResults);
      } finally {
        if (current) setLoading(false);
      }
    }, 220);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [query]);

  const choose = (result: SearchResult) => {
    setOpen(false);
    setQuery("");
    router.push(result.href);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    } else if (event.key === "ArrowDown" && flatResults.length) {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % flatResults.length);
    } else if (event.key === "ArrowUp" && flatResults.length) {
      event.preventDefault();
      setActiveIndex((index) => (index <= 0 ? flatResults.length - 1 : index - 1));
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      choose(flatResults[activeIndex]);
    }
  };

  const hasResults = flatResults.length > 0;
  let itemIndex = -1;

  return (
    <div ref={rootRef} className="relative ml-auto hidden w-full max-w-md md:block">
      <div className={`flex items-center gap-2 rounded-lg border bg-white px-3 py-2 shadow-sm transition ${open ? "border-primary ring-2 ring-blue-100" : "border-line"}`}>
        <Search className="h-5 w-5 shrink-0 text-slate-500" aria-hidden />
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => { setQuery(event.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          className="min-w-0 flex-1 border-0 bg-transparent text-sm outline-none placeholder:text-slate-400"
          placeholder="Search projects, rooms, products..."
          role="combobox"
          aria-expanded={open && Boolean(query.trim())}
          aria-controls="global-search-results"
          aria-autocomplete="list"
        />
        {query ? (
          <button type="button" onClick={() => setQuery("")} className="rounded p-0.5 text-slate-400 hover:text-slate-700" aria-label="Clear search"><X className="h-4 w-4" /></button>
        ) : (
          <button type="button" onClick={() => inputRef.current?.focus()} className="rounded border border-line px-2 py-1 text-xs font-bold text-slate-500" aria-label="Focus search">K</button>
        )}
      </div>

      {open && query.trim() ? (
        <div id="global-search-results" role="listbox" className="absolute right-0 top-[calc(100%+8px)] z-50 max-h-[70vh] w-full min-w-[360px] overflow-y-auto rounded-xl border border-line bg-white p-2 shadow-[0_18px_45px_rgba(15,23,42,0.16)]">
          {loading ? (
            <div className="flex items-center justify-center gap-2 px-4 py-8 text-sm text-slate-500"><LoaderCircle className="h-4 w-4 animate-spin" /> Searching…</div>
          ) : hasResults ? (
            groups.map((group) => {
              const Icon = group.icon;
              const groupResults = results[group.key];
              if (!groupResults.length) return null;
              return (
                <section key={group.key} className="mb-1 last:mb-0">
                  <div className="px-3 pb-1 pt-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">{group.label}</div>
                  {groupResults.map((result) => {
                    itemIndex += 1;
                    const index = itemIndex;
                    return (
                      <Link
                        key={`${group.key}-${result.id}`}
                        href={result.href}
                        role="option"
                        aria-selected={activeIndex === index}
                        onMouseEnter={() => setActiveIndex(index)}
                        onClick={() => { setOpen(false); setQuery(""); }}
                        className={`flex items-center gap-3 rounded-lg px-3 py-2.5 ${activeIndex === index ? "bg-blue-50" : "hover:bg-slate-50"}`}
                      >
                        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-600"><Icon className="h-4 w-4" /></span>
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-semibold text-ink">{result.title}</span>
                          <span className="block truncate text-xs text-slate-500">{result.subtitle}</span>
                        </span>
                      </Link>
                    );
                  })}
                </section>
              );
            })
          ) : (
            <div className="px-4 py-8 text-center">
              <div className="text-sm font-semibold text-slate-700">No matches found</div>
              <div className="mt-1 text-xs text-slate-500">Try a project code, room name, or product SKU.</div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
