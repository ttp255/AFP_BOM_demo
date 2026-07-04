"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Box, ClipboardList, FileDown, Home, Menu, Package, Plus, Truck, X } from "lucide-react";

const items = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/projects", label: "All Projects", icon: ClipboardList },
  { href: "/projects/new", label: "New Project", icon: Plus },
  { href: "/products", label: "Product Catalog", icon: Package },
  { href: "/suppliers", label: "Suppliers", icon: Truck },
  { href: "/projects", label: "Exports", icon: FileDown },
];

export function MobileMenu() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  return (
    <>
      <button className="inline-grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-line bg-white text-slate-600 lg:hidden" aria-label="Open navigation" aria-expanded={open} onClick={() => setOpen(true)}>
        <Menu className="h-5 w-5" aria-hidden />
      </button>
      {open ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-slate-950/40 backdrop-blur-[1px]" aria-label="Close navigation" onClick={() => setOpen(false)} />
          <aside className="relative flex h-full w-[min(86vw,300px)] flex-col bg-white shadow-2xl" aria-label="Mobile navigation">
            <div className="flex h-20 items-center justify-center border-b border-line">
              <Link href="/" className="grid h-12 w-12 place-items-center rounded-xl bg-primary text-white" aria-label="AFP dashboard"><Box className="h-6 w-6" aria-hidden /></Link>
              <button className="absolute right-3 top-5 grid h-10 w-10 place-items-center rounded-lg text-slate-600 hover:bg-mist" aria-label="Close navigation" onClick={() => setOpen(false)}><X className="h-5 w-5" aria-hidden /></button>
            </div>
            <nav className="grid gap-2 p-3" aria-label="Main navigation">
              {items.map((item) => {
                const Icon = item.icon;
                const active = item.href === "/"
                  ? pathname === "/"
                  : item.href === "/projects"
                    ? pathname === "/projects" || /^\/projects\/(?!new(?:\/|$))/.test(pathname)
                    : pathname === item.href || pathname.startsWith(`${item.href}/`);
                return <Link key={`${item.href}-${item.label}`} href={item.href} aria-current={active ? "page" : undefined} className={`flex min-h-12 items-center gap-3 rounded-lg px-4 text-sm font-semibold ${active ? "bg-blue-50 text-primary" : "text-slate-700 hover:bg-blue-50 hover:text-primary"}`}><Icon className="h-5 w-5" aria-hidden />{item.label}</Link>;
              })}
            </nav>
          </aside>
        </div>
      ) : null}
    </>
  );
}
