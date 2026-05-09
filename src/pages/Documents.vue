<template>
  <DynamicLayoutContainer>
    <div class="max-w-6xl mx-auto space-y-6">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold">Upload Documents</h1>
        <p class="text-muted-foreground">
          Upload Form 16 (or any tax PDF/JPG/PNG). The backend runs OCR and, when it
          detects a Form 16, extracts gross salary, deductions and TDS automatically.
        </p>
      </div>

      <Card
        :class="cn(
          'border-2 border-dashed transition-all duration-300',
          isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
        )"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <CardContent class="flex flex-col items-center justify-center py-12 text-center space-y-4">
          <div class="p-4 rounded-full bg-primary/10">
            <Upload class="h-8 w-8 text-primary" />
          </div>
          <div class="space-y-1">
            <h3 class="text-lg font-semibold">Drag & drop your tax document</h3>
            <p class="text-sm text-muted-foreground">
              Form 16 / 26AS / AIS / bank statements. PDF, JPG, PNG.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <Button variant="outline" :disabled="uploading" @click="fileInput?.click()">
              {{ uploading ? 'Uploading...' : 'Browse Files' }}
            </Button>
            <input
              ref="fileInput"
              type="file"
              class="hidden"
              accept=".pdf,.jpg,.jpeg,.png"
              @change="handleFileSelect"
            />
          </div>
          <div v-if="uploadStatus" :class="cn('flex items-center gap-2 text-sm font-medium', statusError ? 'text-destructive' : 'text-primary')">
            <AlertCircle class="h-4 w-4" />
            {{ uploadStatus }}
          </div>
          <div v-if="!authStore.token" class="text-xs text-amber-600">
            You need to be logged in - the backend rejects unauthenticated uploads.
          </div>
        </CardContent>
      </Card>

      <!-- Previous-year ITR upload (PDF / JSON) -->
      <Card
        :class="cn(
          'border-2 border-dashed transition-all duration-300',
          isDraggingItr ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
        )"
        @dragover.prevent="isDraggingItr = true"
        @dragleave.prevent="isDraggingItr = false"
        @drop.prevent="handleItrDrop"
      >
        <CardContent class="flex flex-col items-center justify-center py-10 text-center space-y-3">
          <div class="p-3 rounded-full bg-blue-500/10">
            <FileJson class="h-7 w-7 text-blue-500" />
          </div>
          <div class="space-y-1">
            <h3 class="text-lg font-semibold">Upload last year's ITR (PDF or JSON)</h3>
            <p class="text-sm text-muted-foreground">
              The ingestion agent parses your previous return and pre-fills a new filing automatically.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <Button variant="outline" :disabled="uploadingItr" @click="itrFileInput?.click()">
              {{ uploadingItr ? 'Parsing...' : 'Browse ITR file' }}
            </Button>
            <input
              ref="itrFileInput"
              type="file"
              class="hidden"
              accept=".pdf,.json"
              @change="handleItrSelect"
            />
          </div>
          <div v-if="itrStatus" :class="cn('flex items-center gap-2 text-sm font-medium', itrStatusError ? 'text-destructive' : 'text-primary')">
            <AlertCircle class="h-4 w-4" />
            {{ itrStatus }}
          </div>
        </CardContent>
      </Card>

      <!-- ITR parse result -->
      <Card v-if="itrResult">
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle>Previous ITR — extracted</CardTitle>
            <Button size="sm" @click="useItrPrefill">
              Use this to start a new filing
              <ArrowRight class="ml-2 h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent class="space-y-2 text-sm">
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div v-for="(value, key) in displayedItrFields" :key="key">
              <div class="text-xs uppercase tracking-wider text-muted-foreground">{{ key }}</div>
              <div class="font-mono">{{ value }}</div>
            </div>
          </div>
          <div class="flex justify-between pt-2 border-t mt-2">
            <span class="text-muted-foreground">Confidence</span>
            <span class="font-mono">{{ ((itrResult.extraction_confidence || 0) * 100).toFixed(0) }}%</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Status</span>
            <span class="font-mono">{{ itrResult.extraction_status }}</span>
          </div>
        </CardContent>
      </Card>

      <!-- Last upload result -->
      <Card v-if="lastResult">
        <CardHeader>
          <CardTitle>Last upload</CardTitle>
        </CardHeader>
        <CardContent class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-muted-foreground">File</span>
            <span class="font-mono">{{ lastResult.filename }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Status</span>
            <span class="font-mono">{{ lastResult.extraction_status }}</span>
          </div>
          <div v-if="lastResult.extraction_confidence !== undefined" class="flex justify-between">
            <span class="text-muted-foreground">Extraction confidence</span>
            <span class="font-mono">{{ (lastResult.extraction_confidence * 100).toFixed(0) }}%</span>
          </div>
          <div v-if="lastResult.form16_id" class="flex justify-between">
            <span class="text-muted-foreground">Form 16 row</span>
            <span class="font-mono">#{{ lastResult.form16_id }}</span>
          </div>
          <div v-if="lastResult.extracted_fields" class="mt-3">
            <div class="text-muted-foreground text-xs uppercase tracking-wider mb-1">Extracted fields</div>
            <pre class="bg-muted p-3 rounded text-xs overflow-auto max-h-60">{{ JSON.stringify(lastResult.extracted_fields, null, 2) }}</pre>
          </div>
          <div v-if="lastResult.raw_text_preview" class="mt-3">
            <div class="text-muted-foreground text-xs uppercase tracking-wider mb-1">OCR text preview</div>
            <pre class="bg-muted p-3 rounded text-xs overflow-auto max-h-40 whitespace-pre-wrap">{{ lastResult.raw_text_preview }}</pre>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Document checklist</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              v-for="category in documentCategories" :key="category.id"
              :class="cn(
                'p-4 rounded-lg border transition-all flex items-start gap-3',
                category.uploaded ? 'bg-green-50 border-green-200' : 'hover:border-primary/50'
              )"
            >
              <div :class="cn('mt-1', category.uploaded ? 'text-green-600' : 'text-muted-foreground')">
                <CheckCircle v-if="category.uploaded" class="h-5 w-5" />
                <FileText v-else class="h-5 w-5" />
              </div>
              <div>
                <h4 class="font-semibold text-sm">{{ category.name }}</h4>
                <p class="text-xs text-muted-foreground">{{ category.description }}</p>
                <p v-if="category.uploaded && category.fileName" class="text-xs text-green-600 mt-1 font-medium">
                  {{ category.fileName }}
                </p>
              </div>
            </div>
          </div>
          <p class="text-xs text-muted-foreground mt-3">
            Form 16 is auto-detected by the backend. Other categories tick when you upload a matching file.
          </p>
        </CardContent>
      </Card>

      <div class="flex gap-4">
        <Button variant="outline" @click="router.push('/dashboard')">
          <ArrowLeft class="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>
      </div>
    </div>
  </DynamicLayoutContainer>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Upload, CheckCircle, FileText, FileJson, AlertCircle } from 'lucide-vue-next'
