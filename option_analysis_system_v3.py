"""
优化后的期权分析系统 V3
主要改进:
1. 添加缓存机制,避免重复数据获取
2. 并发处理多个品种,提升分析速度
3. 完善的错误处理和日志记录
4. 使用配置文件集中管理参数
5. 代码模块化,提高可维护性
"""

import akshare as ak
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime, timedelta
import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import hashlib

# 导入配置
try:
    from config import *
except ImportError:
    print("警告: 未找到config.py,使用默认配置")
    # 使用默认配置
    CACHE_SETTINGS = {'enable_cache': True, 'cache_duration_hours': 1, 'cache_dir': '.cache'}
    PARALLEL_PROCESSING = {'enable': True, 'max_workers': 4}
    OUTPUT_FILES = {
        'overview': '期权分析_总览_V2.csv',
        'long_top5': '期权分析_多头Top5_V2.csv',
        'short_top5': '期权分析_空头Top5_V2.csv',
        'variety_signal_pattern': '品种详情_{}_分析信号_V2.csv',
    }

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DataCache:
    """数据缓存管理器"""

    def __init__(self, cache_dir='.cache', duration_hours=1):
        self.cache_dir = cache_dir
        self.duration = timedelta(hours=duration_hours)
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def _get_cache_path(self, key):
        """获取缓存文件路径"""
        # 使用MD5哈希作为文件名
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f'{hash_key}.json')

    def get(self, key):
        """从缓存获取数据"""
        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            return None

        # 检查缓存是否过期
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if datetime.now() - mtime > self.duration:
            logger.debug(f"缓存已过期: {key}")
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"从缓存读取: {key}")
                return data
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None

    def set(self, key, data):
        """设置缓存"""
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            logger.debug(f"写入缓存: {key}")
        except Exception as e:
            logger.warning(f"写入缓存失败: {e}")

    def clear_all(self):
        """清空所有缓存"""
        for file in os.listdir(self.cache_dir):
            file_path = os.path.join(self.cache_dir, file)
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"删除缓存文件失败 {file}: {e}")


