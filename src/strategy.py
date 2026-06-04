"""
策略模块 — DC+Elo融合概率、贝叶斯凯利仓位计算
"""
from config import (FUSION_DC, FUSION_ELO, KELLY_FRAC, SINGLE_MAX,
                    BAYES_WEIGHT, SLIP_COST)


def fuse_probs(dc_h: float, dc_d: float, dc_a: float,
               elo_h: float, elo_d: float, elo_a: float):
    """融合DC泊松和Elo的概率输出"""
    fh = FUSION_DC * dc_h + FUSION_ELO * elo_h
    fd = FUSION_DC * dc_d + FUSION_ELO * elo_d
    fa = FUSION_DC * dc_a + FUSION_ELO * elo_a
    total = fh + fd + fa
    return fh / total, fd / total, fa / total


def market_probs(psh: float, psd: float, psa: float):
    """从赔率反推市场隐含概率（剔除抽水）"""
    implied = 1 / psh + 1 / psd + 1 / psa
    return (1 / psh / implied, 1 / psd / implied, 1 / psa / implied)


def kelly_stake(prob: float, odds: float, market_p: float) -> float:
    """贝叶斯凯利仓位计算"""
    expected_value = prob * odds - 1
    if expected_value <= 0:
        return 0.0
    # 贝叶斯平滑：模型概率 + 市场概率 加权
    adjusted_prob = prob * BAYES_WEIGHT + market_p * (1 - BAYES_WEIGHT)
    adj_ev = adjusted_prob * odds - 1
    if adj_ev <= 0:
        return 0.0
    # 扣除滑点成本
    adj_ev -= SLIP_COST
    if adj_ev <= 0:
        return 0.0
    # 凯利比例，限制单注上限
    stake = min(adj_ev / (odds - 1) * KELLY_FRAC, SINGLE_MAX)
    return max(stake, 0.0) if stake > 0.001 else 0.0


def evaluate_bets(match, dc_probs, elo_probs):
    """对一场比赛生成所有可下注选项（H/D/A），返回押注列表"""
    fh, fd, fa = fuse_probs(*dc_probs, *elo_probs)
    mkt_h, mkt_d, mkt_a = market_probs(match["psh"], match["psd"], match["psa"])
    hg, ag = match["hg"], match["ag"]
    bets = []
    for prob, odds, outcome, mkt_p in [
        (fh, match["psh"], "H", mkt_h),
        (fd, match["psd"], "D", mkt_d),
        (fa, match["psa"], "A", mkt_a),
    ]:
        stake = kelly_stake(prob, odds, mkt_p)
        if stake <= 0:
            continue
        won = 1 if ((outcome == "H" and hg > ag) or
                     (outcome == "D" and hg == ag) or
                     (outcome == "A" and hg < ag)) else 0
        bets.append({
            "outcome": outcome, "odds": odds, "stake": stake,
            "won": won, "pnl": won * odds - 1,
        })
    return bets
