"""
数据加载模块 — 读取CSV、过滤Top10球队、匹配xG数据
"""
import csv
import json
import os
from collections import defaultdict

# 足球数据 → xG数据 球队名映射
FB2XG = {
    "Man City": "Manchester City", "Man United": "Manchester United",
    "Newcastle": "Newcastle United", "Nott'm Forest": "Nottingham Forest",
    "Wolves": "Wolverhampton Wanderers", "Milan": "AC Milan", "Inter": "Inter",
    "Ath Bilbao": "Athletic Club", "Ath Madrid": "Atletico Madrid",
    "Atletico": "Atletico Madrid", "Sociedad": "Real Sociedad", "Betis": "Real Betis",
    "Vallecano": "Rayo Vallecano", "Celta": "Celta Vigo", "Espanol": "Espanyol",
    "Valladolid": "Real Valladolid", "Alaves": "Alaves", "Dortmund": "Borussia Dortmund",
    "Leverkusen": "Bayer Leverkusen", "Ein Frankfurt": "Eintracht Frankfurt",
    "M'gladbach": "Borussia M.Gladbach", "FC Koln": "FC Cologne", "Koln": "FC Cologne",
    "Mainz": "Mainz 05", "Stuttgart": "VfB Stuttgart", "Leipzig": "RasenBallsport Leipzig",
    "RB Leipzig": "RasenBallsport Leipzig", "Hertha": "Hertha Berlin",
    "Heidenheim": "FC Heidenheim", "Paris SG": "Paris Saint Germain",
    "St Etienne": "Saint-Etienne", "St Pauli": "St. Pauli",
    "Clermont": "Clermont Foot", "Parma": "Parma Calcio 1913",
}

# 赛季Top10球队（按最终排名取前10）
TOP10 = {
    ("2223", "EPL"): {"Man City", "Arsenal", "Man United", "Newcastle", "Liverpool",
                       "Brighton", "Aston Villa", "Tottenham", "Brentford", "Fulham"},
    ("2324", "EPL"): {"Man City", "Arsenal", "Liverpool", "Aston Villa", "Tottenham",
                       "Chelsea", "Newcastle", "Man United", "West Ham", "Crystal Palace"},
    ("2425", "EPL"): {"Liverpool", "Arsenal", "Man City", "Chelsea", "Newcastle",
                       "Aston Villa", "Nott'm Forest", "Brighton", "Bournemouth", "Brentford"},
    ("2526", "EPL"): {"Arsenal", "Man City", "Man United", "Aston Villa", "Liverpool",
                       "Bournemouth", "Sunderland", "Brighton", "Brentford", "Chelsea"},
    ("2223", "La liga"): {"Barcelona", "Real Madrid", "Ath Madrid", "Sociedad", "Villarreal",
                           "Betis", "Osasuna", "Ath Bilbao", "Mallorca", "Girona"},
    ("2324", "La liga"): {"Real Madrid", "Barcelona", "Girona", "Ath Madrid", "Ath Bilbao",
                           "Sociedad", "Betis", "Villarreal", "Valencia", "Alaves"},
    ("2425", "La liga"): {"Barcelona", "Real Madrid", "Ath Madrid", "Ath Bilbao", "Villarreal",
                           "Betis", "Celta", "Osasuna", "Vallecano", "Mallorca"},
    ("2526", "La liga"): {"Barcelona", "Real Madrid", "Villarreal", "Ath Madrid", "Betis",
                           "Celta", "Getafe", "Vallecano", "Valencia", "Sociedad"},
    ("2223", "Bundesliga"): {"Bayern Munich", "Dortmund", "RB Leipzig", "Union Berlin", "Freiburg",
                              "Leverkusen", "Ein Frankfurt", "Wolfsburg", "Mainz", "M'gladbach"},
    ("2324", "Bundesliga"): {"Leverkusen", "Stuttgart", "Bayern Munich", "RB Leipzig", "Dortmund",
                              "Ein Frankfurt", "Hoffenheim", "Heidenheim", "Werder Bremen", "Freiburg"},
    ("2425", "Bundesliga"): {"Bayern Munich", "Leverkusen", "Ein Frankfurt", "Dortmund", "Freiburg",
                              "Mainz", "RB Leipzig", "Werder Bremen", "Stuttgart", "M'gladbach"},
    ("2526", "Bundesliga"): {"Bayern Munich", "Dortmund", "RB Leipzig", "Stuttgart", "Hoffenheim",
                              "Leverkusen", "Freiburg", "Ein Frankfurt", "Augsburg", "Mainz"},
    ("2223", "Serie A"): {"Napoli", "Lazio", "Inter", "Juventus", "Milan",
                           "Atalanta", "Roma", "Fiorentina", "Bologna", "Torino"},
    ("2324", "Serie A"): {"Inter", "Milan", "Juventus", "Atalanta", "Bologna",
                           "Roma", "Lazio", "Fiorentina", "Napoli", "Torino"},
    ("2425", "Serie A"): {"Napoli", "Inter", "Atalanta", "Juventus", "Roma",
                           "Fiorentina", "Lazio", "Milan", "Bologna", "Como"},
    ("2526", "Serie A"): {"Inter", "Napoli", "Roma", "Como", "Milan",
                           "Juventus", "Atalanta", "Bologna", "Lazio", "Udinese"},
    ("2223", "Ligue 1"): {"Paris SG", "Lens", "Marseille", "Rennes", "Lille",
                           "Monaco", "Lyon", "Clermont", "Nice", "Lorient"},
    ("2324", "Ligue 1"): {"Paris SG", "Monaco", "Brest", "Lille", "Nice",
                           "Lyon", "Lens", "Marseille", "Reims", "Rennes"},
    ("2425", "Ligue 1"): {"Paris SG", "Marseille", "Monaco", "Nice", "Lille",
                           "Lyon", "Strasbourg", "Lens", "Brest", "Toulouse"},
    ("2526", "Ligue 1"): {"Paris SG", "Lens", "Lille", "Lyon", "Marseille",
                           "Rennes", "Monaco", "Strasbourg", "Lorient", "Toulouse"},
}

