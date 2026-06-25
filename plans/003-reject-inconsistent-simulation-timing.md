# Plan 003: Reject inconsistent simulation timing parameters

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If any STOP condition occurs, stop and report; do not improvise.
>
> **Drift check (run first)**: this workspace had no git repository when the plan was written. Manually compare the "Current state" excerpts below with the live files before editing. If they do not match, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `no-git`, 2026-06-26

## Why this matters

The binary exposes `--simulationStop`, but traffic timing is fixed in code. If a user runs with `--simulationStop` before `trafficStop`, FlowMonitor sees a partial experiment while throughput still divides by the fixed active-traffic duration. That makes output look valid even though the scenario is internally inconsistent.

## Current state

```cpp
// src/queue_buffer_qos.cc:59-71
double simulationStop = 25.0;
double trafficStart = 1.0;
double trafficStop = 19.0;
std::string mainRate = "1Mbps";
std::string backgroundRate = "0.5Mbps";

CommandLine cmd(__FILE__);
cmd.AddValue("bufferPackets", "FifoQueueDisc MaxSize on R4->H4 in packets", bufferPackets);
cmd.AddValue("runSeed", "NS-3 run number for reproducible repetitions", runSeed);
cmd.AddValue("csvHeader", "Print CSV header before data row", csvHeader);
cmd.AddValue("simulationStop", "Simulation stop time in seconds", simulationStop);
cmd.AddValue("mainRate", "UDP CBR rate for H0->H4", mainRate);
cmd.AddValue("backgroundRate", "UDP CBR rate for each background flow", backgroundRate);
```

```cpp
// src/queue_buffer_qos.cc:196-197
Simulator::Stop(Seconds(simulationStop));
Simulator::Run();
```

```cpp
// src/queue_buffer_qos.cc:247-250
const double measurementDuration = trafficStop - trafficStart;
const double throughputMbps = static_cast<double>(rxBytes) * 8.0 / measurementDuration / 1000000.0;
const double lossRatio =
    static_cast<double>(lostPackets) * 100.0 / static_cast<double>(txPackets);
```

## Commands you will need

| Purpose              | Command                                                                                    | Expected on success                         |
| -------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------- |
| Compile              | `rtk ns3-compile src/queue_buffer_qos.cc -o build/queue_buffer_qos`                        | exit 0                                      |
| Valid default smoke  | `rtk ./build/queue_buffer_qos --bufferPackets=10 --runSeed=1 --csvHeader=true`             | exit 0, header plus one CSV row             |
| Invalid timing smoke | `rtk ./build/queue_buffer_qos --bufferPackets=10 --simulationStop=18`                      | non-zero exit, clear timing error on stderr |
| Python tests         | `rtk env PYTHONDONTWRITEBYTECODE=1 python -m unittest tests/test_experiment_scripts.py -v` | exit 0                                      |

## Scope

**In scope**:

- `src/queue_buffer_qos.cc`
- `README.md` if documenting the timing constraint
- `docs/superpowers/plans/2026-06-26-ns3-queue-buffer-qos-final.md` only if the operator wants documentation kept in sync

**Out of scope**:

- Adding CLI flags for `trafficStart` or `trafficStop`
- Changing default timings
- Changing throughput formula

## Git workflow

This workspace is not a git repository. If git exists by execution time, use branch `advisor/003-reject-inconsistent-simulation-timing` and commit message `fix: reject inconsistent simulation timing`.

## Steps

### Step 1: Add timing validation after CLI parse

In `src/queue_buffer_qos.cc`, after `cmd.Parse(argc, argv)` and after the existing `bufferPackets` validation, add validation for:

- `trafficStop > trafficStart`,
- `simulationStop > trafficStop`.

Use `std::cerr` and return a distinct non-zero code. Keep the existing `bufferPackets` error unchanged.

Suggested message shape:

```text
simulationStop must be greater than trafficStop so all offered traffic is measured
```

**Verify**: `rtk ns3-compile src/queue_buffer_qos.cc -o build/queue_buffer_qos` exits 0.

### Step 2: Verify valid and invalid runtime behavior

Run the valid default smoke command. It should still print a CSV header and one data row.

Run the invalid timing smoke command. It should exit non-zero and print the timing error. Do not accept output that still looks like a CSV row.

**Verify**:

```bash
rtk ./build/queue_buffer_qos --bufferPackets=10 --runSeed=1 --csvHeader=true
rtk ./build/queue_buffer_qos --bufferPackets=10 --simulationStop=18
```

### Step 3: Update README if needed

If README keeps `--simulationStop` undocumented, add one concise note under "Cara Menjalankan" or "Variabel kontrol": `simulationStop` must be greater than the fixed traffic stop time `19s`.

**Verify**: README still accurately lists default commands and outputs.

## Test plan

- Compile C++ source.
- Run one valid binary smoke test.
- Run one invalid timing smoke test.
- Run Python unit tests to ensure runner helpers are unaffected.

## Done criteria

- [ ] Invalid `--simulationStop=18` exits non-zero before simulation runs.
- [ ] Default simulation output unchanged.
- [ ] Compile and Python tests pass.
- [ ] `plans/README.md` row 003 updated.

## STOP conditions

- The operator wants `simulationStop <= trafficStop` to be supported for partial-run experiments.
- Timing variables have already been made fully configurable before this plan is executed.
- NS-3 reports a different command-line parsing behavior that prevents clean validation.

## Maintenance notes

If future work exposes `trafficStart` and `trafficStop` as CLI flags, keep these invariants and update `measurementDuration` validation in the same change.
