<template>
  <div class="p-8 space-y-8">
    <div class="flex justify-between items-center print:hidden">
      <div class="flex items-center gap-4">
        <BackButton />
        <h1 class="text-3xl font-bold">Tax Report</h1>
      </div>
      <div class="flex gap-2">
        <select
          v-model.number="selectedFilingId"
          class="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option v-if="!filings.length" :value="null">No filings yet</option>
          <option v-for="f in filings" :key="f.id" :value="f.id">
            #{{ f.id }} - AY {{ f.assessment_year }} ({{ f.regime }})
          </option>
        </select>
        <Button variant="outline" @click="refresh">Refresh</Button>
        <Button variant="outline" @click="exportReport" :disabled="!filing">
          <Download class="mr-2 h-4 w-4" />
          Export Report
        </Button>
        <Button variant="outline" @click="printReport" :disabled="!filing">
          <Printer class="mr-2 h-4 w-4" />
          Print
        </Button>
      </div>
    </div>

    <!-- Loading / errors / empty states -->
    <div v-if="loading" class="text-center py-16 text-muted-foreground">Loading filings...</div>
    <div v-else-if="loadError" class="rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
      {{ loadError }}
    </div>
    <div v-else-if="!filing" class="rounded-md border bg-muted/30 p-8 text-center">
      <p class="text-muted-foreground mb-4">
        No ITR-1 filings found in the system. Reports here are populated from your real filings.
      </p>
      <Button @click="router.push('/filing/new')">Create your first filing</Button>
    </div>

    <!-- Real report content -->
    <div v-else class="space-y-6 print:space-y-4" id="printable-report">
      <div class="hidden print:block text-center mb-8 border-b pb-4">
        <h1 class="text-2xl font-bold">ITR-1 (Sahaj) Tax Computation</h1>
        <p class="text-sm text-gray-500">Filing #{{ filing.id }} - Assessment Year {{ filing.assessment_year }} - {{ filing.regime.toUpperCase() }} regime</p>
      </div>

      <!-- Summary cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 print:grid-cols-4">
        <Card class="bg-blue-50/50 border-blue-100">
          <CardHeader>
            <CardTitle class="text-sm font-medium text-blue-600">Gross Income</CardTitle>
            <div class="text-2xl font-bold text-blue-900">&#8377;{{ filing.gross_income.toLocaleString('en-IN') }}</div>
          </CardHeader>
        </Card>
        <Card class="bg-purple-50/50 border-purple-100">
          <CardHeader>
            <CardTitle class="text-sm font-medium text-purple-600">Taxable Income</CardTitle>
            <div class="text-2xl font-bold text-purple-900">&#8377;{{ filing.taxable_income.toLocaleString('en-IN') }}</div>
          </CardHeader>
        </Card>
        <Card class="bg-green-50/50 border-green-100">
          <CardHeader>
            <CardTitle class="text-sm font-medium text-green-600">Total Tax</CardTitle>
            <div class="text-2xl font-bold text-green-900">&#8377;{{ filing.total_tax.toLocaleString('en-IN') }}</div>
          </CardHeader>
        </Card>
        <Card :class="filing.tax_due > 0 ? 'bg-red-50/50 border-red-100' : 'bg-emerald-50/50 border-emerald-100'">
          <CardHeader>
            <CardTitle :class="['text-sm font-medium', filing.tax_due > 0 ? 'text-red-600' : 'text-emerald-600']">
              {{ filing.tax_due > 0 ? 'Tax Due' : 'Refund' }}
            </CardTitle>
            <div :class="['text-2xl font-bold', filing.tax_due > 0 ? 'text-red-900' : 'text-emerald-900']">
              &#8377;{{ Math.max(filing.tax_due, filing.refund_due).toLocaleString('en-IN') }}
            </div>
          </CardHeader>
        </Card>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 print:grid-cols-2">
        <!-- Income breakdown - from itr1_json -->
        <Card>
          <CardHeader>
            <CardTitle>Income from Salary</CardTitle>
          </CardHeader>
          <CardContent>
            <div class="space-y-3">
              <Row label="Gross Salary" :value="filing.gross_income" />
              <Row label="Less: Standard Deduction" :value="standardDeduction" :negative="true" />
              <template v-if="filing.regime === 'old'">
                <Row label="Less: Section 80C" :value="json?.deductions?.section80C || 0" :negative="true" />
                <Row label="Less: Section 80D" :value="json?.deductions?.section80D || 0" :negative="true" />
              </template>
              <div class="flex justify-between pt-3 border-t font-semibold">
                <span>Taxable Income</span>
                <span>&#8377;{{ filing.taxable_income.toLocaleString('en-IN') }}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Tax computation breakdown -->
        <Card>
          <CardHeader>
            <CardTitle>Tax Computation ({{ filing.regime.toUpperCase() }} regime)</CardTitle>
          </CardHeader>
          <CardContent>
            <div class="space-y-3">
              <Row label="Slab Tax" :value="json?.taxComputation?.slabTax || 0" />
              <Row label="Less: Rebate u/s 87A" :value="json?.taxComputation?.rebate87A || 0" :negative="true" />
              <Row label="Surcharge" :value="json?.taxComputation?.surcharge || 0" />
              <Row label="Health & Education Cess (4%)" :value="json?.taxComputation?.cess || 0" />
              <div class="flex justify-between pt-3 border-t font-semibold text-primary">
                <span>Total Tax Liability</span>
                <span>&#8377;{{ filing.total_tax.toLocaleString('en-IN') }}</span>
              </div>
              <Row label="TDS Paid" :value="filing.tds_paid" :negative="true" />
              <div class="flex justify-between pt-3 border-t font-semibold">
                <span>{{ filing.tax_due > 0 ? 'Tax Due' : 'Refund' }}</span>
                <span :class="filing.tax_due > 0 ? 'text-red-600' : 'text-green-600'">
                  &#8377;{{ Math.max(filing.tax_due, filing.refund_due).toLocaleString('en-IN') }}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- XAI Explanation Panel -->
      <Card class="print:hidden">
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle>Tax Explanation (AI)</CardTitle>
            <div class="flex gap-2">
              <button
                @click="xaiTab = 'breakdown'"
                :class="['text-xs px-3 py-1 rounded-full transition-colors', xaiTab === 'breakdown' ? 'bg-primary text-white' : 'bg-muted hover:bg-muted/80']"
              >Breakdown</button>
              <button
                @click="fetchRegimeCompare(); xaiTab = 'compare'"
                :class="['text-xs px-3 py-1 rounded-full transition-colors', xaiTab === 'compare' ? 'bg-primary text-white' : 'bg-muted hover:bg-muted/80']"
              >Compare Regimes</button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div v-if="xaiLoading" class="text-sm text-muted-foreground py-2">Loading explanation…</div>
          <div v-else-if="xaiTab === 'breakdown' && xaiResult">
            <p class="text-sm text-muted-foreground mb-3">{{ xaiResult.summary }}</p>
            <div v-for="line in xaiResult.lines" :key="line.label" class="border-b last:border-0">
              <button
                class="w-full flex justify-between items-center py-2 text-left hover:bg-muted/40 transition-colors px-1 rounded"
                @click="xaiExpanded = xaiExpanded === line.label ? null : line.label"
              >
                <span class="text-sm font-medium">{{ line.label }}</span>
                <span class="text-sm tabular-nums">{{ line.value < 0 ? '−' : '' }}₹{{ Math.abs(line.value).toLocaleString('en-IN') }}</span>
              </button>
              <div v-if="xaiExpanded === line.label" class="text-xs text-muted-foreground bg-blue-50 dark:bg-blue-950/20 rounded p-2 mb-1">
                {{ line.explanation }}
              </div>
            </div>
            <!-- What-if 80C -->
            <div class="mt-4 pt-3 border-t">
              <p class="text-sm font-medium mb-2">What if you invest in 80C?</p>
              <div class="flex gap-2">
                <input
                  v-model.number="whatif80c"
                  type="number"
                  placeholder="Amount (max ₹1,50,000)"
                  class="border rounded px-2 py-1 text-sm flex-1 bg-background"
                  :max="150000"
                  @change="fetchWhatIf"
                />
              </div>
              <div v-if="whatifResult" class="mt-2 text-xs text-green-700 bg-green-50 rounded p-2">
                {{ whatifResult.explanation }}
              </div>
            </div>
          </div>
          <div v-else-if="xaiTab === 'compare' && regimeCompare" class="space-y-2 text-sm">
            <div class="flex justify-between py-1"><span>Old Regime Tax</span><span class="font-medium">₹{{ regimeCompare.old.tax_payable.toLocaleString('en-IN') }}</span></div>
            <div class="flex justify-between py-1"><span>New Regime Tax</span><span class="font-medium">₹{{ regimeCompare.new.tax_payable.toLocaleString('en-IN') }}</span></div>
            <div class="mt-2 p-3 bg-green-50 dark:bg-green-950/20 rounded text-xs text-green-800 dark:text-green-300">
              <strong>Recommended: {{ regimeCompare.recommendation }} regime</strong><br/>{{ regimeCompare.recommendation_reason }}
            </div>
          </div>
          <div v-else class="text-sm text-muted-foreground">Select a filing to see AI explanation.</div>
        </CardContent>
      </Card>

      <Card class="border-primary/20 bg-primary/5 print:hidden">
        <CardHeader>
          <CardTitle class="text-sm">Filing Metadata</CardTitle>
        </CardHeader>
        <CardContent class="text-sm text-muted-foreground space-y-1">
          <div>Filing ID: <span class="font-mono">{{ filing.id }}</span></div>
          <div>Status: <span class="font-mono">{{ filing.status }}</span></div>
          <div>Created: {{ filing.created_at ? new Date(filing.created_at).toLocaleString('en-IN') : '-' }}</div>
          <div v-if="filing.form16_id">Source Form 16: #{{ filing.form16_id }}</div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Printer, Download } from 'lucide-vue-next'
