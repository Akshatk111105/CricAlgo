
import os
import sys
from pathlib import Path
from collections import defaultdict
from psycopg.rows import dict_row
import psycopg
from dotenv import load_dotenv


# Load .env from app/services/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# Wickets credited to the bowler
BOWLER_CREDITED_WICKETS = {
    "bowled",
    "caught",
    "caught and bowled",
    "lbw",
    "stumped",
    "hit wicket",
}


def get_match_players(cur, source_match_id):
    """Get all players and match information."""

    cur.execute(
        """
        SELECT
            m.match_id,
            m.venue,
            mp.player_id,
            mp.team,
            CASE
                WHEN mp.team = m.team1 THEN m.team2
                ELSE m.team1
            END AS opposition
        FROM matches m
        JOIN match_players mp
            ON m.match_id = mp.match_id
        WHERE m.source_match_id = %s;
        """,
        (source_match_id,),
    )

    return cur.fetchall()


def get_deliveries(cur, match_id):
    """Fetch all deliveries belonging to one match."""

    cur.execute(
        """
        SELECT
            batter_id,
            bowler_id,
            batter_runs,
            extras,
            wickets,
            is_wide,
            is_no_ball
        FROM deliveries
        WHERE match_id = %s
        ORDER BY innings_no, delivery_no;
        """,
        (match_id,),
    )

    return cur.fetchall()


def calculate_statistics(players, deliveries):
    """Calculate batting and bowling statistics."""

    stats = {}

    # Initialize all players, including those who did not bat or bowl.
    for player in players:
        player_id = player["player_id"]

        stats[player_id] = {
            "runs": 0,
            "balls": 0,
            "wickets": 0,
            "balls_bowled": 0,
            "runs_conceded": 0,
            "dismissal_types": [],
        }

    for delivery in deliveries:

        batter_id = delivery["batter_id"]
        bowler_id = delivery["bowler_id"]

        batter_runs = delivery["batter_runs"] or 0
        extras = delivery["extras"] or {}
        wickets = delivery["wickets"] or []

        is_wide = delivery["is_wide"] or False
        is_no_ball = delivery["is_no_ball"] or False

        # -------------------------
        # BATTING STATISTICS
        # -------------------------

        stats[batter_id]["runs"] += batter_runs

        # Wides do not count as balls faced.
        # No-balls do count as balls faced.
        if not is_wide:
            stats[batter_id]["balls"] += 1

        # -------------------------
        # BOWLING STATISTICS
        # -------------------------

        # Wides and no-balls do not count as legal balls.
        if not is_wide and not is_no_ball:
            stats[bowler_id]["balls_bowled"] += 1

        # Bowler is charged with batter runs, wides and no-balls.
        # Byes and legbyes are not charged to the bowler.
        bowler_runs = (
            batter_runs
            + extras.get("wides", 0)
            + extras.get("noballs", 0)
        )

        stats[bowler_id]["runs_conceded"] += bowler_runs

        # -------------------------
        # WICKET STATISTICS
        # -------------------------

        for wicket in wickets:

            player_out = wicket.get("player_out")
            wicket_kind = wicket.get("kind")

            # Record dismissal against the dismissed player.
            dismissed_player = next(
                (
                    player["player_id"]
                    for player in players
                    if player["name"] == player_out
                ),
                None,
            )

            if dismissed_player is not None:
                stats[dismissed_player]["dismissal_types"].append(
                    wicket_kind
                )

            # Run outs, retired hurt, etc. are not credited
            # to the bowler.
            if wicket_kind in BOWLER_CREDITED_WICKETS:
                stats[bowler_id]["wickets"] += 1

    return stats


def save_statistics(cur, match_id, players, stats):
    """Insert or update player_match_stats."""

    for player in players:

        player_id = player["player_id"]
        player_stats = stats[player_id]

        runs = player_stats["runs"]
        balls = player_stats["balls"]
        wickets = player_stats["wickets"]
        balls_bowled = player_stats["balls_bowled"]
        runs_conceded = player_stats["runs_conceded"]

        # Strike rate is undefined if the player faced no balls.
        strike_rate = (
            round((runs / balls) * 100, 2)
            if balls > 0 else None
        )

        # Economy is undefined if the player bowled no legal balls.
        economy = (
            round(runs_conceded / (balls_bowled / 6), 2)
            if balls_bowled > 0 else None
        )

        # Store overs as decimal overs, not cricket notation.
        overs = round(balls_bowled / 6, 4)

        dismissal_type = (
            ", ".join(player_stats["dismissal_types"])
            if player_stats["dismissal_types"]
            else None
        )

        cur.execute(
            """
            INSERT INTO player_match_stats (
                match_id,
                player_id,
                runs,
                balls,
                wickets,
                overs,
                economy,
                strike_rate,
                dismissal_type,
                opposition,
                venue,
                balls_bowled,
                runs_conceded
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (match_id, player_id)
            DO UPDATE SET
                runs = EXCLUDED.runs,
                balls = EXCLUDED.balls,
                wickets = EXCLUDED.wickets,
                overs = EXCLUDED.overs,
                economy = EXCLUDED.economy,
                strike_rate = EXCLUDED.strike_rate,
                dismissal_type = EXCLUDED.dismissal_type,
                opposition = EXCLUDED.opposition,
                venue = EXCLUDED.venue,
                balls_bowled = EXCLUDED.balls_bowled,
                runs_conceded = EXCLUDED.runs_conceded;
            """,
            (
                match_id,
                player_id,
                runs,
                balls,
                wickets,
                overs,
                economy,
                strike_rate,
                dismissal_type,
                player["opposition"],
                player["venue"],
                balls_bowled,
                runs_conceded,
            ),
        )


def process_match(source_match_id):
    """Run the complete statistics processing pipeline."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing from .env")

    with psycopg.connect(database_url, row_factory=dict_row) as conn:

        with conn.cursor() as cur:

            match_players = get_match_players(
                cur,
                source_match_id,
            )

            if not match_players:
                raise ValueError(
                    f"No match or match_players found for "
                    f"Cricsheet ID {source_match_id}"
                )

            match_id = match_players[0]["match_id"]

            # Convert database rows into dictionaries.
            players = [
                {
                    "player_id": row["player_id"],
                    "team": row["team"],
                    "opposition": row["opposition"],
                    "venue": row["venue"],
                }
                for row in match_players
            ]

            # Fetch player names for dismissal mapping.
            cur.execute(
                """
                SELECT p.player_id, p.name
                FROM players p
                JOIN match_players mp
                    ON p.player_id = mp.player_id
                WHERE mp.match_id = %s;
                """,
                (match_id,),
            )

            names = {
                row["player_id"]: row["name"]
                for row in cur.fetchall()
            }

            for player in players:
                player["name"] = names[player["player_id"]]

            deliveries = get_deliveries(cur, match_id)

            if not deliveries:
                raise ValueError("No deliveries found for this match")

            stats = calculate_statistics(players, deliveries)

            save_statistics(
                cur,
                match_id,
                players,
                stats,
            )

    print("Statistics processing successful!")
    print(f"Match ID: {source_match_id}")
    print(f"Players processed: {len(players)}")
    print(f"Deliveries processed: {len(deliveries)}")
    print(f"Player statistics saved: {len(stats)}")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            "Usage: python -m data_processing.match_stats "
            "CRICSHEET_MATCH_ID"
        )
        sys.exit(1)

    process_match(sys.argv[1])
