import '@testing-library/jest-dom/vitest'

// Mock scrollIntoView (not supported in jsdom)
Element.prototype.scrollIntoView = () => {}
