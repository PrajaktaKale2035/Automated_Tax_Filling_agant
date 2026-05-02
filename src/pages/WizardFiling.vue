<template>
  <DynamicLayoutContainer>
    <div class="max-w-7xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
      <!-- Stepper -->
      <div class="mb-6">
        <div class="flex justify-between items-center mb-2">
          <h1 class="text-2xl font-bold">Tax Filing Wizard</h1>
          <div class="text-sm text-muted-foreground">Step {{ currentStep + 1 }} of {{ steps.length }}</div>
        </div>
        <div class="h-2 bg-secondary rounded-full overflow-hidden">
          <div
            class="h-full bg-primary transition-all duration-500 ease-out"
            :style="{ width: `${((currentStep + 1) / steps.length) * 100}%` }"
          ></div>
        </div>
        <div class="flex justify-between mt-2 text-xs text-muted-foreground">
          <span
            v-for="(step, index) in steps" :key="index"
            :class="cn('transition-colors', index <= currentStep ? 'text-primary font-medium' : '')"
          >
            {{ step.title }}
          </span>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 overflow-hidden">
        <!-- Left Panel: form -->
        <div class="lg:col-span-2 flex flex-col">
          <Card class="flex-1 flex flex-col">
            <CardHeader>
              <CardTitle>{{ steps[currentStep].title }}</CardTitle>
              <p class="text-muted-foreground">{{ steps[currentStep].description }}</p>
            </CardHeader>
            <CardContent class="flex-1 overflow-y-auto space-y-6 p-6">

              <!-- Step 1: regime -->
              <div v-if="currentStep === 0" class="space-y-4 animate-in fade-in slide-in-from-right-4">
                <div class="space-y-2">
                  <Label>Choose your tax regime</Label>
                  <div class="grid grid-cols-2 gap-4">
                    <div
                      @click="formData.regime = 'old'"
                      :class="cn(
                        'p-4 border rounded-lg cursor-pointer transition-all hover:border-primary',
                        formData.regime === 'old' ? 'border-primary bg-primary/5 ring-2 ring-primary/20' : ''
                      )"
                    >
                      <div class="font-semibold text-red-600">Old Regime</div>
                      <div class="text-xs text-muted-foreground mt-1">Claim 80C, 80D and other deductions. Higher slab rates.</div>
                    </div>
                    <div
                      @click="formData.regime = 'new'"
                      :class="cn(
                        'p-4 border rounded-lg cursor-pointer transition-all hover:border-primary',
                        formData.regime === 'new' ? 'border-primary bg-primary/5 ring-2 ring-primary/20' : ''
                      )"
                    >
                      <div class="font-semibold text-green-600">New Regime (Default)</div>
                      <div class="text-xs text-muted-foreground mt-1">Lower slab rates. Standard deduction Rs 75,000. No 80C / 80D.</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Step 2: income -->
              <div v-if="currentStep === 1" class="space-y-4 animate-in fade-in slide-in-from-right-4">
                <div class="space-y-2">
                  <Label>Gross Salary (INR)</Label>
                  <p class="text-xs text-muted-foreground">Per Part B of your Form 16.</p>
                  <Input type="number" v-model.number="formData.salary" placeholder="e.g. 1250000" />
                </div>
                <div class="space-y-2">
                  <Label>TDS already deducted (INR)</Label>
                  <p class="text-xs text-muted-foreground">Tax already withheld by your employer.</p>
                  <Input type="number" v-model.number="formData.tds" placeholder="e.g. 100000" />
                </div>
              </div>

              <!-- Step 3: deductions -->
              <div v-if="currentStep === 2" class="space-y-4 animate-in fade-in slide-in-from-right-4">
                <div v-if="formData.regime === 'new'" class="p-4 bg-blue-50 text-blue-700 rounded-lg flex items-start gap-3">
                  <Info class="h-5 w-5 mt-0.5" />
                  <div>
                    <p class="font-medium">New Regime selected</p>
                    <p class="text-sm">Most deductions (80C, 80D) don't apply. Click Next to compute.</p>
                  </div>
                </div>
                <div v-else class="space-y-4">
                  <div class="space-y-2">
                    <Label>Section 80C investments (PPF, ELSS, LIC, ...)</Label>
                    <Input type="number" v-model.number="formData.section80c" />
                    <p v-if="formData.section80c > 150000" class="text-xs text-amber-600 font-medium flex items-center gap-1">
                      <AlertTriangle class="h-3 w-3" />
                      Cap is Rs 1,50,000. The engine will cap automatically.
                    </p>
                  </div>
                  <div class="space-y-2">
                    <Label>Section 80D health insurance premium</Label>
                    <Input type="number" v-model.number="formData.section80d" />
                  </div>
                </div>
              </div>

              <!-- Step 4: review (real API) -->
              <div v-if="currentStep === 3" class="space-y-4 animate-in fade-in slide-in-from-right-4">
                <div v-if="previewError" class="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
                  {{ previewError }}
                </div>
                <div v-else-if="previewLoading" class="text-center py-8 text-muted-foreground">
                  Calling tax engine...
                </div>
                <div v-else-if="preview" class="bg-muted p-6 rounded-lg space-y-2">
                  <Row label="Gross Income" :value="preview.gross_income" />
                  <Row label="Taxable Income" :value="preview.taxable_income" />
                  <Row label="Slab Tax" :value="preview.slab_tax" />
                  <Row label="Rebate u/s 87A" :value="preview.rebate_87a" :negative="true" />
                  <Row label="Surcharge" :value="preview.surcharge" />
                  <Row label="Cess (4%)" :value="preview.cess" />
                  <div class="flex justify-between pt-3 mt-3 border-t">
                    <span class="font-semibold">Total Tax</span>
                    <span class="font-mono font-bold text-primary">&#8377;{{ preview.total_tax.toLocaleString('en-IN') }}</span>
                  </div>
                  <div class="flex justify-between text-sm text-muted-foreground">
                    <span>TDS already paid</span>
                    <span>&#8377;{{ Number(formData.tds).toLocaleString('en-IN') }}</span>
                  </div>
                  <div class="flex justify-between pt-3 mt-3 border-t">
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
            <div class="flex justify-between border-t p-6">
              <Button variant="outline" @click="prevStep" :disabled="currentStep === 0 || submitting">Back</Button>
              <Button @click="nextStep" :disabled="submitting || (currentStep === 3 && previewLoading)">
                {{ currentStep === steps.length - 1 ? (submitting ? 'Submitting...' : 'Submit & Save Filing') : 'Next' }}
              </Button>
            </div>
          </Card>
        </div>

        <!-- Right Panel -->
        <div class="hidden lg:flex flex-col gap-6 h-full overflow-hidden">
          <Card class="flex-1 flex flex-col min-h-[300px]">
             <CardHeader class="pb-2">
              <CardTitle class="text-sm font-medium">Tax Flow Visualization</CardTitle>
            </CardHeader>
            <CardContent class="flex-1 p-0">
              <SankeyDiagram />
            </CardContent>
          </Card>
          <LiveTracking class="h-[300px]" />
        </div>
      </div>
    </div>
  </DynamicLayoutContainer>
