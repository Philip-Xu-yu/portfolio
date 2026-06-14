"""
通用工具函数
"""

import json
import csv
import io
import re
from datetime import datetime
from typing import Any


def format_datetime(dt: datetime = None) -> str:
    """格式化日期时间"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def truncate_text(text: str, max_length: int = 200) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def clean_html(text: str) -> str:
    """清理 HTML 标签"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def to_json_response(data: Any, status: str = "success") -> dict:
    """统一的 JSON 响应格式"""
    return {
        "status": status,
        "data": data,
        "timestamp": format_datetime(),
    }


def to_error_response(message: str, code: int = 500) -> dict:
    """统一的错误响应格式"""
    return {
        "status": "error",
        "message": message,
        "code": code,
        "timestamp": format_datetime(),
    }


def export_to_csv(data: list[dict], filename: str = None) -> str:
    """导出数据为 CSV 格式"""
    if not data:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def export_to_json(data: Any, pretty: bool = True) -> str:
    """导出数据为 JSON 格式"""
    return json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)


def parse_json_safely(text: str) -> dict:
    """安全地解析 JSON"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 部分
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except:
                pass
        return {"raw_text": text}


def split_text_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    将文本分割成重叠的块（用于知识库）

    Args:
        text: 原始文本
        chunk_size: 每块的最大字符数
        overlap: 块之间的重叠字符数

    Returns:
        文本块列表
    """
    if not text:
        return []

    chunks = []
    # 先按段落分割
    paragraphs = text.split("\n\n")

    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # 保留最后一部分作为重叠
            if overlap > 0 and current_chunk:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def validate_required_fields(data: dict, fields: list[str]) -> list[str]:
    """验证必填字段"""
    missing = []
    for field in fields:
        if field not in data or not data[field]:
            missing.append(field)
    return missing
