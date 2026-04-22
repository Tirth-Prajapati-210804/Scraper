import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp } from "lucide-react";
import { TagInput } from "./ui/TagInput";
import { type FormEvent, useEffect, useState } from "react";
import {
  createRouteGroup,
  createRouteGroupFromText,
  updateRouteGroup,
} from "../api/route-groups";
import { useToast } from "../context/ToastContext";
import type { RouteGroup } from "../types/route-group";
import { Button } from "./ui/Button";
import { Modal } from "./ui/Modal";

interface RouteGroupFormProps {
  open: boolean;
  onClose: () => void;
  initial?: RouteGroup | null;
}

const CURRENCIES = [
  { value: "USD", label: "USD – US Dollar" },
  { value: "EUR", label: "EUR – Euro" },
  { value: "GBP", label: "GBP – British Pound" },
  { value: "CAD", label: "CAD – Canadian Dollar" },
  { value: "AUD", label: "AUD – Australian Dollar" },
  { value: "JPY", label: "JPY – Japanese Yen" },
  { value: "SGD", label: "SGD – Singapore Dollar" },
  { value: "AED", label: "AED – UAE Dirham" },
  { value: "INR", label: "INR – Indian Rupee" },
  { value: "THB", label: "THB – Thai Baht" },
  { value: "VND", label: "VND – Vietnamese Dong" },
];

const STOP_OPTIONS: { label: string; value: number | null }[] = [
  { label: "Any", value: null },
  { label: "Direct", value: 0 },
  { label: "1", value: 1 },
  { label: "2", value: 2 },
];

// ── Shared "additional options" fields ───────────────────────────────────────

interface ExtraOptions {
  currency: string;
  max_stops: number | null;
  start_date: string;
  end_date: string;
}

