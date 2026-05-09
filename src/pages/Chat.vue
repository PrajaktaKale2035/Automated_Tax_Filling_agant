<template>
  <DynamicLayoutContainer>
    <div class="max-w-7xl mx-auto h-[calc(100vh-8rem)]">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
        <!-- Chat -->
        <div class="lg:col-span-2 flex flex-col h-full overflow-hidden min-h-0">
          <div class="flex justify-between items-center mb-4 flex-shrink-0">
            <div class="space-y-1">
              <h1 class="text-2xl font-bold">Tax Assistant (LangGraph + pgvector RAG)</h1>
              <p class="text-muted-foreground text-sm">
                Powered by the backend deterministic engine and the Indian tax rulebook.
                <span v-if="threadId" class="ml-2 font-mono text-xs">thread: {{ threadId }}</span>
              </p>
            </div>
            <Button variant="outline" @click="router.push('/dashboard')">
              <ArrowLeft class="mr-2 h-4 w-4" />
              Back
            </Button>
          </div>

          <Card class="flex-1 flex flex-col overflow-hidden min-h-0">
            <div ref="messagesContainer" class="flex-1 overflow-y-auto p-6 space-y-4">

              <div v-if="messages.length === 0" class="text-center py-12">
                <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                  <Bot class="h-8 w-8 text-primary" />
                </div>
                <h3 class="text-lg font-semibold mb-2">Welcome to the Indian Tax Assistant</h3>
                <p class="text-muted-foreground mb-6">Ask in natural language. I'll use the IT rulebook (pgvector RAG) and the deterministic Indian tax engine.</p>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                  <button
                    v-for="suggestion in suggestions" :key="suggestion"
                    @click="() => { trackChatBehavior('help_click', 1.0); sendMessage(suggestion) }"
                    :disabled="isReadOnly"
                    class="p-3 text-left rounded-lg border hover:border-primary hover:bg-primary/5 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {{ suggestion }}
                  </button>
                </div>
                <div v-if="needsAuthHint" class="mt-6 text-xs text-muted-foreground">
                  Heads up: this chat needs you to be logged in (so it knows your user_id) and the backend
                  needs <code>OPENAI_API_KEY</code> set in <code>backend/.env</code>.
                </div>
              </div>

              <div
                v-for="(message, index) in messages" :key="index"
                :class="cn('flex gap-3', message.role === 'user' ? 'justify-end' : 'justify-start')"
              >
                <div
                  v-if="message.role !== 'user'"
                  class="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center"
                >
                  <Bot class="h-5 w-5 text-primary" />
                </div>
                <div
                  :class="cn(
                    'max-w-[85%] rounded-lg p-4',
                    message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'
                  )"
                >
                  <!-- User messages stay plain text; assistant replies render as markdown. -->
                  <p v-if="message.role === 'user'" class="text-sm whitespace-pre-wrap">
                    {{ message.content }}
                  </p>
                  <div
                    v-else
                    class="prose prose-sm dark:prose-invert max-w-none text-sm"
                    v-html="renderMarkdown(message.content)"
                  />
                </div>
                <div
                  v-if="message.role === 'user'"
                  class="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center"
                >
                  <User class="h-5 w-5 text-primary-foreground" />
                </div>
              </div>

              <div v-if="isTyping" class="flex gap-3">
                <div class="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Bot class="h-5 w-5 text-primary" />
                </div>
                <div class="bg-muted rounded-lg p-4">
                  <div class="flex gap-1">
                    <div class="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" style="animation-delay: 0ms"></div>
                    <div class="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" style="animation-delay: 150ms"></div>
                    <div class="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" style="animation-delay: 300ms"></div>
                  </div>
                </div>
              </div>

              <div v-if="lastError" class="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
                {{ lastError }}
              </div>
            </div>

            <div class="border-t p-4 space-y-3 flex-shrink-0">
              <!-- Read-only role notice -->
              <div
                v-if="isReadOnly"
                class="bg-amber-50 border border-amber-200 rounded p-3 text-sm text-amber-800"
              >
                You have read-only access. You can view the conversation but cannot send messages.
              </div>
              <form @submit.prevent="handleSubmit" class="flex gap-3">
                <Input
                  v-model="inputMessage"
                  placeholder="Ask about ITR-1, regime choice, deductions..."
                  class="flex-1"
                  :disabled="isTyping || isReadOnly"
                />
                <Button type="submit" :disabled="!inputMessage.trim() || isTyping || isReadOnly">
                  <Send class="h-4 w-4" />
                </Button>
              </form>
            </div>
          </Card>
        </div>

        <!-- Right rail: latest tax breakdown + RAG sources -->
        <div class="hidden lg:flex flex-col gap-4 h-full overflow-hidden">
          <Card v-if="lastBreakdown" class="flex-shrink-0">
            <CardHeader class="pb-2">
              <CardTitle class="text-sm font-medium">Tax Breakdown ({{ lastBreakdown.regime }} regime)</CardTitle>
            </CardHeader>
            <CardContent class="space-y-1 text-xs">
              <div class="flex justify-between">
                <span class="text-muted-foreground">Taxable</span>
                <span class="font-mono">&#8377;{{ Number(lastBreakdown.taxable_income).toLocaleString('en-IN') }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted-foreground">Slab tax</span>
                <span class="font-mono">&#8377;{{ Number(lastBreakdown.slab_tax).toLocaleString('en-IN') }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted-foreground">Rebate 87A</span>
                <span class="font-mono">&#8377;{{ Number(lastBreakdown.rebate_87a).toLocaleString('en-IN') }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted-foreground">Surcharge</span>
                <span class="font-mono">&#8377;{{ Number(lastBreakdown.surcharge).toLocaleString('en-IN') }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted-foreground">Cess</span>
                <span class="font-mono">&#8377;{{ Number(lastBreakdown.cess).toLocaleString('en-IN') }}</span>
              </div>
              <div class="flex justify-between border-t pt-1 mt-1 font-semibold">
                <span>Total tax</span>
                <span class="font-mono">&#8377;{{ Number(lastBreakdown.total_tax).toLocaleString('en-IN') }}</span>
              </div>
            </CardContent>
          </Card>

          <Card class="flex-1 flex flex-col min-h-[200px] overflow-hidden">
            <CardHeader class="pb-2">
              <CardTitle class="text-sm font-medium">RAG sources from rulebook</CardTitle>
            </CardHeader>
            <CardContent class="flex-1 overflow-y-auto space-y-2 text-xs">
              <p v-if="!lastResearch || !lastResearch.length" class="text-muted-foreground">
                No retrievals yet. Ask a question to see which rulebook chunks the researcher pulls.
              </p>
              <div
                v-for="(r, i) in lastResearch || []" :key="i"
                class="rounded-md border p-2"
              >
                <div class="flex justify-between text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                  <span>{{ r.section || 'general' }}</span>
                  <span>score {{ r.score?.toFixed(3) }}</span>
                </div>
                <p class="text-xs whitespace-pre-wrap">{{ r.description }}</p>
                <p class="text-[10px] text-muted-foreground mt-1">{{ r.source }}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  </DynamicLayoutContainer>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Bot, User, Send } from 'lucide-vue-next'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import DynamicLayoutContainer from '@/components-vue/dynamic/DynamicLayoutContainer.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Button from '@/components-vue/ui/Button.vue'
