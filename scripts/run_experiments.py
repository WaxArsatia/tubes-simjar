#!/usr/bin/env python3
import argparse
import csv
import io
import math
import subprocess
import sys
from pathlib import Path

BUFFER_SAMPLES = [1, 5, 10, 20, 50, 100, 200, 500, 750, 1000]
FIELDNAMES = [
    "buffer_packets",
    "tx_packets",
    "rx_packets",
    "lost_packets",
    "queue_disc_drops",
    "packet_loss_ratio_percent",
    "throughput_mbps",
    "average_delay_ms",
    "run_seed",
    "flow_id",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_simulation_command(executable: Path, buffer_packets: int, run_seed: int) -> list[str]:
    return [
        str(executable),
        f"--bufferPackets={buffer_packets}",
        f"--runSeed={run_seed}",
        "--csvHeader=true",
    ]


def parse_simulation_csv(stdout: str) -> dict[str, str]:
    rows = list(csv.DictReader(io.StringIO(stdout.strip())))
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one simulation row, got {len(rows)}")
    missing = [field for field in FIELDNAMES if field not in rows[0]]
    if missing:
        raise ValueError(f"Simulation output missing columns: {', '.join(missing)}")
    return rows[0]


def parse_int_field(row: dict[str, str], field: str) -> int:
    try:
        return int(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer for row {row}") from exc


def parse_float_field(row: dict[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number for row {row}") from exc
    if not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number for row {row}")
    return value


def validate_rows(rows: list[dict[str, str]], repetitions: int) -> None:
    expected_count = len(BUFFER_SAMPLES) * repetitions
    if len(rows) != expected_count:
        raise ValueError(f"Expected {expected_count} rows, got {len(rows)}")

    expected_pairs = {(buffer, seed) for buffer in BUFFER_SAMPLES for seed in range(1, repetitions + 1)}
    actual_pairs = set()
    for row in rows:
        missing = [field for field in FIELDNAMES if field not in row]
        if missing:
            raise ValueError(f"Row missing columns: {', '.join(missing)}")

        buffer_packets = parse_int_field(row, "buffer_packets")
        run_seed = parse_int_field(row, "run_seed")
        pair = (buffer_packets, run_seed)
        if pair in actual_pairs:
            raise ValueError(f"Duplicate buffer/seed pair: {pair}")
        actual_pairs.add(pair)

        tx_packets = parse_int_field(row, "tx_packets")
        rx_packets = parse_int_field(row, "rx_packets")
        lost_packets = parse_int_field(row, "lost_packets")
        queue_disc_drops = parse_int_field(row, "queue_disc_drops")
        packet_loss_ratio_percent = parse_float_field(row, "packet_loss_ratio_percent")
        throughput_mbps = parse_float_field(row, "throughput_mbps")
        average_delay_ms = parse_float_field(row, "average_delay_ms")
        flow_id = parse_int_field(row, "flow_id")

        if tx_packets <= 0:
            raise ValueError(f"tx_packets must be > 0 for row {row}")
        if rx_packets < 0 or rx_packets > tx_packets:
            raise ValueError(f"rx_packets must be between 0 and tx_packets for row {row}")
        if lost_packets != tx_packets - rx_packets:
            raise ValueError(f"lost_packets must equal tx_packets - rx_packets for row {row}")
        if queue_disc_drops < 0:
            raise ValueError(f"queue_disc_drops must be >= 0 for row {row}")
        if packet_loss_ratio_percent < 0 or packet_loss_ratio_percent > 100:
            raise ValueError(f"packet_loss_ratio_percent must be between 0 and 100 for row {row}")
        expected_loss_ratio = lost_packets * 100 / tx_packets
        if abs(packet_loss_ratio_percent - expected_loss_ratio) > 1e-4:
            raise ValueError(f"packet_loss_ratio_percent does not match packet counts for row {row}")
        if throughput_mbps < 0:
            raise ValueError(f"throughput_mbps must be >= 0 for row {row}")
        if average_delay_ms < 0:
            raise ValueError(f"average_delay_ms must be >= 0 for row {row}")
        if flow_id <= 0:
            raise ValueError(f"flow_id must be > 0 for row {row}")

    if actual_pairs != expected_pairs:
        raise ValueError(f"Unexpected buffer/seed pairs: {sorted(actual_pairs)}")


def validate_metric_variation(rows: list[dict[str, str]], metric_names: list[str]) -> None:
    flat_metrics = []
    for metric_name in metric_names:
        values = {row[metric_name] for row in rows}
        if len(values) == 1:
            flat_metrics.append(metric_name)
    if flat_metrics:
        raise ValueError(f"Metrics are flat across buffer samples: {', '.join(flat_metrics)}")


def compile_simulation(root: Path, source: Path, executable: Path) -> None:
    executable.parent.mkdir(parents=True, exist_ok=True)
    command = ["ns3-compile", str(source), "-o", str(executable)]
    subprocess.run(command, cwd=root, check=True)


def run_simulation(root: Path, executable: Path, buffer_packets: int, run_seed: int) -> dict[str, str]:
    command = build_simulation_command(executable, buffer_packets, run_seed)
    completed = subprocess.run(command, cwd=root, check=True, text=True, capture_output=True)
    return parse_simulation_csv(completed.stdout)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NS-3 queue buffer QoS experiments.")
    parser.add_argument("--repetitions", type=int, default=1, help="Run seeds per buffer sample.")
    parser.add_argument("--compile-only", action="store_true", help="Only compile the NS-3 source.")
    parser.add_argument("--skip-plots", action="store_true", help="Do not generate PNG graphs.")
    args = parser.parse_args()

    if args.repetitions < 1:
        raise SystemExit("--repetitions must be >= 1")

    root = project_root()
    source = root / "src" / "queue_buffer_qos.cc"
    executable = root / "build" / "queue_buffer_qos"
    output_csv = root / "results" / "qos_results.csv"

    compile_simulation(root, source, executable)
    if args.compile_only:
        return 0

    rows: list[dict[str, str]] = []
    for seed in range(1, args.repetitions + 1):
        for buffer_packets in BUFFER_SAMPLES:
            print(f"running buffer={buffer_packets} seed={seed}", file=sys.stderr)
            rows.append(run_simulation(root, executable, buffer_packets, seed))

    rows.sort(key=lambda row: (int(row["run_seed"]), int(row["buffer_packets"])))
    validate_rows(rows, args.repetitions)
    validate_metric_variation(rows, ["queue_disc_drops", "average_delay_ms"])
    write_csv(output_csv, rows)
    print(f"wrote {output_csv}")

    if not args.skip_plots:
        subprocess.run([sys.executable, str(root / "scripts" / "plot_results.py")], cwd=root, check=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
