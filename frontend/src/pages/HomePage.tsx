import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import {
  BrainCircuit,
  Wand2,
  Search,
  FileSearch,
  BookOpen,
  Sparkles,
  Github,
  Twitter,
  Linkedin,
  ArrowRight,
} from "lucide-react"

const features = [
  {
    icon: BrainCircuit,
    title: "AI Agents",
    description:
      "Specialized research agents that search, review, write, and recommend — all powered by state-of-the-art LLMs.",
  },
  {
    icon: Wand2,
    title: "Skills Library",
    description:
      "Reusable academic skills for literature synthesis, novelty assessment, venue matching, and more.",
  },
  {
    icon: Search,
    title: "Smart Search",
    description:
      "Multi-source search across Semantic Scholar, arXiv, CrossRef, and OpenAlex with AI-powered ranking.",
  },
  {
    icon: FileSearch,
    title: "Paper Review",
    description:
      "7-stage automated review pipeline with citation analysis, methodology checks, and actionable feedback.",
  },
]

const stats = [
  { value: "50K+", label: "Papers Analyzed" },
  { value: "120+", label: "Active Researchers" },
  { value: "1M+", label: "Citations Tracked" },
  { value: "99.9%", label: "Platform Uptime" },
]

const footerLinks = {
  Product: [
    { label: "Features", href: "#features" },
    { label: "Pricing", href: "#pricing" },
    { label: "Documentation", href: "#docs" },
  ],
  Resources: [
    { label: "Blog", href: "#blog" },
    { label: "Research", href: "#research" },
    { label: "Help Center", href: "#help" },
  ],
  Company: [
    { label: "About", href: "#about" },
    { label: "Contact", href: "#contact" },
    { label: "Privacy", href: "#privacy" },
  ],
}

