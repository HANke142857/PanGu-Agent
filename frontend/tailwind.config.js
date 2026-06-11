/** @type {import('tailwindcss').Config} */
// IDMAS Industrial Workspace Theme —— 颜色由 CSS 变量驱动，支持 light / dark(驾驶舱) 切换
const v = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: v("--canvas"),
        panel: v("--panel"),
        "panel-2": v("--panel-2"),
        line: v("--line"),
        "line-strong": v("--line-strong"),
        ink: v("--ink"),
        "ink-2": v("--ink-2"),
        "ink-3": v("--ink-3"),
        "ink-4": v("--ink-4"),
        industrial: {
          DEFAULT: v("--industrial"),
          600: v("--industrial-600"),
          50: v("--industrial-50"),
        },
        accent: v("--accent"),
        ok: { DEFAULT: v("--ok"), 50: v("--ok-50") },
        warn: { DEFAULT: v("--warn"), 50: v("--warn-50") },
        danger: { DEFAULT: v("--danger"), 50: v("--danger-50") },
        proc: { DEFAULT: v("--proc"), 50: v("--proc-50") },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "Segoe UI", "Microsoft YaHei", "PingFang SC", "Noto Sans SC", "sans-serif"],
        mono: ["SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      fontSize: {
        "2xs": ["11px", "16px"],
        xs: ["12px", "16px"],
        sm: ["13px", "18px"],
        base: ["14px", "20px"],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(8,12,20,0.04), 0 1px 3px rgba(8,12,20,0.06)",
        drawer: "-12px 0 32px rgba(8,12,20,0.28)",
        pop: "0 8px 28px rgba(8,12,20,0.18)",
        glow: "0 0 0 1px rgb(var(--accent) / 0.4), 0 0 16px rgb(var(--accent) / 0.35)",
      },
      keyframes: {
        flow: { "0%": { backgroundPosition: "0 0" }, "100%": { backgroundPosition: "16px 0" } },
        pulseGlow: {
          "0%,100%": { boxShadow: "0 0 0 0 rgb(var(--proc) / 0.45)" },
          "50%": { boxShadow: "0 0 0 5px rgb(var(--proc) / 0)" },
        },
      },
      animation: {
        flow: "flow 0.6s linear infinite",
        "pulse-glow": "pulseGlow 1.6s ease-out infinite",
      },
    },
  },
  plugins: [],
};
