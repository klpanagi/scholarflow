import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { pageVariants, useReducedMotion, withReducedMotion, fastTransition } from '@/lib/motion'
import { cn } from '@/lib/utils'

interface PageMotionProps {
  children: ReactNode
  className?: string
}

/**
 * PageMotion — wraps page content with entrance/exit animations.
 * Automatically respects prefers-reduced-motion.
 */
export function PageMotion({ children, className }: PageMotionProps) {
  const prefersReduced = useReducedMotion()
  const variants = withReducedMotion(pageVariants, prefersReduced)

  return (
    <motion.div
      variants={variants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={prefersReduced ? { duration: 0 } : fastTransition}
      className={cn('min-h-full', className)}
    >
      {children}
    </motion.div>
  )
}

PageMotion.displayName = 'PageMotion'

export default PageMotion
