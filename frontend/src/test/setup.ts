import '@testing-library/jest-dom/vitest';

// Mock ResizeObserver for Recharts ResponsiveContainer in jsdom
(globalThis as any).ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