function ExtraOptionsFields({
  values,
  onChange,
  originalCurrency,
}: {
  values: ExtraOptions;
  onChange: <K extends keyof ExtraOptions>(key: K, value: ExtraOptions[K]) => void;
  originalCurrency?: string;
}) {
  const currencyChanged = originalCurrency != null && values.currency !== originalCurrency;

  return (
    <div className="space-y-4">
      {/* Currency */}
      <div>
        <label className="field-label">Display Currency</label>
        <select
          className="field-input"
          value={values.currency}
          onChange={(e) => onChange("currency", e.target.value)}
        >
          {CURRENCIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        {currencyChanged && (
          <p className="mt-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
            Changing currency only affects new collections. Already-collected prices will still show their original currency.
          </p>
        )}
      </div>

      {/* Stops */}
      <div>
        <label className="field-label">Max Stops</label>
        <div className="flex gap-2 flex-wrap">
          {STOP_OPTIONS.map((opt) => (
            <button
              key={String(opt.value)}
              type="button"
              onClick={() => onChange("max_stops", opt.value)}
              className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                values.max_stops === opt.value
                  ? "border-brand-600 bg-brand-600 text-white"
                  : "border-slate-300 bg-white text-slate-700 hover:border-brand-400"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <p className="mt-1.5 text-xs text-slate-400">Filter results by number of stops. "Any" returns all flights.</p>
      </div>

      {/* Date range */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="field-label">Start Date <span className="text-slate-400">(optional, default: today)</span></label>
          <input
            type="date"
            className="field-input"
            value={values.start_date}
            onChange={(e) => onChange("start_date", e.target.value)}
          />
        </div>
        <div>
          <label className="field-label">End Date <span className="text-slate-400">(optional)</span></label>
          <input
            type="date"
            className="field-input"
            value={values.end_date}
            onChange={(e) => onChange("end_date", e.target.value)}
          />
        </div>
      </div>
    </div>
  );
}

// ── Quick-setup form ──────────────────────────────────────────────────────────

interface QuickState {
  origin: string;
  destination: string;
  nights: number;
  days_ahead: number;
  currency: string;
  max_stops: number | null;
  start_date: string;
  end_date: string;
}

function QuickForm({
  onSuccess,
  onClose,
}: {
  onSuccess: () => void;
  onClose: () => void;
}) {
  const { showToast } = useToast();
  const [form, setForm] = useState<QuickState>({
    origin: "",
    destination: "",
    nights: 10,
    days_ahead: 365,
    currency: "USD",
    max_stops: null,
    start_date: "",
    end_date: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resolved, setResolved] = useState<{
    origins: string[];
    destinations: string[];
    name: string;
  } | null>(null);
  const [showExtra, setShowExtra] = useState(false);

  function set<K extends keyof QuickState>(key: K, value: QuickState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
    setResolved(null);
    setError(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const res = await createRouteGroupFromText({
        origin: form.origin.trim(),
        destination: form.destination.trim(),
        nights: form.nights,
        days_ahead: form.days_ahead,
        currency: form.currency,
        max_stops: form.max_stops,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
      });
      setResolved({
        origins: res.resolved_origins,
        destinations: res.resolved_destinations,
        name: res.group.name,
      });
      showToast(`Created: ${res.group.name}`, "success");
      onSuccess();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Could not resolve location. Try a different name.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Route input */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <label className="field-label">From</label>
          <input
            className="field-input"
            value={form.origin}
            onChange={(e) => set("origin", e.target.value)}
            required
            placeholder="Canada"
            autoFocus
          />
        </div>
        <div className="mt-5 text-xl font-bold text-slate-400">→</div>
        <div className="flex-1">
          <label className="field-label">To</label>
          <input
            className="field-input"
            value={form.destination}
            onChange={(e) => set("destination", e.target.value)}
            required
            placeholder="Vietnam"
          />
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Type a country or city name. Examples: <em>Canada</em>, <em>Japan</em>,{" "}
        <em>Tokyo</em>, <em>Bali</em>, <em>London</em>.
        You can also combine: <em>Tokyo, Osaka</em> or use IATA codes directly:{" "}
        <em>YYZ, YVR</em>.
      </p>

      {/* Nights & Days ahead */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="field-label">Nights at destination</label>
          <input
            type="number"
            min={1}
            max={90}
            className="field-input"
            value={form.nights}
            onChange={(e) => set("nights", Number(e.target.value))}
            required
          />
          <p className="mt-1 text-xs text-slate-400">Duration of stay, e.g. 7</p>
        </div>
        <div>
          <label className="field-label">Days ahead to track</label>
          <input
            type="number"
            min={1}
            max={730}
            className="field-input"
            value={form.days_ahead}
            onChange={(e) => set("days_ahead", Number(e.target.value))}
            required
          />
          <p className="mt-1 text-xs text-slate-400">How far into the future to collect, e.g. 365</p>
        </div>
      </div>

      {/* Additional Options collapsible */}
      <div className="rounded-lg border border-slate-200">
        <button
          type="button"
          onClick={() => setShowExtra((v) => !v)}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          Additional Options
          {showExtra ? (
            <ChevronUp className="h-4 w-4 text-slate-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-400" />
          )}
        </button>
        {showExtra && (
          <div className="border-t border-slate-100 px-3 py-4">
            <ExtraOptionsFields
              values={{ currency: form.currency, max_stops: form.max_stops, start_date: form.start_date, end_date: form.end_date }}
              onChange={(key, value) => set(key as keyof QuickState, value as QuickState[typeof key])}
            />
          </div>
        )}
      </div>

      {/* Resolution preview */}
      {resolved && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm">
          <p className="font-medium text-green-800">{resolved.name}</p>
          <p className="mt-1 text-green-700">
            <span className="font-medium">Origins:</span>{" "}
            {resolved.origins.join(", ")}
          </p>
          <p className="text-green-700">
            <span className="font-medium">Destinations:</span>{" "}
            {resolved.destinations.join(", ")}
          </p>
        </div>
      )}

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      <div className="flex justify-end gap-2 pt-1">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={saving}>
          {resolved ? "Add another" : "Create route"}
        </Button>
      </div>
    </form>
  );
}

// ── Advanced form ─────────────────────────────────────────────────────────────

interface AdvancedState {
  name: string;
  destination_label: string;
  destinations: string[];
  origins: string[];
  nights: number;
  days_ahead: number;
  is_active: boolean;
  currency: string;
  max_stops: number | null;
  start_date: string;
  end_date: string;
}

function toAdvancedState(rg?: RouteGroup | null): AdvancedState {
  if (!rg) {
    return {
      name: "",
      destination_label: "",
      destinations: [],
      origins: [],
      nights: 12,
      days_ahead: 365,
      is_active: true,
      currency: "USD",
      max_stops: null,
      start_date: "",
      end_date: "",
    };
  }
  return {
    name: rg.name,
    destination_label: rg.destination_label,
    destinations: rg.destinations,
    origins: rg.origins,
    nights: rg.nights,
    days_ahead: rg.days_ahead,
    is_active: rg.is_active,
    currency: rg.currency ?? "USD",
    max_stops: rg.max_stops ?? null,
    start_date: rg.start_date ?? "",
    end_date: rg.end_date ?? "",
  };
}

function AdvancedForm({
  initial,
  onSuccess,
  onClose,
}: {
  initial?: RouteGroup | null;
  onSuccess: () => void;
  onClose: () => void;
}) {
  const { showToast } = useToast();
  const [form, setForm] = useState<AdvancedState>(() =>
    toAdvancedState(initial),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setForm(toAdvancedState(initial));
    setError(null);
  }, [initial]);

  function set<K extends keyof AdvancedState>(key: K, value: AdvancedState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (form.origins.length === 0 || form.destinations.length === 0) {
        setError("Add at least one origin and one destination airport.");
        setSaving(false);
        return;
      }
      const payload = {
        name: form.name.trim(),
        destination_label: form.destination_label.trim(),
        destinations: form.destinations,
        origins: form.origins,
        nights: form.nights,
        days_ahead: form.days_ahead,
        is_active: form.is_active,
        currency: form.currency,
        max_stops: form.max_stops,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
      };
      if (initial) {
        await updateRouteGroup(initial.id, payload);
      } else {
        await createRouteGroup(payload);
      }
      showToast("Route group saved", "success");
      onSuccess();
    } catch {
      setError("Failed to save. Please check your input and try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="field-label">Name</label>
        <input
          className="field-input"
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          required
          placeholder="CAD-Tokyo-Shanghai-CAD"
        />
        <p className="mt-1 text-xs text-slate-400">A unique identifier for this route group</p>
      </div>

      <div>
        <label className="field-label">Destination Label</label>
        <input
          className="field-input"
          value={form.destination_label}
          onChange={(e) => set("destination_label", e.target.value)}
          required
          placeholder="TYO/SHA"
        />
        <p className="mt-1 text-xs text-slate-400">Short display name shown in the UI, e.g. TYO/SHA</p>
      </div>

      <div>
        <label className="field-label">Origin airports</label>
        <TagInput
          value={form.origins}
          onChange={(tags) => set("origins", tags)}
          placeholder="YYZ, YVR…"
          hint="Type an IATA code and press Enter or comma to add"
        />
      </div>

      <div>
        <label className="field-label">Destination airports</label>
        <TagInput
          value={form.destinations}
          onChange={(tags) => set("destinations", tags)}
          placeholder="NRT, BKK…"
          hint="Type an IATA code and press Enter or comma to add"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="field-label">Nights</label>
          <input
            type="number"
            min={1}
            className="field-input"
            value={form.nights}
            onChange={(e) => set("nights", Number(e.target.value))}
            required
          />
          <p className="mt-1 text-xs text-slate-400">Duration of stay at destination</p>
        </div>
        <div>
          <label className="field-label">Days Ahead</label>
          <input
            type="number"
            min={1}
            className="field-input"
            value={form.days_ahead}
            onChange={(e) => set("days_ahead", Number(e.target.value))}
            required
          />
          <p className="mt-1 text-xs text-slate-400">How many future dates to collect prices for</p>
        </div>
      </div>

      <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={(e) => set("is_active", e.target.checked)}
          className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
        />
        Active
      </label>

      {/* Additional Options */}
      <div className="rounded-lg border border-slate-200 px-3 py-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Additional Options
        </p>
        <ExtraOptionsFields
          values={{ currency: form.currency, max_stops: form.max_stops, start_date: form.start_date, end_date: form.end_date }}
          onChange={(key, value) => set(key as keyof AdvancedState, value as AdvancedState[typeof key])}
          originalCurrency={initial?.currency}
        />
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={saving}>
          {initial ? "Save changes" : "Create"}
        </Button>
      </div>
    </form>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function RouteGroupForm({ open, onClose, initial }: RouteGroupFormProps) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"quick" | "advanced">(
    initial ? "advanced" : "quick",
  );

  async function handleSuccess() {
    await qc.invalidateQueries({ queryKey: ["route-groups"] });
    if (initial) {
      await qc.invalidateQueries({ queryKey: ["route-group", initial.id] });
      onClose();
    }
  }

  const title = initial ? "Edit Route Group" : "New Route Group";

  return (
    <Modal open={open} onClose={onClose} title={title}>
      {!initial && (
        <div className="mb-5 flex rounded-lg border border-slate-200 bg-slate-50 p-1">
          <button
            type="button"
            onClick={() => setTab("quick")}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === "quick"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Quick Setup
          </button>
          <button
            type="button"
            onClick={() => setTab("advanced")}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === "advanced"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Manual (IATA codes)
          </button>
        </div>
      )}

      {tab === "quick" && !initial ? (
        <QuickForm onSuccess={handleSuccess} onClose={onClose} />
      ) : (
        <AdvancedForm
          initial={initial}
          onSuccess={handleSuccess}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}
