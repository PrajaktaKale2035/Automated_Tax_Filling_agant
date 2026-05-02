<template>
  <DynamicLayoutContainer>
    <div v-if="loading" class="space-y-6">
      <Skeleton class="h-12 w-full max-w-sm" />
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Skeleton class="h-32 w-full" />
        <Skeleton class="h-32 w-full" />
        <Skeleton class="h-32 w-full" />
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Skeleton class="h-64 w-full col-span-2" />
        <Skeleton class="h-64 w-full" />
      </div>
    </div>
    
    <div v-else-if="error" class="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div class="text-destructive mb-4">
        <AlertCircle class="h-12 w-12" />
      </div>
      <h3 class="text-lg font-semibold">Failed to load dashboard</h3>
      <p class="text-muted-foreground mb-4">{{ error }}</p>
      <Button @click="fetchDashboard">Retry</Button>
    </div>

    <div v-else-if="screen" class="space-y-8 animate-in fade-in duration-500">
      <!-- Layout handling -->
      <div v-if="screen.layout === 'bento-grid'" class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <SDUIRenderer 
          v-for="(comp, index) in screen.components" 
          :key="index" 
          :component="comp" 
        />
      </div>
      
      <div v-else class="flex flex-col gap-6">
        <SDUIRenderer 
          v-for="(comp, index) in screen.components" 
          :key="index" 
          :component="comp" 
        />
      </div>
    </div>
  </DynamicLayoutContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { AlertCircle } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/authStore'
import DynamicLayoutContainer from '@/components-vue/dynamic/DynamicLayoutContainer.vue'
import SDUIRenderer from '@/components-vue/sdui/SDUIRenderer.vue'
import Button from '@/components-vue/ui/Button.vue'
import Skeleton from '@/components-vue/ui/Skeleton.vue'

const screen = ref<any>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const authStore = useAuthStore()

const fetchDashboard = async () => {
  loading.value = true
  error.value = null
  try {
    const userId = authStore.user?.id || 1 // Fallback to 1 for dev/testing if not logged in
    const apiBase = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
    const response = await fetch(`${apiBase}/api/sdui/dashboard/${userId}`)
    if (!response.ok) {
      throw new Error('Failed to fetch dashboard configuration')
    }
    screen.value = await response.json()
  } catch (e: any) {
    console.error('Failed to load SDUI schema', e)
    error.value = e.message || 'Unknown error occurred'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboard()
})
</script>
