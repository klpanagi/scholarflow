import { describe, it, expect } from 'vitest'
import {
  learningSections,
  learningSectionSchema,
  getSectionBySlug,
  LUCIDE_ICON_NAMES,
} from '@/content/learning'

const EXPECTED_SLUGS = [
  'assets',
  'cult',
  'roles',
  'strategies',
  'skills',
  'configs',
] as const

const EXPECTED_DIFFICULTIES = [
  'Beginner',
  'Intermediate',
  'Advanced',
] as const

const EXPECTED_BLOCK_TYPES = [
  'text',
  'diagram',
  'list',
  'callout',
] as const

const URL_SAFE = /^[a-z0-9-]+$/

describe('learningSections', () => {
  it('has exactly 6 sections', () => {
    expect(learningSections).toHaveLength(6)
  })

  it('contains the canonical slugs in order', () => {
    const slugs = learningSections.map((s) => s.slug)
    expect(slugs).toEqual(EXPECTED_SLUGS)
  })

  it('has unique slugs', () => {
    const slugs = learningSections.map((s) => s.slug)
    expect(new Set(slugs).size).toBe(slugs.length)
  })
})

describe('slug format', () => {
  it('each slug matches the URL-safe regex /^[a-z0-9-]+$/', () => {
    for (const s of learningSections) {
      expect(s.slug).toMatch(URL_SAFE)
    }
  })

  it('each id matches the URL-safe regex /^[a-z0-9-]+$/', () => {
    for (const s of learningSections) {
      expect(s.id).toMatch(URL_SAFE)
    }
  })
})

describe('difficulty', () => {
  it('each difficulty is one of Beginner | Intermediate | Advanced', () => {
    for (const s of learningSections) {
      expect(EXPECTED_DIFFICULTIES).toContain(s.difficulty)
    }
  })
})

describe('readingMinutes', () => {
  it('each readingMinutes is a positive integer', () => {
    for (const s of learningSections) {
      expect(Number.isInteger(s.readingMinutes)).toBe(true)
      expect(s.readingMinutes).toBeGreaterThan(0)
    }
  })
})

describe('icon', () => {
  it('each icon is a member of LUCIDE_ICON_NAMES', () => {
    for (const s of learningSections) {
      expect(LUCIDE_ICON_NAMES).toContain(s.icon)
    }
  })
})

describe('sections', () => {
  it('every section has at least 3 content blocks', () => {
    for (const s of learningSections) {
      expect(s.sections.length).toBeGreaterThanOrEqual(3)
    }
  })

  it('every block has a valid type of text | diagram | list | callout', () => {
    for (const s of learningSections) {
      for (const block of s.sections) {
        expect(EXPECTED_BLOCK_TYPES).toContain(block.type)
      }
    }
  })
})

describe('learningSectionSchema', () => {
  const firstSection = learningSections[0]

  it('parses a valid section without throwing', () => {
    expect(() => learningSectionSchema.parse(firstSection)).not.toThrow()
  })

  it('rejects a typo in difficulty (Intermidiate) by throwing', () => {
    const bad = { ...firstSection, difficulty: 'Intermidiate' }
    expect(() => learningSectionSchema.parse(bad)).toThrow()
  })

  it('rejects an invalid slug (with space and uppercase) by throwing', () => {
    const bad = { ...firstSection, slug: 'INVALID SLUG' }
    expect(() => learningSectionSchema.parse(bad)).toThrow()
  })

  it('rejects readingMinutes of 0 by throwing', () => {
    const bad = { ...firstSection, readingMinutes: 0 }
    expect(() => learningSectionSchema.parse(bad)).toThrow()
  })

  it('rejects readingMinutes of -1 by throwing', () => {
    const bad = { ...firstSection, readingMinutes: -1 }
    expect(() => learningSectionSchema.parse(bad)).toThrow()
  })
})

describe('getSectionBySlug', () => {
  it('returns the Cult section for slug "cult"', () => {
    const section = getSectionBySlug('cult')
    expect(section).toBeDefined()
    expect(section?.slug).toBe('cult')
    expect(section?.title).toContain('Cult')
  })

  it('returns undefined for an unknown slug ("nope")', () => {
    expect(getSectionBySlug('nope')).toBeUndefined()
  })
})
