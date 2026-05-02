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
      <Button @click="$router.push('/filing/new')">Create your first filing</Button>
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
import { Printer } from 'lucide-vue-next'
import BackButton from '@/components-vue/navigation/BackButton.vue'
import Button from '@/components-vue/ui/Button.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import { useAuthStore } from '@/stores/authStore'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
const authStore = useAuthStore()

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

const filing = computed<ITR1Filing | null>(() =>
  filings.value.find(f => f.id === selectedFilingId.value) || null,
)

const standardDeduction = computed(() => {
  if (!filing.value) return 0
  return filing.value.regime === 'new' ? 75_000 : 50_000
})

const refresh = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const userId = authStore.user?.id
    const url = userId
      ? `${API_BASE}/api/v2/filings?user_id=${userId}`
      : `${API_BASE}/api/v2/filings`
    const resp = await fetch(url)
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
    const resp = await fetch(`${API_BASE}/api/v2/filing/${id}/json`)
    if (resp.ok) json.value = await resp.json()
  } catch {
    /* swallow - cards still render summary fields */
  }
}

watch(selectedFilingId, (id) => { if (id) fetchJson(id) })

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
