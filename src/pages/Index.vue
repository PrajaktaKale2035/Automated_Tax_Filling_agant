<template>
  <DynamicLayoutContainer>
    <!-- Loading skeleton ─────────────────────────────────────────────────── -->
    <div v-if="loading" class="space-y-8">
      <Skeleton class="h-32 w-full" />
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <Skeleton v-for="i in 4" :key="i" class="h-28 w-full" />
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton v-for="i in 3" :key="i" class="h-40 w-full" />
      </div>
      <Skeleton class="h-64 w-full" />
    </div>

    <!-- Error ─────────────────────────────────────────────────────────────── -->
    <div v-else-if="error" class="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div class="text-destructive mb-4">
        <AlertCircle class="h-12 w-12" />
      </div>
      <h3 class="text-lg font-semibold">Failed to load dashboard</h3>
      <p class="text-muted-foreground mb-4">{{ error }}</p>
      <Button @click="fetchDashboard">Retry</Button>
    </div>

    <!-- Dashboard ─────────────────────────────────────────────────────────── -->
    <div v-else class="space-y-10 animate-in fade-in duration-500 pb-10">

      <!-- Hero ──────────────────────────────────────────────────────────── -->
      <section class="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-primary/15 via-background to-accent/10 px-6 py-10 sm:px-10 sm:py-14">
        <div class="absolute -top-20 -right-20 h-72 w-72 rounded-full bg-primary/20 blur-[100px] pointer-events-none" />
        <div class="absolute -bottom-24 -left-16 h-72 w-72 rounded-full bg-accent/20 blur-[100px] pointer-events-none" />

        <div class="relative z-10 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div class="space-y-3 max-w-2xl">
            <div class="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
              <span class="h-2 w-2 rounded-full bg-accent animate-pulse" />
              <span>{{ greeting }} · AY 2025-26</span>
            </div>
            <h1 class="text-3xl sm:text-4xl lg:text-5xl font-heading font-bold leading-tight">
              Welcome back, <span class="text-gradient">{{ firstName }}</span>
            </h1>
            <p class="text-muted-foreground text-base sm:text-lg max-w-xl">
              {{ heroSubtitle }}
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-3">
            <div class="rounded-xl border border-white/10 bg-background/50 backdrop-blur-md px-4 py-2.5">
              <div class="text-[10px] uppercase tracking-wider text-muted-foreground">Filing Mode</div>
              <div class="font-semibold capitalize text-sm flex items-center gap-1.5">
                <component :is="modeIcon" class="h-3.5 w-3.5 text-primary" />
                {{ authStore.mode }}
              </div>
            </div>
            <Button size="lg" variant="glow" class="h-11 px-6" @click="router.push('/filing/new')">
              <Plus class="mr-2 h-4 w-4" />
              New Filing
            </Button>
          </div>
        </div>
      </section>

      <!-- Stats grid ────────────────────────────────────────────────────── -->
      <section>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div
            v-for="stat in stats" :key="stat.label"
            class="group relative overflow-hidden rounded-xl border border-white/10 bg-background/50 backdrop-blur-md p-5 transition-all hover:border-primary/40 hover:bg-background/80"
          >
            <div class="flex items-start justify-between mb-4">
              <div :class="cn('p-2 rounded-lg', stat.iconBg)">
                <component :is="stat.icon" :class="cn('h-5 w-5', stat.iconColor)" />
              </div>
              <span
                v-if="stat.badge"
                :class="cn(
                  'text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full font-semibold',
                  stat.badgeColor || 'bg-muted text-muted-foreground'
                )"
              >
                {{ stat.badge }}
              </span>
            </div>
            <div class="space-y-1">
              <div class="text-2xl sm:text-3xl font-heading font-bold leading-none">{{ stat.value }}</div>
              <div class="text-xs text-muted-foreground">{{ stat.label }}</div>
            </div>
            <div
              v-if="stat.subtext"
              class="text-xs mt-2 pt-2 border-t border-white/5"
              :class="stat.subtextColor || 'text-muted-foreground'"
            >
              {{ stat.subtext }}
            </div>
          </div>
        </div>
      </section>

      <!-- Quick actions ─────────────────────────────────────────────────── -->
      <section class="space-y-4">
        <div class="flex items-end justify-between">
          <div>
            <h2 class="text-xl font-heading font-bold">Quick Actions</h2>
            <p class="text-sm text-muted-foreground">Pick where to go next.</p>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
          <button
            v-for="action in actions" :key="action.title"
            @click="router.push(action.route)"
            class="group relative overflow-hidden rounded-xl border border-white/10 bg-background/50 backdrop-blur-md p-6 text-left transition-all hover:border-primary/40 hover:bg-background/80 hover:-translate-y-0.5"
          >
            <div :class="cn('absolute -top-10 -right-10 h-32 w-32 rounded-full opacity-20 blur-2xl transition-opacity group-hover:opacity-40', action.glow)" />
            <div :class="cn('relative inline-flex p-3 rounded-xl mb-4', action.iconBg)">
              <component :is="action.icon" :class="cn('h-6 w-6', action.iconColor)" />
            </div>
            <h3 class="relative font-heading font-bold text-lg mb-1">{{ action.title }}</h3>
            <p class="relative text-sm text-muted-foreground mb-4">{{ action.description }}</p>
            <div class="relative inline-flex items-center gap-1.5 text-sm font-medium text-primary">
              {{ action.cta }}
              <ArrowRight class="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </div>
          </button>
        </div>
      </section>

      <!-- Recent filings + Tips ─────────────────────────────────────────── -->
      <section class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Recent filings -->
        <Card class="lg:col-span-2 glass-card">
          <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-3">
            <div>
              <CardTitle class="flex items-center gap-2">
                <FileText class="h-5 w-5 text-primary" />
                Recent Filings
              </CardTitle>
              <p class="text-xs text-muted-foreground mt-1">Last {{ Math.min(filings.length, 5) }} of {{ filings.length }} filings</p>
            </div>
            <Button v-if="filings.length" variant="ghost" size="sm" @click="router.push('/filings')">
              View all
              <ArrowRight class="ml-1 h-3.5 w-3.5" />
            </Button>
          </CardHeader>
          <CardContent class="pt-0">
            <div v-if="!filings.length" class="rounded-lg border border-dashed border-white/10 p-8 text-center">
              <FilePlus class="h-10 w-10 text-muted-foreground mx-auto mb-3" />
              <p class="font-medium">No filings yet</p>
              <p class="text-sm text-muted-foreground mb-4">Start your first ITR filing for AY 2025-26.</p>
              <Button variant="glow" size="sm" @click="router.push('/filing/new')">
                <Plus class="mr-1.5 h-3.5 w-3.5" />
                Create your first filing
              </Button>
            </div>

            <div v-else class="space-y-2">
              <div
                v-for="f in filings.slice(0, 5)" :key="f.id"
                class="flex items-center justify-between p-3 rounded-lg border border-white/5 hover:border-primary/30 hover:bg-primary/5 transition-colors cursor-pointer"
                @click="router.push('/filings')"
              >
                <div class="flex items-center gap-3 min-w-0">
                  <div :class="cn('h-9 w-9 rounded-lg flex items-center justify-center flex-shrink-0', filingStatusBg(f.status))">
                    <component :is="filingStatusIcon(f.status)" class="h-4 w-4 text-white" />
                  </div>
                  <div class="min-w-0">
                    <div class="font-medium truncate flex items-center gap-2">
                      {{ f.form_type || 'ITR-1' }}
                      <span class="text-xs text-muted-foreground font-normal">AY {{ f.assessment_year }}</span>
                    </div>
                    <div class="text-xs text-muted-foreground truncate">
                      {{ f.regime === 'new' ? 'New regime' : 'Old regime' }} · {{ formatDate(f.created_at) }}
                    </div>
                  </div>
                </div>
                <div class="text-right flex-shrink-0 ml-3">
                  <div
                    class="text-sm font-mono font-semibold"
                    :class="f.refund_due > 0 ? 'text-green-500' : f.tax_due > 0 ? 'text-amber-500' : 'text-foreground'"
                  >
                    {{ f.refund_due > 0
                      ? `+₹${f.refund_due.toLocaleString('en-IN')}`
                      : f.tax_due > 0
                        ? `−₹${f.tax_due.toLocaleString('en-IN')}`
                        : '₹0' }}
                  </div>
                  <div class="text-[10px] uppercase tracking-wider text-muted-foreground">
                    {{ f.refund_due > 0 ? 'Refund' : f.tax_due > 0 ? 'Due' : 'Settled' }}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Tips / status panel -->
        <Card class="glass-card">
          <CardHeader class="pb-3">
            <CardTitle class="flex items-center gap-2">
              <Sparkles class="h-5 w-5 text-primary" />
              {{ insightsTitle }}
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-3">
            <div
              v-for="tip in insights" :key="tip.title"
              class="rounded-lg border border-white/5 bg-background/30 p-3"
            >
              <div class="flex items-start gap-3">
                <div :class="cn('p-1.5 rounded-md flex-shrink-0', tip.iconBg)">
                  <component :is="tip.icon" :class="cn('h-3.5 w-3.5', tip.iconColor)" />
                </div>
                <div class="space-y-1 min-w-0">
                  <div class="text-sm font-medium">{{ tip.title }}</div>
                  <p class="text-xs text-muted-foreground leading-relaxed">{{ tip.body }}</p>
                  <button
                    v-if="tip.action"
                    @click="router.push(tip.action.route)"
                    class="text-xs font-medium text-primary hover:underline inline-flex items-center gap-1 mt-1"
                  >
                    {{ tip.action.label }}
                    <ArrowRight class="h-3 w-3" />
                  </button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  </DynamicLayoutContainer>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertCircle,
  ArrowRight,
  Plus,
  FileText,
  FilePlus,
  Upload,
  MessageCircle,
  IndianRupee,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Sparkles,
  CalendarClock,
  TrendingUp,
  Lightbulb,
  GraduationCap,
  Compass,
  Zap,
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/authStore'
import { useAgentStore } from '@/stores/agentStore'
import DynamicLayoutContainer from '@/components-vue/dynamic/DynamicLayoutContainer.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Button from '@/components-vue/ui/Button.vue'
import Skeleton from '@/components-vue/ui/Skeleton.vue'
import { cn } from '@/lib/utils'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

