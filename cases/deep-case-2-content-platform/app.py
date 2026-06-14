"""
深度案例2：AI内容平台 v2.0
内容创作、分析、优化、发布一体化平台
支持 SQLite 持久化、结构化输出、历史记录
"""

import sys
import os
import json
import sqlite3
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import call_ai, call_ai_json, to_json_response

DB_PATH = os.getenv("DATABASE_URL", "data/content_platform.db")

app = FastAPI(title="AI内容平台", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def get_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                content_type TEXT DEFAULT 'article',
                platform TEXT DEFAULT '小红书',
                status TEXT DEFAULT 'draft',
                score REAL,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                analysis_type TEXT,
                result_json TEXT,
                score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES contents(id)
            )
        """)
        conn.commit()


init_db()


class ContentCreate(BaseModel):
    topic: str
    platform: str = "小红书"
    content_type: str = "article"
    style: str = "干货分享"


class ContentAnalyze(BaseModel):
    content: str
    platform: str = "小红书"


class ContentOptimize(BaseModel):
    content: str
    platform: str = "小红书"
    target_score: float = 8.0


def generate_content(topic: str, platform: str, content_type: str, style: str) -> dict:
    """生成内容"""
    system = f"""你是一个{platform}平台的资深内容创作者。
请根据主题生成高质量的{content_type}。

返回 JSON 格式：
{{
    "title": "标题",
    "content": "正文内容",
    "tags": ["标签1", "标签2", "标签3"],
    "hook": "开头钩子",
    "cta": "结尾CTA",
    "estimated_score": 8.0
}}

风格：{style}
平台：{platform}"""

    user = f"主题：{topic}"
    return call_ai_json(system, user, temperature=0.8)


def analyze_content(content: str, platform: str) -> dict:
    """分析内容"""
    system = f"""你是{platform}内容分析专家。
分析内容并返回 JSON：
{{
    "title_score": {{"score": 8, "reason": "..."}},
    "structure_score": {{"score": 7, "reason": "..."}},
    "emotion_score": {{"score": 8, "triggers": ["共鸣"]}},
    "platform_fit": {{"score": 8, "reason": "..."}},
    "overall_score": 7.5,
    "strengths": ["亮点1"],
    "weaknesses": ["不足1"],
    "suggestions": ["建议1"]
}}"""

    return call_ai_json(system, f"分析以下{platform}内容：\n\n{content}", temperature=0.3)


def optimize_content(content: str, platform: str, target_score: float) -> dict:
    """优化内容"""
    system = f"""你是{platform}内容优化专家。
请优化内容，目标评分 {target_score}/10。

