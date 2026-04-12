import pathlib

import pandas as pd
import matplotlib.pyplot as plt

# --- Paths ---
ROOT = pathlib.Path(__file__).parent
CSV_PATH = ROOT / "exports" / "sensor_readings_20260412_190646.csv"
FIG_DIR = ROOT / "figs"
FIG_DIR.mkdir(exist_ok=True)

# --- Scenario ID ranges (from manual inspection of the CSV) ---
# Baseline: stable wl ~70, sm slowly drifting 37 -> 26
BASELINE_ID_RANGE = (1, 84)

# Strong underground leak: pump off, wl ~66–69, sm spikes 17 -> 90+ near id ~110–186
LEAK_ID_RANGE = (110, 186)

# Sensor-fault: pump on & water_level drops but sm stays low and drifts (probe out of soil)
# This corresponds to the last run around ids ~234–273
FAULT_ID_RANGE = (234, 273)


def load_data():
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
    # Ensure sorted by id just in case
    df = df.sort_values("id").reset_index(drop=True)
    return df


def slice_by_id(df, id_range):
    start, end = id_range
    mask = (df["id"] >= start) & (df["id"] <= end)
    return df.loc[mask].copy()


def plot_scenario(df, out_path, title):
    """
    Plot water_level, soil_moisture (left y-axis) and flow_rate (right y-axis) vs time.
    """
    if df.empty:
        print(f"[WARN] No data for {title}, skipping.")
        return

    t = df["timestamp"]
    wl = df["water_level"]
    sm = df["soil_moisture"]
    fr = df["flow_rate"]

    fig, ax1 = plt.subplots(figsize=(7, 3))

    ax1.set_title(title)
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Water level / Soil moisture")

    l1, = ax1.plot(t, wl, label="water level (%)", color="tab:blue")
    l2, = ax1.plot(t, sm, label="soil moisture", color="tab:green")
    ax1.tick_params(axis="y")

    ax2 = ax1.twinx()
    ax2.set_ylabel("Flow rate")
    l3, = ax2.plot(t, fr, label="flow rate", color="tab:red", linestyle="--")
    ax2.tick_params(axis="y", labelcolor="tab:red")

    fig.autofmt_xdate()
    fig.tight_layout()

    # Combine legends from both axes
    lines = [l1, l2, l3]
    labels = [ln.get_label() for ln in lines]
    ax1.legend(lines, labels, loc="upper right")

    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[INFO] Saved figure: {out_path}")


def main():
    df = load_data()

    baseline_df = slice_by_id(df, BASELINE_ID_RANGE)
    leak_df = slice_by_id(df, LEAK_ID_RANGE)
    fault_df = slice_by_id(df, FAULT_ID_RANGE)

    plot_scenario(
        baseline_df,
        FIG_DIR / "baseline_timeseries_wl_fr_sm.png",
        "Baseline (no leak)",
    )
    plot_scenario(
        leak_df,
        FIG_DIR / "leak_timeseries_wl_fr_sm.png",
        "Strong underground leak",
    )
    plot_scenario(
        fault_df,
        FIG_DIR / "fault_timeseries_wl_fr_sm.png",
        "Sensor fault (moisture probe out of soil)",
    )


if __name__ == "__main__":
    main()