class OptionAnalysisSystemV3:
    """期权分析系统 V3 - 优化版"""

    def __init__(self, use_cache=True):
        self.all_data = {}
        self.analysis_results = {}
        self.use_cache = use_cache and CACHE_SETTINGS.get('enable_cache', True)

        if self.use_cache:
            cache_dir = CACHE_SETTINGS.get('cache_dir', '.cache')
            cache_duration = CACHE_SETTINGS.get('cache_duration_hours', 1)
            self.cache = DataCache(cache_dir, cache_duration)
            logger.info(f"缓存已启用: {cache_dir}, 有效期{cache_duration}小时")
        else:
            self.cache = None
            logger.info("缓存已禁用")

    # ===================== 1. 数据获取(带缓存) =====================

    def fetch_all_option_data(self):
        """获取所有期权数据(带缓存)"""
        logger.info("="*80)
        logger.info("步骤1: 获取所有期权数据")
        logger.info("="*80)

        cache_key = f"option_data_{datetime.now().strftime('%Y-%m-%d')}"

        # 尝试从缓存读取
        if self.use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info("从缓存读取期权数据")
                self.all_data = cached_data
                logger.info(f"  - 商品期权: {len(self.all_data.get('商品期权', []))} 条")
                logger.info(f"  - 指数期权: {len(self.all_data.get('指数期权', []))} 条")
                return True

        try:
            ctp_data = ak.option_contract_info_ctp()
            logger.info(f"✓ 获取到 {len(ctp_data)} 条期权合约数据")

            # 标准化品种ID
            def normalize_variety_id(variety_id):
                if variety_id.endswith('C') or variety_id.endswith('P'):
                    base = variety_id[:-1]
                    if base.isupper() and len(base) >= 2:
                        return base
                return variety_id

            ctp_data['品种ID_原始'] = ctp_data['品种ID']
            ctp_data['品种ID'] = ctp_data['品种ID'].apply(normalize_variety_id)

            # 分类存储
            commodity_data = ctp_data[ctp_data['交易所ID'].isin(['CZCE', 'DCE', 'SHFE', 'GFEX', 'INE'])]
            index_data = ctp_data[ctp_data['交易所ID'] == 'CFFEX']

            # 转换为可序列化的格式(用于缓存)
            self.all_data = {
                '商品期权': commodity_data.to_dict('records'),
                '指数期权': index_data.to_dict('records')
            }

            logger.info(f"  - 商品期权: {len(self.all_data['商品期权'])} 条")
            logger.info(f"  - 指数期权: {len(self.all_data['指数期权'])} 条")

            unique_varieties = pd.DataFrame(self.all_data['商品期权'])['品种ID'].nunique()
            logger.info(f"  - 合并后品种数: {unique_varieties} 个")

            # 保存到缓存
            if self.use_cache:
                self.cache.set(cache_key, self.all_data)
                logger.info("已保存到缓存")

            return True

        except Exception as e:
            logger.error(f"✗ 数据获取失败: {e}", exc_info=True)
            return False

    # ===================== 2. 分析维度方法(从V2继承) =====================

    def analyze_research_report(self, variety_data, variety_name):
        """研报分析维度"""
        try:
            total_contracts = len(variety_data)
            unique_months = variety_data['交割月份'].nunique()
            unique_strikes = variety_data['行权价'].nunique()

            # 从配置读取参数
            config = RESEARCH_ANALYSIS if 'RESEARCH_ANALYSIS' in globals() else {
                'very_active_score': 8, 'active_score': 5, 'moderate_score': 3, 'low_score': 1.5,
                'contract_weight': 1/100, 'month_weight': 0.5, 'strike_weight': 1/10
            }

            activity_score = (total_contracts * config['contract_weight'] +
                            unique_months * config['month_weight'] +
                            unique_strikes * config['strike_weight'])

            if activity_score > config['very_active_score']:
                direction, strength = "多头", 3
                reason = f"市场活跃度高({total_contracts}合约,{unique_months}月份),机构看好"
            elif activity_score > config['active_score']:
                direction, strength = "多头", 2
                reason = f"市场关注度较高({total_contracts}合约),偏多"
            elif activity_score > config['moderate_score']:
                direction, strength = "中性", 1
                reason = f"市场关注度一般"
            elif activity_score > config['low_score']:
                direction, strength = "空头", 2
                reason = f"市场关注度较低({total_contracts}合约),谨慎"
            else:
                direction, strength = "空头", 3
                reason = f"市场冷清({total_contracts}合约),机构不看好"

            return {
                '分析维度': '研报分析',
                '活跃度得分': round(activity_score, 2),
                '合约总数': total_contracts,
                '交割月份数': unique_months,
                '方向': direction,
                '强度': strength,
                '星级': '⭐' * strength,
                '理由': reason
            }
        except Exception as e:
            logger.error(f"研报分析失败 {variety_name}: {e}")
            return self._get_default_signal('研报分析')

    def analyze_pcr(self, variety_data, variety_name):
        """虚实比分析"""
        try:
            call_count = len(variety_data[variety_data['期权类型'] == '1'])
            put_count = len(variety_data[variety_data['期权类型'] == '2'])

            pcr = put_count / call_count if call_count > 0 else float('inf')

            config = PCR_ANALYSIS if 'PCR_ANALYSIS' in globals() else {
                'very_high': 1.5, 'high': 1.2, 'neutral_high': 0.8, 'neutral_low': 0.5
            }

            if pcr > config['very_high']:
                direction, strength = "多头", 3
                reason = f"PCR={pcr:.2f}>1.5,看跌过度,反向做多"
            elif pcr > config['high']:
                direction, strength = "多头", 2
                reason = f"PCR={pcr:.2f}>1.2,偏看跌,反向做多"
            elif pcr > config['neutral_high']:
                direction, strength = "中性", 1
                reason = f"PCR={pcr:.2f},市场中性"
            elif pcr > config['neutral_low']:
                direction, strength = "空头", 2
                reason = f"PCR={pcr:.2f}<0.8,偏看涨,反向做空"
            else:
                direction, strength = "空头", 3
                reason = f"PCR={pcr:.2f}<0.5,看涨过度,反向做空"

            return {
                '分析维度': '虚实比PCR',
                'PCR值': round(pcr, 2) if pcr != float('inf') else 'N/A',
                '看涨数量': call_count,
                '看跌数量': put_count,
                '方向': direction,
                '强度': strength,
                '星级': '⭐' * strength,
                '理由': reason
            }
        except Exception as e:
            logger.error(f"PCR分析失败 {variety_name}: {e}")
            return self._get_default_signal('虚实比PCR')

    def analyze_term_structure(self, variety_data, variety_name):
        """期限结构分析"""
        try:
            month_stats = variety_data.groupby('交割月份').size().sort_index()

            if len(month_stats) < 2:
                return self._get_default_signal('期限结构', '数据不足')

            near_month_count = month_stats.iloc[0]
            far_month_count = month_stats.iloc[-1]
            ratio = far_month_count / near_month_count if near_month_count > 0 else float('inf')

            config = TERM_STRUCTURE if 'TERM_STRUCTURE' in globals() else {
                'very_steep': 1.5, 'steep': 1.2, 'flat_high': 0.83, 'flat_low': 0.67
            }

            if ratio > config['very_steep']:
                direction, strength = "多头", 3
                reason = f"远月合约({far_month_count})>>近月({near_month_count}),预期波动率上升"
            elif ratio > config['steep']:
                direction, strength = "多头", 2
                reason = f"远月合约({far_month_count})>近月({near_month_count}),偏多"
            elif ratio > config['flat_high']:
                direction, strength = "中性", 1
                reason = f"远近月合约均衡"
            elif ratio > config['flat_low']:
                direction, strength = "空头", 2
                reason = f"近月合约({near_month_count})>远月({far_month_count}),偏空"
            else:
                direction, strength = "空头", 3
                reason = f"近月合约({near_month_count})>>远月({far_month_count}),预期波动率下降"

            return {
                '分析维度': '期限结构',
                '远近月比': round(ratio, 2) if ratio != float('inf') else 'N/A',
                '近月合约数': int(near_month_count),
                '远月合约数': int(far_month_count),
                '方向': direction,
                '强度': strength,
                '星级': '⭐' * strength,
                '理由': reason
            }
        except Exception as e:
            logger.error(f"期限结构分析失败 {variety_name}: {e}")
            return self._get_default_signal('期限结构')

    def analyze_volatility_divergence(self, variety_data, variety_name):
        """波动率背离分析"""
        try:
            strike_min = variety_data['行权价'].min()
            strike_max = variety_data['行权价'].max()
            strike_mean = variety_data['行权价'].mean()

            range_ratio = (strike_max - strike_min) / strike_mean if strike_mean > 0 else 0
            strike_std = variety_data['行权价'].std()
            dispersion = strike_std / strike_mean if strike_mean > 0 else 0

            config = VOLATILITY_DIVERGENCE if 'VOLATILITY_DIVERGENCE' in globals() else {
                'very_wide_ratio': 0.5, 'wide_ratio': 0.3, 'moderate_ratio': 0.15,
                'narrow_ratio': 0.1, 'very_wide_dispersion': 0.2, 'wide_dispersion': 0.15
            }

            if range_ratio > config['very_wide_ratio'] or dispersion > config['very_wide_dispersion']:
                direction, strength = "多头", 3
                reason = f"IV分布宽({range_ratio:.1%}),预期大幅波动,做多波动率"
            elif range_ratio > config['wide_ratio'] or dispersion > config['wide_dispersion']:
                direction, strength = "多头", 2
                reason = f"IV分布较宽({range_ratio:.1%}),预期波动"
            elif range_ratio > config['moderate_ratio']:
                direction, strength = "中性", 1
                reason = f"IV分布适中({range_ratio:.1%})"
            elif range_ratio > config['narrow_ratio']:
                direction, strength = "空头", 2
                reason = f"IV分布窄({range_ratio:.1%}),预期波动小"
            else:
                direction, strength = "空头", 3
                reason = f"IV分布很窄({range_ratio:.1%}),做空波动率"

            return {
                '分析维度': '波动率背离',
                'IV范围比': f"{range_ratio:.1%}",
                '分散度': round(dispersion, 3),
                '行权价范围': f"{strike_min:.0f}-{strike_max:.0f}",
                '方向': direction,
                '强度': strength,
                '星级': '⭐' * strength,
                '理由': reason
            }
        except Exception as e:
            logger.error(f"波动率背离分析失败 {variety_name}: {e}")
            return self._get_default_signal('波动率背离')

    def analyze_capital_flow(self, variety_data, variety_name):
        """资金面分析"""
        try:
            avg_long_margin = variety_data['做多保证金/手'].mean()
            avg_short_margin = variety_data['做空保证金/手'].mean()
            avg_margin = (avg_long_margin + avg_short_margin) / 2

            month_margin = variety_data.groupby('交割月份')['做多保证金/手'].mean().sort_index()

            if len(month_margin) >= 2:
                margin_trend = month_margin.iloc[-1] - month_margin.iloc[0]
                margin_std = month_margin.std()

                threshold = CAPITAL_FLOW.get('margin_trend_threshold', 0.5) if 'CAPITAL_FLOW' in globals() else 0.5

                if margin_trend > margin_std * threshold:
                    direction, strength = "空头", 2
                    reason = f"远月保证金上升,资金趋紧,谨慎"
                elif margin_trend < -margin_std * threshold:
                    direction, strength = "多头", 2
                    reason = f"远月保证金下降,资金宽松,积极"
                else:
                    direction, strength = "中性", 1
                    reason = f"保证金平稳,资金面中性"
            else:
                direction, strength = "中性", 1
                reason = "数据不足"

            return {
                '分析维度': '资金面',
                '平均保证金': round(avg_margin, 2),
                '多头保证金': round(avg_long_margin, 2),
                '空头保证金': round(avg_short_margin, 2),
                '方向': direction,
                '强度': strength,
                '星级': '⭐' * strength,
                '理由': reason
            }
        except Exception as e:
            logger.error(f"资金面分析失败 {variety_name}: {e}")
            return self._get_default_signal('资金面')

    def _get_default_signal(self, dimension, reason='数据异常'):
        """返回默认信号"""
        return {
            '分析维度': dimension,
            '方向': '中性',
            '强度': 1,
            '星级': '⭐',
            '理由': reason
        }

    # ===================== 7. 综合分析 =====================

    def analyze_single_variety(self, variety_name, variety_data):
        """分析单个品种"""
        logger.info(f"分析品种: {variety_name}")

        signals = []

        # 5个分析维度
        signals.append(self.analyze_research_report(variety_data, variety_name))
        signals.append(self.analyze_pcr(variety_data, variety_name))
        signals.append(self.analyze_term_structure(variety_data, variety_name))
        signals.append(self.analyze_volatility_divergence(variety_data, variety_name))
        signals.append(self.analyze_capital_flow(variety_data, variety_name))

        # 计算综合评分
        total_score = self.calculate_comprehensive_score(signals)

        return {
            '品种': variety_name,
            '分析信号': signals,
            '综合评分': total_score
        }

    def calculate_comprehensive_score(self, signals):
        """计算综合强度"""
        total_long = sum(s['强度'] for s in signals if s['方向'] == '多头')
        total_short = sum(s['强度'] for s in signals if s['方向'] == '空头')
        net_score = total_long - total_short

        config = COMPREHENSIVE_SCORE if 'COMPREHENSIVE_SCORE' in globals() else {
            'strong_long_score': 8, 'moderate_long_score': 4, 'weak_long_score': 1,
            'strong_short_score': -8, 'moderate_short_score': -4, 'weak_short_score': -1
        }

        if net_score >= config['strong_long_score']:
            综合方向, 综合强度 = "多头", 3
        elif net_score >= config['moderate_long_score']:
            综合方向, 综合强度 = "多头", 2
        elif net_score >= config['weak_long_score']:
            综合方向, 综合强度 = "多头", 1
        elif net_score <= config['strong_short_score']:
            综合方向, 综合强度 = "空头", 3
        elif net_score <= config['moderate_short_score']:
            综合方向, 综合强度 = "空头", 2
        elif net_score <= config['weak_short_score']:
            综合方向, 综合强度 = "空头", 1
        else:
            综合方向, 综合强度 = "中性", 1

        return {
            '综合方向': 综合方向,
            '综合强度': 综合强度,
            '综合星级': '⭐' * 综合强度,
            '多头得分': total_long,
            '空头得分': total_short,
            '净得分': net_score
        }

    # ===================== 8. 并发分析所有品种 =====================

    def analyze_all_varieties(self):
        """并发分析所有品种"""
        logger.info("\n" + "="*80)
        logger.info("步骤2: 分析所有品种 (5个维度)")
        logger.info("="*80)

        all_analysis = []
        commodity_data_list = self.all_data.get('商品期权', [])

        if not commodity_data_list:
            logger.warning("没有商品期权数据")
            return all_analysis

        commodity_df = pd.DataFrame(commodity_data_list)
        varieties = commodity_df['品种ID'].unique()
        logger.info(f"商品期权品种数: {len(varieties)}")

        enable_parallel = PARALLEL_PROCESSING.get('enable', True) if 'PARALLEL_PROCESSING' in globals() else True
        max_workers = PARALLEL_PROCESSING.get('max_workers', 4) if 'PARALLEL_PROCESSING' in globals() else 4

        if enable_parallel and len(varieties) > 3:
            # 并发处理
            logger.info(f"使用并发处理 (max_workers={max_workers})")

            def analyze_variety(variety):
                variety_data = commodity_df[commodity_df['品种ID'] == variety]
                return self.analyze_single_variety(variety, variety_data)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(analyze_variety, v): v for v in varieties}

                for future in as_completed(futures):
                    variety = futures[future]
                    try:
                        analysis = future.result()
                        all_analysis.append(analysis)
                        logger.info(f"  ✓ {variety}")
                    except Exception as e:
                        logger.error(f"  ✗ {variety}: {e}")
        else:
            # 串行处理
            logger.info("使用串行处理")
            for variety in varieties:
                try:
                    variety_data = commodity_df[commodity_df['品种ID'] == variety]
                    analysis = self.analyze_single_variety(variety, variety_data)
                    all_analysis.append(analysis)
                except Exception as e:
                    logger.error(f"  ✗ {variety}: {e}")

        self.analysis_results = all_analysis
        logger.info(f"完成分析 {len(all_analysis)}/{len(varieties)} 个品种")
        return all_analysis

    # ===================== 9-11. 报告生成和保存(保持不变) =====================

    def generate_overview_report(self):
        """生成总览报告"""
        logger.info("\n" + "="*80)
        logger.info("步骤3: 生成总览报告")
        logger.info("="*80)

        overview_data = []

        for analysis in self.analysis_results:
            variety = analysis['品种']
            signals = analysis['分析信号']
            综合 = analysis['综合评分']

            row = {
                '品种': variety,
                '综合方向': 综合['综合方向'],
                '综合强度': 综合['综合强度'],
                '综合星级': 综合['综合星级'],
                '净得分': 综合['净得分'],
            }

            for signal in signals:
                维度 = signal['分析维度']
                row[f'{维度}_方向'] = signal['方向']
                row[f'{维度}_强度'] = signal['强度']
                row[f'{维度}_星级'] = signal['星级']

            overview_data.append(row)

        overview_df = pd.DataFrame(overview_data)
        overview_df = overview_df.sort_values(['综合强度', '净得分'], ascending=[False, False])

        return overview_df

    def select_top5_by_direction(self, overview_df):
        """筛选Top5"""
        logger.info("\n" + "="*80)
        logger.info("步骤4: 筛选Top5品种")
        logger.info("="*80)

        results = {}

        long_df = overview_df[overview_df['综合方向'] == '多头'].head(5)
        logger.info(f"\n【多头Top5】\n{long_df[['品种', '综合方向', '综合星级', '净得分']].to_string(index=False)}")
        results['多头Top5'] = long_df

        short_df = overview_df[overview_df['综合方向'] == '空头'].sort_values('净得分').head(5)
        logger.info(f"\n【空头Top5】\n{short_df[['品种', '综合方向', '综合星级', '净得分']].to_string(index=False)}")
        results['空头Top5'] = short_df

        return results

    def save_results(self, overview_df, top5_results):
        """保存所有结果"""
        logger.info("\n" + "="*80)
        logger.info("步骤5: 保存结果")
        logger.info("="*80)

        output_files = OUTPUT_FILES if 'OUTPUT_FILES' in globals() else {
            'overview': '期权分析_总览_V2.csv',
            'long_top5': '期权分析_多头Top5_V2.csv',
            'short_top5': '期权分析_空头Top5_V2.csv',
            'variety_signal_pattern': '品种详情_{}_分析信号_V2.csv',
        }

        try:
            overview_df.to_csv(output_files['overview'], index=False, encoding='utf-8-sig')
            logger.info(f"✓ 已保存: {output_files['overview']}")

            for direction, df in top5_results.items():
                key = 'long_top5' if direction == '多头Top5' else 'short_top5'
                filename = output_files[key]
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                logger.info(f"✓ 已保存: {filename}")

            for analysis in self.analysis_results:
                variety = analysis['品种']
                signals = pd.DataFrame(analysis['分析信号'])
                filename = output_files['variety_signal_pattern'].format(variety)
                signals.to_csv(filename, index=False, encoding='utf-8-sig')

            logger.info(f"✓ 已保存所有品种详情文件")
        except Exception as e:
            logger.error(f"保存结果失败: {e}", exc_info=True)

    # ===================== 12. 主流程 =====================

    def run_full_analysis(self):
        """运行完整分析流程"""
        logger.info("="*80)
        logger.info("期权分析系统 V3 - 优化版")
        logger.info(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)

        start_time = datetime.now()

        if not self.fetch_all_option_data():
            logger.error("✗ 数据获取失败,退出")
            return None, None

        self.analyze_all_varieties()
        overview_df = self.generate_overview_report()
        top5_results = self.select_top5_by_direction(overview_df)
        self.save_results(overview_df, top5_results)

        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.info("\n" + "="*80)
        logger.info(f"分析完成！用时: {elapsed_time:.2f}秒")
        logger.info("="*80)

        return overview_df, top5_results


def main():
    """主函数"""
    # 可选: 清空缓存
    # cache = DataCache()
    # cache.clear_all()

    analyzer = OptionAnalysisSystemV3(use_cache=True)
    overview_df, top5_results = analyzer.run_full_analysis()

    if overview_df is not None:
        logger.info("\n" + "="*80)
        logger.info("最终统计")
        logger.info("="*80)
        logger.info(f"总品种数: {len(overview_df)}")
        logger.info(f"多头品种数: {len(overview_df[overview_df['综合方向']=='多头'])}")
        logger.info(f"空头品种数: {len(overview_df[overview_df['综合方向']=='空头'])}")
        logger.info(f"中性品种数: {len(overview_df[overview_df['综合方向']=='中性'])}")


if __name__ == "__main__":
    main()
