import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';
import { Toaster } from 'react-hot-toast';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'LostMindAI - AI Chat Assistant',
  description: 'Advanced AI chat assistant powered by Google Gemini with RAG capabilities, knowledge management, and real-time conversations.',
  keywords: ['AI', 'chat', 'assistant', 'Gemini', 'LostMindAI', 'RAG', 'knowledge management'],
  authors: [{ name: 'LostMindAI', url: 'https://lostmindai.com' }],
  creator: 'LostMindAI',
  publisher: 'LostMindAI',
  viewport: 'width=device-width, initial-scale=1',
  robots: 'index, follow',
  
  // Open Graph / Facebook
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://lostmindai.com',
    siteName: 'LostMindAI',
    title: 'LostMindAI - AI Chat Assistant',
    description: 'Advanced AI chat assistant with RAG capabilities and knowledge management.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'LostMindAI Chat Assistant',
      },
    ],
  },
  
  // Twitter
  twitter: {
    card: 'summary_large_image',
    title: 'LostMindAI - AI Chat Assistant',
    description: 'Advanced AI chat assistant with RAG capabilities and knowledge management.',
    creator: '@lostmindai',
    images: ['/og-image.png'],
  },
  
  // Apple
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'LostMindAI',
  },
  
  // Microsoft
  msApplication: {
    tileColor: '#0ea5e9',
  },
  
  // Theme
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
  
  // Icons
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180' },
    ],
    other: [
      { rel: 'mask-icon', url: '/safari-pinned-tab.svg', color: '#0ea5e9' },
    ],
  },
  
  // Manifest
  manifest: '/manifest.json',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <head>
        {/* Additional meta tags for better SEO and performance */}
        <meta name="format-detection" content="telephone=no" />
        <meta name="theme-color" content="#0ea5e9" />
        <meta name="color-scheme" content="light dark" />
        
        {/* Preconnect to backend for better performance */}
        <link rel="preconnect" href={process.env.BACKEND_URL || 'http://localhost:8000'} />
        <link rel="dns-prefetch" href={process.env.BACKEND_URL || 'http://localhost:8000'} />
        
        {/* Security headers via meta tags */}
        <meta httpEquiv="X-Content-Type-Options" content="nosniff" />
        <meta httpEquiv="X-Frame-Options" content="DENY" />
        <meta httpEquiv="X-XSS-Protection" content="1; mode=block" />
        
        {/* Performance hints */}
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="application-name" content="LostMindAI" />
      </head>
      <body className="min-h-screen bg-gradient-to-br from-secondary-50 to-primary-50 dark:from-secondary-900 dark:to-secondary-800 font-sans antialiased">
        <Providers>
          {/* Main application content */}
          <main className="relative min-h-screen">
            {children}
          </main>
          
          {/* Global toast notifications */}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              className: 'bg-white dark:bg-secondary-800 text-secondary-900 dark:text-secondary-100 border border-secondary-200 dark:border-secondary-700 shadow-soft',
              style: {
                borderRadius: '12px',
                padding: '12px 16px',
                fontSize: '14px',
                fontWeight: '500',
              },
              success: {
                iconTheme: {
                  primary: '#22c55e',
                  secondary: '#ffffff',
                },
              },
              error: {
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#ffffff',
                },
              },
            }}
          />
          
          {/* Loading indicator for page transitions */}
          <div id="page-loader" className="hidden fixed inset-0 bg-white/80 dark:bg-secondary-900/80 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="flex flex-col items-center space-y-4">
              <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-500 rounded-full animate-spin"></div>
              <p className="text-sm text-secondary-600 dark:text-secondary-400 font-medium">Loading...</p>
            </div>
          </div>
        </Providers>
        
        {/* Service Worker registration for PWA capabilities */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js');
                });
              }
            `,
          }}
        />
        
        {/* Performance monitoring */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if (typeof window !== 'undefined') {
                // Log core web vitals
                function logWebVital(metric) {
                  console.log('[WebVital]', metric.name, metric.value);
                }
                
                // Performance observer for monitoring
                if ('PerformanceObserver' in window) {
                  const observer = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                      if (entry.entryType === 'navigation') {
                        console.log('[Navigation]', entry.duration + 'ms');
                      }
                    }
                  });
                  observer.observe({ entryTypes: ['navigation', 'measure'] });
                }
              }
            `,
          }}
        />
      </body>
    </html>
  );
}