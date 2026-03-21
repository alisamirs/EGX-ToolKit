import argparse
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

from symbol_sync import sync_symbols_from_tradingview

DEFAULT_URL = "https://stockanalysis.com/list/egyptian-stock-exchange/"


def _fetch_symbols_from_web(url):
    tables = pd.read_html(url)
    if not tables:
        raise RuntimeError("No tables found on source page.")

    table = None
    for t in tables:
        if "Symbol" in t.columns:
            table = t
            break

    if table is None:
        raise RuntimeError("No table with a 'Symbol' column found.")

    table["Symbol"] = table["Symbol"].astype(str).str.strip().str.upper()
    table = table[table["Symbol"] != ""]
    table = table.drop_duplicates(subset=["Symbol"])

    return table


def _write_outputs(df, out_csv, source_url):
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

    meta_path = out_csv.with_suffix(".meta.json")
    meta = {
        "source_url": source_url,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "symbol_count": int(df["Symbol"].nunique()),
    }
    meta_path.write_text(pd.Series(meta).to_json(), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Update EGX symbols list")
    parser.add_argument(
        "--source",
        choices=["tv", "web"],
        default="tv",
        help="Symbol source: tv (TradingView screener) or web (EGX list page).",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Source URL for EGX symbols list.")
    parser.add_argument(
        "--out",
        default=str(Path("data") / "egx_symbols.csv"),
        help="Output CSV path.",
    )
    args = parser.parse_args()

    out_csv = Path(args.out)

    if args.source == "tv":
        result = sync_symbols_from_tradingview([], out_csv=out_csv)
        print(f"Saved {len(result.active_symbols)} symbols to {result.csv_path}")
        return

    df = _fetch_symbols_from_web(args.url)
    _write_outputs(df, out_csv, args.url)
    print(f"Saved {len(df)} symbols to {out_csv}")


if __name__ == "__main__":
    main()
