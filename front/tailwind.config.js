/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class', // CSS 클래스 기반 다크 모드
  theme: {
    extend: {
      colors: {
        // MAICE 테마 색상 변수들을 Tailwind에 통합
        maice: {
          primary: 'var(--maice-primary)',
          'primary-hover': 'var(--maice-primary-hover)',
          'primary-dark': 'var(--maice-primary-dark)',
          secondary: 'var(--maice-secondary)',
          success: 'var(--maice-success)',
          warning: 'var(--maice-warning)',
          error: 'var(--maice-error)',
          'bg-primary': 'var(--maice-bg-primary)',
          'bg-secondary': 'var(--maice-bg-secondary)',
          'bg-tertiary': 'var(--maice-bg-tertiary)',
          'bg-card': 'var(--maice-bg-card)',
          'text-primary': 'var(--maice-text-primary)',
          'text-secondary': 'var(--maice-text-secondary)',
          'text-tertiary': 'var(--maice-text-tertiary)',
          'text-muted': 'var(--maice-text-muted)',
          'border-primary': 'var(--maice-border-primary)',
          'border-secondary': 'var(--maice-border-secondary)',
        }
      },
      backgroundColor: {
        'maice-bg': 'var(--maice-bg-primary)',
        'maice-card': 'var(--maice-bg-card)',
        'maice-secondary': 'var(--maice-bg-secondary)',
      },
      textColor: {
        'maice-primary': 'var(--maice-text-primary)',
        'maice-secondary': 'var(--maice-text-secondary)',
        'maice-muted': 'var(--maice-text-muted)',
      },
      borderColor: {
        'maice-primary': 'var(--maice-border-primary)',
        'maice-secondary': 'var(--maice-border-secondary)',
      },
      boxShadow: {
        'maice-sm': 'var(--maice-shadow-sm)',
        'maice-md': 'var(--maice-shadow-md)',
        'maice-lg': 'var(--maice-shadow-lg)',
        'maice-xl': 'var(--maice-shadow-xl)',
      }
    },
  },
  plugins: [],
}
