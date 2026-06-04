"""
回测模块 — 回测运行、评估、蒙特卡洛模拟
"""
import math
import random
from collections import defaultdict

from config import WARM_UP, MC_SIMS, INITIAL_CAPITAL
from src.models import DCPoisson, BayesianRating, Elo, estimate_lambdas
from src.strategy import evaluate_bets


def run_backtest(matched: list) -> list:
    """在xG匹配后的比赛列表上运行完整回测"""
    dc = DCPoisson()
    br = BayesianRating()
    elo = Elo()
    all_bets = []

    for m in matched:
        ht, at = m["home"], m["away"]
        hg, ag = m["hg"], m["ag"]
        hx, ax = m.get("h_xg", 0), m.get("a_xg", 0)
        dt = m["date"]

        # 估算期望进球
        lh, la = estimate_lambdas(br, ht, at)

        # DC泊松概率
        dc_probs = dc.probs(lh, la)

        # Elo概率
        elo_probs = elo.to_threeway(elo.rating[ht], elo.rating[at])

        # 生成押注
        bets = evaluate_bets(m, dc_probs, elo_probs)
        for b in bets:
            b["match_idx"] = len(all_bets)
            all_bets.append(b)

        # 更新模型
        elo.update(ht, at, hg, ag)
        br.update(ht, dt, hx, ax, at)
        br.update(at, dt, ax, hx, ht)

    return all_bets


def calc_zscore(bets: list) -> float:
    """计算Z-score — 衡量实际表现与期望的偏离程度"""
    if not bets:
        return 0.0
    wins = sum(1 for b in bets if b["won"])
    n = len(bets)
    avg_odds = sum(b["odds"] for b in bets) / n
    exp_wins = sum(1 / b["odds"] for b in bets)
    if exp_wins <= 0:
        return 0.0
    return (wins - exp_wins) / math.sqrt(exp_wins * (1 - 1 / avg_odds))


def calc_metrics(bets: list) -> dict:
    """计算回测核心指标"""
    if not bets:
        return {"n_bets": 0, "win_rate": 0, "roi": 0, "zscore": 0}
    total_stake = sum(b["stake"] for b in bets)
    total_pnl = sum(b["pnl"] * b["stake"] for b in bets)
    wins = sum(1 for b in bets if b["won"])
    return {
        "n_bets": len(bets),
        "win_rate": wins / len(bets) * 100,
        "roi": total_pnl / total_stake * 100 if total_stake > 0 else 0.0,
        "zscore": calc_zscore(bets),
        "total_stake": total_stake,
        "total_pnl": total_pnl,
    }


def monte_carlo(bets: list, sims: int = MC_SIMS,
                init_cap: float = INITIAL_CAPITAL) -> dict:
    """蒙特卡洛模拟 — 评估策略在随机波动下的稳健性"""
    if not bets:
        return {"mean_roi": 0, "median_roi": 0, "bankruptcies": 0}
    rois = []
    bankruptcies = 0
    for _ in range(sims):
        cap = init_cap
        for b in bets:
            stake = b["stake"] * cap
            if random.random() < 1 / b["odds"]:
                cap += stake * (b["odds"] - 1)
            else:
                cap -= stake
            if cap <= 0:
                bankruptcies += 1
                break
        rois.append((cap - init_cap) / init_cap * 100)
    rois.sort()
    return {
        "mean_roi": sum(rois) / len(rois),
        "median_roi": rois[len(rois) // 2],
        "bankruptcies": f"{bankruptcies}/{sims}",
    }


def by_league(matched: list, bets: list) -> dict:
    """按联赛拆分回测结果"""
    # 建立 match_idx -> league 映射
    match_leagues = {}
    for m in matched:
        # 找到这个match在bets中对应的记录（通过日期+球队判断）
        pass
    league_bets = defaultdict(list)
    for b in bets:
        idx = b.get("match_idx")
        if idx is not None and idx < len(matched):
            league_bets[matched[idx]["league"]].append(b)
    results = {}
    for league, bl in sorted(league_bets.items(), key=lambda x: -sum(b["stake"] for b in x[1])):
        results[league] = calc_metrics(bl)
    return results
