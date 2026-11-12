# adapt - other devices, sizes, inputs

Decide the target (small phone, tablet, large desktop, print, touch vs keyboard vs pointer, embedded webview) from `product.md`; then:
layout reflows by content (grid/flex/container queries), not by device names; one column on narrow, density increases with width, max measure on wide; navigation pattern changes (tabs/drawer/bar) at a content breakpoint;
touch: targets ≥ 44px, no hover-only, gestures have a visible alternative, thumb-reachable primary actions, safe-area insets; pointer: hover and keyboard shortcuts as additions;
tables → stacked cards or horizontal scroll with sticky first column, chosen per data; images `srcset`/`sizes`, aspect-ratio set; text zoom 200% and reduced-motion/contrast preferences honoured; print stylesheet when documents matter.
Test at 320, 375, 768, 1024, 1440 and in landscape; fix overflow first, then hierarchy. Native apps (iOS/Android) follow platform conventions (navigation, back, dynamic type, system components) before brand.
