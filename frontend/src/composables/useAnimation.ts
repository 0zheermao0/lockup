import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Composable for scroll-triggered animations
 */
export function useScrollAnimation(options: {
  threshold?: number
  rootMargin?: string
  triggerOnce?: boolean
} = {}) {
  const { threshold = 0.1, rootMargin = '0px', triggerOnce = true } = options
  const elementRef = ref<HTMLElement | null>(null)
  const isVisible = ref(false)

  let observer: IntersectionObserver | null = null

  onMounted(() => {
    if (!elementRef.value) return

    observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          isVisible.value = true
          if (triggerOnce && observer && elementRef.value) {
            observer.unobserve(elementRef.value)
          }
        } else if (!triggerOnce) {
          isVisible.value = false
        }
      },
      { threshold, rootMargin }
    )

    observer.observe(elementRef.value)
  })

  onUnmounted(() => {
    if (observer && elementRef.value) {
      observer.unobserve(elementRef.value)
    }
  })

  return { elementRef, isVisible }
}

/**
 * Composable for staggered animations
 */
export function useStaggerAnimation(itemCount: number, baseDelay = 50) {
  const getDelay = (index: number) => `${index * baseDelay}ms`

  const getStaggerStyle = (index: number) => ({
    animationDelay: getDelay(index),
    transitionDelay: getDelay(index)
  })

  return { getDelay, getStaggerStyle }
}

/**
 * Composable for modal animations
 */
export function useModalAnimation() {
  const isAnimating = ref(false)

  const beforeEnter = () => {
    isAnimating.value = true
  }

  const afterEnter = () => {
    isAnimating.value = false
  }

  const beforeLeave = () => {
    isAnimating.value = true
  }

  const afterLeave = () => {
    isAnimating.value = false
  }

  return {
    isAnimating,
    beforeEnter,
    afterEnter,
    beforeLeave,
    afterLeave
  }
}

/**
 * Composable for page transitions
 */
export function usePageTransition() {
  const isTransitioning = ref(false)

  const onBeforeLeave = () => {
    isTransitioning.value = true
    document.body.style.overflow = 'hidden'
  }

  const onAfterEnter = () => {
    isTransitioning.value = false
    document.body.style.overflow = ''
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return {
    isTransitioning,
    onBeforeLeave,
    onAfterEnter
  }
}

/**
 * Composable for loading states with minimum duration
 */
export function useLoadingState(minDuration = 500) {
  const isLoading = ref(false)
  let loadingStartTime = 0

  const startLoading = () => {
    isLoading.value = true
    loadingStartTime = Date.now()
  }

  const stopLoading = async () => {
    const elapsed = Date.now() - loadingStartTime
    const remaining = Math.max(0, minDuration - elapsed)

    if (remaining > 0) {
      await new Promise(resolve => setTimeout(resolve, remaining))
    }

    isLoading.value = false
  }

  return {
    isLoading,
    startLoading,
    stopLoading
  }
}

/**
 * Composable for ripple effect
 */
export function useRipple() {
  const createRipple = (event: MouseEvent, color = 'rgba(255, 255, 255, 0.6)') => {
    const button = event.currentTarget as HTMLElement
    const rect = button.getBoundingClientRect()
    const size = Math.max(rect.width, rect.height)
    const x = event.clientX - rect.left - size / 2
    const y = event.clientY - rect.top - size / 2

    const ripple = document.createElement('span')
    ripple.style.cssText = `
      position: absolute;
      border-radius: 50%;
      background: ${color};
      width: ${size}px;
      height: ${size}px;
      left: ${x}px;
      top: ${y}px;
      animation: ripple 600ms linear;
      pointer-events: none;
    `

    button.style.position = 'relative'
    button.style.overflow = 'hidden'
    button.appendChild(ripple)

    setTimeout(() => ripple.remove(), 600)
  }

  return { createRipple }
}

/**
 * Composable for reduced motion preference
 */
export function useReducedMotion() {
  const prefersReducedMotion = ref(false)

  onMounted(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReducedMotion.value = mediaQuery.matches

    const handler = (e: MediaQueryListEvent) => {
      prefersReducedMotion.value = e.matches
    }

    mediaQuery.addEventListener('change', handler)

    onUnmounted(() => {
      mediaQuery.removeEventListener('change', handler)
    })
  })

  return { prefersReducedMotion }
}

/**
 * Easing functions
 */
export const easings = {
  standard: 'cubic-bezier(0.4, 0.0, 0.2, 1)',
  bounce: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  decelerate: 'cubic-bezier(0.0, 0.0, 0.2, 1)',
  accelerate: 'cubic-bezier(0.4, 0.0, 1, 1)',
  elastic: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)'
} as const

/**
 * Duration constants
 */
export const durations = {
  micro: 150,
  fast: 200,
  normal: 300,
  slow: 500,
  complex: 800
} as const
