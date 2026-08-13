from dataclasses import dataclass

@dataclass(frozen=True)
class WeightConfig:
    sar_weight: float = 0.35
    ndmi_weight: float = 0.25
    ndre_weight: float = 0.20
    precipitation_weight: float = 0.12
    soil_moisture_weight: float = 0.08

    def __post_init__(self):
        total = self.sar_weight + self.ndmi_weight + self.ndre_weight + self.precipitation_weight + self.soil_moisture_weight
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {total}")
