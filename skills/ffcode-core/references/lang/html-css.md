# HTML / CSS
- Semantic HTML (landmarks, headings in order, `button` vs `a`), labels on inputs, `alt` on images, `lang` set.
- CSS: design tokens as custom properties; one place per shared pattern; scoped styles next to the component; no `!important` except to defeat third-party CSS (comment why); mobile-first, relative units.
- No inline styles except dynamic values. Respect `prefers-reduced-motion` and dark mode if the project has it. Follow `DESIGN.md`.
