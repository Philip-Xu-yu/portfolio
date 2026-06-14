"""
SQLite 数据库工具模块
支持本地 SQLite 和 Turso (分布式 SQLite)
提供统一的数据库操作接口
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, Any
from contextlib import contextmanager

from .config import db_config


def ensure_db_dir():
    """确保数据库目录存在"""
    db_dir = os.path.dirname(db_config.path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


def get_connection():
    """获取数据库连接（支持 Turso 和本地 SQLite）"""
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")

    if turso_url and turso_token:
        # 使用 Turso (分布式 SQLite)
        try:
            import libsql_experimental as libsql
            conn = libsql.connect(turso_url, auth_token=turso_token)
            return conn
        except ImportError:
            # 如果没有安装 libsql，回退到本地 SQLite
            pass

    # 使用本地 SQLite
    ensure_db_dir()
    conn = sqlite3.connect(db_config.path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """获取数据库连接（上下文管理器）"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_table(table_name: str, schema: str):
    """初始化表"""
    with get_db() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {schema}
            )
        """)


def insert_record(table_name: str, data: dict) -> int:
    """插入记录，返回 ID"""
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    values = tuple(data.values())

    with get_db() as conn:
        cursor = conn.execute(
            f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
            values
        )
        return cursor.lastrowid


def query_records(table_name: str, where: str = "", params: tuple = (),
                  order_by: str = "id DESC", limit: int = 100) -> list:
    """查询记录"""
    with get_db() as conn:
        sql = f"SELECT * FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        sql += f" ORDER BY {order_by} LIMIT {limit}"
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def count_records(table_name: str, where: str = "", params: tuple = ()) -> int:
    """统计记录数"""
    with get_db() as conn:
        sql = f"SELECT COUNT(*) FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        return conn.execute(sql, params).fetchone()[0]


def update_record(table_name: str, record_id: int, data: dict):
    """更新记录"""
    set_clause = ", ".join([f"{k}=?" for k in data.keys()])
    values = tuple(data.values()) + (record_id,)

    with get_db() as conn:
        conn.execute(
            f"UPDATE {table_name} SET {set_clause} WHERE id=?",
            values
        )


def delete_record(table_name: str, record_id: int):
    """删除记录"""
    with get_db() as conn:
        conn.execute(f"DELETE FROM {table_name} WHERE id=?", (record_id,))
