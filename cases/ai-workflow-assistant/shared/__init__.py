"""
共享模块
提供统一的 AI 客户端、数据库工具和通用函数
"""

from .config import ai_config, db_config, app_config
from .ai_client import call_ai, call_ai_json, clear_cache, get_cache_stats
from .database import get_db, init_table, insert_record, query_records, count_records
from .utils import (
    format_datetime,
    truncate_text,
    clean_html,
    to_json_response,
    to_error_response,
    export_to_csv,
    export_to_json,
    parse_json_safely,
    split_text_chunks,
    validate_required_fields,
)

__all__ = [
    # Config
    "ai_config",
    "db_config",
    "app_config",
    # AI Client
    "call_ai",
    "call_ai_json",
    "clear_cache",
    "get_cache_stats",
    # Database
    "get_db",
    "init_table",
    "insert_record",
    "query_records",
    "count_records",
    # Utils
    "format_datetime",
    "truncate_text",
    "clean_html",
    "to_json_response",
    "to_error_response",
    "export_to_csv",
    "export_to_json",
    "parse_json_safely",
    "split_text_chunks",
    "validate_required_fields",
]
