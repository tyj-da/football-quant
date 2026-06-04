#!/usr/bin/env python3
"""
Football Quant — 足球量化回测系统
入口文件：python run.py
"""
import os
import sys

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR, XG_CACHE, RESULTS_DIR
from src.data_loader import load_matches, match_xg, LEAGUE_NAMES
from src.backtest import run_backtest, calc_metrics, monte_carlo, by_league


def main():
    print("=" * 60)
    print("  Football Quant — 足球量化回测")
    print("  DC双变量泊松 + Elo + 贝叶斯凯利")
    print("=" * 60)

    # 1. 加载数据
    print("\n📂 加载数据...")
    data_path = os.path.join(os.path.dirname(__file__), DATA_DIR)
    if not os.path.exists(data_path):
        print(f"  ❌ 数据目录不存在: {data_path}")
        print(f"  请将 football-data.co.uk 的CSV放入 {DATA_DIR}/")
        sys.exit(1)
    matches = load_matches(data_path)
    print(f"  Top10球队比赛: {len(matches)} 场")

    # 2. 匹配xG
    xg_path = os.path.join(os.path.dirname(__file__), XG_CACHE)
    if not os.path.exists(xg_path):
        print(f"  ⚠️  xG缓存不存在: {xg_path}")
        print(f"  将跳过xG匹配，使用基础模型")
        matched = matches
    else:
        matched = match_xg(matches, xg_path)
        print(f"  xG匹配成功: {len(matched)} 场")

    if len(matched) < 50:
        print(f"  ⚠️  匹配场次不足50场，结果可能不具统计意义")

    # 3. 回测
    print("\n📊 运行回测...")
    bets = run_backtest(matched)
    if not bets:
        print("  没有符合条件的押注，尝试调整参数或扩大数据范围")
        sys.exit(1)

    # 4. 评估
    metrics = calc_metrics(bets)
    print(f"\n  {'=' * 50}")
    print(f"  回测结果 ({metrics['n_bets']} 次押注)")
    print(f"  {'=' * 50}")
    print(f"    胜率:        {metrics['win_rate']:.1f}%")
    print(f"    ROI:         {metrics['roi']:.2f}%")
    print(f"    Z-score:     {metrics['zscore']:.3f}")
    print(f"    总押注额:    {metrics['total_stake']:.4f}")
    print(f"    总盈亏:      {metrics['total_pnl']:.4f}")

    # 5. 蒙特卡洛
    mc = monte_carlo(bets)
    print(f"\n  蒙特卡洛模拟 ({mc['bankruptcies']} 次破产)")
    print(f"    平均ROI:     {mc['mean_roi']:.1f}%")
    print(f"    中位数ROI:   {mc['median_roi']:.1f}%")

    # 6. 按联赛拆分
    leagues = by_league(matched, bets)
    if leagues:
        print(f"\n  {'=' * 50}")
        print(f"  按联赛拆分")
        print(f"  {'=' * 50}")
        for league, lm in sorted(leagues.items(), key=lambda x: -x[1]["n_bets"]):
            name = LEAGUE_NAMES.get(league, league)
            print(f"    {name:8s} {lm['n_bets']:4d}注  "
                  f"胜率:{lm['win_rate']:5.1f}%  "
                  f"ROI:{lm['roi']:6.2f}%  "
                  f"Z:{lm['zscore']:+.2f}")

    print(f"\n  {'=' * 50}")
    print(f"  ✅ 完成")
    print(f"  {'=' * 50}\n")


if __name__ == "__main__":
    main()
