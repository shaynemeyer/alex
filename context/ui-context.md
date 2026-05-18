# UI Context

## Theme

Light mode only. The visual language is a clean enterprise financial dashboard — white and light-gray surfaces, a dark navy brand color for authority, a blue primary for interactive elements, and purple for AI/agent features.

All colors are defined as CSS custom properties in `frontend/styles/globals.css` and mapped to Tailwind tokens via `@theme inline`. Components must use these tokens — no hardcoded hex values or raw Tailwind color classes like `blue-500`.

| Role                  | CSS Variable / Tailwind Token                          | Hex       |
| --------------------- | ------------------------------------------------------ | --------- |
| Primary (interactive) | `--color-primary` / `text-primary`, `bg-primary`       | `#209DD7` |
| AI / agent accent     | `--color-ai-accent` / `text-ai-accent`, `bg-ai-accent` | `#753991` |
| Accent (highlights)   | `--color-accent` / `text-accent`, `bg-accent`          | `#FFB707` |
| Dark navy (headings)  | `--color-dark` / `text-dark`, `bg-dark`                | `#062147` |
| Success               | `--color-success` / `text-success`                     | `#10b981` |
| Error                 | `--color-error` / `text-error`                         | `#ef4444` |
| Page background       | `--background`                                         | `#ffffff` |
| Body text             | `--foreground`                                         | `#171717` |

## Typography

| Role      | Font       | CSS Variable        |
| --------- | ---------- | ------------------- |
| UI text   | Geist Sans | `--font-geist-sans` |
| Code/mono | Geist Mono | `--font-geist-mono` |

Both fonts are loaded via `next/font/google` and applied as CSS variables. The base `body` uses `system-ui, -apple-system, sans-serif` as a fallback.

## Border Radius

| Context            | Class                        |
| ------------------ | ---------------------------- |
| Inputs / small UI  | `rounded-lg`                 |
| Cards / panels     | `rounded-lg` or `rounded-xl` |
| Feature highlights | `rounded-xl`                 |

## Layout Patterns

- **Landing page**: full-viewport gradient (`from-blue-50 to-gray-50`), top nav with white background and shadow, stacked hero / features / CTA sections.
- **Authenticated app**: `min-h-screen bg-gray-50 flex flex-col` shell via `Layout`. Top nav is white with a bottom border. Main content is `flex-1`. Footer contains a disclaimer banner.
- **Content area**: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8` for all pages inside `Layout`.
- **Cards**: `bg-white rounded-lg shadow p-6` — white cards on the gray-50 page background.
- **Grids**: `grid grid-cols-1 md:grid-cols-N gap-6` responsive grid for dashboards.

## Navigation

Top nav inside `Layout`:

- Logo: `text-dark` brand name + `text-primary` subtitle.
- Nav links: `text-gray-600 hover:text-primary` with active state `text-primary`.
- Mobile: secondary row of links visible below `md` breakpoint.
- User section: Clerk `UserButton` + display name on the right.

## Color Usage by Role

- **Headings and page titles**: `text-dark` (`#062147`)
- **Primary actions / CTAs**: `bg-primary text-white hover:bg-blue-600`
- **AI / agent features**: `bg-ai-accent text-white hover:bg-purple-700`
- **Accent highlights** (e.g. CTA on dark backgrounds): `bg-accent text-dark`
- **Secondary / outline buttons**: `border border-primary text-primary hover:bg-primary hover:text-white`
- **Muted labels**: `text-gray-500` or `text-gray-600`
- **Borders and dividers**: `border-gray-200` or `border-gray-300`

## Data Visualization

Recharts is used for all charts. The shared color palette for pie/bar charts maps to the Alex brand tokens in this order:

```ts
const COLORS = ['#209DD7', '#753991', '#FFB707', '#062147', '#10B981'];
```

Charts are wrapped in `<ResponsiveContainer width="100%" height="100%">`. Tooltips use `formatter` to apply `$` or `%` formatting. `<Legend>` is shown when chart labels are not self-evident.

Inline mini charts (e.g. dashboard summary cards) use fixed heights (`h-24`, `h-32`) with inner/outer radius to create donut charts.

## Component Library

No shadcn/ui — components are hand-built with Tailwind. Shared UI lives in `frontend/components/`:

- `Layout.tsx` — authenticated shell with nav + footer
- `Toast.tsx` — slide-in toast notifications (dispatched via `showToast()`)
- `Skeleton.tsx` — loading placeholders (`Skeleton`, `SkeletonCard`, `SkeletonTable`, `SkeletonText`)
- `ConfirmModal.tsx` — confirmation dialog
- `ErrorBoundary.tsx` — top-level error fallback
- `PageTransition.tsx` — page-level transition wrapper

Do not modify these unless a task explicitly requires it.

## Animations

Defined in `globals.css`:

| Class                  | Effect                                   |
| ---------------------- | ---------------------------------------- |
| `animate-strong-pulse` | Scale + opacity pulse for agent activity |
| `animate-glow-pulse`   | Purple box-shadow glow for active agents |
| `animate-slide-in`     | Slide from right for toast notifications |

## Forms and Inputs

- Text inputs: `w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary`
- Sliders: native `<input type="range">` with Tailwind `w-full`
- Labels: `block text-sm font-medium text-gray-700 mb-2`
- Disabled state: `bg-gray-300 text-gray-500 cursor-not-allowed`

## Icons

No icon library — icons are expressed as inline emoji in the current codebase. If a proper icon library is introduced, use Lucide React with stroke-based icons only.

## State Feedback

- Loading: skeleton components from `Skeleton.tsx` — never raw spinners
- Errors: `bg-red-50 border border-red-200 rounded-lg p-4` with `text-red-600` message
- Success: toast via `showToast('success', message)` — not inline banners
- Empty states: descriptive `text-sm text-gray-500` inline message

## Pages

| Route           | Purpose                                  |
| --------------- | ---------------------------------------- |
| `/`             | Marketing landing page (unauthenticated) |
| `/dashboard`    | Portfolio summary + user settings        |
| `/accounts`     | Account list and position management     |
| `/advisor-team` | AI agent team overview                   |
| `/analysis`     | Run analysis + view reports              |
| `/404`          | Not found                                |
| `/500`          | Server error                             |
