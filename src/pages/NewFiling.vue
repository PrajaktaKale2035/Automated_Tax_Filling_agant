<template>
  <DynamicLayoutContainer>
    <div class="max-w-4xl mx-auto space-y-6">
      <BackButton />
      <div class="space-y-2">
        <h1 class="text-3xl font-bold">New ITR Filing</h1>
        <p class="text-muted-foreground">Choose Assessment Year and ITR form to start.</p>
      </div>

      <div
        v-if="prefillSource !== 'none'"
        class="p-3 rounded-lg border border-blue-200 bg-blue-50 text-sm text-blue-900 flex items-center gap-2"
      >
        <span class="font-semibold">Prefill ready:</span>
        <span v-if="prefillSource === 'form16'">Form 16 data will pre-populate salary &amp; TDS.</span>
        <span v-else-if="prefillSource === 'itr'">Last year's ITR will seed income, deductions and regime.</span>
        <span v-else>Form 16 + previous ITR will both pre-fill the form (Form 16 wins on salary).</span>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Assessment Year</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              v-for="ay in assessmentYears" :key="ay.value"
              @click="selectedAY = ay.value"
              :class="cn(
                'p-4 rounded-lg border-2 transition-all text-left',
                selectedAY === ay.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              )"
            >
              <div class="text-lg font-semibold">AY {{ ay.value }}</div>
              <div class="text-sm text-muted-foreground">FY {{ ay.fy }}</div>
            </button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>ITR Form</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              v-for="form in itrForms" :key="form.value"
              @click="selectedForm = form.value"
              :class="cn(
                'p-4 rounded-lg border-2 transition-all text-left',
                selectedForm === form.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              )"
            >
              <div class="font-semibold">{{ form.label }}</div>
              <div class="text-sm text-muted-foreground">{{ form.description }}</div>
            </button>
          </div>
        </CardContent>
      </Card>

      <div class="flex gap-4">
        <Button variant="outline" size="lg" @click="router.push('/dashboard')" class="flex-1">
          <ArrowLeft class="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>
        <Button
          size="lg"
          @click="startFiling"
          :disabled="!selectedAY || !selectedForm"
          class="flex-1"
        >
          Start Filing
          <ArrowRight class="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  </DynamicLayoutContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight } from 'lucide-vue-next'
import BackButton from '@/components-vue/navigation/BackButton.vue'
import DynamicLayoutContainer from '@/components-vue/dynamic/DynamicLayoutContainer.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Button from '@/components-vue/ui/Button.vue'
import { cn } from '@/lib/utils'

import { useAuthStore } from '@/stores/authStore'
import { useAgentStore } from '@/stores/agentStore'

const router = useRouter()
const authStore = useAuthStore()
const agentStore = useAgentStore()

const selectedAY = ref<string | null>('2025-26')
const selectedForm = ref<string | null>('ITR-1')

// Prefill fields combined from Form 16 OCR (if any) + previous-year ITR
// import (if any). Form 16 wins on conflict for current-year salary fields.
const prefillGrossSalary = ref<number | null>(null)
const prefillTdsPaid = ref<number | null>(null)
const prefillEmployerName = ref<string | null>(null)
const prefillSection80c = ref<number | null>(null)
const prefillSection80d = ref<number | null>(null)
const prefillRegime = ref<string | null>(null)
const prefillCgEquity = ref<number | null>(null)
const prefillHouseIncome = ref<number | null>(null)
const prefillBusinessIncome = ref<number | null>(null)
const prefillSource = ref<'none' | 'form16' | 'itr' | 'both'>('none')

onMounted(() => {
  let fromForm16 = false
  let fromItr = false

  if (agentStore.itrImportData) {
    const d = agentStore.itrImportData
    fromItr = true
    if (d.gross_salary) prefillGrossSalary.value = d.gross_salary
    if (d.tds_paid) prefillTdsPaid.value = d.tds_paid
    if (d.deductions_80c) prefillSection80c.value = d.deductions_80c
    if (d.deductions_80d) prefillSection80d.value = d.deductions_80d
    if (d.house_property_income) prefillHouseIncome.value = d.house_property_income
    if (d.capital_gains) prefillCgEquity.value = d.capital_gains
    if (d.business_income) prefillBusinessIncome.value = d.business_income
    if (d.regime) prefillRegime.value = String(d.regime)
    if (d.form_type) selectedForm.value = d.form_type
  }

  if (agentStore.form16Data) {
    const d = agentStore.form16Data
    fromForm16 = true
    // Form 16 is current-year authoritative — overrides ITR import.
    if (d.gross_salary != null) prefillGrossSalary.value = d.gross_salary
    if (d.tds_paid != null) prefillTdsPaid.value = d.tds_paid
    if (d.employer_name) prefillEmployerName.value = d.employer_name
    if (d.fy && !agentStore.itrImportData?.assessment_year) {
      const [startYear] = d.fy.split('-')
      if (startYear) selectedAY.value = `${Number(startYear) + 1}-${String(Number(startYear) + 2).slice(-2)}`
    }
  }

  prefillSource.value = fromForm16 && fromItr ? 'both' : fromForm16 ? 'form16' : fromItr ? 'itr' : 'none'
})

const assessmentYears = [
  { value: '2025-26', fy: '2024-25', disabled: false },
  { value: '2024-25', fy: '2023-24', disabled: false },
  { value: '2023-24', fy: '2022-23', disabled: false },
]

const itrForms = [
  { value: 'ITR-1', label: 'ITR-1 (Sahaj)', description: 'Salary, one house property, other sources up to ₹50L' },
  { value: 'ITR-2', label: 'ITR-2', description: 'Capital gains, multiple properties, foreign income' },
  { value: 'ITR-3', label: 'ITR-3', description: 'Income from business or profession' },
  { value: 'ITR-4', label: 'ITR-4 (Sugam)', description: 'Presumptive income — Section 44AD / 44ADA' },
]

const startFiling = () => {
  if (!selectedAY.value || !selectedForm.value) return
  const prefillQuery = {
    ay: selectedAY.value,
    form: selectedForm.value,
    mode: authStore.mode,
    ...(prefillGrossSalary.value != null ? { gross_salary: String(prefillGrossSalary.value) } : {}),
    ...(prefillTdsPaid.value != null ? { tds_paid: String(prefillTdsPaid.value) } : {}),
    ...(prefillEmployerName.value != null ? { employer_name: prefillEmployerName.value } : {}),
    ...(prefillSection80c.value != null ? { section80c: String(prefillSection80c.value) } : {}),
    ...(prefillSection80d.value != null ? { section80d: String(prefillSection80d.value) } : {}),
    ...(prefillRegime.value ? { regime: prefillRegime.value } : {}),
    ...(prefillCgEquity.value != null ? { cg_equity: String(prefillCgEquity.value) } : {}),
    ...(prefillHouseIncome.value != null ? { house_income: String(prefillHouseIncome.value) } : {}),
    ...(prefillBusinessIncome.value != null ? { business_income: String(prefillBusinessIncome.value) } : {}),
    ...(prefillSource.value !== 'none' ? { prefill_from: prefillSource.value } : {}),
  }
  if (authStore.mode === 'expert') {
    router.push({ path: '/filing/grid', query: prefillQuery })
  } else {
    router.push({
      path: '/filing/wizard',
      query: { context: 'new_filing', ...prefillQuery },
    })
  }
}
</script>
