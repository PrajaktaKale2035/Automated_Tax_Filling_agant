<template>
  <div class="p-8 space-y-8">
    <div class="flex items-center gap-4">
      <BackButton />
      <h1 class="text-3xl font-bold">Settings</h1>
    </div>

    <div v-if="loadError" class="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
      {{ loadError }}
    </div>

    <div class="flex flex-col md:flex-row gap-8">
      <div class="w-full md:w-64 space-y-2">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="cn(
            'w-full text-left px-4 py-2 rounded-lg transition-colors',
            activeTab === tab.id ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
          )"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="flex-1 max-w-2xl">
        <!-- Profile -->
        <Card v-if="activeTab === 'profile'">
          <CardHeader>
            <CardTitle>Profile Information</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div v-if="loading" class="text-sm text-muted-foreground">Loading...</div>
            <template v-else>
              <div class="grid gap-2">
                <label class="text-sm font-medium">Full Name</label>
                <Input v-model="profile.full_name" />
              </div>
              <div class="grid gap-2">
                <label class="text-sm font-medium">Email</label>
                <Input v-model="profile.email" type="email" />
              </div>
              <div v-if="profileMessage" :class="cn('text-sm', profileError ? 'text-destructive' : 'text-green-600')">
                {{ profileMessage }}
              </div>
              <Button :disabled="profileSaving" @click="saveProfile">
                {{ profileSaving ? 'Saving...' : 'Save Changes' }}
              </Button>
            </template>
          </CardContent>
        </Card>

        <!-- Preferences -->
        <Card v-if="activeTab === 'preferences'">
          <CardHeader>
            <CardTitle>Filing Preferences</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div v-if="loading" class="text-sm text-muted-foreground">Loading...</div>
            <template v-else>
              <div class="grid gap-2">
                <label class="text-sm font-medium">Preferred Tax Regime</label>
                <select v-model="prefs.preferred_regime" class="rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="new">New Regime (default)</option>
                  <option value="old">Old Regime</option>
                </select>
              </div>
              <div class="grid gap-2">
                <label class="text-sm font-medium">Filing Mode</label>
                <select v-model="prefs.preferred_mode" class="rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="novice">Novice (guided wizard)</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="expert">Expert (direct grid)</option>
                </select>
              </div>
              <div class="grid gap-2">
                <label class="text-sm font-medium">Theme</label>
                <select v-model="prefs.theme" class="rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </div>
              <div class="flex items-center justify-between">
                <div class="space-y-0.5">
                  <div class="font-medium">Email Notifications</div>
                  <div class="text-sm text-muted-foreground">Receive updates about filings</div>
                </div>
                <input v-model="prefs.notifications_enabled" type="checkbox" class="h-4 w-4" />
              </div>
              <div v-if="prefMessage" :class="cn('text-sm', prefError ? 'text-destructive' : 'text-green-600')">
                {{ prefMessage }}
              </div>
              <Button :disabled="prefSaving" @click="savePreferences">
                {{ prefSaving ? 'Saving...' : 'Save Preferences' }}
              </Button>
            </template>
          </CardContent>
        </Card>

        <!-- Account -->
        <Card v-if="activeTab === 'account'">
          <CardHeader>
            <CardTitle>Account</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <p class="text-sm text-muted-foreground">
              Sign out to clear local credentials. Password change will be added when the backend exposes it.
            </p>
            <Button variant="outline" @click="signOut">Sign Out</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { cn } from '@/lib/utils'
import BackButton from '@/components-vue/navigation/BackButton.vue'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Input from '@/components-vue/ui/Input.vue'
import Button from '@/components-vue/ui/Button.vue'
import { useAuthStore } from '@/stores/authStore'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
const authStore = useAuthStore()
const router = useRouter()

const activeTab = ref('profile')
const tabs = [
  { id: 'profile', label: 'Profile' },
  { id: 'preferences', label: 'Preferences' },
  { id: 'account', label: 'Account' },
]

const loading = ref(true)
const loadError = ref('')

const profile = reactive({ full_name: '', email: '' })
const profileSaving = ref(false)
const profileMessage = ref('')
const profileError = ref(false)

const prefs = reactive({
  preferred_mode: 'novice',
  preferred_regime: 'new',
  theme: 'light',
  notifications_enabled: true,
})
const prefSaving = ref(false)
const prefMessage = ref('')
const prefError = ref(false)

const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${authStore.token}`,
})

const loadAll = async () => {
  if (!authStore.token) {
    loadError.value = 'Please log in to view settings.'
    loading.value = false
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    const [meResp, profResp] = await Promise.all([
      fetch(`${API_BASE}/api/users/me`, { headers: authHeaders() }),
      fetch(`${API_BASE}/api/users/me/profile`, { headers: authHeaders() }),
    ])
    if (meResp.ok) {
      const me = await meResp.json()
      profile.full_name = me.full_name || ''
      profile.email = me.email || ''
    } else {
      throw new Error(`HTTP ${meResp.status} fetching user`)
    }
    if (profResp.ok) {
      const p = await profResp.json()
      prefs.preferred_mode = p.preferred_mode || 'novice'
      prefs.preferred_regime = p.preferred_regime || 'new'
      prefs.theme = p.theme || 'light'
      prefs.notifications_enabled = !!p.notifications_enabled
    }
  } catch (e: any) {
    loadError.value = e.message || 'Failed to load settings'
  } finally {
    loading.value = false
  }
}

const saveProfile = async () => {
  profileSaving.value = true
  profileError.value = false
  profileMessage.value = ''
  try {
    const resp = await fetch(`${API_BASE}/api/users/me`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ full_name: profile.full_name, email: profile.email }),
    })
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }
    profileMessage.value = 'Profile updated.'
  } catch (e: any) {
    profileError.value = true
    profileMessage.value = e.message || 'Failed to update profile'
  } finally {
    profileSaving.value = false
  }
}

const savePreferences = async () => {
  prefSaving.value = true
  prefError.value = false
  prefMessage.value = ''
  try {
    const resp = await fetch(`${API_BASE}/api/users/me/profile`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ ...prefs }),
    })
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }
    prefMessage.value = 'Preferences saved.'
  } catch (e: any) {
    prefError.value = true
    prefMessage.value = e.message || 'Failed to save preferences'
  } finally {
    prefSaving.value = false
  }
}

const signOut = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(loadAll)
</script>
