# Plan 002: Enforce CSV metric invariants in experiment validation

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If any STOP condition occurs, stop and report; do not improvise.
>
> **Drift check (run first)**: this workspace had no git repository when the plan was written. Manually compare the "Current state" excerpts below with the live files before editing. If they do not match, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: tests
- **Planned at**: commit `no-git`, 2026-06-26

## Why this matters

`validate_rows` is the main quality gate before experiment data is written and plotted. It currently verifies row count, expected buffer/seed pairs, and a few basic fields. It does not verify that numeric metrics are internally consistent, so corrupted rows can pass and produce invalid graphs.

## Current state

```python
# scripts/run_experiments.py:47-67
def validate_rows(rows: list[dict[str, str]], repetitions: int) -> None:
    expected_count = len(BUFFER_SAMPLES) * repetitions
    if len(rows) != expected_count:
        raise ValueError(f"Expected {expected_count} rows, got {len(rows)}")

    expected_pairs = {(buffer, seed) for buffer in BUFFER_SAMPLES for seed in range(1, repetitions + 1)}
    actual_pairs = {(int(row["buffer_packets"]), int(row["run_seed"])) for row in rows}
    if actual_pairs != expected_pairs:
        raise ValueError(f"Unexpected buffer/seed pairs: {sorted(actual_pairs)}")

    for row in rows:
        missing = [field for field in FIELDNAMES if field not in row]
        if missing:
            raise ValueError(f"Row missing columns: {', '.join(missing)}")
        if int(row["tx_packets"]) <= 0:
            raise ValueError(f"tx_packets must be > 0 for row {row}")
        if int(row["flow_id"]) <= 0:
            raise ValueError(f"flow_id must be > 0 for row {row}")
        if int(row["queue_disc_drops"]) < 0:
            raise ValueError(f"queue_disc_drops must be >= 0 for row {row}")
```

Existing tests cover defaults, command construction, one-row parsing, missing samples, missing `queue_disc_drops`, and flat metrics at `tests/test_experiment_scripts.py:5-101`.

## Commands you will need

| Purpose         | Command                                                                                    | Expected on success                |
| --------------- | ------------------------------------------------------------------------------------------ | ---------------------------------- |
| Unit tests      | `rtk env PYTHONDONTWRITEBYTECODE=1 python -m unittest tests/test_experiment_scripts.py -v` | exit 0, all tests pass             |
| Full experiment | `rtk python scripts/run_experiments.py`                                                    | exit 0, 10 data rows and five PNGs |

## Scope

**In scope**:

- `scripts/run_experiments.py`
- `tests/test_experiment_scripts.py`

**Out of scope**:

- Changing CSV column names
- Changing NS-3 metric formulas in `src/queue_buffer_qos.cc`
- Changing plotting behavior; that is Plan 001

## Git workflow

This workspace is not a git repository. If git exists by execution time, use branch `advisor/002-enforce-csv-metric-invariants` and commit message `test: enforce qos csv invariants`.

## Steps

### Step 1: Add typed parsing helpers

In `scripts/run_experiments.py`, add small helpers inside the module, for example:

- `parse_int_field(row, field) -> int`
- `parse_float_field(row, field) -> float`

They should raise `ValueError` with field name and row context when parsing fails. Keep messages concise; do not dump huge data.

**Verify**: `rtk env PYTHONDONTWRITEBYTECODE=1 python -m unittest tests/test_experiment_scripts.py -v` exits 0.

### Step 2: Validate metric invariants

Extend `validate_rows` to enforce:

- every `buffer_packets` and `run_seed` parses as int before pair comparison,
- no duplicate `(buffer_packets, run_seed)` pair,
- `tx_packets > 0`,
- `0 <= rx_packets <= tx_packets`,
- `lost_packets == tx_packets - rx_packets`,
- `queue_disc_drops >= 0`,
- `0 <= packet_loss_ratio_percent <= 100`,
- `packet_loss_ratio_percent` matches `lost_packets * 100 / tx_packets` within a small tolerance such as `1e-4`,
- `throughput_mbps >= 0`,
- `average_delay_ms >= 0`,
- `flow_id > 0`.

Keep `validate_metric_variation` separate.

**Verify**: unit tests pass.

### Step 3: Add focused tests

Add tests in `tests/test_experiment_scripts.py` using helper row factories to avoid repeated boilerplate. Cover:

- valid rows for all default buffers pass,
- `rx_packets > tx_packets` fails,
- wrong `lost_packets` fails,
- wrong packet loss ratio fails,
- negative throughput or delay fails,
- duplicate `(buffer_packets, run_seed)` fails with a useful message.

**Verify**: `rtk env PYTHONDONTWRITEBYTECODE=1 python -m unittest tests/test_experiment_scripts.py -v` exits 0 and test count increases.

### Step 4: Run integration check

Run:

```bash
rtk python scripts/run_experiments.py
```

Expected:

- exit 0,
- `results/qos_results.csv` contains 10 data rows,
- all generated rows satisfy the stricter invariants.

## Test plan

- Unit tests for each invariant failure.
- Full experiment run after implementation.
- Keep `parse_simulation_csv` behavior unchanged except for any helper reuse that preserves current errors.

## Done criteria

- [ ] Stricter invariants implemented in `validate_rows`.
- [ ] New unit tests prove corrupt rows are rejected.
- [ ] Default full experiment still succeeds.
- [ ] No CSV column names changed.
- [ ] `plans/README.md` row 002 updated.

## STOP conditions

- Current CSV schema has changed from `FIELDNAMES`.
- Full experiment output violates an invariant because the C++ source uses a different metric definition than assumed here.
- The fix requires modifying `src/queue_buffer_qos.cc`; write a new plan or ask the operator instead.

## Maintenance notes

Validation should stay close to the CSV writer because this script is the reproducibility gate. If new metrics are added, update `FIELDNAMES`, `validate_rows`, and tests in the same change.