import BackButton from '@/components-vue/navigation/BackButton.vue'
import Button from '@/components-vue/ui/Button.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import { useAuthStore } from '@/stores/authStore'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
const authStore = useAuthStore()
const router = useRouter()

interface ITR1Filing {
  id: number
  user_id: number
  form16_id: number | null
  assessment_year: string
  regime: 'old' | 'new'
  status: string
  gross_income: number
  taxable_income: number
  total_tax: number
  tds_paid: number
  refund_due: number
  tax_due: number
  pdf_path: string | null
  created_at: string | null
}

const filings = ref<ITR1Filing[]>([])
const selectedFilingId = ref<number | null>(null)
const loading = ref(true)
const loadError = ref('')
const json = ref<any>(null)

// XAI state
const xaiResult = ref<any>(null)
const xaiLoading = ref(false)
const xaiExpanded = ref<string | null>(null)
const xaiTab = ref<'breakdown' | 'compare'>('breakdown')
const whatif80c = ref<number | null>(null)
const whatifResult = ref<any>(null)
const regimeCompare = ref<any>(null)

const filing = computed<ITR1Filing | null>(() =>
  filings.value.find(f => f.id === selectedFilingId.value) || null,
)

const standardDeduction = computed(() => {
  if (!filing.value) return 0
  return filing.value.regime === 'new' ? 75_000 : 50_000
})

