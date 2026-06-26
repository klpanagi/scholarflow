import { describe, it, expect } from 'vitest'
import {
  fastTransition,
  smoothTransition,
  springTransition,
  pageVariants,
  cardVariants,
  fadeInUp,
  staggerContainer,
  pulseVariants,
  reducedMotionVariants,
  hoverScale,
  hoverLift,
  withReducedMotion,
} from '../motion'

describe('motion transitions', () => {
  it('fastTransition has correct shape', () => {
    expect(fastTransition).toHaveProperty('duration', 0.15)
    expect(fastTransition).toHaveProperty('ease', 'easeOut')
  })

  it('smoothTransition has correct shape', () => {
    expect(smoothTransition).toHaveProperty('duration', 0.2)
    expect(smoothTransition).toHaveProperty('ease', 'easeInOut')
  })

  it('springTransition has correct type', () => {
    expect(springTransition).toHaveProperty('type', 'spring')
    expect(springTransition).toHaveProperty('stiffness', 300)
    expect(springTransition).toHaveProperty('damping', 25)
  })
})

describe('motion variants', () => {
  it('pageVariants has initial/animate/exit', () => {
    expect(pageVariants).toHaveProperty('initial')
    expect(pageVariants).toHaveProperty('animate')
    expect(pageVariants).toHaveProperty('exit')
    expect(pageVariants.animate).toHaveProperty('opacity', 1)
    expect(pageVariants.animate).toHaveProperty('y', 0)
    expect(pageVariants.animate).toHaveProperty('filter', 'blur(0px)')
  })

  it('cardVariants has initial/animate/hover/tap', () => {
    expect(cardVariants).toHaveProperty('initial')
    expect(cardVariants).toHaveProperty('animate')
    expect(cardVariants).toHaveProperty('hover')
    expect(cardVariants).toHaveProperty('tap')
    expect(cardVariants.animate).toHaveProperty('opacity', 1)
    expect(cardVariants.animate).toHaveProperty('scale', 1)
  })

  it('fadeInUp has initial/animate', () => {
    expect(fadeInUp).toHaveProperty('initial')
    expect(fadeInUp).toHaveProperty('animate')
    expect(fadeInUp.animate).toHaveProperty('opacity', 1)
    expect(fadeInUp.animate).toHaveProperty('y', 0)
  })

  it('staggerContainer has initial/animate with staggerChildren', () => {
    expect(staggerContainer).toHaveProperty('initial')
    expect(staggerContainer).toHaveProperty('animate')
    expect(staggerContainer.animate.transition).toHaveProperty('staggerChildren', 0.06)
    expect(staggerContainer.animate.transition).toHaveProperty('delayChildren', 0.05)
  })

  it('pulseVariants has animate with scale/opacity arrays', () => {
    expect(pulseVariants).toHaveProperty('animate')
    expect(Array.isArray(pulseVariants.animate.scale)).toBe(true)
    expect(Array.isArray(pulseVariants.animate.opacity)).toBe(true)
    expect(pulseVariants.animate.transition).toHaveProperty('repeat', Infinity)
  })

  it('reducedMotionVariants has zero-duration animate', () => {
    expect(reducedMotionVariants).toHaveProperty('initial')
    expect(reducedMotionVariants).toHaveProperty('animate')
    expect(reducedMotionVariants).toHaveProperty('exit')
    expect(reducedMotionVariants.animate.transition).toHaveProperty('duration', 0)
  })
})

describe('hover helpers', () => {
  it('hoverScale has whileHover and whileTap', () => {
    expect(hoverScale).toHaveProperty('whileHover')
    expect(hoverScale).toHaveProperty('whileTap')
    expect(hoverScale.whileHover.scale).toBe(1.02)
    expect(hoverScale.whileTap.scale).toBe(0.98)
  })

  it('hoverLift has whileHover with y offset', () => {
    expect(hoverLift).toHaveProperty('whileHover')
    expect(hoverLift.whileHover.y).toBe(-2)
    expect(hoverLift.whileTap.scale).toBe(0.98)
  })
})

describe('withReducedMotion', () => {
  it('returns reducedMotionVariants when prefersReduced is true', () => {
    const result = withReducedMotion(pageVariants, true)
    expect(result).toBe(reducedMotionVariants)
  })

  it('returns original variants when prefersReduced is false', () => {
    const result = withReducedMotion(pageVariants, false)
    expect(result).toBe(pageVariants)
  })
})
