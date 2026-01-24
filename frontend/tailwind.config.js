/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      typography: ({ theme }) => ({
        DEFAULT: {
          css: {
            "--tw-prose-bullets": "var(--foreground)",
          },
        },
      }),
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