import DynamicLayoutContainer from '@/components-vue/dynamic/DynamicLayoutContainer.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Button from '@/components-vue/ui/Button.vue'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'
import { useAgentStore } from '@/stores/agentStore'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

const router = useRouter()
const authStore = useAuthStore()
const agentStore = useAgentStore()

interface DocCategory {
  id: string
  name: string
  description: string
  uploaded: boolean
  fileName?: string
}

const documentCategories = ref<DocCategory[]>([
  { id: 'form16',     name: 'Form 16',           description: 'Salary & TDS certificate (auto-extracted)', uploaded: false },
  { id: 'form26as',   name: 'Form 26AS',         description: 'Tax credit statement', uploaded: false },
  { id: 'ais',        name: 'AIS',               description: 'Annual Information Statement', uploaded: false },
  { id: 'bank',       name: 'Bank Statements',   description: 'Interest income proofs', uploaded: false },
  { id: 'investments',name: 'Investment Proofs', description: '80C, 80D deduction proofs', uploaded: false },
])

const isDragging = ref(false)
const uploading = ref(false)
const uploadStatus = ref<string | null>(null)
const statusError = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const lastResult = ref<any>(null)

// ── Previous-year ITR upload state ────────────────────────────────────────────
const isDraggingItr = ref(false)
const uploadingItr = ref(false)
const itrStatus = ref<string | null>(null)
const itrStatusError = ref(false)
const itrFileInput = ref<HTMLInputElement | null>(null)
const itrResult = ref<any>(null)