const router = useRouter()
const authStore = useAuthStore()
const agentStore = useAgentStore()

interface FilingRow {
  id: number
  assessment_year: string
  form_type?: string
  regime: string
  status: string
  total_tax: number
  tds_paid: number
  refund_due: number
  tax_due: number
  created_at: string | null
}

const loading = ref(true)
const error = ref<string | null>(null)
const filings = ref<FilingRow[]>([])

const firstName = computed(() => {
  const full = authStore.user?.full_name || ''
  return full.split(' ')[0] || authStore.user?.email?.split('@')[0] || 'there'
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
})

const heroSubtitle = computed(() => {
  if (!filings.value.length) return 'Let\'s file your first ITR-1 with our AI assistant. Upload Form 16 or chat to get started.'
  const total = filings.value.length
  const refundCount = filings.value.filter(f => f.refund_due > 0).length
  return `You have ${total} filing${total === 1 ? '' : 's'} on record${refundCount ? ` · ${refundCount} with a refund due` : ''}. Pick up where you left off.`
})

const modeIcon = computed(() => {
  switch (authStore.mode) {
    case 'expert': return Zap
    case 'intermediate': return Compass
    default: return GraduationCap
  }
})

// ── Stats ────────────────────────────────────────────────────────────────────
const totalRefund = computed(() =>
  filings.value.reduce((sum, f) => sum + (f.refund_due || 0), 0))
