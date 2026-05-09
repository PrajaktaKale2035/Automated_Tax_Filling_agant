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
        <div class="lg:col-span-2 flex flex-col overflow-hidden min-h-0">
          <Card class="flex-1 flex flex-col overflow-hidden min-h-0">
            <CardHeader>
              <CardTitle>{{ steps[currentStep].title }}</CardTitle>
              <p class="text-muted-foreground">{{ steps[currentStep].description }}</p>
            </CardHeader>
            <CardContent class="flex-1 overflow-y-auto space-y-6 p-6">

              <!-- Step: regime -->
              <div v-if="stepKey === 'regime'" class="space-y-4 animate-in fade-in slide-in-from-right-4">
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

              <!-- Step: income -->
              <div v-if="stepKey === 'income'" class="space-y-4 animate-in fade-in slide-in-from-right-4">
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

              <!-- Step: deductions -->
              <div v-if="stepKey === 'deductions'" class="space-y-4 animate-in fade-in slide-in-from-right-4">
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

              <!-- Step: Capital Gains (ITR-2) -->
              <div v-if="stepKey === 'capital_gains'" class="space-y-4 animate-in fade-in slide-in-from-right-4">
                <div class="p-4 bg-blue-50/70 border border-blue-100 rounded-lg text-sm text-blue-700">
                  <p class="font-medium mb-1">Section 111A & 112A — Special rate capital gains</p>
                  <p>Equity / equity MF gains are taxed at special rates (15% STCG, 10% LTCG above ₹1L) — not at slab rates.</p>
                </div>
                <div class="space-y-2">
                  <Label>STCG on Equity / Equity MFs (held &lt; 1 year) — Section 111A</Label>
                  <Input type="number" v-model.number="formData.cg_stcg_equity" placeholder="e.g. 50000" />
                  <p class="text-xs text-muted-foreground">Taxed @ 15%. Enter net gains after purchase cost.</p>
                </div>
                <div class="space-y-2">
                  <Label>LTCG on Equity / Equity MFs (held &gt; 1 year) — Section 112A</Label>
                  <Input type="number" v-model.number="formData.cg_ltcg_equity" placeholder="e.g. 150000" />
                  <p class="text-xs text-muted-foreground">Taxed @ 10% on gains above ₹1,00,000 exemption.</p>
                </div>
                <div class="space-y-2">
                  <Label>Other Capital Gains (debt MF, property, etc.)</Label>
                  <Input type="number" v-model.number="formData.cg_other" placeholder="e.g. 80000" />
                  <p class="text-xs text-muted-foreground">Added to regular income and taxed at slab rates.</p>
                </div>
              </div>

              <!-- Step: House Property (ITR-2) -->
              <div v-if="stepKey === 'house_property'" class="space-y-4 animate-in fade-in slide-in-from-right-4">
                <div class="space-y-2">
                  <Label>Annual Rental Income (INR)</Label>
                  <Input type="number" v-model.number="formData.house_rental_income" placeholder="e.g. 240000" />
                  <p class="text-xs text-muted-foreground">Gross rent received. Leave 0 for self-occupied property.</p>
                </div>
                <div class="space-y-2">
                  <Label>Home Loan Interest Paid — Section 24b (INR)</Label>
                  <Input type="number" v-model.number="formData.house_loan_interest" placeholder="e.g. 200000" />
                  <p class="text-xs text-muted-foreground">
                    Old regime: deductible up to ₹2L for self-occupied; unlimited for let-out.
                    New regime: not deductible for self-occupied.
                  </p>
                </div>
              </div>

              <!-- Step: Business / Profession (ITR-3) -->
              <div v-if="stepKey === 'business'" class="space-y-4 animate-in fade-in slide-in-from-right-4">
                <div class="p-4 bg-amber-50/70 border border-amber-100 rounded-lg text-sm text-amber-800">
                  <p class="font-medium mb-1">ITR-3: Business / Profession</p>
                  <p>Enter your net business profit (after all allowable business expenses). This is added to your salary income for tax computation.</p>
                </div>
                <div class="space-y-2">
                  <Label>Net Business / Professional Profit (INR)</Label>
                  <Input type="number" v-model.number="formData.business_net_profit" placeholder="e.g. 800000" />
                  <p class="text-xs text-muted-foreground">Total revenue minus allowable expenses. Enter 0 if no business income.</p>
                </div>
              </div>

              <!-- Step: Presumptive Income (ITR-4) -->
              <div v-if="stepKey === 'presumptive'" class="space-y-4 animate-in fade-in slide-in-from-right-4">
                <div class="space-y-2">
                  <Label>Presumptive Income Scheme</Label>
                  <div class="grid grid-cols-2 gap-3">
                    <div
                      @click="formData.presumptive_type = '44AD'"
                      :class="cn(
                        'p-3 border rounded-lg cursor-pointer text-sm transition-all',
                        formData.presumptive_type === '44AD' ? 'border-primary bg-primary/5 ring-1 ring-primary/20' : 'border-border hover:border-primary/50'
                      )"
                    >
                      <div class="font-medium">Section 44AD</div>
                      <div class="text-xs text-muted-foreground mt-0.5">Business — 6% / 8% of turnover</div>
                    </div>
                    <div
                      @click="formData.presumptive_type = '44ADA'"
                      :class="cn(
                        'p-3 border rounded-lg cursor-pointer text-sm transition-all',
                        formData.presumptive_type === '44ADA' ? 'border-primary bg-primary/5 ring-1 ring-primary/20' : 'border-border hover:border-primary/50'
                      )"
                    >
                      <div class="font-medium">Section 44ADA</div>
                      <div class="text-xs text-muted-foreground mt-0.5">Profession — 50% of receipts</div>
                    </div>
                  </div>
                </div>
                <div class="space-y-2">
                  <Label>{{ formData.presumptive_type === '44ADA' ? 'Gross Professional Receipts (INR)' : 'Business Turnover (INR)' }}</Label>
                  <Input type="number" v-model.number="formData.presumptive_turnover" placeholder="e.g. 5000000" />
                </div>
                <div class="space-y-2">
                  <Label>Declared Income (INR)</Label>
                  <Input type="number" v-model.number="formData.presumptive_declared_income" placeholder="e.g. 300000" />
                  <p class="text-xs text-muted-foreground">
                    Min for 44AD: {{ formData.presumptive_type === '44AD' ? '6% (digital) / 8% (cash) of turnover' : '50% of receipts' }}.
                    Engine adds this to your salary income.
                  </p>
                </div>
              </div>

              <!-- Step: review -->
              <div v-if="stepKey === 'review'" class="space-y-4 animate-in fade-in slide-in-from-right-4">
                <div class="bg-blue-50/50 border border-blue-100 rounded-lg p-4 space-y-2 text-sm">
                  <p class="font-medium text-blue-700 mb-2">What you entered</p>
                  <div class="flex justify-between">
                    <span class="text-muted-foreground">Regime</span>
                    <span class="font-medium capitalize">{{ formData.regime }} regime</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-muted-foreground">Gross Salary</span>
                    <span class="font-medium font-mono">&#8377;{{ Number(formData.salary || 0).toLocaleString('en-IN') }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-muted-foreground">TDS Deducted</span>
                    <span class="font-medium font-mono">&#8377;{{ Number(formData.tds || 0).toLocaleString('en-IN') }}</span>
                  </div>
                  <div v-if="formData.cg_stcg_equity > 0" class="flex justify-between">
                    <span class="text-muted-foreground">STCG (Equity)</span>
                    <span class="font-medium">&#8377;{{ Number(formData.cg_stcg_equity).toLocaleString('en-IN') }}</span>
                  </div>
                  <div v-if="formData.cg_ltcg_equity > 0" class="flex justify-between">
                    <span class="text-muted-foreground">LTCG (Equity)</span>
                    <span class="font-medium">&#8377;{{ Number(formData.cg_ltcg_equity).toLocaleString('en-IN') }}</span>
                  </div>
                  <div v-if="formData.cg_other > 0" class="flex justify-between">
                    <span class="text-muted-foreground">Other Capital Gains</span>
                    <span class="font-medium">&#8377;{{ Number(formData.cg_other).toLocaleString('en-IN') }}</span>
                  </div>
                  <div v-if="formData.house_rental_income > 0 || formData.house_loan_interest > 0" class="flex justify-between">
                    <span class="text-muted-foreground">House Property (net)</span>
                    <span class="font-medium">&#8377;{{ Number(formData.house_rental_income > 0 ? Math.round(formData.house_rental_income * 0.7 - formData.house_loan_interest) : -Math.min(formData.house_loan_interest, 200000)).toLocaleString('en-IN') }}</span>
                  </div>
                  <div v-if="formData.business_net_profit > 0" class="flex justify-between">
                    <span class="text-muted-foreground">Business / Profession</span>
                    <span class="font-medium">&#8377;{{ Number(formData.business_net_profit).toLocaleString('en-IN') }}</span>
                  </div>
                  <div v-if="formData.presumptive_declared_income > 0" class="flex justify-between">
                    <span class="text-muted-foreground">Presumptive Income ({{ formData.presumptive_type }})</span>
                    <span class="font-medium">&#8377;{{ Number(formData.presumptive_declared_income).toLocaleString('en-IN') }}</span>
                  </div>
                  <div v-if="formData.regime === 'old' && formData.section80c > 0" class="flex justify-between">
                    <span class="text-muted-foreground">Section 80C</span>
                    <span class="font-medium font-mono">&#8377;{{ Number(formData.section80c).toLocaleString('en-IN') }}</span>
                  </div>
                  <div v-if="formData.regime === 'old' && formData.section80d > 0" class="flex justify-between">
                    <span class="text-muted-foreground">Section 80D</span>
                    <span class="font-medium font-mono">&#8377;{{ Number(formData.section80d).toLocaleString('en-IN') }}</span>
                  </div>
                </div>
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
                  <div v-if="preview.capital_gains_stcg_tax > 0" class="flex justify-between text-sm">
                    <span class="text-muted-foreground">STCG Tax (15% — Sec 111A)</span>
                    <span class="font-mono">&#8377;{{ Number(preview.capital_gains_stcg_tax).toLocaleString('en-IN') }}</span>
                  </div>
                  <div v-if="preview.capital_gains_ltcg_tax > 0" class="flex justify-between text-sm">
                    <span class="text-muted-foreground">LTCG Tax (10% — Sec 112A)</span>
                    <span class="font-mono">&#8377;{{ Number(preview.capital_gains_ltcg_tax).toLocaleString('en-IN') }}</span>
                  </div>
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
                <div v-if="preview" class="flex justify-end">
                  <button
                    @click="exportDraft"
                    class="inline-flex items-center gap-2 text-sm border rounded-md px-3 py-1.5 hover:bg-muted transition-colors"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                    Export Draft
                  </button>
                </div>
                <div v-if="submitError" class="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
                  {{ submitError }}
                </div>
              </div>

            </CardContent>
            <div class="border-t p-6 space-y-3">
              <div v-if="stepError" class="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">{{ stepError }}</div>
              <div class="flex justify-between">
                <Button variant="outline" @click="prevStep" :disabled="currentStep === 0 || submitting">Back</Button>
                <Button @click="nextStep" :disabled="submitting || (stepKey === 'review' && previewLoading)">
                  {{ currentStep === steps.length - 1 ? (submitting ? 'Submitting...' : 'Submit & Save Filing') : 'Next' }}
                </Button>
              </div>
            </div>
          </Card>
        </div>

        <!-- Right Panel -->
        <div class="hidden lg:flex flex-col gap-6 h-full overflow-hidden">
          <!-- Live tax estimate -->
          <Card class="flex-shrink-0">
            <CardHeader class="pb-2">
              <CardTitle class="text-sm font-medium">Live Tax Estimate</CardTitle>
            </CardHeader>
            <CardContent class="space-y-2 text-sm">
              <div v-if="previewLoading" class="text-muted-foreground text-xs">Computing…</div>
              <template v-else-if="preview">
                <div class="flex justify-between">
                  <span class="text-muted-foreground">Gross Income</span>
                  <span class="font-mono">&#8377;{{ preview.gross_income.toLocaleString('en-IN') }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-muted-foreground">Taxable Income</span>
                  <span class="font-mono">&#8377;{{ preview.taxable_income.toLocaleString('en-IN') }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-muted-foreground">Slab Tax</span>
                  <span class="font-mono">&#8377;{{ preview.slab_tax.toLocaleString('en-IN') }}</span>
                </div>
                <div class="flex justify-between text-green-600">
                  <span>Rebate u/s 87A</span>
                  <span class="font-mono">−&#8377;{{ preview.rebate_87a.toLocaleString('en-IN') }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-muted-foreground">Cess (4%)</span>
                  <span class="font-mono">&#8377;{{ preview.cess.toLocaleString('en-IN') }}</span>
                </div>
                <div class="flex justify-between border-t pt-2 font-semibold text-primary">
                  <span>Total Tax</span>
                  <span class="font-mono">&#8377;{{ preview.total_tax.toLocaleString('en-IN') }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-muted-foreground">{{ netDue >= 0 ? 'Tax Due' : 'Refund' }}</span>
                  <span :class="netDue > 0 ? 'text-red-600 font-medium' : 'text-green-600 font-medium'">
                    &#8377;{{ Math.abs(netDue).toLocaleString('en-IN') }}
                  </span>
                </div>
              </template>
              <div v-else class="text-xs text-muted-foreground">Complete steps 1–3 to see live estimate.</div>
            </CardContent>
          </Card>

          <!-- Quick tips (hidden in intermediate mode for a denser layout) -->
          <Card v-if="showHelp" class="flex-1 overflow-y-auto">
            <CardHeader class="pb-2">
              <CardTitle class="text-sm font-medium">Quick Guide</CardTitle>
            </CardHeader>
            <CardContent class="space-y-3 text-xs text-muted-foreground">
              <div class="space-y-1">
                <p class="font-semibold text-foreground">New Regime</p>
                <p>Lower slab rates. Standard deduction ₹75,000. 80C/80D not applicable. Best for incomes with few deductions.</p>
              </div>
              <div class="space-y-1">
                <p class="font-semibold text-foreground">Old Regime</p>
                <p>Claim 80C (up to ₹1.5L), 80D (up to ₹25K), HRA, and other deductions. Higher slab rates offset by deductions.</p>
              </div>
              <div class="space-y-1">
                <p class="font-semibold text-foreground">Section 87A Rebate</p>
                <p>Zero tax if taxable income ≤ ₹7L (new) or ≤ ₹5L (old). Full rebate of ₹25,000 / ₹12,500 respectively.</p>
              </div>
              <div class="space-y-1">
                <p class="font-semibold text-foreground">TDS</p>
                <p>Tax already deducted by your employer. Shows in Part A of Form 16. Enter here to compute refund or balance due.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  </DynamicLayoutContainer>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Info, AlertTriangle } from 'lucide-vue-next'
