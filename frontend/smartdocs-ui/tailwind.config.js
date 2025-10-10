/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: {
        "2xl": "1280px"
      }
    },
    extend: {
      fontFamily: {
        sans: [
          '"Inter var"',
          "system-ui",
          "ui-sans-serif",
          "Helvetica",
          "Arial",
          "sans-serif"
        ]
      },
      colors: {
        brand: {
          50: "#f0f7ff",
          100: "#dceeff",
          200: "#b0dcff",
          300: "#84c9ff",
          400: "#57b7ff",
          500: "#2ba5ff",
          600: "#008cf0",
          700: "#006ec0",
          800: "#005190",
          900: "#003360",
          950: "#001a33"
        },
        surface: {
          50: "#0f1115",
          100: "#151921",
          200: "#1d2230",
          300: "#262d3c",
          400: "#31394a",
          500: "#3b4457",
          600: "#465066",
          700: "#4f5a72",
          800: "#596480",
          900: "#64708f"
        }
      },
      backgroundImage: {
        "grid-radial":
          "radial-gradient(circle at 50% 50%, rgba(43,165,255,0.12), transparent 60%)",
        "hero-glow":
          "radial-gradient(ellipse at top left, rgba(131,216,255,0.25), transparent 60%), radial-gradient(ellipse at bottom right, rgba(43,165,255,0.18), transparent 65%)"
      },
      boxShadow: {
        soft: "0 2px 4px -1px rgba(0,0,0,0.25), 0 1px 3px rgba(0,0,0,0.3)",
        "brand-glow":
          "0 0 0 1px rgba(43,165,255,0.4), 0 0 12px -2px rgba(43,165,255,0.5)"
      },
      animation: {
        "fade-in": "fade-in 0.6s ease forwards",
        "slide-up": "slide-up 0.5s cubic-bezier(.4,.64,.44,1) forwards"
      },
      keyframes: {
        "fade-in": {
          from: { opacity: 0 },
          to: { opacity: 1 }
        },
        "slide-up": {
          from: { opacity: 0, transform: "translateY(12px)" },
          to: { opacity: 1, transform: "translateY(0)" }
        }
      }
    }
  },
  plugins: []
};
