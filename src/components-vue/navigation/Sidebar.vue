<template>
  <aside
    class="fixed left-0 top-0 z-40 h-screen w-64 -translate-x-full border-r border-white/10 bg-background/80 backdrop-blur-xl transition-transform lg:translate-x-0"
    :class="{ 'translate-x-0': isOpen }"
  >
    <div class="flex h-16 items-center gap-2 border-b border-white/10 px-6">
      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <span class="font-bold">T</span>
      </div>
      <span class="font-heading text-xl font-bold tracking-tight">TaxFluent</span>
    </div>

    <div class="flex flex-col gap-2 p-4">
      <Button
        v-for="item in navigation"
        :key="item.name"
        variant="ghost"
        class="justify-start gap-3"
        :class="{ 'bg-primary/10 text-primary': item.current }"
        @click="navigate(item.path)"
      >
        <component :is="item.icon" class="h-4 w-4" />
        {{ item.name }}
      </Button>
    </div>

    <div class="absolute bottom-4 left-0 right-0 p-4">
      <Card class="glass-card p-4">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-3 overflow-hidden">
            <div class="h-8 w-8 rounded-full bg-accent/20 flex-shrink-0" />
            <div class="text-sm truncate">
              <div class="font-medium truncate">{{ user?.full_name || 'User' }}</div>
              <div class="text-xs text-muted-foreground">Pro Plan</div>
            </div>
          </div>
          <Button variant="ghost" size="icon" @click="handleLogout" title="Log out">
            <LogOut class="h-4 w-4 text-muted-foreground hover:text-destructive" />
          </Button>
        </div>
      </Card>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import {
  LayoutDashboard,
  FileText,
  PieChart,
  Settings,
  HelpCircle,
  LogOut,
  MessageCircle,
  Upload,
} from 'lucide-vue-next';
import Button from '@/components-vue/ui/Button.vue';
import Card from '@/components-vue/ui/Card.vue';

defineProps<{
  isOpen?: boolean
}>();

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const user = computed(() => authStore.user);

const navigation = computed(() => [
  { name: 'Dashboard', icon: LayoutDashboard, path: '/dashboard', current: route.path === '/dashboard' },
  { name: 'My Filings', icon: FileText, path: '/filings', current: route.path === '/filings' },
  { name: 'AI Chat', icon: MessageCircle, path: '/chat', current: route.path === '/chat' },
  { name: 'Documents', icon: Upload, path: '/documents', current: route.path === '/documents' },
  { name: 'Reports', icon: PieChart, path: '/reports', current: route.path === '/reports' },
  { name: 'Settings', icon: Settings, path: '/settings', current: route.path === '/settings' },
  { name: 'Help & Support', icon: HelpCircle, path: '/help', current: route.path === '/help' },
]);

const navigate = (path: string) => {
  router.push(path);
};

const handleLogout = () => {
  authStore.logout();
  router.push('/login');
};
</script>
