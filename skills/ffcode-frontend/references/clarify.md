# clarify - copy and microcopy

Rules: one term per concept (glossary in `product.md`); action labels are verbs naming the result ("Save changes", not "OK"); errors = what happened + why if known + what to do, no blame, no codes alone;
empty states = what this place is for + the next action; confirmations name the object and the consequence; placeholders never replace labels; sentence case unless the system says otherwise; numbers, dates, units unambiguous;
tone from `product.md` in the product's language (check the i18n catalogue, edit keys not JSX); no filler ("Please note that"), no jargon the user does not use.
Process: list the strings of the target (`rg` on i18n keys), group by type (action, error, empty, help), rewrite in a table old → new → why, apply through the catalogue, keep keys stable unless meaning changed.
