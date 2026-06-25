#!/usr/bin/env python3
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def aggregate_rows_by_buffer(rows: list[dict[str, str]], y_column: str) -> tuple[list[int], list[float]]:
    values_by_buffer: dict[int, list[float]] = {}

    for row in rows:
        try:
            buffer_packets = int(row["buffer_packets"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Could not parse buffer_packets value: {row.get('buffer_packets')!r}") from exc

        try:
            metric_value = float(row[y_column])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Could not parse {y_column} value: {row.get(y_column)!r}") from exc

        values_by_buffer.setdefault(buffer_packets, []).append(metric_value)

    buffers = sorted(values_by_buffer)
    averages = [sum(values_by_buffer[buffer]) / len(values_by_buffer[buffer]) for buffer in buffers]
    return buffers, averages


def plot_metric(rows: list[dict[str, str]], y_column: str, y_label: str, title: str, output_path: Path) -> None:
    x_values, y_values = aggregate_rows_by_buffer(rows, y_column)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x_values, y_values, marker="o", linewidth=2)
    ax.set_xlabel("Ukuran Queue Buffer (packet)")
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_xticks(x_values)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    results_dir = root / "results"
    rows = read_rows(results_dir / "qos_results.csv")
    if not rows:
        raise SystemExit("results/qos_results.csv has no rows")

    plot_metric(
        rows,
        "throughput_mbps",
        "Throughput (Mbps)",
        "Throughput vs Ukuran Queue Buffer",
        results_dir / "throughput_vs_buffer.png",
    )
    plot_metric(
        rows,
        "average_delay_ms",
        "Delay rata-rata (ms)",
        "Delay vs Ukuran Queue Buffer",
        results_dir / "delay_vs_buffer.png",
    )
    plot_metric(
        rows,
        "packet_loss_ratio_percent",
        "Packet loss ratio (%)",
        "Packet Loss Ratio vs Ukuran Queue Buffer",
        results_dir / "packet_loss_ratio_vs_buffer.png",
    )
    plot_metric(
        rows,
        "lost_packets",
        "Packet loss (packet)",
        "Packet Loss Count vs Ukuran Queue Buffer",
        results_dir / "lost_packets_vs_buffer.png",
    )
    plot_metric(
        rows,
        "queue_disc_drops",
        "Queue disc drops (packet)",
        "Queue Disc Drops vs Ukuran Queue Buffer",
        results_dir / "queue_disc_drops_vs_buffer.png",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