import DynamicLayoutContainer from '@/components-vue/dynamic/DynamicLayoutContainer.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Button from '@/components-vue/ui/Button.vue'
import Input from '@/components-vue/ui/Input.vue'
import Label from '@/components-vue/ui/Label.vue'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'
import { useSdui } from '@/composables/useSdui'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// ── SDUI ──────────────────────────────────────────────────────────────────────
const { formSchema, fetchFormSchema } = useSdui()

onMounted(() => {
  fetchFormSchema('filing')

  // Hydrate formData from query params produced by NewFiling.vue prefill flow
  // (Form 16 OCR + previous-year ITR import). Numbers are passed as strings.
  const q = route.query
  const num = (v: any): number | undefined => {
    if (v == null) return undefined
    const n = Number(v)
    return Number.isFinite(n) ? n : undefined
  }

  const grossSalary = num(q.gross_salary)
  if (grossSalary != null) formData.salary = grossSalary
  const tds = num(q.tds_paid)
  if (tds != null) formData.tds = tds
  const s80c = num(q.section80c)
  if (s80c != null) formData.section80c = s80c
  const s80d = num(q.section80d)
  if (s80d != null) formData.section80d = s80d
  const cg = num(q.cg_equity)
  if (cg != null) formData.cg_ltcg_equity = cg
  const hp = num(q.house_income)
  if (hp != null) formData.house_rental_income = hp
  const bi = num(q.business_income)
  if (bi != null) formData.business_net_profit = bi

  if (q.regime === 'old' || q.regime === 'new') {
    formData.regime = q.regime
  }
})