返回 JSON：
{{
    "optimized_title": "优化后的标题",
    "optimized_content": "优化后的正文",
    "changes": [
        {{"type": "标题优化", "before": "原标题", "after": "新标题", "reason": "原因"}}
    ],
    "estimated_score": 8.5
}}"""

    return call_ai_json(system, f"优化以下{platform}内容：\n\n{content}", temperature=0.5)


@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI内容平台 v2.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --bg: #0a0a0a; --surface: #141414; --border: #222; --text: #e5e5e5; --text-2: #888; --accent: #3b82f6; --success: #22c55e; }
        body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }
        .container { max-width: 900px; margin: 0 auto; padding: 2rem; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .subtitle { color: var(--text-2); margin-bottom: 2rem; }
        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
        .section h2 { margin-bottom: 1rem; }
        label { display: block; font-size: 0.9rem; color: var(--text-2); margin-bottom: 0.3rem; }
        input, select, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 1rem; margin-bottom: 1rem; font-family: inherit; }
        textarea { min-height: 150px; resize: vertical; }
        button { padding: 0.8rem 2rem; background: var(--accent); color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
        button:hover { background: #2563eb; }
        .result { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; line-height: 1.8; }
        .loading { color: var(--text-2); font-style: italic; }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
        .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: var(--text-2); }
        .tab.active { background: var(--accent); border-color: var(--accent); color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .score-card { display: inline-block; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 0.8rem 1.2rem; margin: 0.3rem; text-align: center; }
        .score-card .num { font-size: 1.5rem; font-weight: 800; color: var(--accent); }
        .score-card .label { font-size: 0.75rem; color: var(--text-2); }
        .content-item { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; cursor: pointer; }
        .content-item:hover { border-color: var(--accent); }
    </style>
</head>
<body>
    <div class="container">
        <h1>✍️ AI内容平台 v2.0</h1>
        <p class="subtitle">内容创作 → 分析 → 优化 → 发布</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('create')">✨ 创作内容</div>
            <div class="tab" onclick="switchTab('analyze')">📊 分析内容</div>
            <div class="tab" onclick="switchTab('optimize')">🔧 优化内容</div>
            <div class="tab" onclick="switchTab('library')">📚 内容库</div>
        </div>

        <div id="tab-create" class="tab-content active">
            <div class="section">
                <h2>✨ AI 内容创作</h2>
                <label>主题/选题</label>
                <input type="text" id="topic" placeholder="例：如何用AI提升工作效率">
                <label>平台</label>
                <select id="create-platform">
                    <option value="小红书">小红书</option>
                    <option value="抖音">抖音</option>
                    <option value="公众号">公众号</option>
                    <option value="B站">B站</option>
                </select>
                <label>内容类型</label>
                <select id="content-type">
                    <option value="article">图文笔记</option>
                    <option value="video_script">视频脚本</option>
                    <option value="thread">系列内容</option>
                </select>
                <label>风格</label>
                    <select id="style">
                    <option value="干货分享">干货分享</option>
                    <option value="故事叙述">故事叙述</option>
                    <option value="对比测评">对比测评</option>
                    <option value="经验分享">经验分享</option>
                </select>
                <button onclick="createContent()">生成内容</button>
                <div id="create-result"></div>
            </div>
        </div>

        <div id="tab-analyze" class="tab-content">
            <div class="section">
                <h2>📊 内容分析</h2>
                <label>粘贴要分析的内容</label>
                <textarea id="analyze-content" placeholder="粘贴要分析的内容..."></textarea>
                <label>平台</label>
                <select id="analyze-platform">
                    <option value="小红书">小红书</option>
                    <option value="抖音">抖音</option>
                    <option value="公众号">公众号</option>
                </select>
                <button onclick="analyzeContent()">分析内容</button>
                <div id="analyze-result"></div>
            </div>
        </div>

        <div id="tab-optimize" class="tab-content">
            <div class="section">
                <h2>🔧 内容优化</h2>
                <label>粘贴要优化的内容</label>
                <textarea id="optimize-content" placeholder="粘贴要优化的内容..."></textarea>
                <label>目标评分</label>
                <input type="number" id="target-score" value="8.5" min="1" max="10" step="0.5">
                <button onclick="optimizeContent()">优化内容</button>
                <div id="optimize-result"></div>
            </div>
        </div>

        <div id="tab-library" class="tab-content">
            <div class="section">
                <h2>📚 内容库</h2>
                <div id="content-list">加载中...</div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-'+name).classList.add('active');
            if (name === 'library') loadLibrary();
        }

        async function createContent() {
            const topic = document.getElementById('topic').value;
            if (!topic) { alert('请输入主题'); return; }
            const resultDiv = document.getElementById('create-result');
            resultDiv.innerHTML = '<p class="loading">生成中...</p>';
            try {
                const resp = await fetch('/api/content/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        topic, platform: document.getElementById('create-platform').value,
                        content_type: document.getElementById('content-type').value,
                        style: document.getElementById('style').value
                    })
                });
                const json = await resp.json();
                if (json.status === 'error') { resultDiv.innerHTML = '<p style="color:red">错误：'+json.message+'</p>'; return; }
                let html = '<div style="margin-bottom:1rem">';
                html += '<div class="score-card"><div class="num">'+json.data.estimated_score+'</div><div class="label">预估评分</div></div>';
                html += '</div>';
                html += '<div class="result"><strong>'+json.data.title+'</strong>\n\n'+json.data.content+'\n\n标签：'+json.data.tags.join(', ')+'</div>';
                resultDiv.innerHTML = html;
            } catch(e) { resultDiv.innerHTML = '<p style="color:red">错误：'+e.message+'</p>'; }
        }

        async function analyzeContent() {
            const content = document.getElementById('analyze-content').value;
            if (!content) { alert('请输入内容'); return; }
            const resultDiv = document.getElementById('analyze-result');
            resultDiv.innerHTML = '<p class="loading">分析中...</p>';
            try {
                const resp = await fetch('/api/content/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({content, platform: document.getElementById('analyze-platform').value})
                });
                const json = await resp.json();
                if (json.status === 'error') { resultDiv.innerHTML = '<p style="color:red">错误：'+json.message+'</p>'; return; }
                let html = '<div style="margin-bottom:1rem">';
                html += '<div class="score-card"><div class="num">'+json.data.overall_score+'</div><div class="label">综合评分</div></div>';
                html += '<div class="score-card"><div class="num">'+json.data.title_score?.score+'</div><div class="label">标题</div></div>';
                html += '<div class="score-card"><div class="num">'+json.data.structure_score?.score+'</div><div class="label">结构</div></div>';
                html += '<div class="score-card"><div class="num">'+json.data.platform_fit?.score+'</div><div class="label">平台适配</div></div>';
                html += '</div>';
                html += '<div class="result">' + JSON.stringify(json.data, null, 2) + '</div>';
                resultDiv.innerHTML = html;
            } catch(e) { resultDiv.innerHTML = '<p style="color:red">错误：'+e.message+'</p>'; }
        }

        async function optimizeContent() {
            const content = document.getElementById('optimize-content').value;
            if (!content) { alert('请输入内容'); return; }
            const resultDiv = document.getElementById('optimize-result');
            resultDiv.innerHTML = '<p class="loading">优化中...</p>';
            try {
                const resp = await fetch('/api/content/optimize', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        content, platform: '小红书',
                        target_score: parseFloat(document.getElementById('target-score').value)
                    })
                });
                const json = await resp.json();
                if (json.status === 'error') { resultDiv.innerHTML = '<p style="color:red">错误：'+json.message+'</p>'; return; }
                let html = '<div class="score-card"><div class="num">'+json.data.estimated_score+'</div><div class="label">优化后评分</div></div>';
                html += '<div class="result"><strong>'+json.data.optimized_title+'</strong>\n\n'+json.data.optimized_content+'</div>';
                resultDiv.innerHTML = html;
            } catch(e) { resultDiv.innerHTML = '<p style="color:red">错误：'+e.message+'</p>'; }
        }

        async function loadLibrary() {
            try {
                const resp = await fetch('/api/contents');
                const json = await resp.json();
                const div = document.getElementById('content-list');
                if (!json.data || json.data.length === 0) {
                    div.innerHTML = '<p style="color:var(--text-2)">暂无内容</p>';
                    return;
                }
                div.innerHTML = json.data.map(item =>
                    '<div class="content-item">' +
                    '<div style="font-weight:600">' + (item.title || '无标题') + '</div>' +
                    '<div style="font-size:0.8rem;color:var(--text-2)">' + item.platform + ' | ' + item.content_type + ' | 得分：' + (item.score || '-') + ' | ' + item.created_at + '</div>' +
                    '</div>'
                ).join('');
            } catch(e) { document.getElementById('content-list').innerHTML = '<p style="color:red">加载失败</p>'; }
        }
    </script>
</body>
</html>"""


