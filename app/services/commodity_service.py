"""
品种信息统一服务
用于将不同网站的品种名称统一映射到标准品种代码
"""
from typing import Optional, Dict
from app.models.database import SessionLocal
from app.models.models import Commodity
from sqlalchemy import text


class CommodityService:
    def __init__(self):
        self.db = SessionLocal()
        self._code_to_name_cache = None
        self._alias_to_code_cache = None

    def _load_cache(self):
        """加载品种信息到缓存"""
        if self._code_to_name_cache is None:
            # 加载 code -> name 映射
            commodities = self.db.query(Commodity).all()
            self._code_to_name_cache = {c.code: c.name for c in commodities}

            # 加载别名映射
            self._alias_to_code_cache = {}

            # 标准名称也作为映射
            for c in commodities:
                self._alias_to_code_cache[c.name] = c.code
                self._alias_to_code_cache[c.code] = c.code  # 代码本身也映射

            # 加载别名表
            result = self.db.execute(text(
                "SELECT commodity_code, alias FROM commodity_aliases"
            ))
            for row in result:
                self._alias_to_code_cache[row[1]] = row[0]

    def get_standard_code(self, variety_name: str) -> Optional[str]:
        """
        将品种名称（可能是别名）转换为标准代码

        Args:
            variety_name: 品种名称或别名（如：白银、氧化铝、多晶硅等）

        Returns:
            标准品种代码（如：AG、AO、SI）或None
        """
        self._load_cache()

        # 直接查找
        if variety_name in self._alias_to_code_cache:
            return self._alias_to_code_cache[variety_name]

        # 尝试模糊匹配（去除空格、"沪"等前缀）
        cleaned_name = variety_name.strip().replace('沪', '')
        if cleaned_name in self._alias_to_code_cache:
            return self._alias_to_code_cache[cleaned_name]

        return None

    def get_standard_name(self, variety_code: str) -> Optional[str]:
        """
        获取品种的标准名称

        Args:
            variety_code: 品种代码（如：AG、CU）

        Returns:
            标准品种名称（如：沪银、沪铜）或None
        """
        self._load_cache()
        return self._code_to_name_cache.get(variety_code)

    def normalize_variety(self, variety_name: str) -> Dict[str, str]:
        """
        标准化品种信息

        Args:
            variety_name: 品种名称或代码

        Returns:
            {"code": "AG", "name": "沪银"}
        """
        code = self.get_standard_code(variety_name)
        if code:
            name = self.get_standard_name(code)
            return {"code": code, "name": name or code}

        # 无法识别，返回原名称
        return {"code": variety_name, "name": variety_name}

    def close(self):
        """关闭数据库连接"""
        self.db.close()


# 全局单例
_commodity_service = None


def get_commodity_service() -> CommodityService:
    """获取品种服务单例"""
    global _commodity_service
    if _commodity_service is None:
        _commodity_service = CommodityService()
    return _commodity_service
