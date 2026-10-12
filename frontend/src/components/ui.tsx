/** Small, accessible design-system primitives. */
import React from "react";

/* ---------------- Button ---------------- */
type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "success";
  size?: "sm" | "md";
  loading?: boolean;
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  className = "",
  children,
  disabled,
  ...rest
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 disabled:opacity-50 disabled:cursor-not-allowed";
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2 text-sm" };
  const variants = {
    primary: "bg-accent text-white hover:bg-accent-hover shadow-sm",
    secondary: "border border-surface-line bg-white text-ink-soft hover:bg-surface hover:text-ink",
    ghost: "text-ink-soft hover:bg-accent-soft hover:text-accent",
    danger: "border border-red-200 bg-white text-red-600 hover:bg-red-50",
    success: "bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm",
  };
  return (
    <button
      className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  );
}

/* ---------------- Card ---------------- */
export function Card({
  className = "",
  children,
  ...rest
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-xl border border-surface-line bg-white shadow-card ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardBody({ className = "", children }: { className?: string; children: React.ReactNode }) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}

/* ---------------- Badge ---------------- */
const badgeTones: Record<string, string> = {
  gray: "bg-slate-100 text-slate-600",
  blue: "bg-accent-soft text-accent",
  green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-700",
  red: "bg-red-50 text-red-600",
  violet: "bg-violet-50 text-violet-700",
};

export function Badge({
  tone = "gray",
  children,
  title,
}: {
  tone?: keyof typeof badgeTones;
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeTones[tone]}`}
    >
      {children}
    </span>
  );
}

/** Trust & activity signal badge — discovered vs reviewed vs verified. */
export function TrustBadge({ status, confidence }: { status: string; confidence?: number }) {
  const map: Record<string, { tone: keyof typeof badgeTones; label: string }> = {
    verified: { tone: "green", label: "Verified" },
    reviewed: { tone: "blue", label: "Reviewed" },
    discovered: { tone: "amber", label: "Discovered" },
  };
  const cfg = map[status] ?? map.discovered;
  return (
    <Badge tone={cfg.tone} title={`Source status: ${status}${confidence != null ? ` · confidence ${confidence}/100` : ""}`}>
      {status === "verified" ? "✓" : status === "reviewed" ? "◐" : "○"} {cfg.label}
      {confidence != null && <span className="opacity-70">· {Math.round(confidence)}</span>}
    </Badge>
  );
}

/* ---------------- Form fields ---------------- */
export function Field({
  label,
  htmlFor,
  error,
  hint,
  children,
}: {
  label: string;
  htmlFor?: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="label">
        {label}
      </label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-ink-faint">{hint}</p>}
      {error && <p className="mt-1 text-xs font-medium text-red-600">{error}</p>}
    </div>
  );
}

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = "", ...rest }, ref) {
    return <input ref={ref} className={`input ${className}`} {...rest} />;
  }
);

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className = "", ...rest }, ref) {
  return <textarea ref={ref} className={`input min-h-[96px] ${className}`} {...rest} />;
});

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className = "", children, ...rest }, ref) {
    return (
      <select ref={ref} className={`input ${className}`} {...rest}>
        {children}
      </select>
    );
  }
);

/* ---------------- Feedback ---------------- */
export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-ink-faint">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-surface-line bg-white/60 px-6 py-12 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      </div>
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      <p className="mx-auto mt-1 max-w-md text-sm text-ink-faint">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {message}
    </div>
  );
}

/* ---------------- Score bar ---------------- */
export function ScoreBar({
  label,
  value,
  weight,
  tone = "bg-accent",
}: {
  label: string;
  value: number;
  weight?: string;
  tone?: string;
}) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-xs">
        <span className="font-medium text-ink-soft">
          {label} {weight && <span className="text-ink-faint">({weight})</span>}
        </span>
        <span className="tabular-nums text-ink">{Math.round(value)}/100</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${tone} transition-all`}
          style={{ width: `${Math.max(3, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}

/* ---------------- Page header ---------------- */
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-ink-faint">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
