import type { Metadata } from 'next';
import Providers from './providers';
import '@/styles/globals.css';

export const metadata: Metadata = {
  description: 'Alex AI Financial Advisor - Your intelligent portfolio management assistant',
};

export const viewport = {
  themeColor: '#209DD7',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" />
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
        <link rel="apple-touch-icon" href="/favicon.ico" />
        <link rel="manifest" href="/manifest.json" />
      </head>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
