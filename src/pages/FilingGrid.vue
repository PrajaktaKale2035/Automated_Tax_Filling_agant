<template>
  <DynamicLayoutContainer>
    <div class="max-w-7xl mx-auto space-y-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <BackButton />
          <div>
            <h1 class="text-2xl font-bold">Expert Filing Mode</h1>
            <p class="text-sm text-muted-foreground">Direct entry for ITR-1 (FY 2024-25 / AY 2025-26)</p>
          </div>
        </div>
        <div class="flex gap-2">
          <Button variant="outline" :disabled="submitting" @click="recomputeNow">Recompute</Button>
          <Button :disabled="submitting" @click="submitFiling">
            {{ submitting ? 'Submitting...' : 'Validate & File' }}
          </Button>
        </div>
      </div>

      <div class="flex gap-2">
        <button
          @click="formData.regime = 'old'"
          :class="cn('px-3 py-1 rounded-full text-xs border',
            formData.regime === 'old' ? 'bg-primary text-primary-foreground border-primary' : 'border-input')"
        >Old regime</button>
        <button
          @click="formData.regime = 'new'"
          :class="cn('px-3 py-1 rounded-full text-xs border',
            formData.regime === 'new' ? 'bg-primary text-primary-foreground border-primary' : 'border-input')"
        >New regime</button>
      </div>

      <!-- Tabs -->
      <div class="flex border-b overflow-x-auto">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="cn(
            'px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
            activeTab === tab.id ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
          )"
        >
          {{ tab.label }}
        </button>
      </div>

      <Card class="min-h-[500px]">
        <CardContent class="p-6">
          <!-- General -->
          <div v-if="activeTab === 'general'" class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="space-y-2">
              <Label>First Name</Label>
              <Input v-model="formData.general.firstName" />
            </div>
            <div class="space-y-2">
              <Label>Middle Name</Label>
              <Input v-model="formData.general.middleName" />
            </div>
            <div class="space-y-2">
              <Label>Last Name</Label>
              <Input v-model="formData.general.lastName" />
            </div>
            <div class="space-y-2">
              <Label>PAN</Label>
              <Input v-model="formData.general.pan" />
            </div>
            <div class="space-y-2">
              <Label>Aadhaar Number</Label>
              <Input v-model="formData.general.aadhaar" />
            </div>
            <div class="space-y-2">
              <Label>Date of Birth</Label>
              <Input type="date" v-model="formData.general.dob" />
            </div>
          </div>

          <!-- Salary -->
          <div v-if="activeTab === 'salary'" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div class="space-y-2">
                <Label>Gross Salary u/s 17(1)</Label>
                <Input type="number" v-model.number="formData.salary.gross" />
              </div>
              <div class="space-y-2">
                <Label>TDS deducted</Label>
                <Input type="number" v-model.number="formData.salary.tds" />
              </div>
            </div>
            <p class="text-xs text-muted-foreground">
              Indian ITR-1 doesn't include perquisites / profits in lieu separately at this granularity. Bundle them into Gross Salary above.
            </p>
          </div>

          <!-- Deductions -->
          <div v-if="activeTab === 'deductions'" class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div v-if="formData.regime === 'new'" class="md:col-span-2 p-3 rounded bg-blue-50 text-blue-700 text-sm">
              New regime: deductions below are ignored by the tax engine. Standard deduction (Rs 75,000) is applied automatically.
            </div>
            <div class="space-y-2">
              <Label>80C (PPF, ELSS, LIC, ...)</Label>
              <Input type="number" v-model.number="formData.deductions.section80c" />
              <p class="text-xs text-muted-foreground">Cap Rs 1,50,000 (engine caps automatically).</p>
            </div>
            <div class="space-y-2">
              <Label>80D (Health insurance)</Label>
              <Input type="number" v-model.number="formData.deductions.section80d" />
              <p class="text-xs text-muted-foreground">Cap Rs 25,000 self / Rs 50,000 senior.</p>
            </div>
          </div>

          <!-- Tax computation: real, from backend -->
          <div v-if="activeTab === 'taxes'" class="space-y-4">
            <div v-if="previewError" class="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
              {{ previewError }}
            </div>
            <div v-else-if="previewLoading" class="text-center py-8 text-muted-foreground">
              Calling tax engine...
            </div>
            <div v-else-if="preview" class="bg-muted p-4 rounded-lg space-y-2">
              <Row label="Regime" :raw="preview.regime.toUpperCase()" />
              <Row label="FY" :raw="preview.fy" />
              <Row label="Gross Income" :value="preview.gross_income" />
              <Row label="Taxable Income" :value="preview.taxable_income" />
              <Row label="Slab Tax" :value="preview.slab_tax" />
              <Row label="Rebate u/s 87A" :value="preview.rebate_87a" :negative="true" />
              <Row label="Surcharge" :value="preview.surcharge" />
              <Row label="Cess (4%)" :value="preview.cess" />
              <div class="flex justify-between pt-3 mt-3 border-t font-semibold">
                <span>Total Tax</span>
                <span class="font-mono">&#8377;{{ preview.total_tax.toLocaleString('en-IN') }}</span>
              </div>
              <Row label="TDS already paid" :value="formData.salary.tds" :negative="true" />
              <div class="flex justify-between pt-2 border-t">
                <span class="font-semibold">{{ netDue >= 0 ? 'Tax Due' : 'Refund' }}</span>
                <span :class="cn('font-mono font-bold', netDue > 0 ? 'text-red-600' : 'text-green-600')">
                  &#8377;{{ Math.abs(netDue).toLocaleString('en-IN') }}
                </span>
              </div>
            </div>
            <div v-if="submitError" class="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
              {{ submitError }}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </DynamicLayoutContainer>