const authHeaders = () => ({
  Authorization: `Bearer ${authStore.token}`,
})

const refresh = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const userId = authStore.user?.id
    const url = userId
      ? `${API_BASE}/api/v2/filings?user_id=${userId}`
      : `${API_BASE}/api/v2/filings`
    const resp = await fetch(url, { headers: authHeaders() })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    filings.value = await resp.json()
    if (filings.value.length && !selectedFilingId.value) {
      selectedFilingId.value = filings.value[0].id
    }
  } catch (e: any) {
    loadError.value = e.message || 'Failed to load filings'
  } finally {
    loading.value = false
  }
}

const fetchJson = async (id: number) => {
  json.value = null
  try {
    const resp = await fetch(`${API_BASE}/api/v2/filing/${id}/json`, { headers: authHeaders() })
    if (resp.ok) json.value = await resp.json()
  } catch {
    /* swallow - cards still render summary fields */
  }
}

// Derive FY from assessment year string (e.g. "2025-26" → "2024-25")
const toFy = (ay: string): string => {
  const m = ay.match(/^(\d{4})-\d{2}$/)
  if (!m) return '2024-25'
  const startYear = Number(m[1]) - 1
  return `${startYear}-${String(startYear + 1).slice(-2)}`
}

const fetchXai = async (f: ITR1Filing) => {
  xaiResult.value = null
  xaiLoading.value = true
  try {
    const resp = await fetch(`${API_BASE}/api/v2/explain/`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gross_income: f.gross_income,
        deductions: {},
        regime: f.regime,
        fy: toFy(f.assessment_year || '2025-26'),
      }),
    })
    if (resp.ok) xaiResult.value = await resp.json()
  } catch { /* swallow */ } finally { xaiLoading.value = false }
}

