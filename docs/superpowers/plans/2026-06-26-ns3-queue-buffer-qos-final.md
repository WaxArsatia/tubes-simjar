# NS-3 Queue Buffer QoS Final Implementation Plan

> **For agentic workers:** This plan reflects the current implemented state. If future changes are needed, use superpowers:executing-plans task-by-task and keep the spec in `docs/superpowers/specs/2026-06-26-ns3-queue-buffer-qos-design.md` aligned.

**Goal:** Build and verify a reproducible NS-3 experiment that shows how `FifoQueueDisc` queue buffer size affects packet loss, throughput, delay, and queue-disc drops on a redundant 5-router/5-host topology.

**Architecture:** The C++ NS-3 binary builds the topology, installs `ns3::FifoQueueDisc` on bottleneck netdevice `R4 -> H4`, emits one CSV row per buffer run, and reports FlowMonitor metrics plus queue-disc drops. Python scripts compile with `ns3-compile`, run the 10 default buffer samples, reject flat representative metrics, write CSV, and generate PNG graphs.

**Tech Stack:** NS-3 C++ modules `core`, `network`, `internet`, `point-to-point`, `traffic-control`, `applications`, `flow-monitor`; Python 3 standard library; `matplotlib`; `unittest`; `ns3-compile`.

## Current State

- Workspace root: `/d/Coding/Kuliah/simjar/tubes`.
- Existing git state: this directory is not a git repository; commit steps are skipped.
- Required compiler helper: `ns3-compile`.
- Approved spec: `docs/superpowers/specs/2026-06-26-ns3-queue-buffer-qos-design.md`.
- Implemented source: `src/queue_buffer_qos.cc`.
- Implemented runner: `scripts/run_experiments.py`.
- Implemented plotter: `scripts/plot_results.py`.
- Implemented tests: `tests/test_experiment_scripts.py`.
- Final outputs: `results/qos_results.csv` and five PNG graphs in `results/`.

## Global Constraints

- Research focus remains queue buffer size as the independent variable.
- Topology must have 5 routers, 5 hosts, loop `R0-R1-R2-R3-R4-R0`, and redundant links `R0-R2`, `R1-R3`.
- Queue buffer variable must be `ns3::FifoQueueDisc` `MaxSize` on netdevice `R4 -> H4`.
- Bottleneck netdevice queue on `R4 -> H4` must be `1p` so the queue disc is the active buffer.
- Default queue buffer samples must be exactly `1,5,10,20,50,100,200,500,750,1000` packets.
- Default output must contain exactly 10 CSV rows, one per buffer size.
- Main flow must be UDP CBR `H0 -> H4`.
- Background UDP CBR flows must be `H1 -> H4`, `H2 -> H4`, `H3 -> H4`.
- Default main rate must be `1Mbps`.
- Default background rate must be `0.5Mbps` per background flow.
- Total default offered load must be `2.5Mbps` into the `2Mbps` bottleneck.
- Default traffic stop must be `19s` and default simulation stop must be `25s` to allow large buffers to drain.
- Throughput formula must use `measurementDuration = trafficStop - trafficStart = 18s`.
- Compile NS-3 code with `ns3-compile`; do not use `./ns3 run`.
- Keep files ASCII.

## File Responsibilities

- `src/queue_buffer_qos.cc`
  - Builds hosts, routers, redundant topology, traffic, bottleneck queue disc, FlowMonitor, and one-row CSV output.
  - CLI args: `--bufferPackets`, `--runSeed`, `--csvHeader`, `--mainRate`, `--backgroundRate`.
  - CSV columns: `buffer_packets,tx_packets,rx_packets,lost_packets,queue_disc_drops,packet_loss_ratio_percent,throughput_mbps,average_delay_ms,run_seed,flow_id`.
- `scripts/run_experiments.py`
  - Compiles with `ns3-compile`.
  - Runs the 10 buffer samples.
  - Parses and validates CSV output.
  - Rejects flat representative metrics: `queue_disc_drops` and `average_delay_ms`.
  - Writes `results/qos_results.csv`.
  - Calls `scripts/plot_results.py` unless `--skip-plots` is used.
- `scripts/plot_results.py`
  - Reads `results/qos_results.csv`.
  - Generates five PNG graphs.
- `tests/test_experiment_scripts.py`
  - Tests default buffer samples, command construction, CSV parsing, row validation, `queue_disc_drops`, and flat-metric rejection.
- `README.md`
  - Documents setup, topology, variables, mild-congestion load, outputs, and verification.

## Commands

| Purpose             | Command                                                                    | Expected on success             |
| ------------------- | -------------------------------------------------------------------------- | ------------------------------- |
| Compile NS-3 source | `ns3-compile src/queue_buffer_qos.cc -o build/queue_buffer_qos`            | exit 0, executable created      |
| Run one simulation  | `./build/queue_buffer_qos --bufferPackets=10 --runSeed=1 --csvHeader=true` | exit 0, header plus one CSV row |
| Run Python tests    | `python -m unittest tests/test_experiment_scripts.py -v`                   | all tests pass                  |
| Run full experiment | `python scripts/run_experiments.py`                                        | CSV and five PNG graphs created |

## Final Verification Checklist

- [x] `ns3-compile src/queue_buffer_qos.cc -o build/queue_buffer_qos` exits 0.
- [x] `python -m unittest tests/test_experiment_scripts.py -v` exits 0.
- [x] `python scripts/run_experiments.py` exits 0.
- [x] `results/qos_results.csv` has exactly 10 data rows.
- [x] Buffers are exactly `1,5,10,20,50,100,200,500,750,1000`.
- [x] Every row has `tx_packets > 0`.
- [x] Every row has `flow_id > 0`.
- [x] CSV includes `queue_disc_drops`.
- [x] `queue_disc_drops` varies across buffer samples.
- [x] `average_delay_ms` varies across buffer samples.
- [x] Five PNG graphs exist and are non-empty:
  - `results/throughput_vs_buffer.png`
  - `results/delay_vs_buffer.png`
  - `results/packet_loss_ratio_vs_buffer.png`
  - `results/lost_packets_vs_buffer.png`
  - `results/queue_disc_drops_vs_buffer.png`

## Representative Result Snapshot

Current default output shows visible X-to-Y effects:

| buffer_packets | queue_disc_drops | lost_packets | packet_loss_ratio_percent | throughput_mbps | average_delay_ms |
| -------------- | ---------------: | -----------: | ------------------------: | --------------: | ---------------: |
| 1              |             1222 |          492 |                 22.394174 |        0.797181 |        26.381596 |
| 1000           |              223 |           90 |                  4.096495 |        0.984615 |      2441.509905 |

Interpretation:

- Larger buffer lowers queue-disc drops.
- Larger buffer lowers packet loss more clearly because simulation drain time lets large queues empty before final statistics.
- Larger buffer slightly increases throughput.
- Larger buffer increases delay, matching the queueing-delay hypothesis.

## Future Change Rules

- Keep queue buffer size as the independent variable unless the research question changes.
- If the queue discipline changes from `FifoQueueDisc`, revisit the queue-disc drop reason used in `GetNDroppedPackets`.
- If traffic rates change, preserve mild congestion: offered load should exceed `2Mbps` bottleneck capacity without overwhelming it so hard that all curves become flat.
- After any change, run the full final verification checklist.
