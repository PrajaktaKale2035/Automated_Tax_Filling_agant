<template>
  <DynamicLayoutContainer>
    <div class="max-w-4xl mx-auto space-y-6">
      <BackButton />
      <div class="space-y-2">
        <h1 class="text-3xl font-bold">New ITR Filing</h1>
        <p class="text-muted-foreground">Choose Assessment Year and ITR form to start.</p>
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

// Prefill fields from Form 16 OCR data captured in Documents.vue (if any).
// These are passed as query params to the wizard so the downstream form can use them.
const prefillGrossSalary = ref<number | null>(null)
const prefillTdsPaid = ref<number | null>(null)
const prefillEmployerName = ref<string | null>(null)

onMounted(() => {
  if (agentStore.form16Data) {
    const d = agentStore.form16Data
    prefillGrossSalary.value = d.gross_salary ?? null
    prefillTdsPaid.value = d.tds_paid ?? null
    prefillEmployerName.value = d.employer_name ?? null
    // Auto-select AY from FY if present (e.g. "2024-25" → AY "2025-26")
    if (d.fy && !selectedAY.value) {
      const [startYear] = d.fy.split('-')
      if (startYear) selectedAY.value = `${Number(startYear) + 1}-${String(Number(startYear) + 2).slice(-2)}`
    }
  }
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
  if (authStore.mode === 'expert') {
    router.push('/filing/grid')
  } else {
    router.push({
      path: '/filing/wizard',
      query: {
        context: 'new_filing',
        ay: selectedAY.value,
        form: selectedForm.value,
        // Pass Form 16 prefill values to the wizard so it can populate fields.
        ...(prefillGrossSalary.value != null ? { gross_salary: String(prefillGrossSalary.value) } : {}),
        ...(prefillTdsPaid.value != null ? { tds_paid: String(prefillTdsPaid.value) } : {}),
        ...(prefillEmployerName.value != null ? { employer_name: prefillEmployerName.value } : {}),
      },
    })
  }
}
</script>
