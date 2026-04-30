<template>
  <div class="min-h-screen flex items-center justify-center bg-background">
    <Card class="w-full max-w-md">
      <CardHeader class="space-y-1">
        <CardTitle class="text-2xl font-bold text-center">Create an account</CardTitle>
        <p class="text-center text-muted-foreground">
          Enter your details below to create your account
        </p>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="handleRegister" class="space-y-4">
          <div class="space-y-2">
            <Label htmlFor="fullName">Full Name</Label>
            <Input 
              id="fullName" 
              type="text" 
              placeholder="John Doe" 
              v-model="fullName"
              required 
            />
          </div>
          <div class="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input 
              id="email" 
              type="email" 
              placeholder="m@example.com" 
              v-model="email"
              required 
            />
          </div>
          <div class="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              v-model="password"
              required
            />
            <p class="text-xs text-muted-foreground">
              Minimum 8 characters, at least one uppercase letter and one digit.
            </p>
          </div>
          <div v-if="error" class="text-sm text-destructive text-center">
            {{ error }}
          </div>
          <Button type="submit" class="w-full" :disabled="loading">
            <span v-if="loading" class="animate-spin mr-2">⏳</span>
            {{ loading ? 'Creating account...' : 'Create account' }}
          </Button>
          <div class="text-center text-sm">
            Already have an account? 
            <router-link to="/login" class="underline text-primary">Sign in</router-link>
          </div>
        </form>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import Card from '@/components-vue/ui/Card.vue'
import CardHeader from '@/components-vue/ui/CardHeader.vue'
import CardTitle from '@/components-vue/ui/CardTitle.vue'
import CardContent from '@/components-vue/ui/CardContent.vue'
import Button from '@/components-vue/ui/Button.vue'
import Input from '@/components-vue/ui/Input.vue'
import Label from '@/components-vue/ui/Label.vue'

const router = useRouter()
const authStore = useAuthStore()

const fullName = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const handleRegister = async () => {
  loading.value = true
  error.value = ''
  
  try {
    await authStore.register(email.value, password.value, fullName.value)
    // Redirect to login after successful registration
    router.push('/login')
  } catch (e: any) {
    error.value = e.message || 'Failed to create account'
  } finally {
    loading.value = false
  }
}
</script>
