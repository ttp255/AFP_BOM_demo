import Link from "next/link";

import { MobileMenu } from "@/components/mobile-menu";
import { GlobalSearch } from "@/components/global-search";
import {
  Bell,
  Box,
  ClipboardList,
  FileDown,
  HelpCircle,
  Home,
  Package,
  Plus,
  Truck,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/projects", label: "All Projects", icon: ClipboardList },
  { href: "/projects/new", label: "New Project", icon: Plus },
  { href: "/products", label: "Product Catalog", icon: Package },
  { href: "/suppliers", label: "Suppliers", icon: Truck },
  { href: "/projects", label: "Exports", icon: FileDown },
];

export function AppChrome({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f7f9fc] text-ink lg:grid lg:grid-cols-[230px_1fr]">
      <aside className="hidden border-r border-line bg-white lg:flex lg:min-h-screen lg:flex-col">
        <div className="flex h-24 items-center justify-center">
          <Link href="/" className="grid h-14 w-14 place-items-center rounded-xl bg-primary text-white shadow-[0_10px_24px_rgba(37,99,235,0.22)]" aria-label="AFP dashboard">
            <Box className="h-7 w-7" aria-hidden />
          </Link>
        </div>
        <nav className="grid gap-2 px-3 py-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={`${item.href}-${item.label}`}
                href={item.href}
                className="flex min-h-12 items-center gap-3 rounded-lg px-4 text-sm font-semibold text-slate-700 hover:bg-blue-50 hover:text-primary"
              >
                <Icon className="h-5 w-5" aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto p-3">
          <div className="flex items-center justify-between rounded-lg border border-line bg-white p-3 shadow-panel">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-full bg-primary text-sm font-bold text-white">AK</div>
              <div>
                <div className="text-sm font-bold">Alex Kim</div>
                <div className="text-xs text-slate-500">BIM Engineer</div>
              </div>
            </div>
          </div>
        </div>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-10 flex h-20 items-center gap-4 border-b border-line bg-white/95 px-4 backdrop-blur lg:px-8">
          <MobileMenu />
          <div className="min-w-0">
            <div className="truncate text-base font-bold tracking-normal text-ink sm:text-xl">AFP Revit BOM System</div>
            <div className="hidden truncate text-sm text-slate-500 sm:block">Revit data to BOM, product mapping, and export</div>
          </div>
          <GlobalSearch />
          <Link href="/projects/new" className="hidden min-h-11 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-white shadow-[0_8px_20px_rgba(37,99,235,0.22)] md:inline-flex">
            <Plus className="h-5 w-5" aria-hidden />
            New Project
          </Link>
          <button className="relative grid h-10 w-10 place-items-center rounded-lg text-slate-600 hover:bg-mist" aria-label="Notifications">
            <Bell className="h-5 w-5" aria-hidden />
            <span className="absolute right-2 top-2 grid h-4 min-w-4 place-items-center rounded-full bg-rose-500 px-1 text-[10px] font-bold leading-none text-white">3</span>
          </button>
          <button className="grid h-10 w-10 place-items-center rounded-lg text-slate-600 hover:bg-mist" aria-label="Help">
            <HelpCircle className="h-5 w-5" aria-hidden />
          </button>
        </header>
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}

export function PageHeader({ title, eyebrow, subtitle, actions }: { title: string; eyebrow?: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <header className="flex flex-col gap-4 bg-[#f7f9fc] px-5 pt-7 sm:flex-row sm:items-start sm:justify-between lg:px-8">
      <div>
        {eyebrow ? <div className="mb-2 text-sm font-medium text-slate-500">{eyebrow}</div> : null}
        <h1 className="text-3xl font-bold tracking-normal text-ink">{title}</h1>
        {subtitle ? <p className="mt-2 text-sm text-slate-500">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}

export function Button({ children, variant = "primary", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" }) {
  const colors = {
    primary: "bg-primary text-white hover:bg-blue-700",
    secondary: "border border-line bg-white text-ink hover:bg-mist",
    danger: "bg-issue text-white hover:bg-red-800",
  };
  return (
    <button {...props} className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60 ${colors[variant]} ${props.className || ""}`}>
      {children}
    </button>
  );
}

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "success" | "warning" | "issue" }) {
  const colors = {
    neutral: "bg-slate-100 text-slate-700",
    success: "bg-emerald-50 text-success",
    warning: "bg-amber-50 text-warning",
    issue: "bg-rose-50 text-issue",
  };
  return <span className={`inline-flex rounded-md px-2 py-1 text-xs font-bold ${colors[tone]}`}>{children}</span>;
}

export function Panel({ children }: { children: React.ReactNode }) {
  return <section className="rounded-lg border border-line bg-white shadow-panel">{children}</section>;
}




