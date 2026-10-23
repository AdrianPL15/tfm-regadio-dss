"""Genera el esquema de arquitectura y distingue estado actual y futuro."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


DEFAULT_OUTPUT = Path("docs/images/arquitectura_sistema_3_2.png")


def _box(
    axis,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    detail: str,
    *,
    implemented: bool,
) -> None:
    color = "#22577A" if implemented else "#6C757D"
    face = "#E8F1F7" if implemented else "#F4F4F4"
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=1.8,
        edgecolor=color,
        facecolor=face,
        linestyle="-" if implemented else "--",
    )
    axis.add_patch(patch)
    axis.text(
        x + width / 2,
        y + height * 0.68,
        title,
        ha="center",
        va="center",
        fontsize=12.5,
        fontweight="bold",
        color="#17324D" if implemented else "#4D4D4D",
    )
    axis.text(
        x + width / 2,
        y + height * 0.34,
        detail,
        ha="center",
        va="center",
        fontsize=10.5,
        color="#334E68" if implemented else "#666666",
        linespacing=1.25,
    )


def _arrow(axis, start: tuple[float, float], end: tuple[float, float], *, dashed=False) -> None:
    axis.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.6,
            color="#527286" if not dashed else "#7A7A7A",
            linestyle="--" if dashed else "-",
            shrinkA=4,
            shrinkB=4,
        )
    )


def build_visual(output: Path = DEFAULT_OUTPUT) -> Path:
    """Construye y guarda la figura de arquitectura."""
    # Una página A4 reduce la figura a unos 15 cm de ancho. Dos filas permiten
    # mantener el texto de las cajas legible al imprimir la memoria.
    figure, axis = plt.subplots(figsize=(9, 6))
    figure.patch.set_facecolor("white")
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")

    axis.text(
        0.5,
        0.965,
        "Arquitectura del DSS de riego y estado de implementación",
        ha="center",
        va="center",
        fontsize=17,
        fontweight="bold",
        color="#17324D",
    )
    axis.text(
        0.5,
        0.925,
        "Piloto actual: pimiento · Almería · estación SiAR AL01",
        ha="center",
        va="center",
        fontsize=11.5,
        color="#52697A",
    )

    h = 0.14
    width = 0.25
    top_y, mid_y = 0.68, 0.43
    positions = [0.045, 0.375, 0.705]
    top_boxes = [
        ("1. Caso piloto", "pimiento · AL01\nperiodo definido"),
        ("2. Fuentes", "SiAR clima y cultivo\nAEMET: integración"),
        ("3. Ingesta Python", "descarga · metadatos\ntrazabilidad"),
    ]
    middle_boxes = [
        ("6. Evidencias", "métricas · CSV\nfiguras · memoria"),
        ("5. Análisis y ML", "variables · EDA\nseis enfoques"),
        ("4. Capas de datos", "raw / external\ninterim / processed"),
    ]
    for x, (title, detail) in zip(positions, top_boxes):
        _box(axis, x, top_y, width, h, title, detail, implemented=True)
    for x, (title, detail) in zip(positions, middle_boxes):
        _box(axis, x, mid_y, width, h, title, detail, implemented=True)
    for left, right in ((0, 1), (1, 2)):
        _arrow(axis, (positions[left] + width, top_y + h / 2), (positions[right], top_y + h / 2))
        _arrow(axis, (positions[right], mid_y + h / 2), (positions[left] + width, mid_y + h / 2))
    _arrow(axis, (positions[2] + width / 2, top_y), (positions[2] + width / 2, mid_y + h))

    axis.text(
        0.045,
        0.855,
        "PROTOTIPO IMPLEMENTADO",
        fontsize=12,
        fontweight="bold",
        color="#22577A",
    )

    future_y = 0.11
    future_boxes = [
        (0.035, 0.20, "Orquestación", "Apache Hop\ncargas programadas", False),
        (0.280, 0.20, "Persistencia", "MySQL / Parquet\nmetadatos", False),
        (0.525, 0.20, "Motor DSS", "reglas · ET0 × Kc\ndosis y explicación", True),
        (0.770, 0.20, "Presentación", "Streamlit · CSV\nPower BI opcional", True),
    ]
    for x, width, title, detail, implemented in future_boxes:
        _box(axis, x, future_y, width, h, title, detail, implemented=implemented)
    for index in range(len(future_boxes) - 1):
        x, width, _, _, done = future_boxes[index]
        next_x, _, _, _, next_done = future_boxes[index + 1]
        _arrow(
            axis,
            (x + width, future_y + h / 2),
            (next_x, future_y + h / 2),
            dashed=not (done and next_done),
        )
    axis.text(
        0.045,
        0.345,
        "SISTEMA DE RECOMENDACIÓN Y ARQUITECTURA OBJETIVO",
        fontsize=12,
        fontweight="bold",
        color="#6C757D",
    )
    axis.text(
        0.5, 0.055,
        "Azul: implementado   ·   Gris discontinuo: previsto",
        ha="center", va="center", fontsize=10.5, color="#52697A",
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el esquema de arquitectura del capítulo 3.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(build_visual(args.output))


if __name__ == "__main__":
    main()
