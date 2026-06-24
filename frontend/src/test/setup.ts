import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// ────────────────────────────────────────────────────────────────────────────
// Clean up after each test
// ────────────────────────────────────────────────────────────────────────────

afterEach(() => {
  cleanup();
});

// ────────────────────────────────────────────────────────────────────────────
// Mock IntersectionObserver (used by MessageList, etc.)
// ────────────────────────────────────────────────────────────────────────────

class MockIntersectionObserver {
  readonly root: Element | null = null;
  readonly rootMargin: string = '';
  readonly thresholds: ReadonlyArray<number> = [0];

  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  takeRecords = vi.fn(() => []);
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

// ────────────────────────────────────────────────────────────────────────────
// Mock ResizeObserver (used by recharts, etc.)
// ────────────────────────────────────────────────────────────────────────────

class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: MockResizeObserver,
});

// ────────────────────────────────────────────────────────────────────────────
// Mock matchMedia (used by dark mode, useReducedMotion, etc.)
// ────────────────────────────────────────────────────────────────────────────

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// ────────────────────────────────────────────────────────────────────────────
// Mock scrollTo
// ────────────────────────────────────────────────────────────────────────────

Object.defineProperty(window, 'scrollTo', {
  writable: true,
  value: vi.fn(),
});

// ────────────────────────────────────────────────────────────────────────────
// Mock getComputedStyle (used by framer-motion)
// ────────────────────────────────────────────────────────────────────────────

const originalGetComputedStyle = window.getComputedStyle;
window.getComputedStyle = (elt, pseudoElt) => {
  const style = originalGetComputedStyle(elt, pseudoElt);
  return style;
};

// ────────────────────────────────────────────────────────────────────────────
// Suppress specific console errors during tests
// ────────────────────────────────────────────────────────────────────────────

const originalConsoleError = console.error;
console.error = (...args: unknown[]) => {
  if (
    typeof args[0] === 'string' &&
    args[0].includes('Inside a test was not wrapped in act')
  ) {
    return;
  }
  originalConsoleError.call(console, ...args);
};