LEAGUE_MAP = {"E0": "EPL", "SP1": "La liga", "D1": "Bundesliga",
              "I1": "Serie A", "F1": "Ligue 1"}

LEAGUE_NAMES = {"EPL": "英超", "La liga": "西甲", "Bundesliga": "德甲",
                "Serie A": "意甲", "Ligue 1": "法甲"}


def load_matches(data_dir: str) -> list:
    """读取所有CSV，过滤Top10球队比赛"""
    matches = []
    for fn in sorted(os.listdir(data_dir)):
        if not fn.endswith(".csv"):
            continue
        parts = fn.replace(".csv", "").split("_")
        if len(parts) != 2:
            continue
        lcode, season = parts
        league = LEAGUE_MAP.get(lcode, "")
        if not league:
            continue
        with open(os.path.join(data_dir, fn), encoding="windows-1252") as f:
            for row in csv.DictReader(f):
                if not row.get("HomeTeam") or not row.get("AwayTeam"):
                    continue
                try:
                    hg, ag = int(row["FTHG"]), int(row["FTAG"])
                except (ValueError, KeyError):
                    continue
                key = (season, league)
                top = TOP10.get(key, set())
                if row["HomeTeam"] not in top or row["AwayTeam"] not in top:
                    continue
                try:
                    psh, psd, psa = float(row["PSH"]), float(row["PSD"]), float(row["PSA"])
                    if not (psh > 1 and psd > 1 and psa > 1):
                        continue
                except (ValueError, KeyError):
                    continue
                date_str = row["Date"]
                if "/" in date_str:
                    p = date_str.split("/")
                    date_str = f"{p[2]}-{p[1].zfill(2)}-{p[0].zfill(2)}"
                matches.append({
                    "date": date_str, "league": league, "season": season,
                    "home": row["HomeTeam"], "away": row["AwayTeam"],
                    "hg": hg, "ag": ag, "psh": psh, "psd": psd, "psa": psa,
                })
    matches.sort(key=lambda m: m["date"])
    return matches


def match_xg(matches: list, xg_path: str) -> list:
    """将比赛数据匹配xG缓存，返回有xG数据的比赛子集"""
    with open(xg_path) as f:
        xg_data = json.load(f)
    # 按日期+进球数索引
    dsi = defaultdict(list)
    for x in xg_data:
        dsi[(x["date"][:10], x["h_goals"], x["a_goals"])].append(x)
    matched = []
    for m in matches:
        cand = dsi.get((m["date"], m["hg"], m["ag"]), [])
        if not cand:
            continue
        hl = (FB2XG.get(m["home"], m["home"])).lower()
        al = (FB2XG.get(m["away"], m["away"])).lower()
        for x in cand:
            xh, xa = x["home"].lower(), x["away"].lower()
            if (hl in xh or xh in hl) and (al in xa or xa in al):
                m["h_xg"], m["a_xg"] = x["h_xg"], x["a_xg"]
                matched.append(m)
                break
            if (hl in xa or xa in hl) and (al in xh or xh in al):
                m["h_xg"], m["a_xg"] = x["a_xg"], x["h_xg"]
                matched.append(m)
                break
    return matched
