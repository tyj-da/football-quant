"""
Football Quant — 全局配置参数
所有可调参数集中在此，方便实验不同组合
"""
# ============ 模型参数 ============
# DC双变量泊松
RHO_DEFAULT = -0.12      # 攻防相关性（负值=攻防此消彼长）

# 贝叶斯评级（Bayesian Rating）
DECAY_HALF_LIFE = 90      # 衰减半衰期（天）
HOME_ADV = 1.45           # 主场进球系数

# Elo
ELO_HA = 70               # 主场优势（Elo分）
DRAW_BASE = 0.26          # 平局基础概率

# ============ 融合策略 ============
FUSION_DC = 0.6           # DC泊松融合权重
FUSION_ELO = 0.4          # Elo融合权重

# ============ 凯利仓位 ============
KELLY_FRAC = 0.1          # 凯利比例（10% = 保守）
SINGLE_MAX = 0.05         # 单注上限（5%）
BAYES_WEIGHT = 0.75       # 先验权重（贝叶斯平滑）
SLIP_COST = 0.03          # 滑点/抽水成本

# ============ 回测参数 ============
WARM_UP = 50              # 预热场次
MC_SIMS = 1000            # 蒙特卡洛模拟次数
INITIAL_CAPITAL = 100     # 初始资金（蒙特卡洛用）

# ============ 数据路径 ============
DATA_DIR = "data"         # 数据目录
XG_CACHE = "data/xg_cache.json"
RESULTS_DIR = "results"
