import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RagSource {
  score?: number;
  [key: string]: unknown;
}

interface TransparencyIndicatorProps {
  auditStatus?: string;
  auditErrors?: string[];
  ragSources?: RagSource[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type AuditColor = "green" | "amber" | "red";

function getAuditColor(
  status: string | undefined,
  errors: string[] | undefined
): AuditColor {
  if (errors && errors.length > 0) return "red";
  if (!status || status === "clean") return "green";
  return "amber";
}

const colorClass: Record<AuditColor, string> = {
  green: "bg-green-100 text-green-800 border-green-200",
  amber: "bg-amber-100 text-amber-800 border-amber-200",
  red: "bg-red-100 text-red-800 border-red-200",
};

const ShieldIcon: Record<AuditColor, typeof ShieldCheck> = {
  green: ShieldCheck,
  amber: ShieldAlert,
  red: ShieldX,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const TransparencyIndicator = ({
  auditStatus,
  auditErrors,
  ragSources,
}: TransparencyIndicatorProps = {}) => {
  const auditColor = getAuditColor(auditStatus, auditErrors);
  const Icon = ShieldIcon[auditColor];

  const ragConfidence =
    ragSources && ragSources.length > 0
      ? ragSources.reduce((sum, s) => sum + (s.score ?? 0), 0) / ragSources.length
      : null;

  const auditLabel =
    auditColor === "green"
      ? "Audit Clean"
      : auditColor === "red"
      ? `${auditErrors?.length ?? 1} Audit Issue${(auditErrors?.length ?? 1) !== 1 ? "s" : ""}`
      : "Review Pending";

  return (
    <div className="flex flex-col gap-1">
      {/* Audit status badge */}
      <div
        className={`inline-flex items-center gap-1.5 px-2 py-1 rounded border text-xs font-medium ${colorClass[auditColor]}`}
        role="status"
        aria-label={`Audit status: ${auditLabel}`}
      >
        <Icon className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
        <span>{auditLabel}</span>
      </div>

      {/* Audit error list */}
      {auditColor === "red" && auditErrors && auditErrors.length > 0 && (
        <ul className="text-xs text-red-700 list-disc list-inside space-y-0.5 pl-1">
          {auditErrors.map((err, i) => (
            <li key={i}>{err}</li>
          ))}
        </ul>
      )}

      {/* RAG confidence */}
      {ragConfidence !== null && (
        <div className="text-xs text-gray-500">
          RAG Confidence:{" "}
          <span className="font-medium">{(ragConfidence * 100).toFixed(0)}%</span>
          {" "}({ragSources!.length} source{ragSources!.length !== 1 ? "s" : ""})
        </div>
      )}

      {/* Fallback label when no props passed (backward-compat) */}
      {!auditStatus && !auditErrors && !ragSources && (
        <div className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-2 py-1 text-xs text-muted-foreground">
          <ShieldCheck className="h-4 w-4 text-accent" />
          Transparent AI
        </div>
      )}
    </div>
  );
};

export default TransparencyIndicator;
