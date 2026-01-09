from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass(frozen=True)
class IndicatorMeta:
    key: str
    indicator_name: str
    category: str
    unit: str
    primary_chart: str
    plot_mode: str
    group_key: str
    data_freq: str
    formula: str


@dataclass(frozen=True)
class GroupMeta:
    key: str
    display_name: str
    description: str
    indicator_keys: List[str]
    require_same_unit: bool = True


@dataclass(frozen=True)
class Schema:
    version: str
    indicators: Dict[str, IndicatorMeta]
    groups: Dict[str, GroupMeta]


def load_schema(path: str | Path = "config/indicators.yaml") -> Schema:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path.resolve()}")

    with path.open("r", encoding="utf-8") as f:
        data: Dict[str, Any] = yaml.safe_load(f) or {}

    indicators_raw = data.get("indicators", {}) or {}
    groups_raw = data.get("groups", {}) or {}

    indicators: Dict[str, IndicatorMeta] = {}
    for key, meta in indicators_raw.items():
        indicators[key] = IndicatorMeta(
            key=key,
            indicator_name=str(meta.get("indicator_name", key)),
            category=str(meta.get("category", "")),
            unit=str(meta.get("unit", "")),
            primary_chart=str(meta.get("primary_chart", "line")),
            plot_mode=str(meta.get("plot_mode", "line_single")),
            group_key=str(meta.get("group_key", "")),
            data_freq=str(meta.get("data_freq", "annual")),
            formula=str(meta.get("formula", "")),
        )

    groups: Dict[str, GroupMeta] = {}
    for key, meta in groups_raw.items():
        groups[key] = GroupMeta(
            key=key,
            display_name=str(meta.get("display_name", key)),
            description=str(meta.get("description", "")),
            indicator_keys=list(meta.get("indicator_keys", [])),
            require_same_unit=bool(meta.get("require_same_unit", True)),
        )

    return Schema(
        version=str(data.get("version", "unknown")),
        indicators=indicators,
        groups=groups,
    )
