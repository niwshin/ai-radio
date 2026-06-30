# Repository Guidelines

## Project Structure & Module Organization

Application code lives in `ai_radio/`. `main.py` exposes the FastAPI API and static UI, `service.py` coordinates research and synthesis, `scheduler.py` creates recurring jobs, and `codex_worker.py` runs Codex on the host. Database, models, research, and TTS concerns remain in their matching modules. Tests belong in `tests/`, browser assets in `static/`, and operational instructions in `docs/`. Docker services are defined in `docker-compose.yml`. Runtime databases, audio, and job files are written to the ignored `data/` directory.

## Build, Test, and Development Commands

Always activate and verify the repository virtual environment before running commands:

```bash
source .venv/bin/activate
python -c 'import os, sys; print(os.environ.get("VIRTUAL_ENV")); print(sys.executable)'
```

Install the package and test dependencies with `python -m pip install -e '.[test]'`. Run unit tests with `python -m pytest` and check imports and syntax with `python -m compileall ai_radio tests`. Start FastAPI, VOICEVOX, and SearXNG using `docker compose up --build`. In a second terminal, run the host worker with:

```bash
python -m ai_radio.codex_worker --data-dir ./data --loop
```

## Coding Style & Naming Conventions

Target Python 3.12 or newer. Use four-space indentation, type hints for public functions, `snake_case` for modules and functions, and `PascalCase` for classes. Keep modules focused on one responsibility. Environment variables use the `AI_RADIO_` prefix. No formatter or linter is currently configured, so follow existing style and keep diffs small.

## Testing Guidelines

Use pytest. Name files `test_*.py` and tests `test_<behavior>`. Add focused unit tests for new logic and regression tests for fixes. External search, Codex, and VOICEVOX calls should be isolated or mocked in tests. No coverage threshold is configured, but changed behavior should be exercised.

## Commit & Pull Request Guidelines

History currently contains only `Initial AI radio MVP`; use similarly concise, imperative commit subjects. Keep commits scoped and exclude generated files. Pull requests should explain the change and impact, list validation commands, link relevant issues, and include screenshots for UI changes. Call out database, environment-variable, or operational-documentation changes explicitly.

## Security & Agent Instructions

Never commit API keys, tokens, Codex credentials, or generated `data/` contents. Codex authentication stays on the host and must not enter Docker images. Agents must verify `.venv` before commands and preserve unrelated working-tree changes.
