import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type ThemeType = 'neo-brutalism' | 'liquid-glass'

interface ThemePreferences {
  autoSwitch: boolean
  transitionDuration: number
  respectSystemPreference: boolean
}

export const useThemeStore = defineStore('theme', () => {
  // State
  const currentTheme = ref<ThemeType>('neo-brutalism')
  const isTransitioning = ref(false)
  const preferences = ref<ThemePreferences>({
    autoSwitch: false,
    transitionDuration: 300,
    respectSystemPreference: true
  })

  // Getters
  const currentThemeClass = computed(() => `theme-${currentTheme.value}`)
  const isNeoBrutalism = computed(() => currentTheme.value === 'neo-brutalism')
  const isLiquidGlass = computed(() => currentTheme.value === 'liquid-glass')

  // Local storage key
  const STORAGE_KEY = 'lockup-theme-preference'

  // Actions
  const setTheme = (theme: ThemeType, skipTransition = false) => {
    if (currentTheme.value === theme) return

    if (!skipTransition) {
      isTransitioning.value = true
    }

    // Apply theme class to document
    const html = document.documentElement
    html.classList.remove(`theme-${currentTheme.value}`)
    html.classList.add(`theme-${theme}`)

    // Update state
    currentTheme.value = theme

    // Save to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch (error) {
      console.warn('Failed to save theme preference:', error)
    }

    // Reset transition flag after animation
    if (!skipTransition) {
      setTimeout(() => {
        isTransitioning.value = false
      }, preferences.value.transitionDuration)
    }
  }

  const toggleTheme = () => {
    const newTheme: ThemeType = currentTheme.value === 'neo-brutalism'
      ? 'liquid-glass'
      : 'neo-brutalism'
    setTheme(newTheme)
  }

  const loadThemeFromStorage = (): ThemeType => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored && (stored === 'neo-brutalism' || stored === 'liquid-glass')) {
        return stored as ThemeType
      }
    } catch (error) {
      console.warn('Failed to load theme from storage:', error)
    }
    return 'neo-brutalism'
  }

  const detectSystemTheme = (): ThemeType => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'liquid-glass'
        : 'neo-brutalism'
    }
    return 'neo-brutalism'
  }

  const initTheme = () => {
    const storedTheme = loadThemeFromStorage()
    const systemTheme = detectSystemTheme()
    const initialTheme = storedTheme || systemTheme

    setTheme(initialTheme, true) // Skip transition on init

    // Listen for system theme changes
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handleSystemThemeChange = (e: MediaQueryListEvent) => {
        if (preferences.value.respectSystemPreference && !localStorage.getItem(STORAGE_KEY)) {
          const newTheme = e.matches ? 'liquid-glass' : 'neo-brutalism'
          setTheme(newTheme)
        }
      }

      mediaQuery.addEventListener('change', handleSystemThemeChange)

      // Return cleanup function
      return () => {
        mediaQuery.removeEventListener('change', handleSystemThemeChange)
      }
    }
  }

  const updatePreferences = (newPreferences: Partial<ThemePreferences>) => {
    preferences.value = { ...preferences.value, ...newPreferences }
  }

  return {
    // State
    currentTheme,
    isTransitioning,
    preferences,

    // Getters
    currentThemeClass,
    isNeoBrutalism,
    isLiquidGlass,

    // Actions
    setTheme,
    toggleTheme,
    initTheme,
    updatePreferences,
    loadThemeFromStorage,
    detectSystemTheme
  }
})

// Type exports for use in components
export type { ThemePreferences }