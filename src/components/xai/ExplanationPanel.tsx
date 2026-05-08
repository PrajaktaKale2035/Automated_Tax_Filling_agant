import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LineExplanation {
  label: string;
  value: number;
  explanation: string;
}

interface ExplanationResult {
  regime: string;
  age_category: string;
  summary: string;
  lines: LineExplanation[];
}

interface WhatIfResult {
  base_tax_payable: number;
  new_tax_payable: number;
  tax_saved: number;
  explanation: string;
  changed_inputs: Record<string, number>;
}

interface RegimeCompare {
  old: { tax_payable: number; taxable_income: number };
  new: { tax_payable: number; taxable_income: number };
  recommendation: string;
  saving: number;
  recommendation_reason: string;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ExplanationPanelProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  /** Kept for backwards compatibility — shown as fallback summary text */
  content?: string;
  // Filing inputs used to call the XAI endpoints
  grossIncome?: number;
  deductions80c?: number;
  deductions80d?: number;
  regime?: "old" | "new";
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE =
  (import.meta as any).env?.VITE_API_BASE || "http://localhost:8000";

function fmt(value: number): string {
  return "₹" + Math.abs(value).toLocaleString("en-IN");
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ExplanationPanel = ({
  open,
  onOpenChange,
  content,
  grossIncome = 0,
  deductions80c = 0,
  deductions80d = 0,
  regime = "new",
}: ExplanationPanelProps) => {
  const [explanation, setExplanation] = useState<ExplanationResult | null>(null);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [expandedLine, setExpandedLine] = useState<string | null>(null);

  const [whatIfAmount, setWhatIfAmount] = useState<number>(0);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResult | null>(null);

  const [activeTab, setActiveTab] = useState<"breakdown" | "regime-compare">("breakdown");
  const [regimeCompare, setRegimeCompare] = useState<RegimeCompare | null>(null);
  const [loadingCompare, setLoadingCompare] = useState(false);

  // ----- fetch explanation on open -----
  useEffect(() => {
    if (!open) return;
    // Reset per-open state
    setExpandedLine(null);
    setWhatIfResult(null);
    setRegimeCompare(null);
    setActiveTab("breakdown");
    fetchExplanation();
  }, [open, grossIncome, deductions80c, deductions80d, regime]);

  async function fetchExplanation() {
    if (grossIncome === 0) return;
    setLoadingExplanation(true);
    try {
      const resp = await fetch(`${API_BASE}/api/v2/explain/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gross_income: grossIncome,
          deductions: {
            "80c": deductions80c,
            "80d": deductions80d,
          },
          regime,
          is_salary_income: true,
          fy: "2024-25",
        }),
      });
      if (resp.ok) {
        const data: ExplanationResult = await resp.json();
        setExplanation(data);
      }
    } catch {
      // Non-critical — panel shows fallback empty state
    } finally {
      setLoadingExplanation(false);
    }
  }

  async function handleWhatIf(amount: number) {
    if (!amount || grossIncome === 0) return;
    try {
      const resp = await fetch(`${API_BASE}/api/v2/explain/whatif`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gross_income: grossIncome,
          deductions: {
            "80c": deductions80c,
            "80d": deductions80d,
          },
          regime,
          is_salary_income: true,
          fy: "2024-25",
          whatif_deductions_80c: amount,
        }),
      });
      if (resp.ok) {
        const data: WhatIfResult = await resp.json();
        setWhatIfResult(data);
      }
    } catch {
      // ignore
    }
  }

  async function fetchRegimeCompare() {
    if (regimeCompare || grossIncome === 0) return;
    setLoadingCompare(true);
    try {
      const resp = await fetch(`${API_BASE}/api/v2/explain/regime-compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gross_income: grossIncome,
          deductions: {
            "80c": deductions80c,
            "80d": deductions80d,
          },
          regime,
          is_salary_income: true,
          fy: "2024-25",
        }),
      });
      if (resp.ok) {
        const data: RegimeCompare = await resp.json();
        setRegimeCompare(data);
      }
    } catch {
      // ignore
    } finally {
      setLoadingCompare(false);
    }
  }

  // ----- render -----
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Tax Explanation</DialogTitle>
        </DialogHeader>

        {/* Tab toggle */}
        <div className="flex gap-2 mb-3">
          <button
            className={`text-xs px-3 py-1 rounded-full transition-colors ${
              activeTab === "breakdown"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
            onClick={() => setActiveTab("breakdown")}
          >
            Breakdown
          </button>
          <button
            className={`text-xs px-3 py-1 rounded-full transition-colors ${
              activeTab === "regime-compare"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
            onClick={() => {
              setActiveTab("regime-compare");
              fetchRegimeCompare();
            }}
          >
            Compare Regimes
          </button>
        </div>

        <ScrollArea className="max-h-[60vh] pr-4">
          {/* ---- Breakdown tab ---- */}
          {activeTab === "breakdown" && (
            <div className="prose prose-sm dark:prose-invert">
              {loadingExplanation && (
                <p className="text-xs text-gray-400 animate-pulse">Loading explanation…</p>
              )}

              {!loadingExplanation && explanation && (
                <>
                  <p className="text-sm text-gray-700 mb-3">{explanation.summary}</p>

                  {/* Clickable line items */}
                  <div className="border rounded-md divide-y divide-gray-100 mb-4">
                    {explanation.lines.map((line) => (
                      <div key={line.label}>
                        <button
                          className="w-full flex justify-between items-center px-3 py-2 text-left hover:bg-gray-50 transition"
                          onClick={() =>
                            setExpandedLine(
                              expandedLine === line.label ? null : line.label
                            )
                          }
                          aria-expanded={expandedLine === line.label}
                        >
                          <span className="font-medium text-sm">{line.label}</span>
                          <span className="text-sm tabular-nums">
                            {line.value < 0 ? "−" : ""}
                            {fmt(line.value)}
                          </span>
                        </button>
                        {expandedLine === line.label && (
                          <div className="px-3 pb-3 pt-1 text-xs text-gray-600 bg-blue-50">
                            {line.explanation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* What-if section */}
                  <div className="border-t pt-4">
                    <h3 className="text-sm font-semibold mb-2">
                      What if you invest in 80C?
                    </h3>
                    <div className="flex gap-2 items-center">
                      <input
                        type="number"
                        placeholder="Amount (max ₹1,50,000)"
                        max={150000}
                        min={0}
                        className="border rounded px-2 py-1 text-sm flex-1"
                        value={whatIfAmount || ""}
                        onChange={(e) => {
                          const val = Number(e.target.value);
                          setWhatIfAmount(val);
                          handleWhatIf(val);
                        }}
                      />
                    </div>
                    {whatIfResult && (
                      <div className="mt-2 text-xs rounded p-2 bg-green-50 text-green-700">
                        <div className="mb-1">{whatIfResult.explanation}</div>
                        <div className="flex gap-4 tabular-nums">
                          <span>
                            Current tax:{" "}
                            <strong>{fmt(whatIfResult.base_tax_payable)}</strong>
                          </span>
                          <span>
                            New tax:{" "}
                            <strong>{fmt(whatIfResult.new_tax_payable)}</strong>
                          </span>
                          {whatIfResult.tax_saved > 0 && (
                            <span className="text-green-800 font-semibold">
                              Saves {fmt(whatIfResult.tax_saved)}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* Fallback to legacy content prop */}
              {!loadingExplanation && !explanation && content && (
                <>
                  <p>{content}</p>
                  <ul>
                    <li>Attribution to your inputs</li>
                    <li>Referenced rules and thresholds</li>
                    <li>Confidence and alternatives</li>
                  </ul>
                </>
              )}

              {!loadingExplanation && !explanation && !content && grossIncome === 0 && (
                <p className="text-xs text-gray-400">
                  Enter income details to see a line-by-line explanation.
                </p>
              )}
            </div>
          )}

          {/* ---- Compare Regimes tab ---- */}
          {activeTab === "regime-compare" && (
            <div>
              {loadingCompare && (
                <p className="text-xs text-gray-400 animate-pulse">Comparing regimes…</p>
              )}
              {!loadingCompare && regimeCompare && (
                <div className="space-y-3 text-sm">
                  <div className="border rounded-md divide-y divide-gray-100">
                    <div className="flex justify-between px-3 py-2">
                      <span className="text-gray-600">Old Regime — Taxable Income</span>
                      <span className="tabular-nums">
                        {fmt(regimeCompare.old.taxable_income)}
                      </span>
                    </div>
                    <div className="flex justify-between px-3 py-2">
                      <span className="text-gray-600">Old Regime — Tax Payable</span>
                      <span className="tabular-nums font-medium">
                        {fmt(regimeCompare.old.tax_payable)}
                      </span>
                    </div>
                    <div className="flex justify-between px-3 py-2">
                      <span className="text-gray-600">New Regime — Taxable Income</span>
                      <span className="tabular-nums">
                        {fmt(regimeCompare.new.taxable_income)}
                      </span>
                    </div>
                    <div className="flex justify-between px-3 py-2">
                      <span className="text-gray-600">New Regime — Tax Payable</span>
                      <span className="tabular-nums font-medium">
                        {fmt(regimeCompare.new.tax_payable)}
                      </span>
                    </div>
                  </div>

                  <div className="p-3 bg-green-50 rounded-md text-xs text-green-800">
                    <strong>
                      Recommendation:{" "}
                      {regimeCompare.recommendation === "new" ? "New" : "Old"} Regime
                    </strong>
                    <br />
                    {regimeCompare.recommendation_reason}
                  </div>
                </div>
              )}
              {!loadingCompare && !regimeCompare && grossIncome === 0 && (
                <p className="text-xs text-gray-400">
                  Enter income details to compare regimes.
                </p>
              )}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};

export default ExplanationPanel;
