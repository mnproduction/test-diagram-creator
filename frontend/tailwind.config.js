/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'clickup-purple': '#7b68ee',
        'clickup-pink': '#ff5ccd',
        'clickup-blue': '#3366ff', 
        'clickup-green': '#00d5aa',
        'clickup-orange': '#ff8a00',
        'clickup-yellow': '#ffd700'
      },
      backgroundImage: {
        'clickup-gradient': 'linear-gradient(135deg, #7b68ee 0%, #ff5ccd 100%)',
        'hero-gradient': 'linear-gradient(135deg, #3366ff 0%, #7b68ee 50%, #ff5ccd 100%)',
        'success-gradient': 'linear-gradient(135deg, #00d5aa 0%, #3366ff 100%)',
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-subtle': 'bounce 2s infinite',
      }
    },
  },
  plugins: [],
} 