const displayedItrFields = computed(() => {
  const r = itrResult.value
  if (!r) return {}
  const f = r.extracted_fields ?? {}
  const view: Record<string, string> = {}
  if (f.assessment_year) view['AY'] = f.assessment_year
  if (f.form_type) view['Form'] = f.form_type
  if (f.pan) view['PAN'] = f.pan
  if (f.regime) view['Regime'] = f.regime
  if (f.gross_salary) view['Gross Salary'] = `₹${Number(f.gross_salary).toLocaleString('en-IN')}`
  if (f.house_property_income) view['House Property'] = `₹${Number(f.house_property_income).toLocaleString('en-IN')}`
  if (f.capital_gains) view['Capital Gains'] = `₹${Number(f.capital_gains).toLocaleString('en-IN')}`
  if (f.business_income) view['Business'] = `₹${Number(f.business_income).toLocaleString('en-IN')}`
  if (f.other_income) view['Other Income'] = `₹${Number(f.other_income).toLocaleString('en-IN')}`
  if (f.deductions_80c) view['80C'] = `₹${Number(f.deductions_80c).toLocaleString('en-IN')}`
  if (f.deductions_80d) view['80D'] = `₹${Number(f.deductions_80d).toLocaleString('en-IN')}`
  if (f.tds_paid) view['TDS Paid'] = `₹${Number(f.tds_paid).toLocaleString('en-IN')}`
  if (f.taxable_income) view['Taxable Income'] = `₹${Number(f.taxable_income).toLocaleString('en-IN')}`
  if (f.total_tax) view['Total Tax'] = `₹${Number(f.total_tax).toLocaleString('en-IN')}`
  return view
})

const inferCategory = (filename: string): string => {
  const name = filename.toLowerCase()
  if (name.includes('form16') || name.includes('form-16') || name.includes('form_16')) return 'form16'
  if (name.includes('26as')) return 'form26as'
  if (name.includes('ais')) return 'ais'
  if (name.includes('bank') || name.includes('statement')) return 'bank'
  if (name.includes('80c') || name.includes('80d') || name.includes('investment') || name.includes('ppf') || name.includes('lic')) return 'investments'
  return ''
}

const handleDrop = (e: DragEvent) => {
  isDragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) uploadOne(f)
}

const handleFileSelect = (e: Event) => {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (f) uploadOne(f)
  input.value = ''
}

