import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    // jsdom >= 25 made localStorage/sessionStorage opt-in until a URL is set.
    // Without this, localStorage.getItem is `undefined` and any code path
    // that touches storage in a render (e.g. ThemeProvider) crashes.
    environmentOptions: {
      jsdom: {
        url: 'http://localhost:3000',
      },
    },
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/**/__tests__/**',
        'src/test/**',
        'src/components/ui/**',
        'src/types/**',
        'src/vite-env.d.ts',
        'src/main.tsx',
      ],
      // Global thresholds reflect project-wide coverage (many pages/layouts/stores
      // are awaiting tests in future waves). The tested surface (shared components,
      // chat components, utilities) exceeds 90% coverage.
      thresholds: {
        lines: 25,
        functions: 25,
        branches: 25,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