const latestTaxDue = computed(() =>
  filings.value[0]?.tax_due || 0)
const latestRefund = computed(() =>
  filings.value[0]?.refund_due || 0)

const formatINR = (n: number) => {
  if (!n) return '₹0'
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(1)}Cr`
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`
  if (n >= 1000) return `₹${(n / 1000).toFixed(1)}K`
  return `₹${n.toLocaleString('en-IN')}`
}

const stats = computed(() => [
  {
    label: 'Total Filings',
    value: filings.value.length.toString(),
    icon: FileText,
    iconBg: 'bg-primary/15',
    iconColor: 'text-primary',
    badge: filings.value.length ? 'Active' : 'Get started',
    badgeColor: filings.value.length ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground',
    subtext: filings.value.length ? `Latest: AY ${filings.value[0].assessment_year}` : 'No filings yet',
  },
  {
    label: latestRefund.value > 0 ? 'Latest Refund' : 'Latest Tax Due',
    value: formatINR(latestRefund.value > 0 ? latestRefund.value : latestTaxDue.value),
    icon: latestRefund.value > 0 ? TrendingUp : IndianRupee,
    iconBg: latestRefund.value > 0 ? 'bg-green-500/15' : 'bg-amber-500/15',
    iconColor: latestRefund.value > 0 ? 'text-green-500' : 'text-amber-500',
    badge: latestRefund.value > 0 ? 'Refund' : latestTaxDue.value > 0 ? 'Pending' : 'Settled',
    badgeColor: latestRefund.value > 0
      ? 'bg-green-500/15 text-green-500'
      : latestTaxDue.value > 0
        ? 'bg-amber-500/15 text-amber-500'
        : 'bg-muted text-muted-foreground',
    subtext: filings.value.length ? `${filings.value[0].regime} regime` : 'Run a calc to see this',
  },
  {
    label: 'Total Refunds',
    value: formatINR(totalRefund.value),
    icon: ShieldCheck,
    iconBg: 'bg-accent/15',
    iconColor: 'text-accent',
    badge: totalRefund.value > 0 ? 'Lifetime' : null,
    subtext: 'Across all filings',
    subtextColor: 'text-muted-foreground',
  },
  {
    label: 'AY 2025-26 Status',
    value: ay2526Filing.value ? 'In Progress' : 'Not Started',
    icon: ay2526Filing.value ? CheckCircle2 : Clock,
    iconBg: ay2526Filing.value ? 'bg-green-500/15' : 'bg-muted',
    iconColor: ay2526Filing.value ? 'text-green-500' : 'text-muted-foreground',
    badge: ay2526Filing.value ? ay2526Filing.value.status : 'Pending',
    badgeColor: ay2526Filing.value
      ? 'bg-green-500/15 text-green-500'
      : 'bg-muted text-muted-foreground',
    subtext: ay2526Filing.value
      ? `${ay2526Filing.value.form_type || 'ITR-1'} draft saved`
      : 'Due by 31 Jul 2025',
  },
])