const uploadOne = async (file: File) => {
  if (!authStore.token) {
    uploadStatus.value = 'Please log in to upload.'
    statusError.value = true
    return
  }
  uploading.value = true
  statusError.value = false
  uploadStatus.value = `Uploading ${file.name}...`
  lastResult.value = null

  const fd = new FormData()
  fd.append('file', file)

  try {
    const resp = await fetch(`${API_BASE}/api/documents/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${authStore.token}` },
      body: fd,
    })
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }
    const data = await resp.json()
    lastResult.value = data

    // Tick the matching checklist row.
    let categoryId = ''
    if (data.extraction_status === 'extracted' || data.form16_id) {
      categoryId = 'form16'
    } else {
      categoryId = inferCategory(data.filename || file.name)
    }
    if (categoryId) {
      const cat = documentCategories.value.find(c => c.id === categoryId)
      if (cat) {
        cat.uploaded = true
        cat.fileName = data.filename || file.name
      }
    }

    if (data.extraction_status === 'extracted') {
      // Persist Form 16 fields in agentStore so NewFiling.vue can prefill them.
      const fields = data.extracted_fields ?? {}
      agentStore.form16Data = {
        gross_salary: fields.gross_salary ?? fields.grossSalary ?? undefined,
        employer_name: fields.employer_name ?? fields.employerName ?? undefined,
        tds_paid: fields.tds_deducted ?? fields.tds_paid ?? fields.tdsPaid ?? undefined,
        pan: fields.pan ?? undefined,
        fy: fields.fy ?? '2024-25',
      }
      uploadStatus.value = `Form 16 detected & extracted (confidence ${(data.extraction_confidence * 100).toFixed(0)}%).`
    } else if (data.extraction_status === 'review_required') {
      uploadStatus.value = `Looks like a Form 16 but extraction confidence is low - manual review needed.`
    } else {
      uploadStatus.value = `Uploaded. OCR ran; no Form 16 detected.`
    }
  } catch (e: any) {
    statusError.value = true
    uploadStatus.value = e.message || 'Upload failed'
  } finally {
    uploading.value = false
  }
}

// ── Previous-year ITR upload handlers ─────────────────────────────────────────
const handleItrDrop = (e: DragEvent) => {
  isDraggingItr.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) uploadItr(f)
}

const handleItrSelect = (e: Event) => {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (f) uploadItr(f)
  input.value = ''
}

const uploadItr = async (file: File) => {
  if (!authStore.token) {
    itrStatus.value = 'Please log in to upload.'
    itrStatusError.value = true
    return
  }
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  if (ext !== 'pdf' && ext !== 'json') {
    itrStatus.value = 'Only .pdf or .json ITR files are supported here.'
    itrStatusError.value = true
    return
  }

  uploadingItr.value = true
  itrStatusError.value = false
  itrStatus.value = `Parsing ${file.name}...`
  itrResult.value = null

  const fd = new FormData()
  fd.append('file', file)

  try {
    const resp = await fetch(`${API_BASE}/api/documents/upload-itr`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${authStore.token}` },
      body: fd,
    })
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }
    const data = await resp.json()
    itrResult.value = data

    // Stash for cross-page prefill.
    const f = data.extracted_fields ?? {}
    agentStore.itrImportData = {
      id: data.id,
      assessment_year: f.assessment_year,
      form_type: f.form_type,
      pan: f.pan,
      name: f.name,
      regime: f.regime,
      gross_salary: f.gross_salary,
      house_property_income: f.house_property_income,
      capital_gains: f.capital_gains,
      business_income: f.business_income,
      other_income: f.other_income,
      deductions_80c: f.deductions_80c,
      deductions_80d: f.deductions_80d,
      deductions_other: f.deductions_other,
      taxable_income: f.taxable_income,
      total_tax: f.total_tax,
      tds_paid: f.tds_paid,
      refund_due: f.refund_due,
      tax_due: f.tax_due,
      extraction_confidence: data.extraction_confidence,
      extraction_status: data.extraction_status,
    }

    if (data.extraction_status === 'parsed') {
      itrStatus.value = `ITR parsed (confidence ${(data.extraction_confidence * 100).toFixed(0)}%). Click "Use this to start a new filing".`
    } else if (data.extraction_status === 'review_required') {
      itrStatus.value = `Parsed with low confidence — please review extracted fields before using.`
    } else {
      itrStatus.value = `Parse failed. Try uploading the JSON download from the IT portal instead.`
      itrStatusError.value = true
    }
  } catch (e: any) {
    itrStatusError.value = true
    itrStatus.value = e.message || 'Upload failed'
  } finally {
    uploadingItr.value = false
  }
}

const useItrPrefill = () => {
  router.push('/filing/new')
}
</script>
