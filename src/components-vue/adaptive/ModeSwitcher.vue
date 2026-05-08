<template>
  <div class="flex items-center gap-3">
    <Label for="mode">Mode</Label>
    <Select v-model="selectedMode" placeholder="Select mode">
      <SelectItem value="novice">Novice (Guided)</SelectItem>
      <SelectItem value="intermediate">Intermediate</SelectItem>
      <SelectItem value="expert">Expert (Fully Auto)</SelectItem>
    </Select>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Select from '@/components-vue/ui/Select.vue';
import SelectItem from '@/components-vue/ui/SelectItem.vue';
import Label from '@/components-vue/ui/Label.vue';

export type Mode = 'novice' | 'intermediate' | 'expert';

interface Props {
  mode: Mode;
}

const props = defineProps<Props>();
const emit = defineEmits<{ change: [mode: Mode] }>();

const selectedMode = computed({
  get: () => props.mode,
  set: (value) => emit('change', value as Mode),
});
</script>