const ay2526Filing = computed(() =>
  filings.value.find(f => f.assessment_year === '2025-26') || null)

// ── Action cards ─────────────────────────────────────────────────────────────
const actions = computed(() => [
  {
    title: 'Start a New Filing',
    description: 'Pick AY, ITR form, and let the wizard or grid guide you.',
    cta: 'Begin filing',
    route: '/filing/new',
    icon: FilePlus,
    iconBg: 'bg-primary/15',
    iconColor: 'text-primary',
    glow: 'bg-primary',
  },
  {
    title: 'Upload a Document',
    description: 'Drop Form 16 or last year\'s ITR (PDF/JSON) to auto-prefill.',
    cta: agentStore.form16Data || agentStore.itrImportData ? 'Prefill ready ›' : 'Upload now',
    route: '/documents',
    icon: Upload,
    iconBg: 'bg-accent/15',
    iconColor: 'text-accent',
    glow: 'bg-accent',
  },
  {
    title: 'Ask the AI Assistant',
    description: 'Natural-language questions answered with the IT rulebook.',
    cta: 'Open chat',
    route: '/chat',
    icon: MessageCircle,
    iconBg: 'bg-purple-500/15',
    iconColor: 'text-purple-500',
    glow: 'bg-purple-500',
  },
])

// ── Insights / tips panel ────────────────────────────────────────────────────
const insightsTitle = computed(() => filings.value.length ? 'For you' : 'Getting started')

