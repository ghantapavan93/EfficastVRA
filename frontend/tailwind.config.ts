import type { Config } from "tailwindcss";

/** The FORGE SYSTEM — semantic tokens map to CSS variables defined in app/globals.css. */
const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--forge-bg)",
        raised: "var(--forge-bg-raised)",
        surface: {
          1: "var(--surface-1)",
          2: "var(--surface-2)",
          3: "var(--surface-3)",
        },
        line: { DEFAULT: "var(--line)", strong: "var(--line-strong)" },
        ink: {
          hi: "var(--text-hi)",
          DEFAULT: "var(--text)",
          mut: "var(--text-mut)",
          faint: "var(--text-faint)",
        },
        brand: { DEFAULT: "var(--brand)", press: "var(--brand-press)", soft: "var(--brand-soft)" },
        agent: { DEFAULT: "var(--agent)", soft: "var(--agent-soft)" },
        verified: { DEFAULT: "var(--verified)", soft: "var(--verified-soft)" },
        pending: { DEFAULT: "var(--pending)", soft: "var(--pending-soft)" },
        warning: { DEFAULT: "var(--warning)", soft: "var(--warning-soft)" },
        failure: { DEFAULT: "var(--failure)", soft: "var(--failure-soft)" },
        approval: { DEFAULT: "var(--approval)", soft: "var(--approval-soft)" },
        evidence: { DEFAULT: "var(--evidence)", soft: "var(--evidence-soft)" },
        steel: "var(--muted)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      borderRadius: {
        sm: "6px",
        DEFAULT: "10px",
        lg: "14px",
        pill: "999px",
      },
      boxShadow: {
        e1: "0 1px 0 0 rgba(255,255,255,.03) inset, 0 1px 2px rgba(0,0,0,.4)",
        e2: "0 1px 0 0 rgba(255,255,255,.04) inset, 0 6px 20px -8px rgba(0,0,0,.6)",
        e3: "0 1px 0 0 rgba(255,255,255,.05) inset, 0 18px 50px -16px rgba(0,0,0,.7)",
        glow: "0 0 0 1px var(--agent-soft), 0 0 28px -6px var(--agent-soft)",
      },
      transitionTimingFunction: {
        enter: "cubic-bezier(.16,1,.3,1)",
        exit: "cubic-bezier(.4,0,1,1)",
        state: "cubic-bezier(.2,.8,.2,1)",
        alert: "cubic-bezier(.3,.7,.1,1)",
      },
      keyframes: {
        "fade-up": { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "none" } },
        "pulse-soft": { "0%,100%": { opacity: "1" }, "50%": { opacity: ".45" } },
        shimmer: { from: { backgroundPosition: "-200% 0" }, to: { backgroundPosition: "200% 0" } },
      },
      animation: {
        "fade-up": "fade-up .26s cubic-bezier(.16,1,.3,1)",
        "pulse-soft": "pulse-soft 2.4s ease-in-out infinite",
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
