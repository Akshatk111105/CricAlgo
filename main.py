# ==============================
# Akshat's Algo - Starter Project
# ==============================

# Run: python main.py
# Requirements: pip install pandas

import pandas as pd

# ------------------------------
# CONFIG (Adjust weights easily)
# ------------------------------
WEIGHTS = {
    "F": 0.30,  # Form
    "V": 0.20,  # Venue
    "M": 0.15,  # Matchup
    "R": 0.15,  # Role
    "O": 0.10,  # Opponent
    "W": 0.05,  # Weather
    "I": 0.05   # Injury
}

# ------------------------------
# CORE FUNCTIONS
# ------------------------------

def base_score(row):
    return (
        WEIGHTS["F"] * row["F"] +
        WEIGHTS["V"] * row["V"] +
        WEIGHTS["M"] * row["M"] +
        WEIGHTS["R"] * row["R"] +
        WEIGHTS["O"] * row["O"] +
        WEIGHTS["W"] * row["W"] +
        WEIGHTS["I"] * row["I"]
    )

# Step 2: Adjustments Layer (Multipliers, not additions)
# S = Streak Effect → (-0.20 to +0.20)
# P = Psychology/Pressure → (-0.10 to +0.10)
# T = Pitch/Toss Impact → (-0.10 to +0.10)
# FW = Fatigue/Workload → (-0.10 to 0)

def final_score(row):
    adjustment = 1 + row["S"] + row["P"] + row["T"] + row["FW"]
    return row["Base"] * adjustment

# ------------------------------
# SAMPLE DATA (Replace this)
# ------------------------------

data = [
    {
        "Player": "Player A",
        "F": 80, "V": 70, "M": 75, "R": 85, "O": 60, "W": 50, "I": 90,
        "S": 0.10, "P": 0.05, "T": 0.05, "FW": -0.05
    },
    {
        "Player": "Player B",
        "F": 65, "V": 80, "M": 70, "R": 60, "O": 75, "W": 60, "I": 95,
        "S": -0.05, "P": 0.00, "T": 0.10, "FW": -0.02
    },
    {
        "Player": "Player C",
        "F": 90, "V": 60, "M": 85, "R": 80, "O": 70, "W": 55, "I": 85,
        "S": 0.15, "P": 0.08, "T": 0.02, "FW": -0.03
    }
]

# ------------------------------
# PIPELINE
# ------------------------------

def run_algo(data):
    df = pd.DataFrame(data)

    # Calculate base score
    df["Base"] = df.apply(base_score, axis=1)

    # Calculate final score
    df["Final"] = df.apply(final_score, axis=1)

    # Rank players
    df = df.sort_values(by="Final", ascending=False)

    return df

# ------------------------------
# MAIN EXECUTION
# ------------------------------

if __name__ == "__main__":
    results = run_algo(data)

    print("\n=== Ranked Players ===")
    print(results[["Player", "Base", "Final"]])

    print("\n=== Top 11 (or available) ===")
    print(results.head(11)["Player"].tolist())

# ------------------------------
# NEXT STEPS (IMPORTANT)
# ------------------------------
# 1. Replace sample data with real match data
# 2. Store data in CSV instead of hardcoding
# 3. Add input system (match conditions)
# 4. Build Flask API on top
# 5. Deploy to Render
