"""
AI爆款内容分析器 v2.0
输入内容 → 结构化分析爆款因素 → 量化评分 → 优化建议 → 仿写生成
支持 SQLite 持久化、结构化 JSON 输出、历史记录
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
from shared import call_ai, call_ai_json, to_json_response, to_error_response

DB_PATH = os.getenv("DATABASE_URL", "data/content_analyzer.db")

app = FastAPI(title="AI爆款内容分析器", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ==================== 数据库 ====================

def get_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_preview TEXT,
                platform TEXT,
                analysis_json TEXT,
                score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


init_db()


# ==================== 数据模型 ====================

class AnalyzeRequest(BaseModel):
    content: str
    platform: str = "小红书"


class OptimizeRequest(BaseModel):
    content: str
    issues: str = ""
    platform: str = "小红书"


class RewriteRequest(BaseModel):
    content: str
    style: str = "爆款风格"
    platform: str = "小红书"


# ==================== AI 调用 ====================

def analyze_content(content: str, platform: str) -> dict:
    """结构化分析内容"""
    system = f"""你是一个{platform}爆款内容分析专家。
请从以下维度分析内容，并返回 JSON 格式结果：

{{
    "title_analysis": {{
        "score": 8,
        "length": 15,
        "has_number": true,
        "has_emotion_word": true,
        "keywords": ["关键词1", "关键词2"],
        "emotion_words": ["情绪词1"],
        "suggestion": "标题优化建议"
    }},
    "structure_analysis": {{
        "score": 7,
        "hook_type": "悬念式/数字式/痛点式",
        "has_cta": true,
        "paragraph_count": 5,
        "suggestion": "结构优化建议"
    }},
    "emotion_triggers": [
        {{"type": "共鸣", "intensity": "强", "example": "原文片段"}}
    ],
    "platform_fit": {{
        "score": 8,
        "reason": "适配原因",
        "suggestions": ["建议1", "建议2"]
    }},
    "overall_score": 7.5,
    "strengths": ["亮点1", "亮点2"],
    "weaknesses": ["不足1", "不足2"],
    "highlight_sentences": ["值得保留的句子"],
    "optimized_title": "优化后的标题建议"
}}"""

    user = f"请分析以下{platform}内容：\n\n{content}"
    return call_ai_json(system, user, temperature=0.3)


def generate_optimization(content: str, platform: str, analysis: dict = None) -> dict:
    """生成优化建议"""
    system = f"""你是一个{platform}内容优化专家。
请针对内容的不足之处，给出具体的优化建议。

返回 JSON 格式：
{{
    "optimizations": [
        {{
            "issue": "问题描述",
            "before": "原文片段",
            "after": "优化后片段",
            "reason": "优化原因"
        }}
    ],
    "overall_tips": ["整体建议1", "整体建议2"]
}}"""

    context = ""
    if analysis:
        context = f"\n之前的分析结果：{json.dumps(analysis, ensure_ascii=False)}"
    user = f"请优化以下{platform}内容：\n\n{content}{context}"
    return call_ai_json(system, user, temperature=0.5)


def rewrite_content(content: str, style: str, platform: str) -> str:
    """仿写生成"""
    system = f"""你是一个{platform}爆款文案写手。
请根据原始内容，用指定风格重新撰写。

要求：
- 保留核心信息
- 用更吸引人的方式表达
- 符合{platform}平台风格
- 风格：{style}

