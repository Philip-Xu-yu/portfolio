"""
共享配置模块
所有项目统一使用此配置
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AIConfig:
    """AI 服务配置"""
    base_url: str = os.getenv("AI_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
    api_key: str = os.getenv("AI_API_KEY", "")
    model: str = os.getenv("AI_MODEL", "mimo-v2.5-pro")
    timeout: int = 60
    max_retries: int = 3


@dataclass(frozen=True)
class DatabaseConfig:
    """数据库配置"""
    path: str = os.getenv("DATABASE_URL", "data/app.db")
    backup_enabled: bool = True


@dataclass(frozen=True)
class AppConfig:
    """应用配置"""
    name: str = "AI应用"
    version: str = "2.0.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    cors_origins: list = None

    def __post_init__(self):
        if self.cors_origins is None:
            object.__setattr__(self, 'cors_origins', ["*"])


# 全局配置实例
ai_config = AIConfig()
db_config = DatabaseConfig()
app_config = AppConfig()
