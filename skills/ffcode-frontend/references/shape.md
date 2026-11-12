# shape - plan before code

Output: a one-page brief (in chat, or `.ffcode/state.md`), not code. Skip questions the product/design files or the code already answer.
1. **Job**: who, in what situation, to accomplish what, how often, what happens if it fails. One sentence each.
2. **Content and data**: the real fields, realistic lengths (shortest, typical, longest), counts (0, 1, many, 10k), permissions.
3. **Flow**: entry → steps → exit; primary action; what can be undone; what needs confirmation.
4. **Screens and states**: for each, default / loading / empty / error / partial / success; mobile and desktop arrangement in a sentence or an ASCII sketch.
5. **System fit**: components and tokens to reuse (from `design.md`/`uitokens`), what is new and why.
6. **Copy**: labels, actions, errors, empty text in the product's language and tone.
7. **Acceptance**: 5–8 checkable statements (keyboard path, contrast, states, responsive, i18n, test).
Ask the user only for decisions that change the design materially; propose a default for the rest.
