"""
AI自媒体起号助手 v2.0
输入领域/赛道 → 生成账号定位、30天内容规划、爆款选题、完整文案
支持 SQLite 持久化、结构化输出、导出功能
"""

import sys
import os
import json
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# 添加共享模块路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import call_ai, call_ai_json, to_json_response, to_error_response, format_datetime

# AI 配置
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "mimo-v2.5-pro")

# 数据库配置
DB_PATH = os.getenv("DATABASE_URL", "data/media_assistant.db")

app = FastAPI(title="AI自媒体起号助手", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 数据库 ====================

def ensure_db_dir():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


def get_db():
    ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field TEXT NOT NULL,
                platform TEXT DEFAULT '小红书',
                plan_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field TEXT NOT NULL,
                hot_topic TEXT,
                topics_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                platform TEXT DEFAULT '小红书',
                style TEXT DEFAULT '干货分享',
                article_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


init_db()


# ==================== 数据模型 ====================

class AccountRequest(BaseModel):
    field: str
    platform: str = "小红书"
    target_audience: str = ""


class TopicRequest(BaseModel):
    field: str
    hot_topic: str = ""
    count: int = 10


class ArticleRequest(BaseModel):
    topic: str
    platform: str = "小红书"
    style: str = "干货分享"


# ==================== AI 调用 ====================

def generate_account_plan(field: str, platform: str, target_audience: str) -> dict:
    """生成账号定位方案（结构化输出）"""
    system = f"""你是一个资深自媒体运营专家，精通{platform}平台。
请根据用户提供的领域，生成详细的账号定位方案。

必须返回 JSON 格式：
{{
    "persona": "账号人设描述",
    "content_direction": "内容方向",
    "differentiation": "差异化定位",
    "monetization": ["变现路径1", "变现路径2", ...],
    "target_audience": "目标人群画像",
    "posting_frequency": "发布频率建议",
    "sample_bio": "示例个人简介"
}}"""

    user = f"领域：{field}\n平台：{platform}\n目标人群：{target_audience or '待定'}"
    return call_ai_json(system, user, temperature=0.7)


def generate_topics(field: str, hot_topic: str, count: int) -> dict:
    """生成爆款选题（结构化输出）"""
    system = f"""你是一个爆款选题专家，精通小红书/抖音平台。
请根据用户提供的领域和热点，生成有爆款潜力的选题。

必须返回 JSON 格式：
{{
    "topics": [
        {{
            "title": "选题标题",
            "angle": "切入角度",
            "hook": "开头钩子",
            "estimated_reach": "预估热度(高/中/低)",
            "best_time": "最佳发布时间"
        }}
    ]
}}"""

    user = f"领域：{field}\n热点：{hot_topic or '无特定热点'}\n数量：{count}个"
    return call_ai_json(system, user, temperature=0.8)


def generate_article(topic: str, platform: str, style: str) -> str:
    """生成完整文案"""
    system = f"""你是一个{platform}爆款文案写手。
请根据选题生成完整的文案。

要求：
- 标题吸引眼球（含数字或情绪词）
- 开头有钩子（3秒内抓住注意力）
- 正文有干货（分点清晰）
- 结尾有CTA（引导互动）
- 适合{platform}平台风格
- 风格：{style}

输出格式：
🔥 标题：xxx
📝 正文：xxx
🏷️ 标签：xxx"""

    user = f"选题：{topic}\n\n请生成完整文案。"
    return call_ai(system, user, temperature=0.8)


# ==================== API 端点 ====================

@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI自媒体起号助手</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --bg: #0a0a0a; --surface: #141414; --border: #222; --text: #e5e5e5; --text-2: #888; --accent: #3b82f6; --accent-hover: #2563eb; }
        body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }
        .container { max-width: 900px; margin: 0 auto; padding: 2rem; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .subtitle { color: var(--text-2); margin-bottom: 2rem; }
        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
        .section h2 { margin-bottom: 1rem; }
        label { display: block; font-size: 0.9rem; color: var(--text-2); margin-bottom: 0.3rem; }
        input, select, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 1rem; margin-bottom: 1rem; font-family: inherit; }
        textarea { min-height: 100px; resize: vertical; }
        button { padding: 0.8rem 2rem; background: var(--accent); color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
        button:hover { background: var(--accent-hover); }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-secondary { background: transparent; border: 1px solid var(--border); color: var(--text); }
        .result { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; line-height: 1.8; }
        .loading { color: var(--text-2); font-style: italic; }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
        .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: var(--text-2); }
        .tab.active { background: var(--accent); border-color: var(--accent); color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .history-item { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; cursor: pointer; }
        .history-item:hover { border-color: var(--accent); }
        .history-item .time { font-size: 0.8rem; color: var(--text-2); }
        .export-btn { font-size: 0.85rem; padding: 0.5rem 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 AI自媒体起号助手</h1>
        <p class="subtitle">输入你的领域，10分钟生成30天内容规划</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('generate')">✨ 生成内容</div>
            <div class="tab" onclick="switchTab('history')">📋 历史记录</div>
            <div class="tab" onclick="switchTab('demo')">🎮 演示</div>
        </div>

        <div id="tab-generate" class="tab-content active">
            <div class="section">
                <h2>📋 账号定位</h2>
                <label>你的领域/赛道</label>
                <input type="text" id="field" placeholder="例：职场成长、母婴育儿、AI工具、美食探店...">
                <label>目标平台</label>
                <select id="platform">
                    <option value="小红书">小红书</option>
                    <option value="抖音">抖音</option>
                    <option value="公众号">公众号</option>
                    <option value="B站">B站</option>
                </select>
                <label>目标人群（可选）</label>
                <input type="text" id="audience" placeholder="例：25-35岁职场女性">
                <button onclick="generatePlan()">生成账号定位</button>
                <button class="btn-secondary" onclick="exportPlan()" style="margin-left:0.5rem">导出方案</button>
                <div id="plan-result"></div>
            </div>

            <div class="section">
                <h2>💡 爆款选题</h2>
                <label>输入热点或留空随机生成</label>
                <input type="text" id="hot-topic" placeholder="例：ChatGPT、双11、职场裁员...">
                <button onclick="generateTopics()">生成10个选题</button>
                <div id="topics-result"></div>
            </div>

            <div class="section">
                <h2>✍️ 完整文案</h2>
                <label>选题</label>
                <input type="text" id="article-topic" placeholder="输入一个选题，或从上面复制">
                <label>风格</label>
                <select id="style">
                    <option value="干货分享">干货分享</option>
                    <option value="故事叙述">故事叙述</option>
                    <option value="对比测评">对比测评</option>
                    <option value="经验分享">经验分享</option>
                </select>
                <button onclick="generateArticle()">生成完整文案</button>
                <div id="article-result"></div>
            </div>
        </div>

        <div id="tab-history" class="tab-content">
            <div class="section">
                <h2>📋 历史生成记录</h2>
                <div id="history-list">加载中...</div>
            </div>
        </div>

        <div id="tab-demo" class="tab-content">
            <div class="section">
                <h2>🎮 演示模式</h2>
                <p style="color:var(--text-2); margin-bottom:1rem">点击下方按钮，自动生成一个完整的自媒体起号方案示例</p>
                <button id="demo-btn" onclick="runDemo()">运行演示</button>
                <div id="demo-result"></div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-'+name).classList.add('active');
            if (name === 'history') loadHistory();
        }

        async function callAPI(endpoint, data, resultId) {
            const resultDiv = document.getElementById(resultId);
            resultDiv.innerHTML = '<p class="loading">生成中...</p>';
            try {
                const resp = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const json = await resp.json();
                if (json.status === 'error') {
                    resultDiv.innerHTML = '<p style="color:red">错误：' + json.message + '</p>';
                    return null;
                }
                const content = json.data?.result || json.data?.plan || json.data?.topics || json.data?.article || JSON.stringify(json.data, null, 2);
                resultDiv.innerHTML = '<div class="result">' + formatContent(content) + '</div>';
                return json.data;
            } catch(e) {
                resultDiv.innerHTML = '<p style="color:red">错误：' + e.message + '</p>';
                return null;
            }
        }

        function formatContent(text) {
            if (typeof text === 'object') text = JSON.stringify(text, null, 2);
            return text.replace(/\\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        }

        async function generatePlan() {
            const field = document.getElementById('field').value;
            if (!field) { alert('请输入领域'); return; }
            await callAPI('/api/account-plan', {
                field, platform: document.getElementById('platform').value,
                target_audience: document.getElementById('audience').value
            }, 'plan-result');
        }

        async function generateTopics() {
            const field = document.getElementById('field').value;
            if (!field) { alert('请先输入领域'); return; }
            await callAPI('/api/topics', {
                field, hot_topic: document.getElementById('hot-topic').value, count: 10
            }, 'topics-result');
        }

        async function generateArticle() {
            const topic = document.getElementById('article-topic').value;
            if (!topic) { alert('请输入选题'); return; }
            await callAPI('/api/article', {
                topic, platform: document.getElementById('platform').value,
                style: document.getElementById('style').value
            }, 'article-result');
        }

        async function exportPlan() {
            const field = document.getElementById('field').value;
            if (!field) { alert('请先生成方案'); return; }
            const resp = await fetch('/api/export/plan?field=' + encodeURIComponent(field));
            const data = await resp.json();
            const blob = new Blob([JSON.stringify(data.data, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = '自媒体方案_' + field + '.json'; a.click();
        }

        async function loadHistory() {
            try {
                const resp = await fetch('/api/history');
                const data = await resp.json();
                const div = document.getElementById('history-list');
                if (data.data.length === 0) {
                    div.innerHTML = '<p style="color:var(--text-2)">暂无历史记录</p>';
                    return;
                }
                div.innerHTML = data.data.map(item =>
                    '<div class="history-item">' +
                    '<div class="time">' + item.created_at + '</div>' +
                    '<div>' + item.field + ' - ' + item.platform + '</div>' +
                    '</div>'
                ).join('');
            } catch(e) {
                document.getElementById('history-list').innerHTML = '<p style="color:red">加载失败</p>';
            }
        }

        async function runDemo() {
            document.getElementById('demo-result').innerHTML = '<p class="loading">演示运行中...</p>';
            // 自动填充演示数据
            document.getElementById('field').value = 'AI工具测评';
            document.getElementById('platform').value = '小红书';
            document.getElementById('audience').value = '25-35岁科技爱好者';
            // 切换到生成标签
            document.querySelectorAll('.tab')[0].click();
            // 执行生成
            await generatePlan();
        }
    </script>
</body>
</html>"""


@app.post("/api/account-plan")
async def account_plan(req: AccountRequest):
    """生成账号定位方案"""
    try:
        plan = generate_account_plan(req.field, req.platform, req.target_audience)
        # 保存到数据库
        with get_db() as conn:
            conn.execute(
                "INSERT INTO plans (field, platform, plan_json) VALUES (?,?,?)",
                (req.field, req.platform, json.dumps(plan, ensure_ascii=False))
            )
        return to_json_response({"plan": plan, "field": req.field, "platform": req.platform})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/topics")
async def generate_topics_api(req: TopicRequest):
    """生成爆款选题"""
    try:
        topics = generate_topics(req.field, req.hot_topic, req.count)
        # 保存到数据库
        with get_db() as conn:
            conn.execute(
                "INSERT INTO topics (field, hot_topic, topics_json) VALUES (?,?,?)",
                (req.field, req.hot_topic, json.dumps(topics, ensure_ascii=False))
            )
        return to_json_response(topics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/article")
async def generate_article_api(req: ArticleRequest):
    """生成完整文案"""
    try:
        article = generate_article(req.topic, req.platform, req.style)
        # 保存到数据库
        with get_db() as conn:
            conn.execute(
                "INSERT INTO articles (topic, platform, style, article_text) VALUES (?,?,?,?)",
                (req.topic, req.platform, req.style, article)
            )
        return to_json_response({"article": article, "topic": req.topic})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history():
    """获取历史记录"""
    with get_db() as conn:
        plans = conn.execute("SELECT field, platform, created_at FROM plans ORDER BY id DESC LIMIT 20").fetchall()
    return to_json_response([dict(p) for p in plans])


@app.get("/api/export/plan")
async def export_plan(field: str):
    """导出方案"""
    with get_db() as conn:
        plans = conn.execute(
            "SELECT plan_json, platform, created_at FROM plans WHERE field=? ORDER BY id DESC LIMIT 1",
            (field,)
        ).fetchall()
    if not plans:
        raise HTTPException(status_code=404, detail="未找到该领域的方案")
    return to_json_response(json.loads(plans[0]["plan_json"]))


@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    with get_db() as conn:
        plan_count = conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
        topic_count = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        article_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    return to_json_response({
        "plans": plan_count,
        "topics": topic_count,
        "articles": article_count,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