export default function HomePage() {
  return (
    <div className="flex flex-col overflow-x-hidden">
      {/* ──────────────── HERO ──────────────── */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden -mx-4 md:-mx-8 w-[calc(100%+2rem)] md:w-[calc(100%+4rem)] -mt-8 bg-gradient-to-b from-navy-950 via-navy-900 to-navy-950">
        {/* Animated mesh gradient orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -left-40 w-[500px] h-[500px] bg-gold-500/10 rounded-full blur-3xl animate-pulse" />
          <div className="absolute top-1/3 -right-20 w-[400px] h-[400px] bg-amber-400/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "1s" }} />
          <div className="absolute -bottom-40 left-1/3 w-[600px] h-[600px] bg-navy-700/50 rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gold-500/5 rounded-full blur-3xl" />
        </div>

        {/* Floating decorative icons */}
        <div className="absolute top-1/4 left-[10%] text-gold-500/15 hidden lg:block animate-bounce" style={{ animationDuration: "4s" }}>
          <BookOpen className="w-14 h-14" />
        </div>
        <div className="absolute top-1/3 right-[12%] text-amber-400/15 hidden lg:block animate-bounce" style={{ animationDuration: "5s", animationDelay: "0.5s" }}>
          <BrainCircuit className="w-11 h-11" />
        </div>
        <div className="absolute bottom-1/4 left-[20%] text-gold-400/10 hidden lg:block animate-bounce" style={{ animationDuration: "6s", animationDelay: "1s" }}>
          <Sparkles className="w-9 h-9" />
        </div>
        <div className="absolute bottom-1/3 right-[22%] text-amber-300/10 hidden lg:block animate-bounce" style={{ animationDuration: "4.5s", animationDelay: "1.5s" }}>
          <Search className="w-10 h-10" />
        </div>

        {/* Hero content */}
        <div className="relative z-10 w-full max-w-5xl mx-auto text-center px-4 space-y-10">
          <div className="space-y-6">
            {/* Gold badge */}
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-gold-500/25 bg-gold-500/10 text-gold-300 text-sm font-medium tracking-wide">
              <Sparkles className="w-4 h-4" />
              AI-Powered Academic Research Platform
            </div>

            {/* Main headline — gold gradient */}
            <h1 className="text-6xl md:text-8xl lg:text-9xl font-bold tracking-tight leading-none text-balance">
              <span className="bg-gradient-to-r from-gold-300 via-gold-400 to-amber-300 bg-clip-text text-transparent">
                ScholarFlow
              </span>
            </h1>

            {/* Tagline */}
            <p className="text-lg md:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed font-light">
              AI-powered research workspace for academic excellence.
              <br />
              Search, write, review, and discover with intelligent agents.
            </p>
          </div>

          {/* CTAs */}
          <div className="flex gap-4 justify-center flex-wrap">
            <Button
              size="lg"
              className="bg-gradient-to-r from-gold-500 to-amber-500 hover:from-gold-600 hover:to-amber-600 text-white font-semibold shadow-lg shadow-gold-500/25 hover:shadow-gold-500/40 transition-all duration-300 text-base px-8 py-6 h-auto"
              asChild
            >
              <Link to="/register">
                Get Started
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="border-gold-500/30 text-gold-300 hover:bg-gold-500/10 hover:border-gold-500/50 text-base px-8 py-6 h-auto"
              asChild
            >
              <Link to="/login">Sign In</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ──────────────── FEATURES ──────────────── */}
      <section id="features" className="py-20 md:py-28">
        <div className="max-w-6xl mx-auto text-center space-y-16">
          {/* Section header */}
          <div className="space-y-4">
            <span className="inline-block text-xs font-semibold tracking-[0.2em] uppercase text-gold-500">
              Capabilities
            </span>
            <h2 className="text-3xl md:text-5xl font-bold text-balance">
              Everything you need for{" "}
              <span className="bg-gradient-to-r from-gold-400 to-amber-400 bg-clip-text text-transparent">
                academic research
              </span>
            </h2>
            <p className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto">
              Powerful tools designed to accelerate every stage of your research workflow
            </p>
          </div>

          {/* Feature cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 md:gap-6">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="group relative bg-card/60 backdrop-blur-xl border border-border/50 rounded-2xl p-8 hover:border-gold-500/40 transition-all duration-300 hover:shadow-lg hover:shadow-gold-500/5 hover:-translate-y-1"
              >
                {/* Top gradient line on hover */}
                <div className="absolute inset-x-0 top-0 h-0.5 scale-x-0 bg-gradient-to-r from-transparent via-gold-500/60 to-transparent transition-transform duration-300 group-hover:scale-x-100 rounded-t-2xl" />

                {/* Icon */}
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-gold-500/20 to-amber-500/20 flex items-center justify-center mb-6 group-hover:from-gold-500/30 group-hover:to-amber-500/30 transition-all duration-300">
                  <feature.icon className="w-7 h-7 text-gold-400" />
                </div>

                {/* Title */}
                <h3 className="text-xl font-bold mb-3 text-left">{feature.title}</h3>

                {/* Description */}
                <p className="text-sm text-muted-foreground leading-relaxed text-left">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──────────────── STATS ──────────────── */}
      <section className="relative py-20 md:py-28 -mx-4 md:-mx-8 w-[calc(100%+2rem)] md:w-[calc(100%+4rem)] bg-gradient-to-r from-navy-900 via-navy-800 to-navy-900 border-y border-gold-500/10">
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12 text-center">
            {stats.map((stat) => (
              <div key={stat.label} className="space-y-2">
                <div className="text-4xl md:text-5xl lg:text-6xl font-bold bg-gradient-to-b from-gold-300 to-amber-400 bg-clip-text text-transparent">
                  {stat.value}
                </div>
                <div className="text-xs md:text-sm text-slate-400 uppercase tracking-widest font-medium">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──────────────── CTA ──────────────── */}
      <section className="relative py-24 md:py-36 -mx-4 md:-mx-8 w-[calc(100%+2rem)] md:w-[calc(100%+4rem)] bg-gradient-to-br from-gold-950 via-navy-950 to-navy-950 overflow-hidden">
        {/* Background orbs */}
        <div className="pointer-events-none absolute top-0 right-0 w-[500px] h-[500px] bg-gold-500/10 rounded-full blur-3xl translate-x-1/3 -translate-y-1/4" />
        <div className="pointer-events-none absolute bottom-0 left-0 w-[400px] h-[400px] bg-amber-500/5 rounded-full blur-3xl -translate-x-1/4 translate-y-1/4" />

        <div className="relative z-10 max-w-3xl mx-auto text-center px-4 space-y-8">
          <h2 className="text-3xl md:text-5xl font-bold text-balance text-white">
            Ready to accelerate your research?
          </h2>
          <p className="text-base md:text-lg text-slate-300 max-w-xl mx-auto">
            Join hundreds of researchers who are already using ScholarFlow to
            streamline their academic workflow.
          </p>
          <div className="flex gap-4 justify-center flex-wrap pt-4">
            <Button
              size="lg"
              className="bg-gradient-to-r from-gold-400 to-amber-500 hover:from-gold-500 hover:to-amber-600 text-navy-950 font-bold shadow-lg shadow-gold-500/25 hover:shadow-gold-500/40 transition-all duration-300 text-base px-10 py-6 h-auto"
              asChild
            >
              <Link to="/register">
                Get Started Free
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
          </div>
          <p className="text-sm text-slate-400">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-gold-400 hover:text-gold-300 underline underline-offset-2 transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </section>

      {/* ──────────────── FOOTER ──────────────── */}
      <footer className="-mx-4 md:-mx-8 w-[calc(100%+2rem)] md:w-[calc(100%+4rem)] bg-navy-950 border-t border-gold-500/10">
        <div className="max-w-6xl mx-auto px-4 py-16 md:py-20">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-12 md:gap-8">
            {/* Brand column */}
            <div className="space-y-5 sm:col-span-2 md:col-span-1">
              <Link
                to="/"
                className="inline-flex items-center gap-2.5 group"
              >
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-gold-400 to-gold-600 flex items-center justify-center shadow-sm shadow-gold-500/20 group-hover:shadow-gold-500/30 transition-shadow">
                  <BookOpen className="w-5 h-5 text-white" />
                </div>
                <span className="text-lg font-bold bg-gradient-to-r from-gold-300 to-amber-400 bg-clip-text text-transparent">
                  ScholarFlow
                </span>
              </Link>
              <p className="text-sm text-slate-400 leading-relaxed max-w-xs">
                AI-powered research workspace designed for academic excellence.
              </p>
            </div>

            {/* Link columns */}
            {Object.entries(footerLinks).map(([category, links]) => (
              <div key={category}>
                <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-widest mb-5">
                  {category}
                </h4>
                <ul className="space-y-3">
                  {links.map((link) => (
                    <li key={link.label}>
                      <a
                        href={link.href}
                        className="text-sm text-slate-400 hover:text-gold-400 transition-colors duration-200"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Bottom bar */}
          <div className="mt-14 pt-8 border-t border-navy-800 flex flex-col md:flex-row items-center justify-between gap-6">
            <p className="text-xs text-slate-500">
              &copy; {new Date().getFullYear()} ScholarFlow. All rights reserved.
            </p>
            <div className="flex items-center gap-5">
              <a
                href="#"
                className="text-slate-400 hover:text-gold-400 transition-colors duration-200"
                aria-label="GitHub"
              >
                <Github className="w-5 h-5" />
              </a>
              <a
                href="#"
                className="text-slate-400 hover:text-gold-400 transition-colors duration-200"
                aria-label="Twitter"
              >
                <Twitter className="w-5 h-5" />
              </a>
              <a
                href="#"
                className="text-slate-400 hover:text-gold-400 transition-colors duration-200"
                aria-label="LinkedIn"
              >
                <Linkedin className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
