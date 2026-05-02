<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Activity, X } from 'lucide-vue-next'
import Card from '@/components-vue/ui/Card.vue'

const messages = ref<string[]>([])
const isConnected = ref(false)
let socket: WebSocket | null = null

const connect = () => {
  // In production, use wss:// and proper host
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const apiBase = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
  const host = apiBase.replace(/^https?:\/\//, '')
  const clientId = Math.random().toString(36).substring(7)
  
  try {
    socket = new WebSocket(`${protocol}//${host}/api/ws/${clientId}`)

    socket.onopen = () => {
      isConnected.value = true
      console.log('WebSocket connected')
    }

    socket.onmessage = (event) => {
      console.log('WS Message:', event.data)
      let msgText = event.data
      try {
        const data = JSON.parse(event.data)
        if (data.message) {
          msgText = data.message
        }
      } catch (e) {
        // Use raw data if not JSON
      }

      messages.value.push(msgText)
      
      // Keep only last 5 messages
      if (messages.value.length > 5) {
        messages.value.shift()
      }

      // Auto-remove after 5 seconds
      setTimeout(() => {
        const index = messages.value.indexOf(msgText)
        if (index > -1) {
          messages.value.splice(index, 1)
        }
      }, 5000)
    }

    socket.onclose = () => {
      isConnected.value = false
      console.log('WebSocket disconnected')
    }
    
    socket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  } catch (e) {
    console.error('Failed to create WebSocket connection', e)
  }
}

onMounted(() => {
  connect()
})

onUnmounted(() => {
  if (socket) {
    socket.close()
  }
})
</script>

<template>
  <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
    <transition-group name="list">
      <Card 
        v-for="(msg, index) in messages" 
        :key="msg + index"
        class="pointer-events-auto w-80 p-4 shadow-lg bg-background/95 backdrop-blur border-l-4 border-l-primary"
      >
        <div class="flex items-start gap-3">
          <div class="p-2 rounded-full bg-primary/10 text-primary">
            <Activity class="h-4 w-4" />
          </div>
          <div class="flex-1">
            <p class="text-sm font-medium">New Activity</p>
            <p class="text-xs text-muted-foreground">{{ msg }}</p>
          </div>
          <button @click="messages.splice(index, 1)" class="text-muted-foreground hover:text-foreground">
            <X class="h-4 w-4" />
          </button>
        </div>
      </Card>
    </transition-group>
  </div>
</template>

<style scoped>
.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
