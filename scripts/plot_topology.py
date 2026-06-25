#!/usr/bin/env python3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch


NODE_POSITIONS = {
    "H0": (-3.2, 2.0),
    "H1": (0.0, 3.1),
    "H2": (3.2, 2.0),
    "H3": (2.2, -1.7),
    "H4": (-2.2, -1.7),
    "R0": (-1.9, 1.2),
    "R1": (0.0, 2.0),
    "R2": (1.9, 1.2),
    "R3": (1.2, -0.7),
    "R4": (-1.2, -0.7),
}

TOPOLOGY_EDGES = [
    {"source": "H0", "target": "R0", "kind": "host", "label": "100Mbps, 2ms"},
    {"source": "H1", "target": "R1", "kind": "host", "label": "100Mbps, 2ms"},
    {"source": "H2", "target": "R2", "kind": "host", "label": "100Mbps, 2ms"},
    {"source": "H3", "target": "R3", "kind": "host", "label": "100Mbps, 2ms"},
    {"source": "R4", "target": "H4", "kind": "bottleneck", "label": "2Mbps, 10ms, FIFO queue disc"},
    {"source": "R0", "target": "R1", "kind": "router", "label": "10Mbps, 5ms"},
    {"source": "R1", "target": "R2", "kind": "router", "label": "10Mbps, 5ms"},
    {"source": "R2", "target": "R3", "kind": "router", "label": "10Mbps, 5ms"},
    {"source": "R3", "target": "R4", "kind": "router", "label": "10Mbps, 5ms"},
    {"source": "R4", "target": "R0", "kind": "router", "label": "10Mbps, 5ms"},
    {"source": "R0", "target": "R2", "kind": "redundant", "label": "redundant"},
    {"source": "R1", "target": "R3", "kind": "redundant", "label": "redundant"},
]

TRAFFIC_FLOWS = [
    {"source": "H0", "target": "H4", "label": "main 1Mbps UDP CBR", "main": True},
    {"source": "H1", "target": "H4", "label": "bg 0.5Mbps", "main": False},
    {"source": "H2", "target": "H4", "label": "bg 0.5Mbps", "main": False},
    {"source": "H3", "target": "H4", "label": "bg 0.5Mbps", "main": False},
]


def _midpoint(source: str, target: str) -> tuple[float, float]:
    x1, y1 = NODE_POSITIONS[source]
    x2, y2 = NODE_POSITIONS[target]
    return (x1 + x2) / 2, (y1 + y2) / 2


def _draw_edge(ax, source: str, target: str, *, color: str, linewidth: float, linestyle: str = "-") -> None:
    x1, y1 = NODE_POSITIONS[source]
    x2, y2 = NODE_POSITIONS[target]
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth, linestyle=linestyle, zorder=1)


def _draw_node(ax, name: str) -> None:
    x, y = NODE_POSITIONS[name]
    is_router = name.startswith("R")
    face_color = "#ffffff" if is_router else "#e8f3ff"
    edge_color = "#274060" if is_router else "#3b82c4"
    marker = "o" if is_router else "s"

    ax.scatter([x], [y], s=1150, marker=marker, facecolor=face_color, edgecolor=edge_color, linewidth=2.2, zorder=4)
    ax.text(x, y, name, ha="center", va="center", fontsize=13, fontweight="bold", color="#1f2933", zorder=5)


def _draw_traffic_arrow(ax, flow: dict[str, object], index: int) -> None:
    source = str(flow["source"])
    target = str(flow["target"])
    x1, y1 = NODE_POSITIONS[source]
    x2, y2 = NODE_POSITIONS[target]
    color = "#b42318" if flow["main"] else "#6b7280"
    linewidth = 2.4 if flow["main"] else 1.4
    radius = 0.15 + index * 0.08
    arrow = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle="-|>",
        mutation_scale=16,
        linewidth=linewidth,
        color=color,
        alpha=0.82,
        connectionstyle=f"arc3,rad={radius}",
        shrinkA=24,
        shrinkB=24,
        zorder=3,
    )
    ax.add_patch(arrow)


def plot_topology(output_path: Path, buffer_packets: int = 10) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11.5, 7.2))
    ax.set_facecolor("#fbfcfd")

    for edge in TOPOLOGY_EDGES:
        kind = edge["kind"]
        if kind == "bottleneck":
            _draw_edge(ax, edge["source"], edge["target"], color="#d92d20", linewidth=4.2)
        elif kind == "redundant":
            _draw_edge(ax, edge["source"], edge["target"], color="#7c8794", linewidth=1.8, linestyle="--")
        elif kind == "router":
            _draw_edge(ax, edge["source"], edge["target"], color="#344054", linewidth=2.3)
        else:
            _draw_edge(ax, edge["source"], edge["target"], color="#3b82c4", linewidth=2.0)

    for index, flow in enumerate(TRAFFIC_FLOWS):
        _draw_traffic_arrow(ax, flow, index)

    for name in NODE_POSITIONS:
        _draw_node(ax, name)

    for edge in TOPOLOGY_EDGES:
        if edge["kind"] in {"bottleneck", "redundant"}:
            x, y = _midpoint(edge["source"], edge["target"])
            label = edge["label"]
            if edge["kind"] == "bottleneck":
                label = f"{label}\nbuffer={buffer_packets}p"
                x = 0.25
                y = -1.65
            else:
                y += 0.18
            ax.text(
                x,
                y,
                label,
                ha="center",
                va="center",
                fontsize=9.5,
                color="#344054",
                bbox={"boxstyle": "round,pad=0.25", "facecolor": "#ffffff", "edgecolor": "#d0d5dd"},
                zorder=6,
            )

    ax.text(
        -3.65,
        -2.55,
        "Traffic\nmain: H0 -> H4 (1Mbps)\nbg: H1-H3 -> H4 (0.5Mbps)",
        fontsize=9.5,
        color="#344054",
        linespacing=1.35,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#ffffff", "edgecolor": "#d0d5dd"},
    )
    ax.text(
        0.95,
        -2.48,
        "Bottleneck: R4 -> H4",
        fontsize=10.5,
        color="#b42318",
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "#fff7f5", "edgecolor": "#fecdca"},
    )

    ax.set_title("Topologi Jaringan Existing Simulasi NS-3", fontsize=15, fontweight="bold", pad=18)
    ax.set_xlim(-4.1, 4.1)
    ax.set_ylim(-3.0, 3.55)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    plot_topology(root / "results" / "network_topology.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
