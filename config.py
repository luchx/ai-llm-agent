"""
统一配置文件 —— API Key 只在这里填一次！

所有阶段的脚本都会从这里读取配置，不用每个文件都改。
"""
import os

# ============================================================
# ⚠️ 只需要改这里！填一次，所有文件都能用。
# ============================================================
API_KEY  = ""
BASE_URL = ""       # 豆包示例：https://ark.cn-beijing.volces.com/api/v3
MODEL    = ""
# ============================================================

# 下面不用改
def get_client():
    """获取 OpenAI 客户端（懒加载，用到才创建）"""
    # pyrefly: ignore [missing-import]
    from openai import OpenAI
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)
