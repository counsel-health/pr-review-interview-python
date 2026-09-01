/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  safelist: [
    {
      pattern: /(text|bg)-brand-*/,
    },
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        content: {
          primary: "hsl(var(--content-primary))",
          secondary: "hsl(var(--content-secondary))",
          tertiary: "hsl(var(--content-tertiary))",
          accent: "hsl(var(--content-accent))",
          disabled: "hsl(var(--content-disabled))",
          onDark: {
            primary: "hsl(var(--content-onDark) / 1.00)",
            secondary: "hsl(var(--content-onDark) / 0.60)",
            tertiary: "hsl(var(--content-onDark) / 0.30)",
          },
        },
        button: {
          primary: {
            background: "hsl(var(--button-primary-background))",
            content: "hsl(var(--button-primary-content))",
          },
          secondary: {
            background: "hsl(var(--button-secondary-background))",
            content: "hsl(var(--button-secondary-content))",
          },
          disabled: {
            background: "hsl(var(--button-disabled-background))",
            content: "hsl(var(--button-disabled-content))",
          },
          "tiny-close": {
            background: "hsl(var(--button-tiny-close-background) / 0.50)",
            content: "hsl(var(--button-tiny-close-content))",
          },
        },
        negative: "hsl(var(--negative))",
        positive: "hsl(var(--positive))",
        warning: "hsl(var(--warning))",
        border: {
          DEFAULT: "hsl(var(--border))",
          onLight: "hsl(var(--border-onLight) / 0.10)",
          onDark: "hsl(var(--border-onDark) / 0.10)",
        },
        brand: {
          teal: {
            DEFAULT: "hsl(var(--brand-teal))",
            deemph: "var(--brand-teal-deemph)",
          },
          orange: {
            DEFAULT: "hsl(var(--brand-orange))",
            deemph: "var(--brand-orange-deemph)",
          },
          purple: {
            DEFAULT: "var(--brand-purple)",
            deemph: "var(--brand-purple-deemph)",
          },
        },
        background: {
          surface: "var(--background-surface)",
          inset: "var(--background-inset)",
        },
        bubble: {
          patient: {
            background: "hsl(var(--bubble-patient-background))",
            text: "hsl(var(--bubble-patient-text))",
          },
        },
        tab: {
          selected: {
            onSurface: "hsl(var(--tab-selected-onSurface))",
            onInset: "hsl(var(--tab-selected-onInset))",
          },
        },
      },
      borderRadius: {
        "3xl": "calc(var(--radius) + 12px)",
        "2xl": "calc(var(--radius) + 8px)",
        xl: "calc(var(--radius) + 4px)",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 4px)",
        sm: "calc(var(--radius) - 8px)",
        xs: "calc(var(--radius) - 12px)",
        "2xs": "calc(var(--radius) - 16px)",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        fadeIn: "fadeIn 0.7s ease-out",
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
