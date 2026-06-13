import pandas as pd
import re
import os
from dotenv import load_dotenv

load_dotenv()

DATASET_PATH = os.getenv("DATASET_PATH", "Problem_1_Sample_Datasets__TEKROWE_.xlsx")

_bid_history_df: pd.DataFrame = None
_capability_library_df: pd.DataFrame = None


def _parse_budget_string(budget_str) -> int:
    """
    Parse budget strings like 'PKR 22M', 'PKR 312M', 'PKR 1.5B' into integer values.
    Returns 0 if parsing fails.
    """
    if pd.isna(budget_str):
        return 0

    budget_str = str(budget_str).strip().upper()

    # Try to extract number and multiplier
    match = re.match(r"PKR\s*([\d,.]+)\s*([MBK])?", budget_str, re.IGNORECASE)
    if not match:
        # Try plain numeric
        try:
            return int(float(re.sub(r"[^\d.]", "", budget_str)))
        except (ValueError, TypeError):
            return 0

    number = float(match.group(1).replace(",", ""))
    multiplier = match.group(2)

    if multiplier == "B":
        return int(number * 1_000_000_000)
    elif multiplier == "M":
        return int(number * 1_000_000)
    elif multiplier == "K":
        return int(number * 1_000)
    else:
        return int(number)


def load_bid_history() -> pd.DataFrame:
    """Load bid history from Excel, skipping the 2 title/description rows."""
    global _bid_history_df
    if _bid_history_df is None:
        _bid_history_df = pd.read_excel(
            DATASET_PATH,
            sheet_name="PS1 \u2013 Bid History",
            header=2  # Row 3 (0-indexed: 2) contains the actual column headers
        )
        _bid_history_df.columns = (
            _bid_history_df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        # Parse the budget string column into a numeric budget_pkr column
        if "budget" in _bid_history_df.columns:
            _bid_history_df["budget_pkr"] = _bid_history_df["budget"].apply(
                _parse_budget_string
            )

    return _bid_history_df


def load_capability_library() -> pd.DataFrame:
    """Load capability library from Excel, skipping the 2 title/description rows."""
    global _capability_library_df
    if _capability_library_df is None:
        _capability_library_df = pd.read_excel(
            DATASET_PATH,
            sheet_name="PS1 \u2013 Capability Library",
            header=2  # Row 3 (0-indexed: 2) contains the actual column headers
        )
        _capability_library_df.columns = (
            _capability_library_df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        # Normalize column names to match what rag_engine.py expects
        rename_map = {
            "contract_value": "contract_value_pkr",
            "duration_(months)": "duration_months",
        }
        _capability_library_df.rename(
            columns={k: v for k, v in rename_map.items() if k in _capability_library_df.columns},
            inplace=True,
        )

    return _capability_library_df


def get_sector_win_rate(sector: str) -> float:
    """Return historical win rate (0.0-1.0) for a given sector."""
    df = load_bid_history()

    if "sector" not in df.columns or "outcome" not in df.columns:
        return 0.5  # neutral fallback if columns missing

    sector_df = df[df["sector"].str.lower() == sector.strip().lower()]
    if sector_df.empty:
        return 0.5  # neutral fallback
    wins = (sector_df["outcome"].str.lower() == "win").sum()
    return round(wins / len(sector_df), 4)


def get_sector_budget_range(sector: str) -> tuple[float, float]:
    """Return (min, max) budget PKR from winning bids in a sector."""
    df = load_bid_history()

    if "sector" not in df.columns or "outcome" not in df.columns or "budget_pkr" not in df.columns:
        return (0, float("inf"))

    wins_df = df[
        (df["sector"].str.lower() == sector.strip().lower()) &
        (df["outcome"].str.lower() == "win")
    ]
    if wins_df.empty:
        return (0, float("inf"))

    valid_budgets = wins_df["budget_pkr"][wins_df["budget_pkr"] > 0]
    if valid_budgets.empty:
        return (0, float("inf"))

    return (valid_budgets.min(), valid_budgets.max())


def get_all_sectors() -> list[str]:
    df = load_bid_history()
    if "sector" not in df.columns:
        return []
    return df["sector"].dropna().unique().tolist()