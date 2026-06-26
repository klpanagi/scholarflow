import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import {
  FileText,
  Sparkles,
  Users,
  Swords,
  ScrollText,
  Settings2,
  GraduationCap,
  BookOpen,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/shared/PageHeader'
import { staggerContainer, cardVariants, withReducedMotion, useReducedMotion } from '@/lib/motion'
import { learningSections } from '@/content/learning'
import type { LucideIconName, Difficulty } from '@/content/learning'

// ========================================================================
// Icon resolution — map string names → Lucide components
// ========================================================================

const ICONS: Record<LucideIconName, LucideIcon> = {
  FileText,
  Sparkles,
  Users,
  Swords,
  ScrollText,
  Settings2,
  GraduationCap,
  BookOpen,
}

// ========================================================================
// Helpers
// ========================================================================

const difficultyVariant = (
  d: Difficulty,
): 'default' | 'secondary' | 'destructive' | 'outline' => {
  switch (d) {
    case 'Beginner':
      return 'secondary'
    case 'Intermediate':
      return 'default'
    case 'Advanced':
      return 'destructive'
  }
}

// ========================================================================
// Main Component
// ========================================================================

export default function LearningPage() {
  const prefersReducedMotion = useReducedMotion()
  const container = withReducedMotion(staggerContainer, prefersReducedMotion)
  const card = withReducedMotion(cardVariants, prefersReducedMotion)

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* ================================================================= */}
      {/* Hero Section                                                     */}
      {/* ================================================================= */}
      <section className="flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <GraduationCap className="h-6 w-6" />
        </div>
        <PageHeader
          title="Learning"
          description="Deepen your understanding of ScholarFlow's architecture, agents, and workflows."
          className="mb-0 flex-1"
        />
      </section>

      {/* ================================================================= */}
      {/* Topic Cards Grid                                                 */}
      {/* ================================================================= */}
      <motion.div
        variants={container}
        initial="initial"
        animate="animate"
        className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3"
      >
        {learningSections.map((section) => {
          const Icon = ICONS[section.icon]

          return (
            <motion.div key={section.id} variants={card}>
              <Link
                to={`/learning/${section.slug}`}
                className="group block h-full"
              >
                <Card className="h-full transition-all duration-300 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5">
                  <CardHeader>
                    <div className="mb-3 flex items-center justify-between">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="h-5 w-5" />
                      </div>
                      <Badge variant={difficultyVariant(section.difficulty)}>
                        {section.difficulty}
                      </Badge>
                    </div>
                    <CardTitle className="font-display">{section.title}</CardTitle>
                    <CardDescription>{section.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">
                        {section.readingMinutes} min read
                      </span>
                      <span className="font-medium text-primary transition-all group-hover:translate-x-0.5">
                        Read more <span aria-hidden="true">→</span>
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          )
        })}
      </motion.div>
    </div>
  )
}

LearningPage.displayName = 'LearningPage'