import Input from '@/components-vue/ui/Input.vue'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'
import { useAgentStore } from '@/stores/agentStore'
import { useUiStore } from '@/stores/uiStore'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

const router = useRouter()
const authStore = useAuthStore()
const agentStore = useAgentStore()
const uiStore = useUiStore()

/** True when the current user has read_only role (cannot send messages). */
const isReadOnly = computed(() => authStore.user?.role === 'read_only')

// Configure marked once: GitHub-flavoured markdown, line breaks honoured.
marked.setOptions({ gfm: true, breaks: true })

/** Render markdown safely for assistant messages. Sanitised with DOMPurify
 *  so model-generated content can't inject <script> or event handlers. */
function renderMarkdown(content: string): string {
  if (!content) return ''
  const raw = marked.parse(content, { async: false }) as string
  return DOMPurify.sanitize(raw, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style', 'script', 'iframe'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick'],
  })
}

interface Message { role: 'user' | 'assistant'; content: string }
interface ResearchResult { section: string; description: string; source: string; score: number }

const messages = ref<Message[]>([])
const inputMessage = ref('')
const isTyping = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const threadId = ref<string | null>(null)
const lastBreakdown = ref<any>(null)
const lastResearch = ref<ResearchResult[] | null>(null)
const lastError = ref('')

const needsAuthHint = computed(() => !authStore.user?.id)

const suggestions = [
  'I earn 12 lakh salary, paid 1L into PPF and 25k for health insurance. Old or new regime?',
  'What is the surcharge for 1.2 crore income in the new regime?',
  'How does Section 87A rebate work for 7L income?',
  'My gross is 6L, no deductions. What tax do I owe in the new regime?',
]

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

/**
 * Typed WebSocket message handler.
 * Handles { type: "message"|"rag_sources"|"error" } frames from the backend.
 * Also accepts plain-text (non-JSON) as a chat reply fallback.
 */