const formStepConfigs: Record<string, Array<{ title: string; description: string; key: string }>> = {
  'ITR-1': [
    { title: 'Regime', description: 'Choose your tax regime', key: 'regime' },
    { title: 'Income', description: 'Salary and TDS', key: 'income' },
    { title: 'Deductions', description: 'Section 80C / 80D', key: 'deductions' },
    { title: 'Review & Submit', description: 'Verified by the deterministic tax engine', key: 'review' },
  ],
  'ITR-2': [
    { title: 'Regime', description: 'Choose your tax regime', key: 'regime' },
    { title: 'Income', description: 'Salary and other income', key: 'income' },
    { title: 'Capital Gains', description: 'STCG and LTCG from equity / debt / property', key: 'capital_gains' },
    { title: 'House Property', description: 'Rental income and home loan interest', key: 'house_property' },
    { title: 'Deductions', description: 'Section 80C / 80D', key: 'deductions' },
    { title: 'Review & Submit', description: 'Verified by the deterministic tax engine', key: 'review' },
  ],
  'ITR-3': [
    { title: 'Regime', description: 'Choose your tax regime', key: 'regime' },
    { title: 'Salary Income', description: 'Salary and TDS (if any)', key: 'income' },
    { title: 'Business / Profession', description: 'Net profit from business or profession', key: 'business' },
    { title: 'Deductions', description: 'Section 80C / 80D', key: 'deductions' },
    { title: 'Review & Submit', description: 'Verified by the deterministic tax engine', key: 'review' },
  ],
  'ITR-4': [
    { title: 'Regime', description: 'Choose your tax regime', key: 'regime' },
    { title: 'Salary Income', description: 'Salary and TDS (if any)', key: 'income' },
    { title: 'Presumptive Income', description: 'Section 44AD / 44ADA / 44AE', key: 'presumptive' },
    { title: 'Review & Submit', description: 'Verified by the deterministic tax engine', key: 'review' },
  ],
}

