# Working principles (how the skills behave)

1. **Read `.ffcode/` first, not the tree.** `context.md` (what the project is), `style.md` (deviations), `state.md` (open work), `map.md`
   (layout and symbols). Use `ffcode find NAME` instead of directory-wide grep. Open a file only to read the part you will touch.
2. **Scripts do the mechanical part, you do the judgment.** Anything listed `[auto]` in `checklist.md` is run, not eyeballed. Show the
   user the compressed result (`ffcode check`), not raw logs.
3. **Small verified steps.** Change → run the narrowest test → continue. Full suite at the end (`ffcode check --changed`).
4. **Smallest diff that solves the problem.** No drive-by refactors; list them as follow-ups instead.
5. **Ask only for what changes the work** (a business rule, an irreversible action); otherwise take the project's convention and say which.
6. **Outward or irreversible actions need confirmation:** push, deploy, migrations on shared DBs, deleting files, rewriting CLAUDE.md.
7. **Report faithfully:** failed check = failed, with the output tail; skipped step = said.
8. **Keep `.ffcode/` honest:** when you learn a durable fact (invariant, command, decision), add it to `context.md`/`state.md`/`decisions/` in one line, not narrative.
