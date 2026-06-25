# Plan 001: Aggregate repeated-seed plot data before graphing

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If any STOP condition occurs, stop and report; do not improvise.
>
> **Drift check (run first)**: this workspace had no git repository when the plan was written. Manually compare the "Current state" excerpts below with the live files before editing. If they do not match, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `no-git`, 2026-06-26

## Why this matters

`scripts/run_experiments.py` supports `--repetitions`, meaning multiple seeds per buffer value. The CSV correctly preserves raw per-seed rows, but `scripts/plot_results.py` plots every row as one line. With repetitions greater than one, the graph contains duplicate x-values and connects seed-ordered rows, so the visual no longer represents "metric vs buffer size" cleanly.

## Current state

- `scripts/run_experiments.py` owns experiment execution and writes raw rows.
- `scripts/plot_results.py` reads `results/qos_results.csv` and creates PNG graphs.
- `tests/test_experiment_scripts.py` has unit tests for runner helpers but no plot aggregation tests.
- The design explicitly allows repetitions: `docs/superpowers/specs/2026-06-26-ns3-queue-buffer-qos-design.md:44` says the script may provide `--repetitions` for several seeds per buffer.

Relevant excerpts:

```python
# scripts/run_experiments.py:101-103
parser.add_argument("--repetitions", type=int, default=1, help="Run seeds per buffer sample.")
parser.add_argument("--compile-only", action="store_true", help="Only compile the NS-3 source.")
parser.add_argument("--skip-plots", action="store_true", help="Do not generate PNG graphs.")
```

```python
# scripts/run_experiments.py:119-124
for seed in range(1, args.repetitions + 1):
    for buffer_packets in BUFFER_SAMPLES:
        print(f"running buffer={buffer_packets} seed={seed}", file=sys.stderr)
        rows.append(run_simulation(root, executable, buffer_packets, seed))

rows.sort(key=lambda row: (int(row["run_seed"]), int(row["buffer_packets"])))
```

```python
# scripts/plot_results.py:16-21
def plot_metric(rows: list[dict[str, str]], y_column: str, y_label: str, title: str, output_path: Path) -> None:
    x_values = [int(row["buffer_packets"]) for row in rows]
    y_values = [float(row[y_column]) for row in rows]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x_values, y_values, marker="o", linewidth=2)
```

## Commands you will need

| Purpose                  | Command                                                                                    | Expected on success                                                         |
| ------------------------ | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| Unit tests               | `rtk env PYTHONDONTWRITEBYTECODE=1 python -m unittest tests/test_experiment_scripts.py -v` | exit 0, 7+ tests pass                                                       |
| One simulation smoke     | `rtk ./build/queue_buffer_qos --bufferPackets=10 --runSeed=1 --csvHeader=true`             | exit 0, header plus one CSV row                                             |
| Full repeated experiment | `rtk python scripts/run_experiments.py --repetitions 2`                                    | exit 0, `results/qos_results.csv` has 20 data rows and PNGs are regenerated |

## Scope

**In scope**:

- `scripts/plot_results.py`
- `tests/test_experiment_scripts.py`
- `README.md` only if you document the repeated-seed plotting behavior

**Out of scope**:

- Changing the raw CSV row format in `results/qos_results.csv`
- Changing C++ simulation parameters or metrics
- Removing `--repetitions`

## Git workflow

This workspace is not a git repository. If the operator has initialized git before execution, use branch `advisor/001-aggregate-repeated-seed-plots` and a conventional commit message such as `fix: aggregate repeated-seed plot data`.

## Steps

### Step 1: Add aggregation helper in `scripts/plot_results.py`

Add a pure helper such as `aggregate_rows_by_buffer(rows, y_column) -> tuple[list[int], list[float]]`.

Required behavior:

- Group rows by integer `buffer_packets`.
- Convert the selected metric to `float`.
- Average metric values across rows with the same buffer.
- Return buffers sorted ascending, not seed order.
- Raise `ValueError` with a clear message if `buffer_packets` or the metric cannot be parsed.

Keep `read_rows` unchanged.

**Verify**: `rtk env PYTHONDONTWRITEBYTECODE=1 python -m unittest tests/test_experiment_scripts.py -v` should still exit 0.

### Step 2: Use the helper from `plot_metric`

Change `plot_metric` so it calls the aggregation helper and plots one point per buffer. Keep the output filenames and labels unchanged.

For a default 10-row CSV, the graph should be visually equivalent to current output. For `--repetitions 2`, each graph should have 10 x positions, one averaged value per buffer.

**Verify**: add a temporary Python check or unit test that passes four rows with two buffers and two seeds, then confirms returned buffers are `[1, 5]` and averages are correct.

### Step 3: Add tests

In `tests/test_experiment_scripts.py`, add tests that import from `scripts.plot_results`:

- aggregation returns sorted unique buffers,
- aggregation averages duplicate buffer rows,
- invalid metric values raise `ValueError`.

Use in-memory row dictionaries; do not write PNGs in unit tests unless you use a temporary directory.

**Verify**: `rtk env PYTHONDONTWRITEBYTECODE=1 python -m unittest tests/test_experiment_scripts.py -v` should exit 0 and include the new tests.

### Step 4: Run repeated experiment verification

Run:

```bash
rtk python scripts/run_experiments.py --repetitions 2
```

Expected:

- exit 0,
- `results/qos_results.csv` has one header plus 20 data rows,
- five PNG graphs exist and are non-empty.

## Test plan

- Unit-test the aggregation helper with two seeds per buffer.
- Keep existing runner tests unchanged.
- Run the full repeated experiment once to verify integration between runner and plotter.

## Done criteria

- [ ] Unit tests pass with `rtk env PYTHONDONTWRITEBYTECODE=1 python -m unittest tests/test_experiment_scripts.py -v`.
- [ ] `rtk python scripts/run_experiments.py --repetitions 2` exits 0.
- [ ] `results/qos_results.csv` keeps raw per-seed rows.
- [ ] Plot code produces one x point per buffer for each metric.
- [ ] `plans/README.md` row 001 updated.

## STOP conditions

- Live `scripts/plot_results.py` no longer has `plot_metric` with the same responsibility.
- The desired output changes from averaged repeated-seed plots to per-seed multi-line plots.
- Verification requires changing C++ simulation behavior.

## Maintenance notes

If future reports need confidence intervals, extend the aggregation helper to return mean plus spread and update plotting to show error bars. Do not overload the raw CSV with summary-only rows.
