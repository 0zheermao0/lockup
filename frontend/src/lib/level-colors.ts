/**
 * Level-based color system for user interface elements
 * Provides consistent color schemes for different user levels across the application
 */

export interface LevelColorScheme {
  background: string
  color: string
  border: string
  gradient: string
  shadow: string
}

/**
 * Color schemes for each user level (1-4)
 * Following Neo-Brutalism design principles with bold, contrasting colors
 */
export const LEVEL_COLOR_SCHEMES = {
  1: {
    background: '#6c757d',  // Gray - Beginner
    color: '#ffffff',
    border: '#000000',
    gradient: 'linear-gradient(135deg, #6c757d, #5a6268)',
    shadow: 'rgba(108, 117, 125, 0.3)'
  },
  2: {
    background: '#17a2b8',  // Cyan - Intermediate
    color: '#ffffff',
    border: '#000000',
    gradient: 'linear-gradient(135deg, #17a2b8, #138496)',
    shadow: 'rgba(23, 162, 184, 0.3)'
  },
  3: {
    background: '#ffc107',  // Yellow/Gold - Advanced
    color: '#000000',
    border: '#000000',
    gradient: 'linear-gradient(135deg, #ffc107, #e0a800)',
    shadow: 'rgba(255, 193, 7, 0.3)'
  },
  4: {
    background: '#fd7e14',  // Orange - Expert
    color: '#ffffff',
    border: '#000000',
    gradient: 'linear-gradient(135deg, #fd7e14, #e76500)',
    shadow: 'rgba(253, 126, 20, 0.3)'
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
 * @returns CSS custom properties object
 */
export function getLevelCSSProperties(level: number): Record<string, string> {
  const colors = getLevelColorScheme(level)
  return {
    '--level-bg': colors.background,
    '--level-color': colors.color,
    '--level-border': colors.border,
    '--level-gradient': colors.gradient,
    '--level-shadow': colors.shadow
  }
}

/**
 * Get CSS classes for level styling
 * @param level User level (1-4)
 * @returns CSS class name
 */
export function getLevelCSSClass(level: number): string {
  const normalizedLevel = Math.max(1, Math.min(4, level || 1))
  return `level-${normalizedLevel}`
}

/**
 * Get username text color based on user level
 * @param level User level (1-4)
 * @returns CSS color value
 */
export function getLevelUsernameColor(level: number): string {
  const colors = getLevelColorScheme(level)
  return colors.background
}

/**
 * Get hover background color for username based on user level
 * @param level User level (1-4)
 * @returns CSS color value for hover background
 */
export function getLevelHoverBackgroundColor(level: number): string {
  const colors = getLevelColorScheme(level)
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