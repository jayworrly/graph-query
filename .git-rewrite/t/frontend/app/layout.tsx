import './globals.css'
import { Inter } from 'next/font/google'
import Navigation from './components/Navigation'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Arena Terminal - Token Analytics Dashboard',
  description: 'Real-time Arena ecosystem analytics and token exploration on Avalanche',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link href="https://cdn.jsdelivr.net/npm/remixicon@4.0.0/fonts/remixicon.css" rel="stylesheet" />
      </head>
      <body className={inter.className}>
        <div className="min-h-screen bg-gradient-to-br from-[#0f0f23] via-[#1a1a2e] to-[#16213e] w-full">
          <Navigation />
          <main className="w-full">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
} 