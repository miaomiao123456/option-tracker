"""
期权分析系统配置文件
集中管理所有可配置参数
"""

# ==================== 分析算法参数 ====================

# 研报分析阈值
RESEARCH_ANALYSIS = {
    'very_active_score': 8,      # 非常活跃阈值
    'active_score': 5,            # 活跃阈值
    'moderate_score': 3,          # 中等阈值
    'low_score': 1.5,             # 较低阈值
    'contract_weight': 1/100,     # 合约数量权重
    'month_weight': 0.5,          # 月份数量权重
    'strike_weight': 1/10         # 行权价权重
}

# PCR分析阈值
PCR_ANALYSIS = {
    'very_high': 1.5,    # PCR>1.5 强烈看跌信号
    'high': 1.2,         # PCR>1.2 看跌信号
    'neutral_high': 0.8, # PCR>0.8 中性偏高
    'neutral_low': 0.5   # PCR>0.5 中性偏低
}

# 期限结构分析阈值
TERM_STRUCTURE = {
    'very_steep': 1.5,   # 远月/近月>1.5 陡峭
    'steep': 1.2,        # 远月/近月>1.2 偏陡
    'flat_high': 0.83,   # 远月/近月>0.83 平坦偏高
    'flat_low': 0.67     # 远月/近月>0.67 平坦偏低
}

# 波动率背离分析阈值
VOLATILITY_DIVERGENCE = {
    'very_wide_ratio': 0.5,      # 行权价范围比>50%
    'wide_ratio': 0.3,           # 行权价范围比>30%
    'moderate_ratio': 0.15,      # 行权价范围比>15%
    'narrow_ratio': 0.1,         # 行权价范围比>10%
    'very_wide_dispersion': 0.2, # 分散度>0.2
    'wide_dispersion': 0.15      # 分散度>0.15
}

# 资金面分析参数
CAPITAL_FLOW = {
    'margin_trend_threshold': 0.5  # 保证金趋势阈值
}

# 综合评分阈值
COMPREHENSIVE_SCORE = {
    'strong_long_score': 8,      # 强烈多头净得分
    'moderate_long_score': 4,    # 中等多头净得分
    'weak_long_score': 1,        # 弱多头净得分
    'strong_short_score': -8,    # 强烈空头净得分
    'moderate_short_score': -4,  # 中等空头净得分
    'weak_short_score': -1       # 弱空头净得分
}

# ==================== 数据处理参数 ====================

# 数据缓存设置
CACHE_SETTINGS = {
    'enable_cache': True,
    'cache_duration_hours': 1,  # 缓存有效期(小时)
    'cache_dir': '.cache'
}

# 并发处理设置
PARALLEL_PROCESSING = {
    'enable': True,
    'max_workers': 4  # 最大并发数
}

# ==================== HTML报告参数 ====================

HTML_REPORT = {
    'gradient_colors': {
        'primary_start': '#667eea',
        'primary_end': '#764ba2'
    },
    'chart_colors': {
        'long': '#10b981',
        'short': '#ef4444',
        'neutral': '#6b7280'
    }
}

# ==================== 文件路径配置 ====================

OUTPUT_FILES = {
    'overview': '期权分析_总览_V2.csv',
    'long_top5': '期权分析_多头Top5_V2.csv',
    'short_top5': '期权分析_空头Top5_V2.csv',
    'variety_signal_pattern': '品种详情_{}_分析信号_V2.csv',
    'html_overview': '期权分析总览.html',
    'html_variety_pattern': '品种详情_{}.html'
}

# ==================== 日志配置 ====================

LOGGING = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S'
}
