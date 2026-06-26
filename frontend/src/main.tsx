import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './lib/queryClient'
import { Toaster } from 'sonner'
import { ThemeProvider } from './components/theme/ThemeProvider'
import App from './App'
import './styles/tokens.css'
import './styles/fonts.css'
import './index.css'

if (import.meta.env.DEV) {
  void import('@axe-core/react').then(({ default: axe }) => {
    void import('react-dom').then((ReactDOM) => {
      void axe(React, ReactDOM, 1000)
    })
  })
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
          <Toaster position="bottom-right" richColors closeButton />
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