const exportReport = () => {
  if (!filing.value) return
  const data = {
    filing_id: filing.value.id,
    assessment_year: filing.value.assessment_year,
    regime: filing.value.regime,
    status: filing.value.status,
    gross_income: filing.value.gross_income,
    taxable_income: filing.value.taxable_income,
    total_tax: filing.value.total_tax,
    tds_paid: filing.value.tds_paid,
    tax_due: filing.value.tax_due,
    refund_due: filing.value.refund_due,
    standard_deduction: standardDeduction.value,
    itr1_json: json.value ?? null,
    xai_explanation: xaiResult.value ?? null,
    regime_compare: regimeCompare.value ?? null,
    exported_at: new Date().toISOString(),
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `TaxReport-AY${filing.value.assessment_year}-filing${filing.value.id}.json`
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

const fetchWhatIf = async () => {
  if (!filing.value || !whatif80c.value) return
  try {
    const resp = await fetch(`${API_BASE}/api/v2/explain/whatif`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ gross_income: filing.value.gross_income, deductions: {}, regime: filing.value.regime, whatif_deductions_80c: whatif80c.value }),
    })
    if (resp.ok) whatifResult.value = await resp.json()
  } catch { /* swallow */ }
}

const fetchRegimeCompare = async () => {
  if (!filing.value || regimeCompare.value) return
  try {
    const resp = await fetch(`${API_BASE}/api/v2/explain/regime-compare`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ gross_income: filing.value.gross_income, deductions: {}, regime: filing.value.regime }),
    })
    if (resp.ok) regimeCompare.value = await resp.json()
  } catch { /* swallow */ }
}

watch(selectedFilingId, (id) => {
  if (id) {
    fetchJson(id)
    const f = filings.value.find(x => x.id === id)
    if (f) fetchXai(f)
    regimeCompare.value = null
    whatifResult.value = null
  }
})

const printReport = () => window.print()

onMounted(refresh)

// Inline row helper.
const Row = (props: { label: string; value: number; negative?: boolean }) =>
  h('div', { class: 'flex justify-between items-center text-sm' }, [
    h('span', { class: 'text-muted-foreground' }, props.label),
    h('span', { class: 'font-medium' },
      `${props.negative && props.value > 0 ? '- ' : ''}\u20B9${Number(props.value || 0).toLocaleString('en-IN')}`),
  ])
</script>

<style scoped>
@media print {
  @page { margin: 2cm; }
}
</style>
