"""Stochastic parameter loading and transformation outcome models."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


def _sample_poisson_small(rng, lam):
    threshold = math.exp(-lam)
    count = 0
    product = 1.0
    while product > threshold:
        count += 1
        product *= rng.random()
    return count - 1


def sample_poisson(rng, lam):
    """Sample a Poisson-distributed value without requiring numpy."""
    if lam <= 0:
        return 0
    if lam < 30:
        return _sample_poisson_small(rng, lam)
    approximation = int(round(rng.gauss(lam, math.sqrt(lam))))
    return max(0, approximation)


@dataclass
class TransformationParameterBundle:
    raw: Dict[str, object]
    parameter_map: Dict[str, Dict[str, object]]

    def get(self, name: str) -> Dict[str, object]:
        return self.parameter_map[name]

    def sample_base_efficiency(self, rng) -> float:
        parameter = self.get("base_transformation_efficiency_cfu_per_ug")
        bounds = parameter["parameters"]
        minimum = float(bounds["min"])
        maximum = float(bounds["max"])
        return rng.uniform(minimum, maximum)

    def recommended_antibiotic_concentration(self, antibiotic: str) -> Optional[float]:
        for name in (
            "{:s}_selection_working_concentration_ug_per_ml".format(antibiotic.lower()),
            "{:s}_selection_working_concentration_ug_ml".format(antibiotic.lower()),
        ):
            if name in self.parameter_map:
                return float(self.parameter_map[name]["parameters"]["value"])
        return None

    def countable_colony_range(self) -> tuple[int, int]:
        parameter = self.get("countable_colony_range_per_plate")["parameters"]
        return int(parameter["min"]), int(parameter["max"])

    def soc_multiplier(self) -> float:
        return float(self.get("soc_vs_lb_efficiency_multiplier")["parameters"]["soc"])

    def lb_multiplier(self) -> float:
        return float(self.get("soc_vs_lb_efficiency_multiplier")["parameters"]["lb"])

    def shaking_multiplier(self) -> float:
        return float(self.get("shaking_efficiency_multiplier")["parameters"]["with_shaking"])

    def static_multiplier(self) -> float:
        return float(self.get("shaking_efficiency_multiplier")["parameters"]["without_shaking"])

    def recovery_penalty(self, recovery_minutes: int) -> float:
        parameter = self.get("recovery_penalty_per_15_min_shortened")["parameters"]
        optimal = int(parameter["optimal_minutes"])
        penalty = float(parameter["penalty_factor_per_15_min_shortened"])
        if recovery_minutes >= optimal:
            return 1.0
        shortfall_steps = (optimal - recovery_minutes) / 15.0
        return penalty ** shortfall_steps

    def ice_incubation_penalty(self, ice_incubation_minutes: int) -> float:
        parameter = self.get("dna_ice_incubation_penalty_per_10_min_shortened")["parameters"]
        optimal = int(parameter["optimal_minutes"])
        penalty = float(parameter["penalty_factor_per_10_min_shortened"])
        if ice_incubation_minutes >= optimal:
            return 1.0
        shortfall_steps = (optimal - ice_incubation_minutes) / 10.0
        return penalty ** shortfall_steps


def load_transformation_parameters(path: Path) -> TransformationParameterBundle:
    """Load the transformation parameter bundle from disk."""
    with open(path) as handle:
        raw = json.load(handle)
    parameter_map = {
        item["parameter_name"]: item for item in raw.get("parameters", [])
    }
    return TransformationParameterBundle(raw=raw, parameter_map=parameter_map)


@dataclass
class GrowthParameterBundle:
    raw: Dict[str, object]
    parameter_map: Dict[str, Dict[str, object]]

    def get(self, name: str) -> Dict[str, object]:
        return self.parameter_map[name]

    def value(self, name: str) -> float:
        return float(self.get(name)["parameters"]["value"])

    def fraction(self, name: str) -> float:
        return float(self.get(name)["parameters"]["fraction"])


def load_growth_parameters(path: Path) -> GrowthParameterBundle:
    with open(path) as handle:
        raw = json.load(handle)
    parameter_map = {
        item["parameter_name"]: item for item in raw.get("parameters", [])
    }
    return GrowthParameterBundle(raw=raw, parameter_map=parameter_map)


@dataclass
class PcrParameterBundle:
    raw: Dict[str, object]
    parameter_map: Dict[str, Dict[str, object]]

    def get(self, name: str) -> Dict[str, object]:
        return self.parameter_map[name]

    def values(self, name: str) -> list[str]:
        return list(self.get(name)["parameters"]["values"])

    def range(self, name: str) -> tuple[float, float]:
        parameter = self.get(name)["parameters"]
        return float(parameter["min"]), float(parameter["max"])


def load_pcr_parameters(path: Path) -> PcrParameterBundle:
    with open(path) as handle:
        raw = json.load(handle)
    parameter_map = {
        item["parameter_name"]: item for item in raw.get("parameters", [])
    }
    return PcrParameterBundle(raw=raw, parameter_map=parameter_map)


@dataclass
class ScreeningParameterBundle:
    raw: Dict[str, object]
    parameter_map: Dict[str, Dict[str, object]]

    def get(self, name: str) -> Dict[str, object]:
        return self.parameter_map[name]

    def value(self, name: str) -> float:
        return float(self.get(name)["parameters"]["value"])

    def integer(self, name: str) -> int:
        return int(self.get(name)["parameters"]["value"])


def load_screening_parameters(path: Path) -> ScreeningParameterBundle:
    with open(path) as handle:
        raw = json.load(handle)
    parameter_map = {
        item["parameter_name"]: item for item in raw.get("parameters", [])
    }
    return ScreeningParameterBundle(raw=raw, parameter_map=parameter_map)


@dataclass
class CloningParameterBundle:
    raw: Dict[str, object]
    parameter_map: Dict[str, Dict[str, object]]

    def get(self, name: str) -> Dict[str, object]:
        return self.parameter_map[name]

    def value(self, name: str) -> float:
        return float(self.get(name)["parameters"]["value"])

    def integer(self, name: str) -> int:
        return int(self.get(name)["parameters"]["value"])

    def text(self, name: str) -> str:
        return str(self.get(name)["parameters"]["value"])

    def choices(self, name: str) -> List[str]:
        value = self.get(name)["parameters"]["value"]
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]


def load_cloning_parameters(path: Path) -> CloningParameterBundle:
    with open(path) as handle:
        raw = json.load(handle)
    parameter_map = {
        item["parameter_name"]: item for item in raw.get("parameters", [])
    }
    return CloningParameterBundle(raw=raw, parameter_map=parameter_map)