const selectedForm = computed(() => (route.query.form as string) || 'ITR-1')

// Mode-driven density. Novice = full help; Intermediate = denser, hints
// hidden by default; Expert never lands here (routes to /filing/grid). The
// query param wins so a user can override via URL.
const effectiveMode = computed(() => {
  const q = route.query.mode
  if (q === 'novice' || q === 'intermediate' || q === 'expert') return q
  return authStore.mode || 'novice'
})
const showHelp = computed(() => effectiveMode.value !== 'intermediate')

const steps = computed(() => {
  if (formSchema.value?.steps?.length) {
    return formSchema.value.steps.map((s: any) => ({
      title: s.title,
      description: s.description ?? '',
      key: s.key ?? s.title.toLowerCase().replace(/[^a-z0-9]/g, '_'),
    }))
  }
  return formStepConfigs[selectedForm.value] ?? formStepConfigs['ITR-1']
})

const stepKey = computed(() => steps.value[currentStep.value]?.key ?? '')

const currentStep = ref(0)

const authHeaders = () => ({
  'Content-Type': 'application/json',
  ...(authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {}),
})

// ── Behavioral tracking ────────────────────────────────────────────────────────
let stepEnteredAt = Date.now()

async function trackBehavior(eventType: string, value: number, page: string) {
  try {
    await fetch(`${API_BASE}/api/users/behavior`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        user_id: authStore.user?.id ?? 0,
        event_type: eventType,
        value,
        page,
        current_mode: authStore.mode,
      }),
    })
  } catch {
    // Non-critical — fire and forget
  }
}

