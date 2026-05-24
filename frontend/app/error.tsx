'use client';

import Link from 'next/link';

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-red-500 mb-4">500</h1>
        <h2 className="text-2xl font-semibold text-dark mb-4">Internal Server Error</h2>
        <p className="text-gray-600 mb-4">
          Something went wrong on our end. Please try again later.
        </p>
        {error?.message && (
          <details className="mb-6 text-left bg-gray-100 p-4 rounded-lg max-w-md mx-auto">
            <summary className="cursor-pointer font-medium text-sm">Error details</summary>
            <pre className="mt-2 text-xs overflow-auto">{error.message}</pre>
          </details>
        )}
        <div className="flex gap-4 justify-center">
          <button
            onClick={reset}
            className="bg-primary hover:bg-blue-600 text-white px-6 py-3 rounded-lg transition-colors"
          >
            Try Again
          </button>
          <Link href="/dashboard">
            <button className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-6 py-3 rounded-lg transition-colors">
              Return to Dashboard
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}