</template>

<script setup lang="ts">
import { computed, h, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { cn } from '@/lib/utils'
import DynamicLayoutContainer from '@/components-vue/dynamic/DynamicLayoutContainer.vue'
import BackButton from '@/components-vue/navigation/BackButton.vue'
import Button from '@/components-vue/ui/Button.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Input from '@/components-vue/ui/Input.vue'
import Label from '@/components-vue/ui/Label.vue'
import { useAuthStore } from '@/stores/authStore'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('general')
const tabs = [
  { id: 'general',     label: 'General Information' },
  { id: 'salary',      label: 'Salary & TDS' },
  { id: 'deductions',  label: 'Deductions (VI-A)' },
  { id: 'taxes',       label: 'Tax Computation' },
]

const formData = reactive({
  regime: 'new' as 'old' | 'new',
  general: { firstName: '', middleName: '', lastName: '', pan: '', aadhaar: '', dob: '' },
  salary: { gross: 0, tds: 0 },
  deductions: { section80c: 0, section80d: 0 },
})

interface TaxBreakdown {
  regime: string
  fy: string
  gross_income: number
  taxable_income: number
  slab_tax: number
  rebate_87a: number
  tax_after_rebate: number
  surcharge: number
  cess: number
  total_tax: number
}

const preview = ref<TaxBreakdown | null>(null)
const previewLoading = ref(false)
const previewError = ref('')
const submitting = ref(false)
const submitError = ref('')

const netDue = computed(() => {
  if (!preview.value) return 0
  return preview.value.total_tax - Number(formData.salary.tds || 0)
})

let debounceHandle: ReturnType<typeof setTimeout> | null = null
const fetchPreview = async () => {
  previewLoading.value = true
  previewError.value = ''
  try {
    const resp = await fetch(`${API_BASE}/api/v2/calc/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gross_income: Number(formData.salary.gross || 0),
        deductions: {
          '80c': Number(formData.deductions.section80c || 0),
          '80d': Number(formData.deductions.section80d || 0),
        },
        regime: formData.regime,
        is_salary_income: true,
      }),
    })
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }
    preview.value = await resp.json()
  } catch (e: any) {
    preview.value = null
    previewError.value = e.message || 'Failed to compute tax'
  } finally {
    previewLoading.value = false
  }
}

const recomputeNow = () => {
  if (debounceHandle) clearTimeout(debounceHandle)
  fetchPreview()
}

watch(
  () => [
    formData.regime,
    formData.salary.gross,
    formData.salary.tds,
    formData.deductions.section80c,
    formData.deductions.section80d,
  ],
  () => {
    if (debounceHandle) clearTimeout(debounceHandle)
    debounceHandle = setTimeout(fetchPreview, 400)
  },
  { immediate: true },
)

const submitFiling = async () => {
  if (!authStore.user?.id) {
    submitError.value = 'Please log in first.'
    return
  }
  if (!formData.salary.gross) {
    submitError.value = 'Enter Gross Salary on the Salary & TDS tab.'
    activeTab.value = 'salary'
    return
  }
  submitting.value = true
  submitError.value = ''
  try {
    const resp = await fetch(`${API_BASE}/api/v2/filing/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: authStore.user.id,
        regime: formData.regime,
        salary: { gross: Number(formData.salary.gross), tds: Number(formData.salary.tds || 0) },
        deductions: {
          '80c': Number(formData.deductions.section80c || 0),
          '80d': Number(formData.deductions.section80d || 0),
        },
      }),
    })
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }
    router.push('/filings')
  } catch (e: any) {
    submitError.value = e.message || 'Failed to submit'
  } finally {
    submitting.value = false
  }
}

// Tiny render-helper component, used inline so we don't need a separate file.
const Row = (props: { label: string; value?: number; raw?: string; negative?: boolean }) =>
  h('div', { class: 'flex justify-between text-sm' }, [
    h('span', { class: 'text-muted-foreground' }, props.label),
    h('span', { class: 'font-mono' },
      props.raw !== undefined
        ? props.raw
        : `${props.negative && (props.value || 0) > 0 ? '-' : ''}\u20B9${Number(props.value || 0).toLocaleString('en-IN')}`),
  ])
</script>
