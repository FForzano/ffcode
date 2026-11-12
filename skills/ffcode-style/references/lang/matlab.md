# MATLAB
- One function per file, file name = function name, `camelCase` or `snake_case` consistently per project; a header comment of one line + units/shapes of inputs and outputs.
- Vectorise; preallocate; no `clear all`/`close all` in functions; no globals. Scripts only orchestrate (load → call functions → plot/save).
- Fixed seeds (`rng`) for reproducible results; parameters in a struct validated at entry (`arguments` block / `validateattributes`).
- Cite equations with the source tag (C3). Keep results (`.mat`, figures) out of git or in a dedicated folder. Tests: `matlab.unittest` or a `tests/` script with assertions.
