# Plan 004: Add reproducible Python and generated-artifact tooling baseline

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If any STOP condition occurs, stop and report; do not improvise.
>
> **Drift check (run first)**: this workspace had no git repository when the plan was written. Manually compare the "Current state" excerpts below with the live files before editing. If they do not match, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `no-git`, 2026-06-26

## Why this matters

The project depends on `matplotlib` and `ns3-compile`, but only command usage is documented. The workspace also contains generated artifacts (`build/queue_buffer_qos`, `__pycache__`) that should not become accidental source files if the project is later placed under git. A small tooling baseline makes reproduction easier.

## Current state

README documents commands but not dependency setup:

````markdown
# README.md:32-50

## Cara Menjalankan

Compile saja:

```bash
ns3-compile src/queue_buffer_qos.cc -o build/queue_buffer_qos
```

Jalankan semua eksperimen dan grafik:

```bash
python scripts/run_experiments.py
```
````

`scripts/plot_results.py` imports matplotlib:

```python
# scripts/plot_results.py:5-8
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
```

Root listing at audit time had no `.gitignore`, no `requirements.txt`, and no package metadata.

## Commands you will need

| Purpose                 | Command                                                                                    | Expected on success     |
| ----------------------- | ------------------------------------------------------------------------------------------ | ----------------------- |
| Python dependency check | `rtk python -c "import matplotlib; print(matplotlib.__version__)"`                         | exit 0, version printed |
| Unit tests              | `rtk env PYTHONDONTWRITEBYTECODE=1 python -m unittest tests/test_experiment_scripts.py -v` | exit 0                  |
| Compile tool check      | `rtk proxy sh -lc 'command -v ns3-compile'`                                                | exit 0, path printed    |

## Scope

**In scope**:

- `requirements.txt` (create)
- `.gitignore` (create)
- `README.md`

**Out of scope**:

- Introducing a larger package manager (`pyproject.toml`, Poetry, uv) unless the operator requests it
- Removing existing generated artifacts from the workspace
- Changing experiment code

## Git workflow

This workspace is not a git repository. If git exists by execution time, use branch `advisor/004-add-tooling-baseline` and commit message `docs: add experiment tooling baseline`.

## Steps

### Step 1: Add `requirements.txt`

Create a root `requirements.txt` with the Python runtime dependency:

```text
matplotlib
```

Do not pin unless the operator wants strict reproducibility. If pinning is requested, use the currently verified version from `rtk python -c "import matplotlib; print(matplotlib.__version__)"`.

**Verify**: `rtk python -c "import matplotlib; print(matplotlib.__version__)"` exits 0.

### Step 2: Add `.gitignore`

Create a root `.gitignore` that ignores generated caches and build outputs:

```gitignore
__pycache__/
*.py[cod]
build/
```

Do not ignore `results/` in this plan because README lists `results/qos_results.csv` and PNGs as deliverables.

**Verify**: if git exists, `rtk git status --short --ignored` should show build/pycache as ignored. If git does not exist, manually inspect `.gitignore`.

### Step 3: Update README prerequisites

Add a short "Prasyarat" or "Setup" section before "Cara Menjalankan":

- Python 3,
- `matplotlib` installed with `python -m pip install -r requirements.txt`,
- `ns3-compile` available on PATH.

Keep existing run commands unchanged.

**Verify**: README still contains compile, single-scenario, full experiment, and unittest commands.

### Step 4: Run checks

Run:

```bash
rtk proxy sh -lc 'command -v ns3-compile'
rtk python -c "import matplotlib; print(matplotlib.__version__)"
rtk env PYTHONDONTWRITEBYTECODE=1 python -m unittest tests/test_experiment_scripts.py -v
```

Expected: all exit 0.

## Test plan

This is docs/tooling work. Verification is import/tool availability plus existing unit tests.

## Done criteria

- [ ] Root `requirements.txt` exists and lists `matplotlib`.
- [ ] Root `.gitignore` ignores Python bytecode and `build/`.
- [ ] README documents Python dependency setup and `ns3-compile` requirement.
- [ ] Existing unit tests pass.
- [ ] `plans/README.md` row 004 updated.

## STOP conditions

- Operator wants generated `build/` artifacts tracked intentionally.
- Operator wants a different Python dependency workflow.
- `matplotlib` is no longer used by `scripts/plot_results.py`.

## Maintenance notes

If this project later gains CI, reuse these commands as the base workflow: install requirements, run unit tests, compile NS-3 source, run experiment.
