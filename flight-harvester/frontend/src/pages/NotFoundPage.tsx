import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 text-center">
      <p className="text-6xl font-bold text-slate-200">404</p>
      <h1 className="text-xl font-semibold text-slate-700">Page not found</h1>
      <p className="text-sm text-slate-400">This page doesn't exist or was moved.</p>
      <Link to="/" className="text-sm text-brand-600 hover:underline">
        Back to Dashboard
      </Link>
    </div>
  );
}
