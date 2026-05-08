import { defineStore } from 'pinia'
import { ref } from 'vue'

export type UiMode = 'novice' | 'intermediate' | 'expert' | 'accessibility'

export const useUiStore = defineStore('ui', () => {
  const mode = ref<UiMode>('novice')
  const a11yEnabled = ref(false)

  function setMode(newMode: UiMode) {
    mode.value = newMode
  }

  function toggleA11y() {
    a11yEnabled.value = !a11yEnabled.value
    if (a11yEnabled.value) {
      document.documentElement.classList.add('a11y-mode')
    } else {
      document.documentElement.classList.remove('a11y-mode')
    }
  }

  return {
    mode,
    a11yEnabled,
    setMode,
    toggleA11y,
  }
})
