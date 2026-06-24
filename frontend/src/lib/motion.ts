import { useReducedMotion as useFramerReducedMotion } from 'framer-motion'
import type { Variants, Transition } from 'framer-motion'

// ========================================================================
// Transition presets
// ========================================================================

export const fastTransition: Transition = {
  duration: 0.15,
  ease: 'easeOut',
}

export const smoothTransition: Transition = {
  duration: 0.2,
  ease: 'easeInOut',
}

export const springTransition: Transition = {
  type: 'spring',
  stiffness: 300,
  damping: 25,
  mass: 0.8,
}

// ========================================================================
// Page transition variants
// ========================================================================

export const pageVariants: Variants = {
  initial: {
    opacity: 0,
    y: 8,
    filter: 'blur(2px)',
  },
  animate: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: {
      duration: 0.2,
      ease: 'easeOut',
      when: 'beforeChildren',
      staggerChildren: 0.05,
    },
  },
  exit: {
    opacity: 0,
    y: -4,
    filter: 'blur(2px)',
    transition: {
      duration: 0.15,
      ease: 'easeIn',
    },
  },
}

// ========================================================================
// Card / feature entrance variants
// ========================================================================

export const cardVariants: Variants = {
  initial: {
    opacity: 0,
    y: 16,
    scale: 0.98,
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.3,
      ease: 'easeOut',
    },
  },
  hover: {
    y: -2,
    transition: {
      duration: 0.2,
      ease: 'easeOut',
    },
  },
  tap: {
    scale: 0.98,
    transition: {
      duration: 0.1,
    },
  },
}

// ========================================================================
// Fade-in-up content reveal
// ========================================================================

export const fadeInUp: Variants = {
  initial: {
    opacity: 0,
    y: 12,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: 'easeOut',
    },
  },
}

// ========================================================================
// Staggered children helper
// ========================================================================

export const staggerContainer: Variants = {
  initial: {
    opacity: 1,
  },
  animate: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.05,
    },
  },
}

// ========================================================================
// Interactive element variants
// ========================================================================

export const hoverScale = {
  whileHover: { scale: 1.02 },
  whileTap: { scale: 0.98 },
  transition: fastTransition,
}

export const hoverLift = {
  whileHover: { y: -2 },
  whileTap: { scale: 0.98 },
  transition: { duration: 0.2, ease: 'easeOut' },
}

// ========================================================================
// Pulse animation for running status / active indicators
// ========================================================================

export const pulseVariants: Variants = {
  animate: {
    scale: [1, 1.05, 1],
    opacity: [1, 0.8, 1],
    transition: {
      duration: 2,
      ease: 'easeInOut',
      repeat: Infinity,
      repeatType: 'reverse',
    },
  },
}

// ========================================================================
// Reduced-motion variants (no-op)
// ========================================================================

export const reducedMotionVariants: Variants = {
  initial: {},
  animate: {
    transition: {
      duration: 0,
    },
  },
  exit: {},
}

// ========================================================================
// Reduced motion hook
// ========================================================================

/**
 * Returns true when the user prefers reduced motion.
 * Wraps framer-motion's built-in useReducedMotion for a stable API.
 */
export function useReducedMotion(): boolean {
  return useFramerReducedMotion() ?? false
}

// ========================================================================
// Helper: pick motion-safe variants or no-ops
// ========================================================================

/**
 * Returns motion variants when animations are allowed,
 * or no-op variants when the user prefers reduced motion.
 */
export function withReducedMotion<V extends Variants>(
  variants: V,
  prefersReduced: boolean,
): V | typeof reducedMotionVariants {
  return prefersReduced ? reducedMotionVariants : variants
}
