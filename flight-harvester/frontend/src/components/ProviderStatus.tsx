import { type HealthResponse } from "../types/stats";
import { Card } from "./ui/Card";

interface ProviderStatusProps {
  health?: HealthResponse;
}

export function ProviderStatus({ health }: ProviderStatusProps) {
  const providerStatus = health?.provider_status ?? {};

  if (Object.keys(providerStatus).length === 0) {
    return (
      <Card>
        <p className="text-sm text-slate-400">No provider data available</p>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-slate-700">
        Provider Status
      </h3>
      <div className="flex flex-wrap gap-4">
        {Object.entries(providerStatus).map(([name, status]) => {
          const isConfigured = status === "configured";
          return (
            <div key={name} className="flex items-center gap-2">
              <span
                className={`inline-block h-2 w-2 rounded-full ${
                  isConfigured ? "bg-green-500" : "bg-slate-300"
                }`}
              />
              <span className="text-sm font-medium text-slate-700 capitalize">
                {name}
              </span>
              <span
                className={`text-xs ${
                  isConfigured ? "text-green-600" : "text-slate-400"
                }`}
              >
                {status}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
