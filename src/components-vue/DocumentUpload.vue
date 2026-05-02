<template>
  <Card class="w-full">
    <CardHeader>
      <CardTitle>Upload Tax Document</CardTitle>
    </CardHeader>
    <CardContent>
      <div class="space-y-4">
        <div 
          class="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:bg-muted/50 transition-colors"
          @dragover.prevent
          @drop.prevent="handleDrop"
          @click="triggerFileInput"
        >
          <input 
            type="file" 
            ref="fileInput" 
            class="hidden" 
            accept=".pdf,.jpg,.jpeg,.png"
            @change="handleFileChange"
          />
          <div v-if="!file" class="space-y-2">
            <div class="text-4xl">📄</div>
            <p class="text-sm text-muted-foreground">
              Drag & drop or click to upload W-2 or 1099
            </p>
            <p class="text-xs text-muted-foreground">
              Supports PDF, JPG, PNG
            </p>
          </div>
          <div v-else class="space-y-2">
            <div class="text-4xl">✅</div>
            <p class="font-medium">{{ file.name }}</p>
            <Button variant="ghost" size="sm" @click.stop="file = null">
              Remove
            </Button>
          </div>
        </div>

        <div v-if="error" class="text-sm text-destructive">
          {{ error }}
        </div>

        <Button 
          class="w-full" 
          :disabled="!file || loading"
          @click="uploadDocument"
        >
          <span v-if="loading" class="animate-spin mr-2">⏳</span>
          {{ loading ? 'Processing...' : 'Upload & Process' }}
        </Button>

        <div v-if="result" class="mt-4 space-y-4">
          <div class="bg-muted p-4 rounded-lg">
            <h3 class="font-semibold mb-2">Extracted Data</h3>
            <pre class="text-xs overflow-auto max-h-60">{{ JSON.stringify(result.parsed_data, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Button from '@/components-vue/ui/Button.vue'
import { useAuthStore } from '@/stores/authStore'

const fileInput = ref<HTMLInputElement | null>(null)
const file = ref<File | null>(null)
const loading = ref(false)
const error = ref('')
const result = ref<any>(null)
const authStore = useAuthStore()

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    file.value = target.files[0]
    error.value = ''
    result.value = null
  }
}

const handleDrop = (event: DragEvent) => {
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    file.value = event.dataTransfer.files[0]
    error.value = ''
    result.value = null
  }
}

const uploadDocument = async () => {
  if (!file.value) return

  loading.value = true
  error.value = ''
  result.value = null

  const formData = new FormData()
  formData.append('file', file.value)

  try {
    const apiBase = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
    const response = await fetch(`${apiBase}/api/documents/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      },
      body: formData
    })

    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.detail || 'Upload failed')
    }

    result.value = await response.json()
  } catch (e: any) {
    error.value = e.message || 'Failed to upload document'
  } finally {
    loading.value = false
  }
}
</script>
