import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'

const mcWalletTheme = {
  dark: false,
  colors: {
    primary: '#4F46E5',
    'primary-darken-1': '#4338CA',
    secondary: '#0EA5B7',
    success: '#16A34A',
    error: '#DC2626',
    warning: '#D97706',
    info: '#2563EB',
    background: '#F5F6FB',
    surface: '#FFFFFF',
  },
}

export default createVuetify({
  theme: {
    defaultTheme: 'mcWalletTheme',
    themes: { mcWalletTheme },
  },
  defaults: {
    VCard: {
      rounded: 'lg',
      elevation: '2',
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable',
      color: 'primary',
    },
    VSelect: {
      variant: 'outlined',
      density: 'comfortable',
      color: 'primary',
    },
    VFileInput: {
      variant: 'outlined',
      density: 'comfortable',
      color: 'primary',
    },
    VBtn: {
      rounded: 'lg',
    },
    VAlert: {
      rounded: 'lg',
    },
  },
})
