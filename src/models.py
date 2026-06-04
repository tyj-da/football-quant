"""
模型模块 — DC双变量泊松、Elo评分、贝叶斯评级（BR）
"""
import math
from collections import defaultdict
from datetime import datetime

from config import RHO_DEFAULT, DECAY_HALF_LIFE, HOME_ADV


class DCPoisson:
    """DC双变量泊松分布 — 建模主客队进球联合分布，不假设独立"""
    def __init__(self, rho: float = RHO_DEFAULT):
        self.rho = rho

    def probs(self, lambda_h: float, lambda_a: float, max_goals: int = 10):
        """返回 主胜/平/客胜 概率"""
        ph = [math.exp(-lambda_h) * (lambda_h ** i) / math.factorial(i)
              for i in range(max_goals + 1)]
        pa = [math.exp(-lambda_a) * (lambda_a ** i) / math.factorial(i)
              for i in range(max_goals + 1)]
        h = d = a = 0.0
        for x in range(max_goals + 1):
            for y in range(max_goals + 1):
                t = 1.0
                if x == 0 and y == 0:
                    t = 1 - self.rho * lambda_h * lambda_a
                elif x == 0 and y == 1:
                    t = 1 + self.rho * lambda_h
                elif x == 1 and y == 0:
                    t = 1 + self.rho * lambda_a
                elif x == 1 and y == 1:
                    t = 1 - self.rho
                p = t * ph[x] * pa[y]
                if x > y:
                    h += p
                elif x == y:
                    d += p
                else:
                    a += p
        total = h + d + a
        return h / total, d / total, a / total


class BayesianRating:
    """贝叶斯评级 — 用xG数据的衰减加权平均估计球队攻防强度"""
    def __init__(self, half_life: int = DECAY_HALF_LIFE):
        self.attack = defaultdict(list)   # team -> [(date, xg_scored, weight)]
        self.defense = defaultdict(list)  # team -> [(date, xg_conceded, weight)]
        self.half_life = half_life

    def _weight(self, days_ago: int) -> float:
        return 2 ** (-days_ago / self.half_life) if days_ago >= 0 else 0

    def update(self, team: str, date: str, xg_for: float, xg_against: float, opponent: str):
        """更新球队的攻防记录"""
        opp_att = self.get_attack(opponent, raw=True) if opponent else 1.0
        opp_def = self.get_defense(opponent, raw=True) if opponent else 1.0
        wf = math.log(max(opp_def, 0.5) + 1) + 0.5
        self.attack[team].append((date, xg_for, wf))
        wd = math.log(max(opp_att, 0.5) + 1) + 0.5
        self.defense[team].append((date, xg_against, wd))

    def _get(self, records: list, raw: bool) -> float:
        if not records:
            return 1.0
        if raw:
            if len(records) < 3:
                return 1.0
            return sum(v for _, v, _ in records[-10:]) / len(records[-10:])
        # 衰减加权（最近20场）
        last_date = records[-1][0]
        tw = tv = 0.0
        for ds, val, wf in records[-20:]:
            d = (datetime.strptime(last_date[:10], "%Y-%m-%d")
                 - datetime.strptime(ds[:10], "%Y-%m-%d")).days
            w = self._weight(d) * wf
            tw += w
            tv += w * val
        return tv / tw if tw > 0 else 1.0

    def get_attack(self, team: str, raw: bool = False) -> float:
        return self._get(self.attack.get(team, []), raw)

    def get_defense(self, team: str, raw: bool = False) -> float:
        return self._get(self.defense.get(team, []), raw)


class Elo:
    """Elo评分系统 — 动态追踪球队相对实力"""
    def __init__(self, k: int = 20, ha: int = 70):
        self.rating = defaultdict(lambda: 1500)
        self.k = k
        self.ha = ha

    def win_prob(self, home_elo: float, away_elo: float) -> float:
        return 1 / (1 + 10 ** ((away_elo - home_elo - self.ha) / 400))

    def to_threeway(self, home_elo: float, away_elo: float,
                    draw_base: float = 0.26):
        """返回 主胜/平/客胜 概率（含平局基准）"""
        e = self.win_prob(home_elo, away_elo)
        ph = e * (1 - draw_base)
        pa = (1 - e) * (1 - draw_base)
        pd = draw_base
        total = ph + pd + pa
        return ph / total, pd / total, pa / total

    def update(self, home: str, away: str, hg: int, ag: int):
        hr, ar = self.rating[home], self.rating[away]
        e = self.win_prob(hr, ar)
        actual = 1 if hg > ag else (0.5 if hg == ag else 0)
        self.rating[home] += self.k * (actual - e)
        self.rating[away] += self.k * ((1 - actual) - (1 - e))


def estimate_lambdas(br: BayesianRating, home: str, away: str) -> tuple:
    """用BR攻防强度估算期望进球数（lambda_h, lambda_a）"""
    ha = br.get_defense(home)
    hd = br.get_attack(away)
    aa = br.get_defense(away)
    ad = br.get_attack(home)
    lh = ha * hd * HOME_ADV / 2.75
    la = aa * ad / 2.75
    return max(0.1, min(lh, 6.0)), max(0.1, min(la, 6.0))
