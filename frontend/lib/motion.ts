/** Forge motion tokens (seconds for framer-motion). Mirrors docs/INTERACTION_SYSTEM.md. */
export const DUR = {
  instant: 0.1,
  fast: 0.17,
  standard: 0.26,
  emphasis: 0.52,
} as const;

export const EASE = {
  enter: [0.16, 1, 0.3, 1],
  exit: [0.4, 0, 1, 1],
  state: [0.2, 0.8, 0.2, 1],
  alert: [0.3, 0.7, 0.1, 1],
} as const;

export const fadeUp = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -4 },
  transition: { duration: DUR.standard, ease: EASE.enter },
};

export const listStagger = {
  animate: { transition: { staggerChildren: 0.04 } },
};
