from __future__ import annotations

import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd
import yaml


@dataclass
class RulePack:
    version: int
    name: str
    description: str
    parameters: Dict[str, Any]
    logic: Dict[str, Any]


class RulesEngine:
    """
    Minimal, config-driven rules engine.

    - Loads YAML packs from src/rules/configs
    - Evaluates row-wise conditions using a tiny safe expression parser
    - Emits categories and an audit trace per row
    """

    def __init__(self, rules_path: Path):
        self.rules_path = rules_path

    def load_pack(self, pack_filename: str) -> RulePack:
        data = yaml.safe_load(Path(self.rules_path, pack_filename).read_text(encoding="utf-8"))
        return RulePack(
            version=data["version"],
            name=data["name"],
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            logic=data["logic"],
        )

    def _eval_condition(self, expr: str, row: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """
        Very small DSL:
          - Supports 'and', 'or', 'not', 'in', '==', '!=', '<=', '>=' comparisons
          - 'null' means None; 'not null' check is handled by 'is not None' pattern
        """
        # Replace friendly shortcuts
        expr = expr.replace(" not null", " != None")
        # Replace identifiers with row/param lookups safely
        env: Dict[str, Any] = {"None": None}
        # expose all row and params as variables
        env.update({k: row.get(k) for k in row.keys()})
        env.update(params)

        # Allowed builtins/operators (kept minimal for safety)
        allowed_names = set(env.keys())
        code = compile(expr, "<rules>", "eval")
        for name in code.co_names:
            if name not in allowed_names and name not in {"in"}:
                raise ValueError(f"Illegal name in expression: {name}")
        return bool(eval(code, {"__builtins__": {}}, env))

    def evaluate(self, gdf: gpd.GeoDataFrame, pack: RulePack) -> gpd.GeoDataFrame:
        out = gdf.copy()
        audit: List[List[str]] = [[] for _ in range(len(out))]

        for dimension, rules in pack.logic.items():
            result_col = f"{dimension}_category"
            out[result_col] = None
            for i, row in out.iterrows():
                assigned: Optional[str] = None
                for rule in rules:
                    if "default" in rule:
                        assigned = assigned or rule["default"]
                        continue
                    cond = rule["when"]
                    if self._eval_condition(cond, row.to_dict(), pack.parameters):
                        assigned = rule["then"]
                        audit[i].append(f"{dimension}:{cond}=>{assigned}")
                        break
                out.at[i, result_col] = assigned

        out["rulepack_version"] = pack.version
        out["rulepack_name"] = pack.name
        out["rule_audit"] = audit
        return out
