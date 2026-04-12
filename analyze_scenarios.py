import pandas as pd
from pathlib import Path

# Adjust if your CSV name/path changes
ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "exports" / "sensor_readings_20260412_190646.csv"

# Scenario ID ranges (same as in your plotting script)
SCENARIOS = {
    "S1_baseline": (1, 84),
    "S2_leak": (110, 186),
    "S3_fault": (234, 273),
}

SENSOR_COLS = ["water_level", "flow_rate", "soil_moisture"]


def slice_by_id(df: pd.DataFrame, start_id: int, end_id: int) -> pd.DataFrame:
    return df[(df["id"] >= start_id) & (df["id"] <= end_id)].copy()


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    if "id" not in df.columns:
        raise ValueError("CSV must contain an 'id' column")

    for name, (start, end) in SCENARIOS.items():
        sub = slice_by_id(df, start, end)
        print(f"== {name} (id {start}-{end}, n={len(sub)}) ==")

        for col in SENSOR_COLS:
            mean = sub[col].mean()
            std = sub[col].std()
            vmin = sub[col].min()
            vmax = sub[col].max()
            print(
                f"{col:14s}: mean={mean:6.2f}, std={std:6.2f}, "
                f"min={vmin:6.2f}, max={vmax:6.2f}"
            )

        wl_delta = sub["water_level"].iloc[-1] - sub["water_level"].iloc[0]
        sm_delta = sub["soil_moisture"].iloc[-1] - sub["soil_moisture"].iloc[0]
        print(f"Δwater_level: {wl_delta:6.2f}")
        print(f"Δsoil_moisture: {sm_delta:6.2f}")
        print()


if __name__ == "__main__":
    main()