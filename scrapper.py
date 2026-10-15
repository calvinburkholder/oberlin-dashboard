import requests
import re
import pandas as pd
from bs4 import BeautifulSoup


# ============================================================
# 1. GAME URL
# ============================================================

url = "https://goyeo.com/sports/baseball/stats/2026/kenyon-college/boxscore/8127"


# ============================================================
# 2. DOWNLOAD PAGE
# ============================================================

response = requests.get(url)

print("Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")


# ============================================================
# 3. FIND PLAY-BY-PLAY TABLES
# ============================================================

play_tables = []

seen_innings = set()

for table in soup.find_all("table"):

    caption = table.find("caption")

    if not caption:
        continue

    caption_text = caption.get_text(" ", strip=True)

    match = re.match(
        r"^(Oberlin|Kenyon) - (Top|Bottom) of (\d+)",
        caption_text
    )

    if not match:
        continue

    # Sidearm displays the play-by-play twice.
    # Keep only one copy.
    if caption_text in seen_innings:
        continue

    seen_innings.add(caption_text)

    play_tables.append(table)


print("Play-by-play tables found:", len(play_tables))


# ============================================================
# 4. STARTING PITCHERS
# ============================================================

current_pitcher = {
    "Oberlin": "Jameson Bryant",
    "Kenyon": "Jackson Niedel"
}


# ============================================================
# 5. EXTRACT PLAY-BY-PLAY
# ============================================================

plays = []

for table in play_tables:

    # --------------------------------------------------------
    # Get inning information
    # --------------------------------------------------------

    caption = table.find("caption").get_text(
        " ",
        strip=True
    )

    match = re.match(
        r"^(.*?) - (Top|Bottom) of (\d+)",
        caption
    )

    if not match:
        continue

    batting_team = match.group(1)

    half = match.group(2)

    inning = int(match.group(3))


    # --------------------------------------------------------
    # Determine defensive team
    # --------------------------------------------------------

    if batting_team == "Oberlin":
        pitching_team = "Kenyon"
    else:
        pitching_team = "Oberlin"


    # --------------------------------------------------------
    # Process every row
    # --------------------------------------------------------

    for row in table.find_all("tr"):

        cells = row.find_all("td")

        if not cells:
            continue

        play_text = cells[0].get_text(
            " ",
            strip=True
        )

        if not play_text:
            continue


        # ====================================================
        # PITCHING CHANGE
        # ====================================================

        pitching_change = re.match(
            r"(.+?) to p for (.+?)\.",
            play_text
        )

        if pitching_change:

            new_pitcher = pitching_change.group(1).strip()

            current_pitcher[pitching_team] = new_pitcher

            print(
                f"Pitching change: "
                f"{pitching_team} -> {new_pitcher}"
            )

            continue


        # ====================================================
        # PINCH HITTER
        # ====================================================

        pinch_hit = re.match(
            r"(.+?) pinch hit for (.+?)\.",
            play_text
        )

        if pinch_hit:

            new_batter = pinch_hit.group(1).strip()
            old_batter = pinch_hit.group(2).strip()

            print(
                f"Pinch hitter: "
                f"{new_batter} for {old_batter}"
            )

            continue


        # ====================================================
        # REMOVE COUNT / PITCH SEQUENCE
        # ====================================================

        # Example:
        #
        # Kyle Baxt flied out to lf (0-1 S).
        #
        # becomes:
        #
        # Kyle Baxt flied out to lf

        cleaned_play = re.sub(
            r"\s*\(\d+-\d+(?:\s+[A-Z]+)?\)\.?",
            "",
            play_text
        ).strip()


        # ====================================================
        # EXTRACT FINAL COUNT IF AVAILABLE
        # ====================================================

        count_match = re.search(
            r"\((\d+)-(\d+)(?:\s+[A-Z]+)?\)",
            play_text
        )

        if count_match:

            balls = int(count_match.group(1))
            strikes = int(count_match.group(2))

        else:

            balls = None
            strikes = None


        # ====================================================
        # IGNORE NON-PLAYS
        # ====================================================

        if cleaned_play.startswith(
            (
                "Win:",
                "Loss:",
                "Save:",
                "HBP:",
                "PB:"
            )
        ):
            continue


        # ====================================================
        # IDENTIFY BATTER
        # ====================================================

        batter_match = re.match(
            r"^([A-Za-zÀ-ÿ' .-]+?)\s+"
            r"(?:"
            r"flied|"
            r"grounded|"
            r"struck|"
            r"singled|"
            r"doubled|"
            r"tripled|"
            r"homered|"
            r"walked|"
            r"reached|"
            r"popped|"
            r"lined|"
            r"hit|"
            r"sacrificed|"
            r"bunted|"
            r"fouled|"
            r"intentionally walked"
            r")",
            cleaned_play
        )

        if not batter_match:

            print(
                "Could not identify batter:",
                cleaned_play
            )

            continue


        batter = batter_match.group(1).strip()


        # ====================================================
        # STORE PLAY
        # ====================================================

        plays.append({

            "inning": inning,

            "half": half,

            "batting_team": batting_team,

            "pitching_team": pitching_team,

            "pitcher": current_pitcher[pitching_team],

            "batter": batter,

            "balls": balls,

            "strikes": strikes,

            "play": cleaned_play,

            "raw_play": play_text
        })


# ============================================================
# 6. CREATE DATAFRAME
# ============================================================

df = pd.DataFrame(plays)


# ============================================================
# 7. DISPLAY RESULTS
# ============================================================

print("\n")
print("=" * 100)
print("PLAY-BY-PLAY DATA")
print("=" * 100)

print(
    df.to_string(index=False)
)


# ============================================================
# 8. BASIC VALIDATION
# ============================================================

print("\n")
print("=" * 100)
print("SUMMARY")
print("=" * 100)

print(
    "Total plays:",
    len(df)
)

print(
    "Unique batters:",
    df["batter"].nunique()
)

print(
    "Unique pitchers:",
    df["pitcher"].nunique()
)

print(
    "Missing pitchers:",
    df["pitcher"].isna().sum()
)