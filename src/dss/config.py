"""Parámetros, constantes y casos de uso del motor de recomendación.

Los valores por defecto describen el piloto reproducible del TFM: pimiento en
la estación SiAR AL01 La Mojonera durante la campaña de 2025. Su encuadre como
cultivo al aire libre es una hipótesis pendiente de acreditar para este CSV.
Los casos adicionales de la demo reutilizan la misma lógica del motor. Desde
octubre de 2026 disponen también de una evaluación temporal predictiva por
caso, que no es una validación externa ni un modelo compartido.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


DEFAULT_CROP_NEEDS = Path("data/external/siar_necesidades_pimiento_AL01_2025.csv")
DEFAULT_CROP_METADATA = Path(
    "data/external/siar_necesidades_pimiento_AL01_2025.metadata.json"
)
DEFAULT_VALIDATION_REPORT = Path("docs/data_samples/dss_validation_5_3.json")

# Ventana de ET0 reciente seleccionada en el periodo de desarrollo (apartado 5.3).
ET0_WINDOW_DAYS = 7

# Horizonte validado con mayor detalle en el apartado 4.3.
VALIDATED_HORIZON_DAYS = 1
MAX_HORIZON_DAYS = 7

# Eficiencias de aplicación orientativas por sistema (Brouwer et al., 1989).
IRRIGATION_EFFICIENCY = {
    "goteo": 0.90,
    "aspersion": 0.75,
    "superficie": 0.60,
}

# Un milímetro de lámina sobre una hectárea equivale a 10 m3.
M3_PER_MM_HA = 10.0

# Márgenes para detectar extrapolación respecto a lo observado en la campaña.
EXTRAPOLATION_MARGIN = 0.10

# Umbrales de la regla de lluvia prevista.
RAIN_AMOUNT_THRESHOLD_MM = 5.0
RAIN_PROBABILITY_THRESHOLD_PCT = 60.0

# Antigüedad máxima admitida del último dato observado.
MAX_DATA_AGE_DAYS = 2


@dataclass(frozen=True)
class CropCase:
    """Combinación de cultivo, ubicación y fuente que analiza el sistema."""

    crop: str = "Pimiento"
    production_system: str = "Aire libre"
    station_code: str = "AL01"
    station_name: str = "La Mojonera"
    province: str = "Almería"
    source_file: Path = DEFAULT_CROP_NEEDS
    metadata_file: Path = DEFAULT_CROP_METADATA
    community: str = "Andalucía"
    region: str = "Dalias"
    aemet_municipality_code: str = "04013"
    campaign_year: int = 2025


DEMO_CASES: tuple[CropCase, ...] = (
    CropCase(),
    CropCase(
        crop="Pimiento",
        production_system="No acreditado",
        station_code="AL01",
        station_name="La Mojonera",
        province="Almería",
        source_file=Path("data/external/siar_necesidades_pimiento_AL01_2026.csv"),
        metadata_file=Path("data/external/siar_necesidades_pimiento_AL01_2026.metadata.json"),
        community="Andalucía",
        region="Dalias",
        aemet_municipality_code="04013",
        campaign_year=2026,
    ),
    CropCase(
        crop="Coliflor",
        production_system="No acreditado",
        station_code="AL01",
        station_name="La Mojonera",
        province="Almería",
        source_file=Path("data/external/siar_necesidades_coliflor_AL01_2026.csv"),
        metadata_file=Path("data/external/siar_necesidades_coliflor_AL01_2026.metadata.json"),
        community="Andalucía",
        region="Dalias",
        aemet_municipality_code="04013",
        campaign_year=2026,
    ),
    CropCase(
        crop="Maíz",
        production_system="No acreditado",
        station_code="Z06",
        station_name="Ejea de los Caballeros",
        province="Zaragoza",
        source_file=Path("data/external/siar_necesidades_maiz_Z06_2025.csv"),
        metadata_file=Path("data/external/siar_necesidades_maiz_Z06_2025.metadata.json"),
        community="Aragón",
        region="Ejea de los Caballeros",
        aemet_municipality_code="50095",
    ),
    CropCase(
        crop="Maíz",
        production_system="No acreditado",
        station_code="Z06",
        station_name="Ejea de los Caballeros",
        province="Zaragoza",
        source_file=Path("data/external/siar_necesidades_maiz_Z06_2026.csv"),
        metadata_file=Path("data/external/siar_necesidades_maiz_Z06_2026.metadata.json"),
        community="Aragón",
        region="Ejea de los Caballeros",
        aemet_municipality_code="50095",
        campaign_year=2026,
    ),
    CropCase(
        crop="Algodón",
        production_system="No acreditado",
        station_code="BA08",
        station_name="Don Benito",
        province="Badajoz",
        source_file=Path("data/external/siar_necesidades_algodon_BA08_2025.csv"),
        metadata_file=Path("data/external/siar_necesidades_algodon_BA08_2025.metadata.json"),
        community="Extremadura",
        region="Don Benito",
        aemet_municipality_code="06044",
    ),
    CropCase(
        crop="Algodón",
        production_system="No acreditado",
        station_code="BA08",
        station_name="Don Benito",
        province="Badajoz",
        source_file=Path("data/external/siar_necesidades_algodon_BA08_2026.csv"),
        metadata_file=Path("data/external/siar_necesidades_algodon_BA08_2026.metadata.json"),
        community="Extremadura",
        region="Don Benito",
        aemet_municipality_code="06044",
        campaign_year=2026,
    ),
)


@dataclass(frozen=True)
class RecommendationRequest:
    """Datos que introduce el usuario para solicitar una recomendación."""

    issue_date: date
    horizon_days: int = 7
    irrigation_system: str = "goteo"
    efficiency: float | None = None
    area_ha: float | None = None
    weekly_allocation_mm: float | None = None
    mode: str = "planificacion"
    # Hipótesis explícita del usuario para un escenario condicionado a lluvia;
    # None conserva la dosis base, sin atribuir a AEMET lluvia efectiva medida.
    rain_effective_fraction: float | None = None
    case: CropCase = field(default_factory=CropCase)

    def resolved_efficiency(self) -> float:
        if self.efficiency is not None:
            return float(self.efficiency)
        try:
            return IRRIGATION_EFFICIENCY[self.irrigation_system]
        except KeyError as exc:
            valid = ", ".join(sorted(IRRIGATION_EFFICIENCY))
            raise ValueError(
                f"Sistema de riego desconocido: {self.irrigation_system}. "
                f"Valores admitidos: {valid}."
            ) from exc

    def validate(self) -> None:
        if not 1 <= int(self.horizon_days) <= MAX_HORIZON_DAYS:
            raise ValueError(
                f"El horizonte debe estar entre 1 y {MAX_HORIZON_DAYS} días."
            )
        efficiency = self.resolved_efficiency()
        if not 0.3 <= efficiency <= 1.0:
            raise ValueError("La eficiencia debe estar entre 0,30 y 1,00.")
        if self.area_ha is not None and self.area_ha <= 0:
            raise ValueError("La superficie debe ser positiva.")
        if self.weekly_allocation_mm is not None and self.weekly_allocation_mm < 0:
            raise ValueError("La dotación semanal no puede ser negativa.")
        if self.mode not in {"planificacion", "seguimiento"}:
            raise ValueError("El modo debe ser 'planificacion' o 'seguimiento'.")
        if self.rain_effective_fraction is not None and not 0 <= self.rain_effective_fraction <= 1:
            raise ValueError("La fracción efectiva hipotética de lluvia debe estar entre 0 y 1.")
