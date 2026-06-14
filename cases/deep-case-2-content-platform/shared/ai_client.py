"""
AI 客户端模块
统一的 AI 调用接口，支持缓存、重试、结构化输出
"""

import hashlib
import json
import time
import logging
from typing import Optional, Any
from functools import lru_cache

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import ai_config

logger = logging.getLogger(__name__)

# 全局客户端实例
_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """获取 OpenAI 客户端（单例）"""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=ai_config.base_url,
            api_key=ai_config.api_key,
            timeout=ai_config.timeout,
        )
    return _client


# 简单的内存缓存（生产环境用 Redis）
_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 3600  # 1小时


def _get_cache_key(system: str, user: str, model: str) -> str:
    """生成缓存键"""
    content = f"{system}:{user}:{model}"
    return hashlib.md5(content.encode()).hexdigest()


def _get_from_cache(key: str) -> Optional[str]:
    """从缓存获取"""
    if key in _cache:
        result, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return result
        del _cache[key]
    return None


def _set_cache(key: str, value: str):
    """设置缓存"""
    _cache[key] = (value, time.time())
    # 简单的缓存清理：超过1000条时删除最旧的
    if len(_cache) > 1000:
        oldest_key = min(_cache.keys(), key=lambda k: _cache[k][1])
        del _cache[oldest_key]


@retry(
    stop=stop_after_attempt(ai_config.max_retries),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
def call_ai(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    use_cache: bool = True,
) -> str:
    """
    调用 AI 生成文本

    Args:
        system: 系统提示词
        user: 用户输入
        model: 模型名称（默认使用配置中的模型）
        temperature: 温度参数（0-1，越高越随机）
        use_cache: 是否使用缓存

    Returns:
        AI 生成的文本
    """
    model = model or ai_config.model
    client = get_client()

    # 检查缓存
    if use_cache:
        cache_key = _get_cache_key(system, user, model)
        cached = _get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for key: {cache_key[:8]}...")
            return cached

    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        result = response.choices[0].message.content
        elapsed = time.time() - start_time

        logger.info(f"AI call completed in {elapsed:.2f}s, model={model}")

        # 设置缓存
        if use_cache:
            _set_cache(cache_key, result)

        return result

    except Exception as e:
        logger.error(f"AI call failed: {str(e)}")
        raise


@retry(
    stop=stop_after_attempt(ai_config.max_retries),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
def call_ai_json(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> dict:
    """
    调用 AI 并返回 JSON 格式结果

    Args:
        system: 系统提示词（应要求 AI 返回 JSON）
        user: 用户输入
        model: 模型名称
        temperature: 温度参数（JSON 模式建议用较低值）

    Returns:
        解析后的 JSON 字典
    """
    model = model or ai_config.model
    client = get_client()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {str(e)}")
        # 尝试提取 JSON 部分
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except:
            pass
        raise ValueError(f"AI response is not valid JSON: {content[:200]}")

    except Exception as e:
        logger.error(f"AI JSON call failed: {str(e)}")
        raise


def clear_cache():
    """清空缓存"""
    global _cache
    _cache.clear()
    logger.info("Cache cleared")


def get_cache_stats() -> dict:
    """获取缓存统计"""
    return {
        "size": len(_cache),
        "ttl": CACHE_TTL,
    }
