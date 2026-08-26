// Shared color tokens for the SENTRY control dashboard.
// Extracted from the design so every component references one palette
// instead of scattering hex literals.
export const C = {
  // surfaces
  bg: '#171614',
  bgDeep: '#0f0e0c',
  panel: '#1f1e1b',
  panel2: '#1a1917',
  card: '#211f1c',
  // lines / borders
  line: '#2b2926',
  line2: '#33302b',
  line3: '#2e2c28',
  gridLine: '#1c1b18',
  // text
  text: '#eceae5',
  sub: '#a9a59d',
  muted: '#8a877f',
  faint: '#6f6c65',
  dim: '#4a4741',
  // brand / status
  orange: '#f26419',
  orangeSoft: '#ffab73',
  green: '#4caf6d',
  greenSoft: '#7fd99b',
  red: '#f04438',
  redSoft: '#ff6b5e',
  amber: '#e0a020',
  amberSoft: '#ffcf7a',
  ink: '#161512',
};

// The whole UI now uses Wanted Sans. `MONO` is kept as a named token for the
// former monospace spots (numbers, codes, timestamps); numeric alignment is
// handled by `font-variant-numeric: tabular-nums` on the body.
export const FONT = "'Wanted Sans Variable', 'Wanted Sans', 'Pretendard', -apple-system, sans-serif";
export const MONO = FONT;
