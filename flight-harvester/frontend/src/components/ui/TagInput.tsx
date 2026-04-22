import { useRef, useState } from "react";
import { X } from "lucide-react";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  hint?: string;
}

const IATA_RE = /^[A-Za-z]{2,4}$/;

export function TagInput({ value, onChange, placeholder = "e.g. YYZ", hint }: TagInputProps) {
  const [input, setInput] = useState("");
  const [invalid, setInvalid] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  function tryAdd(raw: string) {
    const code = raw.trim().toUpperCase();
    if (!code) return;
    if (!IATA_RE.test(code)) {
      setInvalid(true);
      return;
    }
    setInvalid(false);
    if (!value.includes(code)) {
      onChange([...value, code]);
    }
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === "," || e.key === "Tab") {
      e.preventDefault();
      tryAdd(input);
    } else if (e.key === "Backspace" && input === "" && value.length > 0) {
      onChange(value.slice(0, -1));
    } else {
      setInvalid(false);
    }
  }

  function handleBlur() {
    if (input.trim()) tryAdd(input);
  }

  function remove(tag: string) {
    onChange(value.filter((t) => t !== tag));
  }

  return (
    <div>
      <div
        ref={containerRef}
        onClick={() => containerRef.current?.querySelector("input")?.focus()}
        className={[
          "mt-1 flex min-h-[2.375rem] w-full flex-wrap gap-1.5 rounded-lg border bg-white px-3 py-2 text-sm shadow-sm",
          "cursor-text focus-within:border-brand-500 focus-within:ring-1 focus-within:ring-brand-500",
          invalid ? "border-red-400" : "border-slate-300",
        ].join(" ")}
      >
        {value.map((tag) => (
          <span
            key={tag}
            className="flex items-center gap-1 rounded-md bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700"
          >
            {tag}
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); remove(tag); }}
              className="rounded hover:text-brand-900"
              aria-label={`Remove ${tag}`}
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          value={input}
          onChange={(e) => { setInput(e.target.value); setInvalid(false); }}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder={value.length === 0 ? placeholder : ""}
          className="min-w-[80px] flex-1 bg-transparent outline-none placeholder-slate-400"
        />
      </div>
      {invalid && (
        <p className="mt-1 text-xs text-red-500">Enter a valid IATA code (2–4 letters), then press Enter or comma.</p>
      )}
      {!invalid && hint && (
        <p className="mt-1 text-xs text-slate-400">{hint}</p>
      )}
    </div>
  );
}
