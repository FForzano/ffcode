# Python
- `snake_case` modules/functions, `PascalCase` classes, `_UPPER_CASE` module constants (with justification comment). Python ≥ 3.11: builtin generics, `X | None`.
- Config: `@dataclass(frozen=True)` tree, validation in `__post_init__`, passed explicitly. ABC only at plugin seams.
- Type hints on all public functions; `mypy` with `disallow_untyped_defs` when the project sets it. Formatter: black (88) or ruff-format; follow `pyproject.toml`.
- `logger = logging.getLogger(__name__)`; no `print` in the package (scripts/CLIs may). No bare `except`.
- Never mutate arguments (arrays: copy, or mark read-only). Numeric code: shape/axis order documented at boundaries; units in names.
- Scripts parse args, call the package, save/plot; no logic in scripts. Tests: pytest, seeded RNG, `tests/` mirrors the package.
- Dependencies in `pyproject.toml` (extras for optional groups). Typical commands: `pytest -q`, `black --check .`, `mypy .`, `ruff check .`.
