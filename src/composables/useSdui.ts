import { ref } from 'vue'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

export interface SduiField {
  id: string
  type: string
  label: string
  placeholder?: string
  required?: boolean
  options?: { value: string; label: string }[]
}

export interface SduiStep {
  id: string
  title: string
  description?: string
  fields: SduiField[]
}

export interface SduiFormSchema {
  steps: SduiStep[]
}

export interface SduiDashboardSchema {
  widgets: { id: string; type: string; title: string }[]
}

export function useSdui() {
  const formSchema = ref<SduiFormSchema | null>(null)
  const dashboardSchema = ref<SduiDashboardSchema | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchFormSchema(formType = 'filing') {
    loading.value = true
    error.value = null
    try {
      const resp = await fetch(`${API_BASE}/api/sdui/form?type=${formType}`)
      if (!resp.ok) {
        // The form endpoint is optional — wizard falls back to its hard-coded
        // step config when missing, so a 404 should not produce a noisy error.
        if (resp.status === 404) {
          formSchema.value = null
          return
        }
        throw new Error(`HTTP ${resp.status}`)
      }
      formSchema.value = await resp.json()
    } catch (e: any) {
      error.value = e?.message ?? 'Failed to load form schema'
    } finally {
      loading.value = false
    }
  }

  async function fetchDashboardSchema(userId: number | string) {
    loading.value = true
    error.value = null
    try {
      const resp = await fetch(`${API_BASE}/api/sdui/dashboard/${userId}`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      dashboardSchema.value = await resp.json()
    } catch (e: any) {
      error.value = e?.message ?? 'Failed to load dashboard schema'
    } finally {
      loading.value = false
    }
  }

  return { formSchema, dashboardSchema, loading, error, fetchFormSchema, fetchDashboardSchema }
}
