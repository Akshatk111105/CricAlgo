
import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


# Load environment variables from the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def load_match_json(file_path):
    """Read one Cricsheet JSON file."""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def insert_match(cur, data, source_match_id):
    """Insert the match and return its internal PostgreSQL ID."""
    info = data["info"]

    teams = info["teams"]
    toss = info.get("toss", {})

    match_date = info["dates"][0]
    venue = info.get("venue")

    cur.execute(
        """
        INSERT INTO matches (
            team1,
            team2,
            venue,
            toss_winner,
            toss_decision,
            match_date,
            source_match_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_match_id)
        DO UPDATE SET
            team1 = EXCLUDED.team1,
            team2 = EXCLUDED.team2,
            venue = EXCLUDED.venue,
            toss_winner = EXCLUDED.toss_winner,
            toss_decision = EXCLUDED.toss_decision,
            match_date = EXCLUDED.match_date
        RETURNING match_id;
        """,
        (
            teams[0],
            teams[1],
            venue,
            toss.get("winner"),
            toss.get("decision"),
            match_date,
            source_match_id,
        ),
    )

    return cur.fetchone()[0]


def insert_players(cur, info, match_id):
    """
    Insert players using Cricsheet registry IDs.
    Return a dictionary mapping player names to internal player IDs.
    """
    player_ids = {}

    squads = info["players"]
    registry = info.get("registry", {}).get("people", {})

    for team, names in squads.items():
        for name in names:

            # Prefer Cricsheet's stable player ID.
            # Fallback is used only if the registry has no entry.
            source_player_id = registry.get(name)

            if not source_player_id:
                source_player_id = "name:" + name.strip().lower()

            cur.execute(
                """
                INSERT INTO players (
                    name,
                    source_player_id
                )
                VALUES (%s, %s)
                ON CONFLICT (source_player_id)
                DO UPDATE SET name = EXCLUDED.name
                RETURNING player_id;
                """,
                (name, source_player_id),
            )

            player_id = cur.fetchone()[0]
            player_ids[name] = player_id

            # Record the team this player represented in this match.
            cur.execute(
                """
                INSERT INTO match_players (
                    match_id,
                    player_id,
                    team
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (match_id, player_id)
                DO UPDATE SET team = EXCLUDED.team;
                """,
                (match_id, player_id, team),
            )

    return player_ids


def insert_deliveries(cur, data, match_id, player_ids):
    """Flatten the innings/overs/deliveries JSON structure into rows."""

    # Safe re-run: replace deliveries for this match.
    cur.execute(
        "DELETE FROM deliveries WHERE match_id = %s;",
        (match_id,),
    )

    delivery_rows = []

    for innings_no, innings in enumerate(data["innings"], start=1):

        delivery_no = 0

        for over in innings["overs"]:
            over_no = over["over"]

            for ball_no, delivery in enumerate(
                over["deliveries"], start=1
            ):
                delivery_no += 1

                batter = delivery["batter"]
                bowler = delivery["bowler"]
                non_striker = delivery["non_striker"]

                runs = delivery["runs"]
                extras = delivery.get("extras", {})
                wickets = delivery.get("wickets", [])

                batter_id = player_ids[batter]
                bowler_id = player_ids[bowler]
                non_striker_id = player_ids[non_striker]

                actual_delivery = delivery.get("actual_delivery")

                delivery_rows.append(
                    (
                        match_id,
                        innings_no,
                        delivery_no,
                        over_no,
                        ball_no,
                        str(actual_delivery)
                        if actual_delivery is not None
                        else None,
                        batter_id,
                        bowler_id,
                        non_striker_id,
                        runs.get("batter", 0),
                        runs.get("total", 0),
                        Jsonb(extras),
                        Jsonb(wickets),
                        extras.get("wides", 0) > 0,
                        extras.get("noballs", 0) > 0,
                    )
                )

    cur.executemany(
        """
        INSERT INTO deliveries (
            match_id,
            innings_no,
            delivery_no,
            over_no,
            ball_no,
            actual_delivery,
            batter_id,
            bowler_id,
            non_striker_id,
            batter_runs,
            total_runs,
            extras,
            wickets,
            is_wide,
            is_no_ball
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        );
        """,
        delivery_rows,
    )

    return len(delivery_rows)


def ingest_match(file_path):
    """Run the complete ingestion process for one Cricsheet match."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing from your .env file")

    data = load_match_json(file_path)

    # Cricsheet's filename is its external match identifier.
    source_match_id = Path(file_path).stem

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:

            match_id = insert_match(
                cur,
                data,
                source_match_id,
            )

            player_ids = insert_players(
                cur,
                data["info"],
                match_id,
            )

            delivery_count = insert_deliveries(
                cur,
                data,
                match_id,
                player_ids,
            )

    print("Ingestion successful!")
    print(f"Cricsheet match ID: {source_match_id}")
    print(f"Internal match ID: {match_id}")
    print(f"Players processed: {len(player_ids)}")
    print(f"Deliveries inserted: {delivery_count}")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            "Usage: python -m data_ingestion.cricsheet "
            "path/to/match.json"
        )
        sys.exit(1)

    ingest_match(sys.argv[1])
