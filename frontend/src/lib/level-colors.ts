/**
 * Level-based color system for user interface elements
 * Provides consistent color schemes for different user levels across the application
 * Now supports theme-aware styling for Neo-Brutalism and Liquid Glass themes
 */

export interface LevelColorScheme {
  background: string
  color: string
  border: string
  gradient: string
  shadow: string
  glassBackground?: string  // For liquid glass theme
  glassBorder?: string     // For liquid glass theme
  glassShadow?: string     // For liquid glass theme
}

export type ThemeType = 'neo-brutalism' | 'liquid-glass'

/**
 * Color schemes for each user level (1-4)
 * Supporting both Neo-Brutalism and Liquid Glass design principles
 */
export const LEVEL_COLOR_SCHEMES = {
  1: {
    // Neo-Brutalism styles
    background: '#6c757d',  // Gray - Beginner
    color: '#ffffff',
    border: '#000000',
    gradient: 'linear-gradient(135deg, #6c757d, #5a6268)',
    shadow: 'rgba(108, 117, 125, 0.3)',
    // Liquid Glass styles
    glassBackground: 'rgba(156, 163, 175, 0.15)',
    glassBorder: '1px solid rgba(156, 163, 175, 0.3)',
    glassShadow: '0 4px 16px rgba(156, 163, 175, 0.2)'
  },
  2: {
    // Neo-Brutalism styles
    background: '#17a2b8',  // Cyan - Intermediate
    color: '#ffffff',
    border: '#000000',
    gradient: 'linear-gradient(135deg, #17a2b8, #138496)',
    shadow: 'rgba(23, 162, 184, 0.3)',
    // Liquid Glass styles
    glassBackground: 'rgba(59, 130, 246, 0.15)',
    glassBorder: '1px solid rgba(59, 130, 246, 0.3)',
    glassShadow: '0 4px 16px rgba(59, 130, 246, 0.2)'
  },
  3: {
    // Neo-Brutalism styles
    background: '#ffc107',  // Yellow/Gold - Advanced
    color: '#000000',
    border: '#000000',
    gradient: 'linear-gradient(135deg, #ffc107, #e0a800)',
    shadow: 'rgba(255, 193, 7, 0.3)',
    // Liquid Glass styles
    glassBackground: 'rgba(147, 51, 234, 0.15)',
    glassBorder: '1px solid rgba(147, 51, 234, 0.3)',
    glassShadow: '0 4px 16px rgba(147, 51, 234, 0.2)'
  },
  4: {
    // Neo-Brutalism styles
    background: '#fd7e14',  // Orange - Expert
    color: '#ffffff',
    border: '#000000',
    gradient: 'linear-gradient(135deg, #fd7e14, #e76500)',
    shadow: 'rgba(253, 126, 20, 0.3)',
    // Liquid Glass styles
    glassBackground: 'rgba(234, 179, 8, 0.15)',
    glassBorder: '1px solid rgba(234, 179, 8, 0.3)',
    glassShadow: '0 4px 16px rgba(234, 179, 8, 0.2)'
  }
} as const

/**
 * Get color scheme for a specific user level
 * @param level User level (1-4)
 * @returns Color scheme object
 */
export function getLevelColorScheme(level: number): LevelColorScheme {
  const normalizedLevel = Math.max(1, Math.min(4, level || 1))

  if (normalizedLevel === 1) return LEVEL_COLOR_SCHEMES[1]
  if (normalizedLevel === 2) return LEVEL_COLOR_SCHEMES[2]
  if (normalizedLevel === 3) return LEVEL_COLOR_SCHEMES[3]
  if (normalizedLevel === 4) return LEVEL_COLOR_SCHEMES[4]

  return LEVEL_COLOR_SCHEMES[1] // Default fallback
}

/**
 * Get CSS custom properties for a user level
 * @param level User level (1-4)
 * @param theme Current theme type (optional, defaults to 'neo-brutalism')
 * @returns CSS custom properties object
 */