function onStepChange() {
  const dwellSeconds = (Date.now() - stepEnteredAt) / 1000
  trackBehavior('page_dwell', dwellSeconds, 'filing')
  stepEnteredAt = Date.now()
}

function onHelpClick() {
  trackBehavior('help_click', 1.0, 'filing')
}

const formData = reactive({
  regime: 'new' as 'old' | 'new',
  salary: 0,
  tds: 0,
  section80c: 0,
  section80d: 0,
  cg_stcg_equity: 0,
  cg_ltcg_equity: 0,
  cg_other: 0,
  house_rental_income: 0,
  house_loan_interest: 0,
  business_net_profit: 0,
  presumptive_type: '44AD' as '44AD' | '44ADA',
  presumptive_turnover: 0,
  presumptive_declared_income: 0,
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
  capital_gains_stcg_equity?: number
  capital_gains_ltcg_equity?: number
  capital_gains_stcg_tax?: number
  capital_gains_ltcg_tax?: number
  house_property_income?: number
  business_income?: number
}

const preview = ref<TaxBreakdown | null>(null)
const previewLoading = ref(false)
const previewError = ref('')
const submitting = ref(false)
const submitError = ref('')
const stepError = ref('')

const netDue = computed(() => {
  if (!preview.value) return 0
  return preview.value.total_tax - Number(formData.tds || 0)
})

const fetchPreview = async () => {
  previewLoading.value = true
  previewError.value = ''
  preview.value = null
  try {
    const presumptiveIncome = selectedForm.value === 'ITR-4'
      ? formData.presumptive_declared_income
      : 0
    const housePropertyIncome = formData.house_rental_income > 0
      ? Math.round(formData.house_rental_income * 0.7 - formData.house_loan_interest)
      : -Math.min(formData.house_loan_interest, formData.regime === 'new' ? 0 : 200_000)
    const resp = await fetch(`${API_BASE}/api/v2/calc/preview`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        gross_income: Number(formData.salary || 0),
        deductions: {
          '80c': Number(formData.section80c || 0),
          '80d': Number(formData.section80d || 0),
        },
        regime: formData.regime,
        is_salary_income: true,
        capital_gains_stcg_equity: Number(formData.cg_stcg_equity || 0),
        capital_gains_ltcg_equity: Number(formData.cg_ltcg_equity || 0),
        capital_gains_other: Number(formData.cg_other || 0),
        house_property_income: housePropertyIncome,
        business_income: Number(formData.business_net_profit || 0) + presumptiveIncome,
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
      headers: authHeaders(),
      body: JSON.stringify({
        user_id: authStore.user.id,
        form_type: selectedForm.value,
        regime: formData.regime,
        salary: { gross: Number(formData.salary || 0), tds: Number(formData.tds || 0) },
        deductions: {
          '80c': Number(formData.section80c || 0),
          '80d': Number(formData.section80d || 0),
        },
        capital_gains_stcg_equity: Number(formData.cg_stcg_equity || 0),
        capital_gains_ltcg_equity: Number(formData.cg_ltcg_equity || 0),
        capital_gains_other: Number(formData.cg_other || 0),
        house_property_income: formData.house_rental_income > 0
          ? Math.round(formData.house_rental_income * 0.7 - formData.house_loan_interest)
          : -Math.min(formData.house_loan_interest, formData.regime === 'new' ? 0 : 200_000),
        business_income: Number(formData.business_net_profit || 0) + (selectedForm.value === 'ITR-4' ? formData.presumptive_declared_income : 0),
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
  if (stepKey.value === 'income' && !formData.salary) {
    trackBehavior('field_error', 1.0, 'filing')
    stepError.value = 'Please enter your Gross Salary before continuing.'
    return
  }
  stepError.value = ''
  if (currentStep.value === steps.value.length - 1) {
    onStepChange()
    submitFiling()
    return
  }
  onStepChange()
  currentStep.value++
  if (steps.value[currentStep.value]?.key === 'review') fetchPreview()
}

const prevStep = () => {
  if (currentStep.value > 0) {
    onStepChange()
    currentStep.value--
  }
}

watch(
  () => [formData.regime, formData.salary, formData.tds, formData.section80c, formData.section80d],
  () => { if (stepKey.value === 'review') fetchPreview() },
)

// Tiny inline component for breakdown rows - avoids a separate file.
const Row = (props: { label: string; value: number; negative?: boolean }) =>
  h('div', { class: 'flex justify-between text-sm' }, [
    h('span', { class: 'text-muted-foreground' }, props.label),
    h('span', { class: 'font-mono' },
      `${props.negative && props.value > 0 ? '-' : ''}\u20B9${Number(props.value || 0).toLocaleString('en-IN')}`),
  ])

const exportDraft = () => {
  if (!preview.value) return
  const data = {
    entered: {
      regime: formData.regime,
      gross_salary: formData.salary,
      tds: formData.tds,
      section_80c: formData.section80c,
      section_80d: formData.section80d,
    },
    computed: preview.value,
    net_due: netDue.value,
    exported_at: new Date().toISOString(),
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ITR1-draft-${formData.regime}-${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}
</script>
