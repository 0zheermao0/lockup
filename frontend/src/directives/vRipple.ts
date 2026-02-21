import type { Directive } from 'vue'

interface RippleOptions {
  color?: string
  duration?: number
  center?: boolean
}

const defaultOptions: RippleOptions = {
  color: 'rgba(255, 255, 255, 0.6)',
  duration: 600,
  center: false
}

const vRipple: Directive<HTMLElement, RippleOptions | undefined> = {
  mounted(el, binding) {
    const options = { ...defaultOptions, ...binding.value }

    // Ensure element has relative positioning and overflow hidden
    const computedStyle = window.getComputedStyle(el)
    if (computedStyle.position === 'static') {
      el.style.position = 'relative'
    }
    el.style.overflow = 'hidden'

    const createRipple = (event: MouseEvent) => {
      const rect = el.getBoundingClientRect()
      const size = Math.max(rect.width, rect.height)

      let x: number
      let y: number

      if (options.center) {
        x = rect.width / 2 - size / 2
        y = rect.height / 2 - size / 2
      } else {
        x = event.clientX - rect.left - size / 2
        y = event.clientY - rect.top - size / 2
      }

      const ripple = document.createElement('span')
      ripple.className = 'v-ripple-effect'
      ripple.style.cssText = `
        position: absolute;
        border-radius: 50%;
        background: ${options.color};
        width: ${size}px;
        height: ${size}px;
        left: ${x}px;
        top: ${y}px;
        animation: v-ripple-animation ${options.duration}ms linear;
        pointer-events: none;
        transform: scale(0);
      `

      el.appendChild(ripple)

      setTimeout(() => {
        ripple.remove()
      }, options.duration)
    }

    // Add click event listener
    el.addEventListener('click', createRipple)

    // Store the handler for cleanup
    ;(el as any)._rippleHandler = createRipple
    ;(el as any)._rippleOptions = options
  },

  updated(el, binding) {
    // Update options if they change
    const options = { ...defaultOptions, ...binding.value }
    ;(el as any)._rippleOptions = options
  },

  unmounted(el) {
    // Clean up event listener
    const handler = (el as any)._rippleHandler
    if (handler) {
      el.removeEventListener('click', handler)
    }
    delete (el as any)._rippleHandler
    delete (el as any)._rippleOptions
  }
}

// Add global styles for ripple animation
const style = document.createElement('style')
style.textContent = `
  @keyframes v-ripple-animation {
    0% {
      transform: scale(0);
      opacity: 0.5;
    }
    100% {
      transform: scale(4);
      opacity: 0;
    }
  }
`
document.head.appendChild(style)

export default vRipple
