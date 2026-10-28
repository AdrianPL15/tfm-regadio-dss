"""Genera el esquema que diferencia los cuatro bloques de evaluación del TFM."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


OUTPUT = Path("docs/images/evaluation_scope_map_1_1.png")


def build(output: Path = OUTPUT) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(11.2, 6.2), dpi=180)
    axis.set_xlim(0, 12)
    axis.set_ylim(0, 7)
    axis.axis("off")

    blocks = [
        (
            0.4,
            3.8,
            "Experimento predictivo",
            "Capítulo 4 · SiAR 2025–2026\nObjetivo: necesidad neta calculada\n6 enfoques · validación temporal + 15 % final",
            "Compara capacidad predictiva sin usar el día objetivo",
            "#DCEAF7",
        ),
        (
            6.2,
            3.8,
            "Motor operativo de ETc",
            "Capítulo 4.3.11 · seis casos\nObjetivo: ETc antes de lluvia\nModelo seleccionado frente a ET0 reciente × Kc",
            "AEMET se aplica después; su aportación histórica no está evaluada",
            "#E8F2E3",
        ),
        (
            0.4,
            0.5,
            "Validación retrospectiva del DSS",
            "Capítulo 5.3 · pimiento AL01 2025\nHorizontes 1–7 y 13 escenarios\nReferencia: necesidad calculada por SiAR",
            "Evalúa reglas y estabilidad, no riego aplicado en parcela",
            "#FFF0D9",
        ),
        (
            6.2,
            0.5,
            "Comprobación cronológica multicaso",
            "Capítulo 5.3.10 · tres casos de 2026\n15 % final · Kc > 0\nBootstrap pareado por bloques de 7 días",
            "Mide consistencia interna; no transferencia interanual",
            "#F1E7F7",
        ),
    ]

    for x, y, title, body, conclusion, color in blocks:
        box = FancyBboxPatch(
            (x, y), 5.4, 2.35,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            linewidth=1.1, edgecolor="#52606D", facecolor=color,
        )
        axis.add_patch(box)
        axis.text(x + 0.25, y + 2.02, title, fontsize=12, fontweight="bold", color="#172B4D")
        axis.text(x + 0.25, y + 1.50, body, fontsize=9.4, va="top", linespacing=1.35, color="#243B53")
        axis.plot([x + 0.25, x + 5.15], [y + 0.58, y + 0.58], color="#9FB3C8", linewidth=0.8)
        axis.text(x + 0.25, y + 0.42, conclusion, fontsize=8.7, va="top", color="#334E68")

    axis.text(
        6, 6.62, "Qué se evalúa en cada fase del proyecto",
        ha="center", fontsize=15, fontweight="bold", color="#102A43",
    )
    axis.text(
        6, 6.28,
        "Los cuatro bloques comparten fuentes, pero responden a preguntas distintas y no constituyen pruebas independientes entre sí.",
        ha="center", fontsize=9.5, color="#486581",
    )
    fig.tight_layout(pad=0.4)
    fig.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output


if __name__ == "__main__":
    print(build())
