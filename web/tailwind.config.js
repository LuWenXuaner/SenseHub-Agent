/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        surface: "var(--surface)",
        "surface-elevated": "var(--surface-elevated)",
        border: "var(--border)",
        primary: "var(--primary)",
        "text-primary": "var(--text-primary)",
        "text-secondary": "var(--text-secondary)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        mimo: {
          bg: "var(--mimo-bg)",
          warm: "var(--mimo-warm)",
          surface: "var(--mimo-surface)",
          text: "var(--mimo-text)",
          muted: "var(--mimo-muted)",
          border: "var(--mimo-border)",
          cta: "var(--mimo-cta)",
          accent: "var(--mimo-accent)",
          link: "var(--mimo-link)",
        },
      },
      maxWidth: {
        mimo: "1120px",
      },
    },
  },
  plugins: [],
};