输出格式：
🔥 新标题：xxx
📝 新正文：xxx
🏷️ 标签：xxx"""

    user = f"原始内容：\n{content}\n\n请重新撰写。"
    return call_ai(system, user, temperature=0.8)


# ==================== API 端点 ====================

@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI爆款内容分析器 v2.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --bg: #0a0a0a; --surface: #141414; --border: #222; --text: #e5e5e5; --text-2: #888; --accent: #3b82f6; --success: #22c55e; --warning: #f59e0b; }
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
        .score-card { display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }
        .score-item { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; text-align: center; min-width: 120px; }
        .score-item .num { font-size: 2rem; font-weight: 800; }
        .score-item .label { font-size: 0.8rem; color: var(--text-2); }
        .score-high { color: var(--success); }
        .score-mid { color: var(--warning); }
        .score-low { color: #ef4444; }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
        .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: var(--text-2); }
        .tab.active { background: var(--accent); border-color: var(--accent); color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 AI爆款内容分析器 v2.0</h1>
        <p class="subtitle">输入内容，AI 帮你量化分析爆款因素并生成优化建议</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('analyze')">🔍 内容分析</div>
            <div class="tab" onclick="switchTab('history')">📋 历史记录</div>
        </div>

        <div id="tab-analyze" class="tab-content active">
            <div class="section">
                <h2>🔍 内容分析</h2>
                <label>粘贴要分析的内容</label>
                <textarea id="content" placeholder="粘贴一篇文章、一条笔记、一段文案..."></textarea>
                <label>平台</label>
                <select id="platform">
                    <option value="小红书">小红书</option>
                    <option value="抖音">抖音</option>
                    <option value="公众号">公众号</option>
                    <option value="B站">B站</option>
                </select>
                <button onclick="analyzeContent()">分析爆款因素</button>
                <div id="analyze-result"></div>
            </div>

            <div class="section">
                <h2>✨ 优化建议</h2>
                <button onclick="getOptimization()">基于分析结果生成优化建议</button>
                <div id="optimize-result"></div>
            </div>

            <div class="section">
                <h2>🔄 仿写生成</h2>
                <label>仿写风格</label>
                <select id="style">
                    <option value="爆款风格">爆款风格</option>
                    <option value="专业干货">专业干货</option>
                    <option value="轻松幽默">轻松幽默</option>
                    <option value="情感共鸣">情感共鸣</option>
                </select>
                <button onclick="rewriteContent()">生成仿写内容</button>
                <div id="rewrite-result"></div>
            </div>
        </div>

        <div id="tab-history" class="tab-content">
            <div class="section">
                <h2>📋 分析历史</h2>
                <div id="history-list">加载中...</div>
            </div>
        </div>
    </div>

    <script>
        let lastAnalysis = null;

        function switchTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-'+name).classList.add('active');
            if (name === 'history') loadHistory();
        }

        function getScoreClass(score) {
            if (score >= 7) return 'score-high';
            if (score >= 5) return 'score-mid';
            return 'score-low';
        }

        function renderScores(analysis) {
            return '<div class="score-card">' +
                '<div class="score-item"><div class="num ' + getScoreClass(analysis.title_analysis?.score || 0) + '">' + (analysis.title_analysis?.score || '-') + '</div><div class="label">标题得分</div></div>' +
                '<div class="score-item"><div class="num ' + getScoreClass(analysis.structure_analysis?.score || 0) + '">' + (analysis.structure_analysis?.score || '-') + '</div><div class="label">结构得分</div></div>' +
                '<div class="score-item"><div class="num ' + getScoreClass(analysis.platform_fit?.score || 0) + '">' + (analysis.platform_fit?.score || '-') + '</div><div class="label">平台适配</div></div>' +
                '<div class="score-item"><div class="num ' + getScoreClass(analysis.overall_score || 0) + '">' + (analysis.overall_score || '-') + '</div><div class="label">综合得分</div></div>' +
                '</div>';
        }

        async function analyzeContent() {
            const content = document.getElementById('content').value;
            if (!content) { alert('请输入内容'); return; }
            const resultDiv = document.getElementById('analyze-result');
            resultDiv.innerHTML = '<p class="loading">分析中...</p>';
            try {
                const resp = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({content, platform: document.getElementById('platform').value})
                });
                const json = await resp.json();
                if (json.status === 'error') {
                    resultDiv.innerHTML = '<p style="color:red">错误：' + json.message + '</p>';
                    return;
                }
                lastAnalysis = json.data;
                let html = renderScores(json.data);
                html += '<div class="result">' + JSON.stringify(json.data, null, 2) + '</div>';
                resultDiv.innerHTML = html;
            } catch(e) {
                resultDiv.innerHTML = '<p style="color:red">错误：' + e.message + '</p>';
            }
        }

        async function getOptimization() {
            const content = document.getElementById('content').value;
            if (!content) { alert('请先输入内容并分析'); return; }
            const resultDiv = document.getElementById('optimize-result');
            resultDiv.innerHTML = '<p class="loading">生成优化建议中...</p>';
            try {
                const resp = await fetch('/api/optimize', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        content, platform: document.getElementById('platform').value,
                        issues: lastAnalysis ? JSON.stringify(lastAnalysis.weaknesses) : ''
                    })
                });
                const json = await resp.json();
                resultDiv.innerHTML = '<div class="result">' + JSON.stringify(json.data, null, 2) + '</div>';
            } catch(e) {
                resultDiv.innerHTML = '<p style="color:red">错误：' + e.message + '</p>';
            }
        }

        async function rewriteContent() {
            const content = document.getElementById('content').value;
            if (!content) { alert('请先输入内容'); return; }
            const resultDiv = document.getElementById('rewrite-result');
            resultDiv.innerHTML = '<p class="loading">生成仿写中...</p>';
            try {
                const resp = await fetch('/api/rewrite', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        content, style: document.getElementById('style').value,
                        platform: document.getElementById('platform').value
                    })
                });
                const json = await resp.json();
                resultDiv.innerHTML = '<div class="result">' + (json.data?.rewrite || JSON.stringify(json.data)) + '</div>';
            } catch(e) {
                resultDiv.innerHTML = '<p style="color:red">错误：' + e.message + '</p>';
            }
        }

        async function loadHistory() {
            try {
                const resp = await fetch('/api/history');
                const json = await resp.json();
                const div = document.getElementById('history-list');
                if (!json.data || json.data.length === 0) {
                    div.innerHTML = '<p style="color:var(--text-2)">暂无分析记录</p>';
                    return;
                }
                div.innerHTML = json.data.map(item =>
                    '<div style="background:#1a1a1a;border:1px solid #222;border-radius:8px;padding:1rem;margin-bottom:0.5rem">' +
                    '<div style="font-size:0.8rem;color:#888">' + item.created_at + ' | ' + item.platform + ' | 得分：' + (item.score || '-') + '</div>' +
                    '<div>' + (item.content_preview || '').substring(0, 100) + '...</div>' +
                    '</div>'
                ).join('');
            } catch(e) {
                document.getElementById('history-list').innerHTML = '<p style="color:red">加载失败</p>';
            }
        }
    </script>
</body>
</html>"""