</template>

<script setup lang="ts">
import { computed, h, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Info, AlertTriangle } from 'lucide-vue-next'
import DynamicLayoutContainer from '@/components-vue/dynamic/DynamicLayoutContainer.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Button from '@/components-vue/ui/Button.vue'
import Input from '@/components-vue/ui/Input.vue'
import Label from '@/components-vue/ui/Label.vue'
import SankeyDiagram from '@/components-vue/visualization/SankeyDiagram.vue'
import LiveTracking from '@/components-vue/visualization/LiveTracking.vue'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

const router = useRouter()
const authStore = useAuthStore()

const currentStep = ref(0)
const steps = [
  { title: 'Regime', description: 'Choose your tax regime' },
  { title: 'Income', description: 'Salary and TDS' },
  { title: 'Deductions', description: 'Section 80C / 80D' },
  { title: 'Review & Submit', description: 'Computed by the deterministic backend tax engine' },
]

const formData = reactive({
  regime: 'new' as 'old' | 'new',
  salary: 0,
  tds: 0,
  section80c: 0,
  section80d: 0,
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
  return preview.value.total_tax - Number(formData.tds || 0)
})

const fetchPreview = async () => {
  previewLoading.value = true
  previewError.value = ''
  preview.value = null
  try {
    const resp = await fetch(`${API_BASE}/api/v2/calc/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gross_income: Number(formData.salary || 0),
        deductions: {
          '80c': Number(formData.section80c || 0),
          '80d': Number(formData.section80d || 0),
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
    previewError.value = e.message || 'Failed to compute tax'
  } finally {
    previewLoading.value = false
  }
}

const submitFiling = async () => {
  if (!authStore.user?.id) {
    submitError.value = 'Please log in before submitting a filing.'
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
        salary: { gross: Number(formData.salary || 0), tds: Number(formData.tds || 0) },
        deductions: {
          '80c': Number(formData.section80c || 0),
          '80d': Number(formData.section80d || 0),
        },
      }),
    })
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }
    router.push('/filings')
  } catch (e: any) {
    submitError.value = e.message || 'Failed to submit filing'
  } finally {
    submitting.value = false
  }
}

const nextStep = () => {
  if (currentStep.value === steps.length - 1) {
    submitFiling()
    return
  }
  currentStep.value++
  if (currentStep.value === 3) fetchPreview()
}

const prevStep = () => {
  if (currentStep.value > 0) currentStep.value--
}

// Re-fetch preview if any input changes while on the review step.
watch(
  () => [formData.regime, formData.salary, formData.tds, formData.section80c, formData.section80d],
  () => { if (currentStep.value === 3) fetchPreview() },
)

// Tiny inline component for breakdown rows - avoids a separate file.
const Row = (props: { label: string; value: number; negative?: boolean }) =>
  h('div', { class: 'flex justify-between text-sm' }, [
    h('span', { class: 'text-muted-foreground' }, props.label),
    h('span', { class: 'font-mono' },
      `${props.negative && props.value > 0 ? '-' : ''}\u20B9${Number(props.value || 0).toLocaleString('en-IN')}`),
  ])
</script>
