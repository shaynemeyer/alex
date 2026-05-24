# Feature Spec: Migrate Frontend to Next.js App Router

## Goal

Replace `frontend/pages/` (Pages Router) with `frontend/app/` (App Router). No runtime behaviour changes — same static export (`output: 'export'`), same client-side Clerk auth, same FastAPI backend.

---

## Pre-conditions

- Next.js version and `@clerk/nextjs ^6.32.0` are already installed — no package changes needed.
- `next.config.ts` stays as-is (`output: 'export'`, `reactStrictMode: true`, `images: { unoptimized: true }`).
- All pages remain `'use client'` (they use Clerk hooks and React state).

---

## Steps

### Step 1 — Create `frontend/app/layout.tsx`

Consolidates `pages/_app.tsx` and `pages/_document.tsx`.

```tsx
// frontend/app/layout.tsx
import type { Metadata } from 'next';
import { ClerkProvider } from '@clerk/nextjs';
import { ToastContainer } from '@/components/Toast';
import ErrorBoundary from '@/components/ErrorBoundary';
import '@/styles/globals.css';

export const metadata: Metadata = {
  description: 'Alex AI Financial Advisor - Your intelligent portfolio management assistant',
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
        <ErrorBoundary>
          <ClerkProvider>
            {children}
            <ToastContainer />
          </ClerkProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
```

**Note:** `ClerkProvider` in App Router does not accept `{...pageProps}` — just wrap children directly.

**Validate:** `npm run build` — should not error on the layout alone (other pages still in `pages/` until Step 3).

---

### Step 2 — Fix `frontend/components/PageTransition.tsx`

`router.events` does not exist in App Router. Replace with `usePathname`.

```tsx
'use client';
import { usePathname } from 'next/navigation';
import { useEffect, useState, ReactNode } from 'react';

export default function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [opacity, setOpacity] = useState(1);

  useEffect(() => {
    setOpacity(0);
    const t = setTimeout(() => setOpacity(1), 150);
    return () => clearTimeout(t);
  }, [pathname]);

  return (
    <div style={{ opacity, transition: 'opacity 0.15s ease' }}>{children}</div>
  );
}
```

**Validate:** Component renders without import errors.

---

### Step 3 — Migrate pages one at a time

For each page: create the `app/` file, verify build, then move on.

**Common changes for every page:**
- Add `'use client'` at the top.
- Replace `import { useRouter } from 'next/router'` → `import { useRouter } from 'next/navigation'`.
- Remove any `import Head from 'next/head'` — title/meta now lives in `layout.tsx`.

#### 3a — `app/page.tsx` (from `pages/index.tsx`)

No router usage expected. Add `'use client'`, remove Head import.

#### 3b — `app/dashboard/page.tsx` (from `pages/dashboard.tsx`)

Add `'use client'`, swap router import.

#### 3c — `app/accounts/page.tsx` (from `pages/accounts.tsx`)

Add `'use client'`, swap router import.

#### 3d — `app/accounts/[id]/page.tsx` (from `pages/accounts/[id].tsx`)

Replace `router.query.id` with `useParams()`:

```tsx
import { useParams } from 'next/navigation';
// ...
const params = useParams();
const id = params.id as string;
```

#### 3e — `app/advisor-team/page.tsx` (from `pages/advisor-team.tsx`)

Add `'use client'`, swap router import.

#### 3f — `app/analysis/page.tsx` (from `pages/analysis.tsx`)

Replace `router.query.job_id` with `useSearchParams()`:

```tsx
import { useSearchParams } from 'next/navigation';
// ...
const searchParams = useSearchParams();
const jobId = searchParams.get('job_id');
```

`useSearchParams` must be wrapped in `<Suspense>` for static export. Wrap the component body or the parent that reads the param:

```tsx
import { Suspense } from 'react';

function AnalysisInner() {
  const searchParams = useSearchParams();
  // ... rest of component
}

export default function AnalysisPage() {
  return <Suspense><AnalysisInner /></Suspense>;
}
```

---

### Step 4 — Add `app/not-found.tsx` (from `pages/404.tsx`)

No `'use client'` needed — static content only. Copy content, remove `Head` import.

---

### Step 5 — Add `app/error.tsx` (from `pages/500.tsx`)

App Router requires `'use client'` on `error.tsx`. Must accept `{ error, reset }` props:

```tsx
'use client';
export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  // existing 500 content + a reset button calling reset()
}
```

---

### Step 6 — Delete `frontend/pages/`

Only after `npm run build` succeeds with all app/ pages in place.

```bash
rm -rf frontend/pages
```

---

### Step 7 — Final verification

Run each item and confirm it passes before calling the migration complete.

1. `npm run build` — static export succeeds, `out/` contains all route `.html` files.
2. `npm run dev` — dev server starts cleanly with no console errors.
3. `/` — landing page loads, Clerk sign-in/sign-up works.
4. Sign in → `/dashboard` — user data loads.
5. `/accounts` — account list loads.
6. `/accounts/[id]` — positions load.
7. `/advisor-team` — trigger an analysis, polling returns results.
8. `/analysis?job_id=<id>` — report, charts, and retirement tabs all render.
9. Non-existent route — custom 404 displays.
10. `out/` directory — verify `.html` files exist for all routes.

---

## File Change Summary

| Action | File |
|--------|------|
| Create | `frontend/app/layout.tsx` |
| Create | `frontend/app/page.tsx` |
| Create | `frontend/app/dashboard/page.tsx` |
| Create | `frontend/app/accounts/page.tsx` |
| Create | `frontend/app/accounts/[id]/page.tsx` |
| Create | `frontend/app/advisor-team/page.tsx` |
| Create | `frontend/app/analysis/page.tsx` |
| Create | `frontend/app/not-found.tsx` |
| Create | `frontend/app/error.tsx` |
| Edit   | `frontend/components/PageTransition.tsx` |
| Delete | `frontend/pages/` (entire directory) |

No changes to `next.config.ts`, `lib/config.ts`, `lib/api.ts`, or any other files.
