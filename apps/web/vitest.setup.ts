import "@testing-library/jest-dom";

// Polyfill ResizeObserver for jsdom
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserverStub;
