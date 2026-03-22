from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import json

import pandas as pd

from config import SYMBOLS_CACHE_PATH


@dataclass
class SymbolSyncResult:
    active_symbols: list[str]
    dormant_symbols: list[str]
    missing_in_config: list[str]
    missing_in_tv: list[str]
    report_path: Path
    csv_path: Path


def _is_dormant(row) -> bool:
    """Heuristic: treat as dormant if close or volume missing/zero."""
    close = row.get("close")
    volume = row.get("volume")
    if close is None or pd.isna(close):
        return True
    if volume is None or pd.isna(volume):
        return True
    try:
        return float(volume) <= 0
    except Exception:
        return True


def sync_symbols_from_tradingview(config_symbols: Iterable[str], out_csv: Path | None = None) -> SymbolSyncResult:
    """
    Fetch EGX symbols via tradingview-screener, compare to config_symbols,
    drop dormant symbols, and write an updated CSV for config.py to load.
    """
    try:
        from tradingview_screener import Query
    except Exception as e:
        raise RuntimeError(
            f"tradingview-screener not available: {e}. Install with: pip install \"egx-toolkit[sync]\""
        ) from e

    out_csv = out_csv or SYMBOLS_CACHE_PATH

    rows, df_symbols = (
        Query()
        .set_markets("egypt")
        .select("name", "description", "close", "change", "volume", "type")
        .limit(500)
        .get_scanner_data()
    )

    if df_symbols is None or df_symbols.empty:
        raise RuntimeError("No symbols returned from tradingview-screener.")

    df_symbols["name"] = df_symbols["name"].astype(str).str.strip().str.upper()
    df_symbols = df_symbols[df_symbols["name"] != ""]

    # Keep only stocks if the column exists
    if "type" in df_symbols.columns:
        df_symbols = df_symbols[df_symbols["type"].astype(str).str.lower() == "stock"]

    df_symbols["is_dormant"] = df_symbols.apply(_is_dormant, axis=1)

    active_df = df_symbols[df_symbols["is_dormant"] == False].copy()
    active_symbols = active_df["name"].tolist()
    dormant_symbols = df_symbols[df_symbols["is_dormant"] == True]["name"].tolist()

    config_set = {s.strip().upper() for s in config_symbols if str(s).strip()}
    tv_set = set(active_symbols)

    missing_in_config = sorted(list(tv_set - config_set))
    missing_in_tv = sorted(list(config_set - tv_set))

    # Write CSV used by config.py
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    active_df = active_df.rename(columns={"name": "Symbol"})
    active_df.to_csv(out_csv, index=False)

    report = {
        "source": "tradingview-screener",
        "market": "egypt",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "active_count": len(active_symbols),
        "dormant_count": len(dormant_symbols),
        "missing_in_config": missing_in_config,
        "missing_in_tv": missing_in_tv,
        "csv_path": str(out_csv),
    }
    report_path = out_csv.with_suffix(".tv_report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return SymbolSyncResult(
        active_symbols=active_symbols,
        dormant_symbols=dormant_symbols,
        missing_in_config=missing_in_config,
        missing_in_tv=missing_in_tv,
        report_path=report_path,
        csv_path=out_csv,
    )
