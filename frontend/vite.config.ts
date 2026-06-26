import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { visualizer } from 'rollup-plugin-visualizer'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // Bundle analyzer — generates dist/stats.html on every build
    visualizer({
      filename: 'dist/stats.html',
      gzipSize: true,
      brotliSize: true,
      template: 'treemap',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // Markdown / recharts deps are now hoisted into their consuming page
    // chunks, which can exceed the default 500 kB warning.
    chunkSizeWarningLimit: 1500,
    // Filter heavy / rarely-used vendor chunks out of the entry HTML
    // modulepreload list. They are still reachable via dynamic imports
    // from lazy pages, so navigation to /login, /settings, etc. still
    // loads them on demand — `/` just doesn't pay the preload cost.
    //
    // vendor-forms   — react-hook-form + zod. Unused on `/`; Lighthouse
    //                  flagged 28 kB wasted JS with it preloaded.
    modulePreload: {
      // App.tsx eagerly imports AppShell, AuthLayout, and the providers.
      // Those pull in React, Router, TanStack Query, Radix primitives,
      // framer-motion, axios, and the utils (cn, fonts, tw-animate-css)
      // BEFORE the first paint. If we don't preload all of them, the
      // browser has to parse index.js, *discover* the dynamic imports,
      // and then fetch them serially — which kills FCP/LCP. We preload
      // every chunk reachable from the entry script so the browser can
      // fetch them in parallel on the first request.
      //
      // Chunks that are NOT preloaded (and therefore loaded on demand
      // when a specific page mounts):
      //   • vendor-forms   — only used by SettingsPage
      //   • vendor-markdown / recharts deps — hoisted into their page
      //     chunks; see manualChunks comment below
      polyfill: false,
      resolveDependencies: (_filename, deps) =>
        deps.filter(
          (d) =>
            d.includes('vendor-react') ||
            d.includes('vendor-icons') ||
            d.includes('vendor-tanstack') ||
            d.includes('vendor-utils') ||
            d.includes('vendor-motion') ||
            d.includes('vendor-radix') ||
            d.includes('vendor-axios'),
        ),
    },
    rollupOptions: {
      output: {
        // Manual vendor chunk splitting.
        //
        // DELIBERATELY NOT SPLIT OUT (so Rollup hoists them to their
        // consuming page chunks and they drop out of the entry preload):
        //   • vendor-markdown — react-markdown, streamdown, remark, micromark
        //     etc. (≈894 kB raw). Only used by 5 components, all in lazy
        //     page chunks (ChatPage, RevisionPage, WorkflowsPage, …).
        //   • vendor-recharts — recharts + d3. Only used by DashboardPage.
        manualChunks: (id) => {
          if (!id.includes('node_modules')) return undefined

          // React core + scheduler (most cacheable, used everywhere)
          if (id.includes('node_modules/react/') ||
              id.includes('node_modules/react-dom/') ||
              id.includes('node_modules/scheduler/')) {
            return 'vendor-react'
          }

          // React Router (used by every route)
          if (id.includes('node_modules/react-router') ||
              id.includes('node_modules/@remix-run/router')) {
            return 'vendor-react'
          }

          // TanStack Query (used by every data-driven page)
          if (id.includes('node_modules/@tanstack')) {
            return 'vendor-tanstack'
          }

          // Icons (lucide-react)
          if (id.includes('node_modules/lucide-react')) {
            return 'vendor-icons'
          }

          // Radix UI primitives (dialog, dropdown, popover, etc.)
          if (id.includes('node_modules/@radix-ui')) {
            return 'vendor-radix'
          }

          // Framer Motion (used by AppShell transitions + button.tsx)
          if (id.includes('node_modules/framer-motion') ||
              id.includes('node_modules/motion') ||
              id.includes('node_modules/motion-utils') ||
              id.includes('node_modules/motion-dom')) {
            return 'vendor-motion'
          }

          // HTTP client
          if (id.includes('node_modules/axios') ||
              id.includes('node_modules/follow-redirects') ||
              id.includes('node_modules/form-data') ||
              id.includes('node_modules/proxy-from-env')) {
            return 'vendor-axios'
          }

          // Forms
          //
          // @floating-ui is intentionally NOT routed here — it is a
          // transitive dep of @radix-ui/react-popper. We route it into
          // vendor-utils (see below) instead. Putting it in vendor-forms
          // would force Rollup to add `import "./vendor-forms..."` at
          // the top of the entry chunk to satisfy vendor-radix's import
          // graph, which puts vendor-forms (≈30 kB gz) on the home-page
          // critical path even though no home-page code uses it.
          // Putting it in vendor-utils keeps vendor-radix lean (lower
          // TBT) and reuses a chunk that is already preloaded.
          if (id.includes('node_modules/react-hook-form') ||
              id.includes('node_modules/@hookform') ||
              id.includes('node_modules/zod')) {
            return 'vendor-forms'
          }

          // Utility / state / toast deps. NOTE: markdown tooling deps
          // (react-markdown, streamdown, remark, micromark, …) used to
          // be routed to vendor-markdown here — they are now intentionally
          // left unmatched so Rollup hoists them to their consuming page
          // chunks. Do not add a vendor-markdown rule. See header comment.
          if (id.includes('node_modules/sonner') ||
              id.includes('node_modules/cmdk') ||
              id.includes('node_modules/zustand') ||
              id.includes('node_modules/date-fns') ||
              id.includes('node_modules/react-resizable-panels') ||
              id.includes('node_modules/use-stick-to-bottom') ||
              id.includes('node_modules/use-sync-external-store') ||
              id.includes('node_modules/clsx') ||
              id.includes('node_modules/tailwind-merge') ||
              id.includes('node_modules/class-variance-authority') ||
              id.includes('node_modules/tw-animate-css') ||
              id.includes('node_modules/@fontsource') ||
              id.includes('node_modules/cookie') ||
              id.includes('node_modules/csstype') ||
              id.includes('node_modules/nanoid') ||
              id.includes('node_modules/@floating-ui') ||
              id.includes('node_modules/ms')) {
            return 'vendor-utils'
          }

          // Catch-all: return undefined so Rollup auto-groups the dep with
          // its consuming chunk. Do NOT return a named chunk here —
          // returning any name makes Vite preload it from the entry HTML,
          // which would put every unmatched dep (markdown, recharts, …)
          // on the critical path of `/`. Verified: returning 'vendor-misc'
          // here produced a 1.5 MB / 495 kB gz chunk preloaded on `/`.
          return undefined
        },
        // Stable file names for long-term caching
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
  },
})