@app.post("/api/analyze")
async def analyze_content_api(req: AnalyzeRequest):
    """分析内容"""
    try:
        if len(req.content) < 10:
            raise HTTPException(status_code=400, detail="内容太短，请输入至少10个字符")
        if len(req.content) > 10000:
            raise HTTPException(status_code=400, detail="内容太长，请控制在10000字符以内")

        analysis = analyze_content(req.content, req.platform)

        # 保存到数据库
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analyses (content_preview, platform, analysis_json, score) VALUES (?,?,?,?)",
                (req.content[:200], req.platform, json.dumps(analysis, ensure_ascii=False), analysis.get("overall_score", 0))
            )
        return to_json_response(analysis)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/optimize")
async def optimize_content_api(req: OptimizeRequest):
    """生成优化建议"""
    try:
        optimization = generate_optimization(req.content, req.platform)
        return to_json_response(optimization)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rewrite")
async def rewrite_content_api(req: RewriteRequest):
    """仿写生成"""
    try:
        rewrite = rewrite_content(req.content, req.style, req.platform)
        return to_json_response({"rewrite": rewrite})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history():
    """获取分析历史"""
    with get_db() as conn:
        rows = conn.execute("SELECT content_preview, platform, score, created_at FROM analyses ORDER BY id DESC LIMIT 50").fetchall()
    return to_json_response([dict(r) for r in rows])


@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        avg_score = conn.execute("SELECT AVG(score) FROM analyses WHERE score > 0").fetchone()[0]
    return to_json_response({"total_analyses": total, "avg_score": round(avg_score, 1) if avg_score else 0})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