const insights = computed(() => {
  const items: Array<{
    title: string; body: string; icon: any;
    iconBg: string; iconColor: string;
    action?: { label: string; route: string };
  }> = []

  if (!filings.value.length) {
    items.push({
      title: 'File your first ITR',
      body: 'AY 2025-26 covers income earned between Apr 2024 - Mar 2025. The wizard takes about 5 minutes for salary income.',
      icon: FilePlus,
      iconBg: 'bg-primary/15',
      iconColor: 'text-primary',
      action: { label: 'Start the wizard', route: '/filing/new' },
    })
  }

  if (!agentStore.form16Data && !agentStore.itrImportData) {
    items.push({
      title: 'Auto-prefill with Form 16',
      body: 'Upload your employer-issued Form 16 or last year\'s ITR. We\'ll extract salary, TDS and deductions.',
      icon: Upload,
      iconBg: 'bg-accent/15',
      iconColor: 'text-accent',
      action: { label: 'Upload now', route: '/documents' },
    })
  }

  items.push({
    title: 'New vs Old regime?',
    body: 'New regime is the default for AY 2025-26 with a ₹75K standard deduction. Old regime is better when your 80C/80D is significant.',
    icon: Lightbulb,
    iconBg: 'bg-amber-500/15',
    iconColor: 'text-amber-500',
    action: { label: 'Compare in chat', route: '/chat' },
  })

  items.push({
    title: 'Filing deadline',
    body: 'ITR for AY 2025-26 is due 31 July 2025 for non-audit cases. Late filing attracts a ₹5,000 penalty u/s 234F.',
    icon: CalendarClock,
    iconBg: 'bg-purple-500/15',
    iconColor: 'text-purple-500',
  })

  return items.slice(0, 4)
})

// ── Recent-filings status helpers ────────────────────────────────────────────
const filingStatusBg = (status: string) => {
  switch (status) {
    case 'computed':
    case 'finalized': return 'bg-gradient-to-br from-green-500 to-emerald-600'
    case 'draft': return 'bg-gradient-to-br from-amber-500 to-orange-600'
    default: return 'bg-gradient-to-br from-primary to-accent'
  }
}
const filingStatusIcon = (status: string) =>
  status === 'finalized' || status === 'computed' ? CheckCircle2 : Clock

const formatDate = (s: string | null) => {
  if (!s) return ''
  try {
    return new Date(s).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch { return s }
}

// ── Data fetch ───────────────────────────────────────────────────────────────
const fetchDashboard = async () => {
  loading.value = true
  error.value = null
  try {
    if (authStore.token) {
      const resp = await fetch(`${API_BASE}/api/v2/filings`, {
        headers: { Authorization: `Bearer ${authStore.token}` },
      })
      if (resp.ok) {
        filings.value = await resp.json()
      } else if (resp.status !== 401) {
        // 401 just means no auth — don't surface that as a hard error.
        throw new Error(`Failed to load filings (HTTP ${resp.status})`)
      }
    }
  } catch (e: any) {
    error.value = e?.message || 'Unknown error'
  } finally {
    loading.value = false
  }
}

onMounted(fetchDashboard)
</script>
