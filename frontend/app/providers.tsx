'use client';

// @clerk/nextjs ClerkProvider imports server actions incompatible with output:export.
// @clerk/clerk-react is the pure-React provider with no Next.js server dependencies.
import { ClerkProvider } from '@clerk/clerk-react';
import { ToastContainer } from '@/components/Toast';
import ErrorBoundary from '@/components/ErrorBoundary';

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <ClerkProvider publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY!} telemetry={false}>
        {children}
        <ToastContainer />
      </ClerkProvider>
    </ErrorBoundary>
  );
}