@app.post("/api/content/create")
async def create_content(req: ContentCreate):
    """创建内容"""
    try:
        result = generate_content(req.topic, req.platform, req.content_type, req.style)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO contents (title, content, content_type, platform, score, tags) VALUES (?,?,?,?,?,?)",
                (result.get("title"), result.get("content"), req.content_type, req.platform, result.get("estimated_score"), json.dumps(result.get("tags", []), ensure_ascii=False))
            )
        return to_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/content/analyze")
async def analyze_content_api(req: ContentAnalyze):
    """分析内容"""
    try:
        result = analyze_content(req.content, req.platform)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analyses (analysis_type, result_json, score) VALUES (?,?,?)",
                ("analyze", json.dumps(result, ensure_ascii=False), result.get("overall_score", 0))
            )
        return to_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/content/optimize")
async def optimize_content_api(req: ContentOptimize):
    """优化内容"""
    try:
        result = optimize_content(req.content, req.platform, req.target_score)
        return to_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/contents")
async def list_contents():
    """列出内容"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM contents ORDER BY id DESC LIMIT 50").fetchall()
    return to_json_response([dict(r) for r in rows])


@app.get("/api/stats")
async def get_stats():
    """获取统计"""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM contents").fetchone()[0]
        avg_score = conn.execute("SELECT AVG(score) FROM contents WHERE score > 0").fetchone()[0]
    return to_json_response({"total_contents": total, "avg_score": round(avg_score, 1) if avg_score else 0})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
