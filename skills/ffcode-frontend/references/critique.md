# critique - UX/design review

Look at the real screen (screenshot/browser if available) or the code; do not edit. Score 0–4 each, with one line of evidence:
1. Visibility of status (loading, progress, result)  2. Match with the user's language and model  3. Control and recovery (undo, cancel, back)  4. Consistency with the system and platform
5. Error prevention and messages  6. Recognition over recall  7. Efficiency for the frequent path  8. Focus (hierarchy, one primary action, noise)  9. Accessibility in practice  10. Content quality.
Then: **first impression** (what the eye hits first vs. what should be first), **top 5 fixes ranked by impact/effort** (each: where, problem, change, which command does it: `clarify`, `layout`, `harden`...), **keep** (what works, ≤ 3 lines).
Run `$FF uilint` on the files and fold hits in rather than re-deriving them. Persona pass when relevant: first-time user, expert, keyboard-only, small phone, slow network.
Severity: blocker (task impossible/inaccessible), major (task slowed/error-prone), minor (polish).
