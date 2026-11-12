# distill - remove what does not earn its place

For the target ask of each element: which user task fails without it? Remove or merge: duplicate actions, decorative containers, redundant labels and helper text, secondary actions competing with the primary, settings no one needs (default them),
steps that can be inferred, nested containers, effects that carry no meaning. Keep one primary action per view, group the rest, move rare things behind progressive disclosure (not into a deep menu).
Deliver the change as a deletion-heavy diff; list what was removed and where it went (or why it is gone), and check that tests and analytics events that referenced it are updated.
