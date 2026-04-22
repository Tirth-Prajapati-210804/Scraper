import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Plane } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      const isNetworkError =
        err instanceof TypeError ||
        (err as { response?: unknown })?.response === undefined;
      setError(
        isNetworkError
          ? "Cannot reach the server. Make sure the backend is running."
          : "Invalid email or password. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Left brand panel — hidden on small screens */}
      <div className="hidden lg:flex lg:w-1/2 flex-col items-center justify-center bg-gradient-to-br from-brand-600 to-brand-800 p-12 text-white">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/20 mb-6">
          <Plane className="h-8 w-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-center">Flight Price Tracker</h1>
        <p className="mt-3 text-brand-100 text-center max-w-xs text-sm leading-relaxed">
          Automated flight price collection and analysis for smarter travel decisions.
        </p>
        <ul className="mt-10 space-y-3 text-sm text-brand-100">
          {[
            "Multi-origin route monitoring",
            "Automated daily collection",
            "Currency & stops filtering",
            "Export to Excel",
          ].map((feat) => (
            <li key={feat} className="flex items-center gap-3">
              <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-brand-300" aria-hidden="true" />
              {feat}
            </li>
          ))}
        </ul>
      </div>

      {/* Right form panel */}
      <div className="flex flex-1 flex-col items-center justify-center bg-slate-50 px-8 py-12">
        {/* Mobile logo */}
        <div className="mb-8 flex flex-col items-center gap-3 text-center lg:hidden">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600">
            <Plane className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Flight Price Tracker</h1>
        </div>

        <div className="w-full max-w-sm">
          <div className="mb-6 text-center">
            <h2 className="text-2xl font-bold text-slate-900">Welcome back</h2>
            <p className="mt-1 text-sm text-slate-500">Sign in to your account</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="field-label">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="field-input"
                  placeholder="admin@example.com"
                />
              </div>

              <div>
                <label htmlFor="password" className="field-label">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="field-input"
                  placeholder="••••••••"
                />
              </div>

              {error && (
                <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                  {error}
                </p>
              )}

              <Button
                type="submit"
                variant="primary"
                loading={loading}
                className="w-full"
              >
                Sign in
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