export function getLevelCSSProperties(level: number, theme: ThemeType = 'neo-brutalism'): Record<string, string> {
  const colors = getLevelColorScheme(level)

  if (theme === 'liquid-glass') {
    return {
      '--level-bg': colors.glassBackground || colors.background,
      '--level-color': getThemeAwareLevelTextColor(level, theme),
      '--level-border': colors.glassBorder || colors.border,
      '--level-gradient': colors.gradient, // Keep gradient for fallback
      '--level-shadow': colors.glassShadow || colors.shadow
    }
  }

  // Neo-Brutalism theme (default)
  return {
    '--level-bg': colors.background,
    '--level-color': colors.color,
    '--level-border': colors.border,
    '--level-gradient': colors.gradient,
    '--level-shadow': colors.shadow
  }
}

/**
 * Get theme-aware text color for level indicators
 * @param level User level (1-4)
 * @param theme Current theme type
 * @returns CSS color value
 */
export function getThemeAwareLevelTextColor(level: number, theme: ThemeType): string {
  if (theme === 'liquid-glass') {
    // Liquid glass theme uses bright, vibrancy colors
    const glassTextColors = {
      1: 'rgba(209, 213, 219, 1)',  // Light gray
      2: 'rgba(96, 165, 250, 1)',   // Light blue
      3: 'rgba(168, 85, 247, 1)',   // Light purple
      4: 'rgba(250, 204, 21, 1)'    // Light yellow
    }
    const normalizedLevel = Math.max(1, Math.min(4, level || 1)) as keyof typeof glassTextColors
    return glassTextColors[normalizedLevel]
  }

  // Neo-Brutalism theme uses original colors
  const colors = getLevelColorScheme(level)
  return colors.color
}

/**
 * Get CSS classes for level styling
 * @param level User level (1-4)
 * @param theme Current theme type (optional)
 * @returns CSS class name
 */
export function getLevelCSSClass(level: number, theme?: ThemeType): string {
  const normalizedLevel = Math.max(1, Math.min(4, level || 1))
  const baseClass = `level-${normalizedLevel}`

  if (theme) {
    return `${baseClass} theme-${theme}`
  }

  return baseClass
}

/**
 * Get username text color based on user level
 * @param level User level (1-4)
 * @param theme Current theme type (optional, defaults to 'neo-brutalism')
 * @returns CSS color value
 */
export function getLevelUsernameColor(level: number, theme: ThemeType = 'neo-brutalism'): string {
  if (theme === 'liquid-glass') {
    return getThemeAwareLevelTextColor(level, theme)
  }

  const colors = getLevelColorScheme(level)
  return colors.background
}

/**
 * Get hover background color for username based on user level
 * @param level User level (1-4)
 * @param theme Current theme type (optional, defaults to 'neo-brutalism')
 * @returns CSS color value for hover background
 */
export function getLevelHoverBackgroundColor(level: number, theme: ThemeType = 'neo-brutalism'): string {
  const colors = getLevelColorScheme(level)

  if (theme === 'liquid-glass') {
    return colors.glassBackground || `rgba(${colors.background}, 0.15)`
  }

  return colors.background
}

/**
 * Get level display name with emoji
 * @param level User level (1-4)
 * @returns Formatted level string
 */
export function getLevelDisplayName(level: number): string {
  const levelEmojis = {
    1: '🥉',  // Bronze
    2: '🥈',  // Silver
    3: '🥇',  // Gold
    4: '💎'   // Diamond
  }

  const normalizedLevel = Math.max(1, Math.min(4, level || 1))
  const emoji = levelEmojis[normalizedLevel as keyof typeof levelEmojis]

  return `${emoji} 等级 ${normalizedLevel}`
}

/**
 * Get current theme from document root class
 * @returns Current theme type
 */
export function getCurrentTheme(): ThemeType {
  const html = document.documentElement
  if (html.classList.contains('theme-liquid-glass')) {
    return 'liquid-glass'
  }
  return 'neo-brutalism'
}

/**
 * Get theme-aware level CSS properties automatically detecting current theme
 * @param level User level (1-4)
 * @returns CSS custom properties object for current theme
 */
export function getThemeAwareLevelCSSProperties(level: number): Record<string, string> {
  const currentTheme = getCurrentTheme()
  return getLevelCSSProperties(level, currentTheme)
}

/**
 * Get theme-aware level CSS class automatically detecting current theme
 * @param level User level (1-4)
 * @returns CSS class name for current theme
 */
export function getThemeAwareLevelCSSClass(level: number): string {
  const currentTheme = getCurrentTheme()
  return getLevelCSSClass(level, currentTheme)
}