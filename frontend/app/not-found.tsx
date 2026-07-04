import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center p-5">
      <h2 className="text-2xl font-bold text-slate-800">Page Not Found</h2>
      <p className="mt-2 text-slate-600">Could not find requested resource</p>
      <Link href="/projects" className="mt-4 text-primary font-semibold hover:underline">
        Return to Projects
      </Link>
    </div>
  );
}
