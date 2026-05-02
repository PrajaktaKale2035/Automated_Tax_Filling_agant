import type { Tool } from '../types';

// ---------------------------------------------------------------------------
// Indian tax calculation tools (Phase 4).
//
// All actual tax math runs on the backend (`tax_engine_in.py`) so the same
// numbers are used for the live preview, the LangGraph calculator node, the
// PDF, and the ITR-1 JSON output. The frontend never recomputes Indian slabs.
//
// Backend endpoint: POST /api/v2/calc/preview
//   body: { gross_income, deductions, regime, is_salary_income, fy }
//   returns TaxBreakdown {
//     regime, fy, gross_income, deductions_applied, taxable_income,
//     slab_tax, rebate_87a, tax_after_rebate, surcharge, cess, total_tax
//   }
// ---------------------------------------------------------------------------

const API_BASE =
  (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE) ||
  'http://localhost:8000';

async function calcPreview(body: {
  gross_income: number;
  deductions?: Record<string, number>;
  regime: 'old' | 'new';
  is_salary_income?: boolean;
  fy?: string;
}) {
  const resp = await fetch(`${API_BASE}/api/v2/calc/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      gross_income: body.gross_income,
      deductions: body.deductions || {},
      regime: body.regime,
      is_salary_income: body.is_salary_income ?? true,
      fy: body.fy ?? '2024-25',
    }),
  });
  if (!resp.ok) {
    throw new Error(`calc/preview failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

const fmt = (n: number) =>
  '\u20B9 ' + new Intl.NumberFormat('en-IN').format(Math.round(n));

export const taxCalculationTools: Tool[] = [
  {
    name: 'calculate_income_tax',
    description:
      'Calculate Indian income tax for a salaried individual under either the old or new regime. ' +
      'Wraps the backend tax engine - applies slabs, standard deduction, 80C/80D (old regime), ' +
      'rebate u/s 87A, surcharge, and 4% cess.',
    parameters: [
      { name: 'grossIncome', type: 'number', description: 'Gross salary income in INR', required: true },
      { name: 'regime', type: 'string', description: '"old" or "new"', required: true },
      { name: 'deductions80c', type: 'number', description: 'Section 80C investments (old regime only)', required: false },
      { name: 'deductions80d', type: 'number', description: 'Section 80D health insurance (old regime only)', required: false },
    ],
    execute: async (params: Record<string, any>) => {
      const { grossIncome, regime, deductions80c, deductions80d } = params;
      const breakdown = await calcPreview({
        gross_income: grossIncome,
        regime,
        deductions: {
          '80c': deductions80c || 0,
          '80d': deductions80d || 0,
        },
      });
      return {
        grossIncome: fmt(breakdown.gross_income),
        taxableIncome: fmt(breakdown.taxable_income),
        slabTax: fmt(breakdown.slab_tax),
        rebate87A: fmt(breakdown.rebate_87a),
        surcharge: fmt(breakdown.surcharge),
        cess: fmt(breakdown.cess),
        totalTax: fmt(breakdown.total_tax),
        regime,
        fy: breakdown.fy,
        raw: breakdown,
      };
    },
  },

  {
    name: 'compare_regimes',
    description:
      'Compute tax under BOTH old and new regimes for the same income/deductions and pick the lower one. ' +
      'Use this when the user is undecided about regime choice.',
    parameters: [
      { name: 'grossIncome', type: 'number', description: 'Gross salary income in INR', required: true },
      { name: 'deductions80c', type: 'number', description: 'Section 80C investments', required: false },
      { name: 'deductions80d', type: 'number', description: 'Section 80D health insurance', required: false },
    ],
    execute: async (params: Record<string, any>) => {
      const { grossIncome, deductions80c, deductions80d } = params;
      const deductions = {
        '80c': deductions80c || 0,
        '80d': deductions80d || 0,
      };
      const [oldR, newR] = await Promise.all([
        calcPreview({ gross_income: grossIncome, regime: 'old', deductions }),
        calcPreview({ gross_income: grossIncome, regime: 'new', deductions }),
      ]);
      const better = oldR.total_tax < newR.total_tax ? 'old' : 'new';
      const savings = Math.abs(oldR.total_tax - newR.total_tax);
      return {
        old: { totalTax: fmt(oldR.total_tax), raw: oldR },
        new: { totalTax: fmt(newR.total_tax), raw: newR },
        recommendedRegime: better,
        savingsIfChoosingRecommended: fmt(savings),
      };
    },
  },

  {
    name: 'taxable_income_after_deductions',
    description:
      'Convenience tool: returns taxable income after applying standard deduction and (in old regime) ' +
      '80C/80D. Calls the backend so the rules stay aligned with the engine.',
    parameters: [
      { name: 'grossIncome', type: 'number', description: 'Gross salary income in INR', required: true },
      { name: 'regime', type: 'string', description: '"old" or "new"', required: true },
      { name: 'deductions80c', type: 'number', description: '80C investments (old only)', required: false },
      { name: 'deductions80d', type: 'number', description: '80D premium (old only)', required: false },
    ],
    execute: async (params: Record<string, any>) => {
      const breakdown = await calcPreview({
        gross_income: params.grossIncome,
        regime: params.regime,
        deductions: {
          '80c': params.deductions80c || 0,
          '80d': params.deductions80d || 0,
        },
      });
      return {
        grossIncome: fmt(breakdown.gross_income),
        deductionsApplied: breakdown.deductions_applied,
        taxableIncome: fmt(breakdown.taxable_income),
      };
    },
  },

  {
    name: 'compare_scenarios',
    description: 'Compare multiple Indian tax scenarios side by side and pick the lowest-tax option.',
    parameters: [
      {
        name: 'scenarios',
        type: 'array',
        description:
          'Array of {name, grossIncome, regime, deductions80c?, deductions80d?} objects to evaluate.',
        required: true,
      },
    ],
    execute: async (params: Record<string, any>) => {
      const { scenarios } = params as {
        scenarios: Array<{
          name?: string;
          grossIncome: number;
          regime: 'old' | 'new';
          deductions80c?: number;
          deductions80d?: number;
        }>;
      };
      const evaluated = await Promise.all(
        scenarios.map(async (s, i) => {
          const breakdown = await calcPreview({
            gross_income: s.grossIncome,
            regime: s.regime,
            deductions: { '80c': s.deductions80c || 0, '80d': s.deductions80d || 0 },
          });
          return {
            name: s.name || `Scenario ${i + 1}`,
            regime: s.regime,
            grossIncome: fmt(s.grossIncome),
            taxableIncome: fmt(breakdown.taxable_income),
            totalTax: fmt(breakdown.total_tax),
            rawTotalTax: breakdown.total_tax,
          };
        }),
      );
      const best = evaluated.reduce((b, c) => (c.rawTotalTax < b.rawTotalTax ? c : b));
      const worst = evaluated.reduce((w, c) => (c.rawTotalTax > w.rawTotalTax ? c : w));
      return {
        comparisons: evaluated.map(({ rawTotalTax, ...rest }) => rest),
        bestScenario: best.name,
        potentialSavings: fmt(worst.rawTotalTax - best.rawTotalTax),
      };
    },
  },
];