function handleWsMessage(event: MessageEvent) {
  try {
    const data = JSON.parse(event.data)
    if (data.type === 'message') {
      messages.value.push({ role: 'assistant', content: data.content })
      scrollToBottom()
    } else if (data.type === 'rag_sources') {
      agentStore.ragSources = data.sources ?? []
    } else if (data.type === 'error') {
      console.error('[Chat WS] server error:', data.detail)
      lastError.value = data.detail || 'Server error'
    }
    // Legacy filing.* events from ws.py are informational; ignore for chat UI.
  } catch {
    // Plain-text fallback (e.g. heartbeat or legacy echo)
    if (event.data && event.data !== '') {
      messages.value.push({ role: 'assistant', content: event.data })
      scrollToBottom()
    }
  }
}

/**
 * Post a behavioral tracking event to the backend.
 * Failures are silently swallowed so they never block the UI.
 */
async function trackChatBehavior(eventType: string, value: number = 1.0) {
  try {
    await fetch(`${API_BASE}/api/users/behavior`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {}),
      },
      body: JSON.stringify({
        user_id: authStore.user?.id ?? 0,
        event_type: eventType,
        value,
        page: 'chat',
        current_mode: uiStore.mode,
      }),
    })
  } catch {
    // Fire-and-forget: ignore failures
  }
}

const callBackend = async (path: string, body: object) => {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    throw new Error(data.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

const ingestResult = (result: any) => {
  // The graph returns the AI message at the end of `messages`. Extract it.
  const list: Array<{ role: string; content: string }> = result.messages || []
  const aiMessages = list.filter(m => m.role === 'ai' || m.role === 'assistant')
  const lastAi = aiMessages.length ? aiMessages[aiMessages.length - 1] : null
  if (lastAi) {
    messages.value.push({ role: 'assistant', content: lastAi.content })
  }
  if (result.tax_breakdown) lastBreakdown.value = result.tax_breakdown
  if (result.research_results) {
    lastResearch.value = result.research_results
    // Mirror to agentStore so other components can read RAG sources.
    agentStore.ragSources = result.research_results
  }
  if (result.thread_id) threadId.value = result.thread_id
}

const sendMessage = async (content: string) => {
  if (!content.trim()) return
  if (isReadOnly.value) {
    lastError.value = 'You have read-only access and cannot send messages.'
    return
  }
  if (!authStore.user?.id) {
    lastError.value = 'Please log in first - the chat needs your user_id.'
    return
  }
  messages.value.push({ role: 'user', content })
  inputMessage.value = ''
  scrollToBottom()
  isTyping.value = true
  lastError.value = ''
  try {
    let result
    if (!threadId.value) {
      result = await callBackend('/api/v2/filing/chat/start', {
        user_id: authStore.user.id,
        initial_message: content,
      })
    } else {
      result = await callBackend('/api/v2/filing/chat/message', {
        thread_id: threadId.value,
        message: content,
      })
    }
    ingestResult(result)
  } catch (e: any) {
    const msg = e.message || 'Chat call failed'
    if (msg.toLowerCase().includes('401') || msg.includes('api key')) {
      lastError.value = 'OPENAI_API_KEY not set on the backend. Add it to backend/.env and restart the API.'
    } else {
      lastError.value = msg
    }
  } finally {
    isTyping.value = false
    scrollToBottom()
  }
}

const handleSubmit = () => sendMessage(inputMessage.value)

// ── WebSocket: stream live agent / filing.* events ───────────────────────────
//
// The backend exposes /api/ws/{client_id}; on connect it sends a "connected"
// frame and forwards filing.* events keyed to the same client_id. We open the
// socket on mount when the user is logged in and close it on unmount.
let chatSocket: WebSocket | null = null

function openChatSocket() {
  if (!authStore.user?.id) return
  if (chatSocket && chatSocket.readyState <= 1) return
  const httpBase = API_BASE.replace(/\/$/, '')
  const wsBase = httpBase.replace(/^http/i, 'ws')
  const clientId = `chat-${authStore.user.id}`
  try {
    chatSocket = new WebSocket(`${wsBase}/api/ws/${clientId}`)
    chatSocket.onmessage = handleWsMessage
    chatSocket.onerror = () => { /* swallow — REST path still works */ }
    chatSocket.onclose = () => { chatSocket = null }
  } catch {
    chatSocket = null
  }
}

onMounted(() => {
  openChatSocket()
})

onBeforeUnmount(() => {
  if (chatSocket) {
    try { chatSocket.close() } catch { /* ignore */ }
    chatSocket = null
  }
})
</script>
