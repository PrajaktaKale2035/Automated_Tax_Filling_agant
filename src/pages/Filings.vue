<template>
  <DynamicLayoutContainer>
    <div class="max-w-6xl mx-auto space-y-6">
      <BackButton />
      <div class="flex justify-between items-center">
        <div class="space-y-2">
          <h1 class="text-3xl font-bold">My ITR-1 Filings</h1>
          <p class="text-muted-foreground">View and manage your Indian tax returns (FY 2024-25 / AY 2025-26)</p>
        </div>
        <div class="space-x-2">
          <Button @click="refresh" variant="outline">
            <ArrowLeft class="mr-2 h-4 w-4 rotate-180" />
            Refresh
          </Button>
          <Button @click="router.push('/filing/new')">
            <PlusCircle class="mr-2 h-4 w-4" />
            New Filing
          </Button>
        </div>
      </div>

      <div v-if="loadError" class="rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
        {{ loadError }}
      </div>

      <div v-if="loading" class="text-center py-12 text-muted-foreground">
        Loading filings...
      </div>

      <div v-else class="grid gap-4">
        <Card
          v-for="filing in filings" :key="filing.id"
          class="hover:shadow-md transition-shadow"
        >
          <CardHeader>
            <div class="flex justify-between items-start">
              <div class="space-y-1">
                <CardTitle>AY {{ filing.assessment_year }} &middot; {{ filing.regime.toUpperCase() }} regime</CardTitle>
                <div class="text-sm text-muted-foreground">
                  Filing #{{ filing.id }} &middot; created {{ filing.created_at ? new Date(filing.created_at).toLocaleString('en-IN') : '-' }}
                </div>
              </div>
              <div
                :class="cn(
                  'px-3 py-1 rounded-full text-xs font-medium',
                  filing.status === 'finalized' && 'bg-green-100 text-green-700',
                  filing.status === 'computed' && 'bg-blue-100 text-blue-700',
                  filing.status === 'draft' && 'bg-gray-100 text-gray-700'
                )"
              >
                {{ filing.status.toUpperCase() }}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
              <div>
                <div class="text-muted-foreground">Gross Income</div>
                <div class="font-medium">&#8377;{{ filing.gross_income.toLocaleString('en-IN') }}</div>
              </div>
              <div>
                <div class="text-muted-foreground">Taxable Income</div>
                <div class="font-medium">&#8377;{{ filing.taxable_income.toLocaleString('en-IN') }}</div>
              </div>
              <div>
                <div class="text-muted-foreground">Total Tax</div>
                <div class="font-medium">&#8377;{{ filing.total_tax.toLocaleString('en-IN') }}</div>
              </div>
              <div>
                <div class="text-muted-foreground">{{ filing.tax_due > 0 ? 'Tax Due' : 'Refund' }}</div>
                <div :class="cn('font-medium', filing.tax_due === 0 ? 'text-green-600' : 'text-red-600')">
                  &#8377;{{ Math.max(filing.tax_due, filing.refund_due).toLocaleString('en-IN') }}
                </div>
              </div>
            </div>
            <div class="flex flex-wrap gap-2 justify-end">
              <Button variant="outline" size="sm" @click.stop="downloadPdf(filing.id)">
                <Download class="mr-2 h-4 w-4" />
                Download PDF
              </Button>
              <Button variant="outline" size="sm" @click.stop="exportJSON(filing.id)">
                <Download class="mr-2 h-4 w-4" />
                Export ITR-1 JSON
              </Button>
              <Button
                variant="default"
                size="sm"
                class="bg-green-600 hover:bg-green-700 text-white"
                :disabled="submittingId === filing.id"
                @click.stop="submitToITDepartment(filing.id)"
              >
                <Send class="mr-2 h-4 w-4" />
                {{ submittingId === filing.id ? 'Preparing...' : 'E-File (Stub)' }}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card v-if="!loading && filings.length === 0" class="p-12 text-center">
          <FileText class="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
          <h3 class="text-lg font-semibold mb-2">No filings yet</h3>
          <p class="text-muted-foreground mb-6">Start your first ITR-1 to see it here.</p>
          <Button @click="router.push('/filing/new')">
            <PlusCircle class="mr-2 h-4 w-4" />
            Create new filing
          </Button>
        </Card>
      </div>
    </div>
  </DynamicLayoutContainer>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, PlusCircle, FileText, Send, Download } from 'lucide-vue-next'
import BackButton from '@/components-vue/navigation/BackButton.vue'
import DynamicLayoutContainer from '@/components-vue/dynamic/DynamicLayoutContainer.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Button from '@/components-vue/ui/Button.vue'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'

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

const API_BASE =
  (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const loadError = ref('')
const filings = ref<ITR1Filing[]>([])
const submittingId = ref<number | null>(null)

const authHeaders = () => ({
  'Authorization': `Bearer ${authStore.token}`,
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
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }
    filings.value = await resp.json()
  } catch (e: any) {
    loadError.value = e.message || 'Failed to load filings'
  } finally {
    loading.value = false
  }
}

const downloadPdf = async (id: number) => {
  try {
    const resp = await fetch(`${API_BASE}/api/v2/filing/${id}/pdf`, { headers: authHeaders() })
    if (!resp.ok) throw new Error(`PDF unavailable (HTTP ${resp.status})`)
    const blob = await resp.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ITR1-filing-${id}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (e: any) {
    alert(e.message)
  }
}

const exportJSON = async (id: number) => {
  try {
    const resp = await fetch(`${API_BASE}/api/v2/filing/${id}/json`, { headers: authHeaders() })
    if (!resp.ok) throw new Error(`JSON unavailable (HTTP ${resp.status})`)
    const data = await resp.json()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ITR1-filing-${id}.json`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (e: any) {
    alert(e.message)
  }
}

const submitToITDepartment = async (id: number) => {
  submittingId.value = id
  try {
    // E-filing to incometax.gov.in is not yet integrated. As a stub, we
    // download the IT-Dept-shaped ITR-1 JSON so the user can upload it manually
    // through the official portal's "Upload XML/JSON" path.
    const resp = await fetch(`${API_BASE}/api/v2/filing/${id}/json`, { headers: authHeaders() })
    if (!resp.ok) throw new Error(`Filing not ready (HTTP ${resp.status})`)
    const data = await resp.json()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ITR1-AY${data.assessmentYear}-filing-${id}.json`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    alert(
      'ITR-1 JSON downloaded.\n\n' +
      'Real e-filing (submission to incometax.gov.in) is on the roadmap. ' +
      'For now, log in at incometax.gov.in and upload this JSON via ' +
      '"e-File > File Income Tax Return > Upload Pre-filled JSON".'
    )
  } catch (e: any) {
    alert(`E-filing failed: ${e.message}`)
  } finally {
    submittingId.value = null
  }
}

onMounted(refresh)
</script>
