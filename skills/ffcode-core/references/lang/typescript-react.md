# TypeScript / React
- Function components + hooks; data logic in hooks/utils, never copied per page. Contexts for cross-cutting state (loading, error, toast, notifications). Route-level code-splitting with lazy pages for private areas.
- Strict TS: no `any` (use `unknown` + narrowing), explicit prop types, API types shared in one place; API calls via one client module (axios instance, interceptors for auth).
- Files: `PascalCase.tsx` components, `useThing.ts` hooks, `camelCase.ts` utils; one component per file; colocated `Component.module.css` for scoped styles, global CSS only for design-system primitives (grep the number of consumers).
- Texts through i18n keys; no hard-coded strings in JSX. Handle loading/empty/error. Accessibility: labels, focus, contrast.
- Check `DESIGN.md`/`PRODUCT.md` before new UI patterns. Commands: `npm run lint`, `npx tsc --noEmit`, `npm test -- --watchAll=false`, `npm run build`.
