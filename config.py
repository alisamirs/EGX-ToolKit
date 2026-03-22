"""Configuration and constants for the finance application."""

import os
from pathlib import Path
from platformdirs import user_data_dir

# Project directories
PROJECT_ROOT = Path(__file__).parent

_env_data_dir = os.environ.get("EGX_DATA_DIR")
if _env_data_dir:
    DATA_DIR = Path(_env_data_dir)
else:
    DATA_DIR = Path(user_data_dir("egx-toolkit"))

DB_PATH = DATA_DIR / "stocks.duckdb"

# Create directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Trading symbols (EGX stocks)
SYMBOLS_SOURCE_URL = "https://stockanalysis.com/list/egyptian-stock-exchange/"
SYMBOLS_CACHE_PATH = DATA_DIR / "egx_symbols.csv"

def _load_symbols_from_cache():
    if not SYMBOLS_CACHE_PATH.exists():
        return None
    try:
        import pandas as pd
        df = pd.read_csv(SYMBOLS_CACHE_PATH)
        if "Symbol" not in df.columns:
            return None
        symbols = [str(s).strip().upper() for s in df["Symbol"].tolist() if str(s).strip()]
        return [s for s in symbols if s]
    except Exception:
        return None

_cached_symbols = _load_symbols_from_cache()

EGX_SYMBOLS = _cached_symbols if _cached_symbols else [
    "COMI", "TMGH", "CCAP", "GBCO", "AMOC", "FWRY", "HELI", "RAYA", "EGAL", "ISPH", "HRHO", "ABUK", "MPCI", "BTFH", "ORHD", "DSCW", "ADIB", "SKPC", "EGCH", "MFPC", "EFIH", "ETEL", "ORAS", "ALCN", "VLMRA", "MASR", "RMDA", "PHDC", "OIH", "EXPA", "EFIC", "JUFO", "MICH", "ACAMD", "NIPH", "ZMID", "CSAG", "ETRS", "AMER", "UEGC", "SCEM", "ARAB", "CIEB", "EGAS", "MCRO", "ATLC", "ARCC", "TAQA", "OLFI", "KRDI", "MPCO", "MEPA", "HBCO", "LCSW", "POUL", "AMIA", "SUGR", "AIDC", "MOED", "EAST", "OFH", "MTIE", "ACTF", "ZEOT", "RACC", "ORWE", "CLHO", "OBRI", "EMFD", "SDTI", "PRMH", "PHAR", "EGS72XL1C014", "MCQE", "AIH", "UNIP", "GDWA", "AMES", "EFID", "OCDI", "GGRN", "BINV", "SWDY", "ATQA", "KZPC", "COPR", "GTWL", "ELEC", "EPCO", "ICFC", "COSG", "RREI", "HDBK", "SNFC", "ANFI", "CRST", "ISMQ", "EHDR", "LUTS", "NINH", "ALUM", "ISMA", "AIFI", "TWSA", "AREH", "IEEC", "SIPC", "KABO", "SAUD", "GPIM", "ASCM", "GRCA", "CCRS", "QNBE", "MPRC", "MAAL", "PRDC", "SVCE", "AFDI", "GOUR", "IDRE", "DTPP", "ADPC", "EGTS", "DAPH", "ELSH", "MBSC", "NARE", "SMFR", "IBCT", "FAIT", "ELKA", "FTNS", "ECAP", "ARVA", "PRCL", "MIPH", "CAED", "ELWA", "EEII", "AMPI", "BONY", "IRON", "VALU", "GIHD", "CNFN", "CERA", "GGCC", "ASPI", "NCCW", "INEG", "EALR", "SPIN", "ROTO", "MBEG", "ODIN", "MHOT", "BIOC", "FIRE", "SPMD", "EGS385S1C012", "EGREF", "INFI", "DGTZ", "TANM", "KWIN", "ACGC", "EASB", "CICH", "AFMC", "EBSC", "AALR", "ADCI", "MILS", "SCFM", "IFAP", "VERT", "CEFM", "DOMT", "WKOL", "ADRI", "CPCI", "AJWA", "OCPH", "EGS370O1C013", "EPPK", "SCTS", "ENGC", "NEDA", "PHTV", "CANA", "ELNA", "RTVC", "ACAP", "NHPS", "GSSC", "UTOP", "UPMS", "EDFM", "MENA", "ICMI", "TALM", "SEIG", "AXPH", "RAKT", "CIRA", "ICID", "BIGP", "MOSC", "RUBX", "UEFM", "MOIL", "UBEE", "FNAR", "MKIT", "UNIT", "VLMR", "APSW", "MFSC", "GMCI", "MOIN", "NAHO", "EGS3E071C013", "RKAZ", "BIDI", "EOSB", "EGBE", "WCDF", "FAITA", "CPME", "EGSA", "TRTO", "CFGH", "MISR", "POCO", "KORA", "SPHT", "MMAT", "EGS72L31C011", "EGWA", "HDST", "DCCC", "SEIGA", "NDRL", "MEGM", "DEIN", "GPPL", "GTEX", "HAVC", "GEOS", "SAIB", "EGS72351C017", "ICLE", "EGS632D1C010"
]

# EGX index symbol used for market-level sentiment.
# Update to the correct TradingView/TVDatafeed symbol in your environment.
EGX_INDEX_SYMBOL = "EGX30"

# Strategy parameters
EMA_SHORT = 20
EMA_LONG = 50
SMA_LONG = 200
RSI_PERIOD = 14
BB_PERIOD = 20
BB_STD_DEV = 2

# Market hours (EGX - Cairo Local Time)
MARKET_OPEN = "10:00"  # 10:00 AM CLT
MARKET_CLOSE = "14:30"  # 2:30 PM CLT

# Signal thresholds
MIN_SIGNAL_COUNT = 3  # For "Golden List"
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
