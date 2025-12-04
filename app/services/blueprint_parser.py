"""
交易蓝图图片解析服务
使用百度OCR提取文字，再用LLM分析策略
"""
import logging
import base64
from pathlib import Path
from typing import List, Dict, Optional
from datetime import date
import sys
import os
import requests
import json

# 百度OCR
from aip import AipOcr

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config.settings import get_settings
from app.services.commodity_service import get_commodity_service

logger = logging.getLogger(__name__)
settings = get_settings()

# 百度OCR配置
BAIDU_APP_ID = '115330318'  # 可以任意填写
BAIDU_API_KEY = 'NSLNpUYovCDcPc1DlVhN0hfk'
BAIDU_SECRET_KEY = 'tinJuWVIjf4Z1Orm9TL5wIXaj7DdOZYe'


class BlueprintParser:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.base_url = settings.GEMINI_BASE_URL
        self.baidu_client = AipOcr(BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY)
        self.commodity_service = get_commodity_service()
        
    def parse_image(self, image_path: str) -> List[Dict]:
        """
        解析蓝图图片,提取策略

        Args:
            image_path: 图片文件路径

        Returns:
            策略列表,每个策略包含: variety, direction, signal, reason
        """
        try:
            # Step 1: 使用百度OCR提取文字
            img_path = Path(image_path)
            if not img_path.exists():
                logger.error(f"Image not found: {image_path}")
                return []

            # 读取图片
            with open(image_path, 'rb') as f:
                image_data = f.read()

            # 调用百度OCR通用文字识别（高精度版）
            logger.info(f"使用百度OCR识别图片: {image_path}")
            ocr_result = self.baidu_client.accurate(image_data)

            if 'error_code' in ocr_result:
                logger.error(f"百度OCR错误: {ocr_result.get('error_msg')}")
                return []

            # 提取所有识别的文字
            if 'words_result' not in ocr_result:
                logger.warning(f"OCR未识别到文字: {image_path}")
                return []

            ocr_text = '\n'.join([item['words'] for item in ocr_result['words_result']])
            logger.info(f"OCR识别到 {len(ocr_result['words_result'])} 行文字")

            # Step 2: 使用LLM分析OCR文字，提取策略
            strategies = self._analyze_text_with_llm(ocr_text)

            logger.info(f"从 {image_path} 解析出 {len(strategies)} 个策略")
            return strategies

        except Exception as e:
            logger.error(f"Failed to parse image {image_path}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _analyze_text_with_llm(self, ocr_text: str) -> List[Dict]:
        """
        使用LLM分析OCR提取的文字，生成交易策略
        """
        try:
            prompt = f"""
分析以下从期货交易蓝图中提取的文字，生成交易策略。

**OCR文字内容：**
{ocr_text}

**核心规则：跟随机构，对抗散户**

**方向判断：**
1. 散户加多 + 机构加空 → 做空
2. 散户加空 + 机构加多 → 做多
3. 散户减多 + 机构减空 → 做多
4. 散户加多 + 机构减多 → 做空

**星级标准：**
- ⭐⭐⭐：冲突强烈（有"大幅"、"持续"等词）
- ⭐⭐：中等冲突
- ⭐：弱冲突（有"小幅"等词）

**关键例子：**
"散户大幅加空碳酸锂 机构大幅加多碳酸锂"
→ {{"variety": "碳酸锂", "direction": "做多", "signal": "⭐⭐⭐", "reason": "散户加空vs机构加多"}}

"散户大幅加多烧碱 机构做空烧碱"
→ {{"variety": "烧碱", "direction": "做空", "signal": "⭐⭐⭐", "reason": "散户加多vs机构做空"}}

只返回JSON，不要其他内容：
{{
  "strategies": [
    {{"variety": "品种", "direction": "做多/做空", "signal": "⭐⭐⭐", "reason": "理由"}}
  ]
}}
"""

            # 调用LLM API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 2000
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            # 提取响应文字
            text = result['choices'][0]['message']['content']

            # 解析JSON
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接查找JSON
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    logger.warning(f"No JSON found in LLM response")
                    return []

            parsed = json.loads(json_str)
            strategies = parsed.get('strategies', [])

            # 标准化品种名称并过滤1-3星策略
            filtered = []
            for s in strategies:
                signal = s.get('signal', '')
                star_count = signal.count('⭐')
                if 1 <= star_count <= 3:
                    # 标准化品种名称
                    variety_raw = s.get('variety', '')
                    variety_info = self.commodity_service.normalize_variety(variety_raw)

                    # 如果无法识别品种，记录警告但仍保留
                    if variety_info['code'] == variety_raw and variety_info['code'] != variety_raw.upper():
                        logger.warning(f"无法识别品种: {variety_raw}")

                    filtered.append({
                        'variety': variety_info['code'],  # 使用标准代码
                        'direction': s.get('direction'),
                        'signal': signal,
                        'reason': s.get('reason')
                    })

            return filtered

        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            import traceback
            traceback.print_exc()
            return []
            
    def parse_all_blueprints(self, image_dir: str = "/Users/pm/Documents/期权交易策略/交易可查/images") -> Dict[date, List[Dict]]:
        """
        解析目录下所有蓝图图片
        
        Returns:
            Dict[date, List[Dict]]: 日期 -> 策略列表
        """
        results = {}
        image_path = Path(image_dir)
        
        if not image_path.exists():
            logger.error(f"Directory not found: {image_dir}")
            return results
            
        for img_file in image_path.glob("*.jpg"):
            # Parse date from filename (e.g., 20251117.jpg)
            try:
                date_str = img_file.stem
                img_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
                
                strategies = self.parse_image(str(img_file))
                if strategies:
                    results[img_date] = strategies
                    
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping file with invalid date format: {img_file.name}")
                
        for img_file in image_path.glob("*.png"):
            try:
                date_str = img_file.stem
                img_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
                
                strategies = self.parse_image(str(img_file))
                if strategies:
                    results[img_date] = strategies
                    
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping file with invalid date format: {img_file.name}")
                
        return results


def save_strategies_to_db(strategies_by_date: Dict[date, List[Dict]]):
    """
    将解析的策略保存到数据库
    """
    from app.models.database import SessionLocal
    from app.models.models import DailyBlueprint
    import json
    
    db = SessionLocal()
    try:
        for img_date, strategies in strategies_by_date.items():
            # Find or create blueprint record
            blueprint = db.query(DailyBlueprint).filter_by(record_date=img_date).first()
            
            if blueprint:
                # Update parsed_strategies
                blueprint.parsed_strategies = json.dumps(strategies, ensure_ascii=False)
                logger.info(f"Updated strategies for {img_date}: {len(strategies)} strategies")
            else:
                logger.warning(f"No blueprint record found for {img_date}")
                
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    parser = BlueprintParser()
    all_strategies = parser.parse_all_blueprints()
    
    print(f"\n找到 {len(all_strategies)} 天的蓝图数据:")
    for img_date, strategies in all_strategies.items():
        print(f"\n{img_date}:")
        for s in strategies:
            print(f"  - {s['variety']} {s['direction']} {s['signal']}")
            print(f"    理由: {s['reason']}")
            
    # Save to DB
    save_strategies_to_db(all_strategies)
