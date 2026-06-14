"""
AI商业机会分析Agent v2.0
输入行业和条件 → 结构化市场分析 → 竞品对比 → 商业画布 → 行动计划
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
from shared import call_ai, call_ai_json, to_json_response

DB_PATH = os.getenv("DATABASE_URL", "data/biz_agent.db")

app = FastAPI(title="AI商业机会分析Agent", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


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
                analysis_type TEXT,
                industry TEXT,
                input_data TEXT,
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


init_db()


class MarketRequest(BaseModel):
    industry: str
    target_user: str = ""
    budget: str = ""


class CompetitorRequest(BaseModel):
    competitors: list[str]
    industry: str = ""


class CanvasRequest(BaseModel):
    industry: str
    idea: str
    target_user: str = ""


class ActionPlanRequest(BaseModel):
    industry: str
    idea: str
    budget: str = "10万元"


def analyze_market(industry: str, target_user: str, budget: str) -> dict:
    """结构化市场分析"""
    system = """你是一个资深商业分析师。
请分析用户提供的行业市场机会，返回 JSON 格式：

{
    "market_overview": {
        "size": "市场规模估计",
        "growth_rate": "增长率",
        "drivers": ["驱动因素1", "驱动因素2"],
        "barriers": ["进入壁垒1", "壁垒2"]
    },
    "target_users": {
        "persona": "用户画像",
        "pain_points": ["痛点1", "痛点2"],
        "needs": ["需求1", "需求2"],
        "behavior": "消费行为特征"
    },
    "opportunities": [
        {"direction": "机会方向", "potential": "高/中/低", "reason": "原因"}
    ],
    "risks": [
        {"risk": "风险描述", "level": "高/中/低", "mitigation": "应对策略"}
    ],
    "scores": {
        "market_attractiveness": 8,
        "competition_intensity": 6,
        "entry_difficulty": 5,
        "profit_potential": 7,
        "timing": 8
    },
    "recommendation": "总体建议"
}"""

    user = f"行业：{industry}\n目标用户：{target_user}\n预算：{budget}"
    return call_ai_json(system, user, temperature=0.5)


def analyze_competitors(competitors: list[str], industry: str) -> dict:
    """结构化竞品分析"""
    system = """你是一个竞品分析专家。
请对比分析用户提供的竞品，返回 JSON 格式：

{
    "competitors": [
        {
            "name": "竞品名称",
            "positioning": "市场定位",
            "strengths": ["优势1", "优势2"],
            "weaknesses": ["劣势1", "劣势2"],
            "pricing": "定价策略",
            "target_users": "目标用户"
        }
    ],
    "comparison_matrix": {
        "features": {"竞品A": ["功能1"], "竞品B": ["功能1"]},
        "pricing": {"竞品A": "价格", "竞品B": "价格"},
        "user_scale": {"竞品A": "用户规模", "竞品B": "用户规模"}
    },
    "differentiation_opportunities": ["差异化机会1", "机会2"],
    "suggested_entry_point": "建议切入点",
    "competitive_advantage": "如何建立竞争优势"
}"""

    user = f"竞品：{', '.join(competitors)}\n行业：{industry}"
    return call_ai_json(system, user, temperature=0.5)


def generate_canvas(industry: str, idea: str, target_user: str) -> dict:
    """生成商业模式画布"""
    system = """你是一个商业模式设计专家。
请根据用户的想法生成商业模式画布，返回 JSON 格式：

{
    "canvas": {
        "key_partners": ["合作伙伴1", "合作伙伴2"],
        "key_activities": ["关键活动1", "关键活动2"],
        "key_resources": ["核心资源1", "核心资源2"],
        "value_proposition": "核心价值主张",
        "customer_relationships": "客户关系类型",
        "channels": ["渠道1", "渠道2"],
        "customer_segments": ["客户细分1", "客户细分2"],
        "cost_structure": {
            "fixed_costs": ["固定成本1"],
            "variable_costs": ["可变成本1"]
        },
        "revenue_streams": ["收入来源1", "收入来源2"]
    },
    "viability_score": {
        "value_clarity": 8,
        "market_fit": 7,
        "revenue_potential": 6,
        "execution_difficulty": 5
    },
    "suggestions": ["优化建议1", "优化建议2"]
}"""

    user = f"行业：{industry}\n想法：{idea}\n目标用户：{target_user}"
    return call_ai_json(system, user, temperature=0.5)


def generate_action_plan(industry: str, idea: str, budget: str) -> dict:
    """生成30天行动计划"""
    system = """你是一个创业导师。
请根据用户的想法制定30天行动计划，返回 JSON 格式：

{
    "plan": {
        "week_1": {
            "theme": "需求验证",
            "tasks": [
                {"task": "具体任务", "priority": "高/中/低", "budget": "预算"}
            ],
            "milestone": "里程碑目标"
        },
        "week_2": {
            "theme": "MVP搭建",
            "tasks": [...],
            "milestone": "里程碑目标"
        },
        "week_3": {
            "theme": "小范围测试",
            "tasks": [...],
            "milestone": "里程碑目标"
        },
        "week_4": {
            "theme": "优化迭代",
            "tasks": [...],
            "milestone": "里程碑目标"
        }
    },
    "total_budget": "总预算分配",
    "key_metrics": ["关键指标1", "关键指标2"],
    "risk_mitigation": ["风险应对1", "风险应对2"]
}"""

    user = f"行业：{industry}\n想法：{idea}\n预算：{budget}"
    return call_ai_json(system, user, temperature=0.5)


@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>AI商业机会分析Agent v2.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --bg: #0a0a0a; --surface: #141414; --border: #222; --text: #e5e5e5; --text-2: #888; --accent: #3b82f6; }
        body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }
        .container { max-width: 900px; margin: 0 auto; padding: 2rem; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .subtitle { color: var(--text-2); margin-bottom: 2rem; }
        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
        .section h2 { margin-bottom: 1rem; }
        label { display: block; font-size: 0.9rem; color: var(--text-2); margin-bottom: 0.3rem; }
        input, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 1rem; margin-bottom: 1rem; font-family: inherit; }
        textarea { min-height: 60px; resize: vertical; }
        button { padding: 0.8rem 2rem; background: var(--accent); color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
        button:hover { background: #2563eb; }
        .result { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; line-height: 1.8; }
        .loading { color: var(--text-2); font-style: italic; }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
        .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: var(--text-2); }
        .tab.active { background: var(--accent); border-color: var(--accent); color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .score-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem; margin-bottom: 1rem; }
        .score-card { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; text-align: center; }
        .score-card .num { font-size: 1.5rem; font-weight: 800; color: var(--accent); }
        .score-card .label { font-size: 0.75rem; color: var(--text-2); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 AI商业机会分析Agent v2.0</h1>
        <p class="subtitle">输入行业和想法，AI 帮你结构化分析商业机会</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('market')">📊 市场分析</div>
            <div class="tab" onclick="switchTab('competitor')">🔍 竞品分析</div>
            <div class="tab" onclick="switchTab('canvas')">📋 商业画布</div>
            <div class="tab" onclick="switchTab('plan')">📅 行动计划</div>
            <div class="tab" onclick="switchTab('history')">📝 历史记录</div>
        </div>

        <div id="tab-market" class="tab-content active">
            <div class="section">
                <h2>市场机会分析</h2>
                <label>行业</label>
                <input type="text" id="m-industry" placeholder="例：AI教育、宠物经济、银发经济">
                <label>目标用户</label>
                <input type="text" id="m-user" placeholder="例：K12学生家长">
                <label>预算</label>
                <input type="text" id="m-budget" placeholder="例：10万元">
                <button onclick="analyze('market')">分析市场</button>
                <div id="r-market"></div>
            </div>
        </div>

        <div id="tab-competitor" class="tab-content">
            <div class="section">
                <h2>竞品分析</h2>
                <label>竞品名称（逗号分隔）</label>
                <input type="text" id="c-competitors" placeholder="例：猿辅导,作业帮,学而思">
                <label>所在行业</label>
                <input type="text" id="c-industry" placeholder="例：AI教育">
                <button onclick="analyze('competitor')">分析竞品</button>
                <div id="r-competitor"></div>
            </div>
        </div>

        <div id="tab-canvas" class="tab-content">
            <div class="section">
                <h2>商业模式画布</h2>
                <label>行业</label>
                <input type="text" id="cv-industry" placeholder="例：AI教育">
                <label>产品/服务想法</label>
                <textarea id="cv-idea" placeholder="例：用AI帮家长诊断孩子学习薄弱点"></textarea>
                <label>目标用户</label>
                <input type="text" id="cv-user" placeholder="例：K12学生家长">
                <button onclick="analyze('canvas')">生成画布</button>
                <div id="r-canvas"></div>
            </div>
        </div>

        <div id="tab-plan" class="tab-content">
            <div class="section">
                <h2>30天行动计划</h2>
                <label>行业</label>
                <input type="text" id="p-industry" placeholder="例：AI教育">
                <label>产品/服务想法</label>
                <textarea id="p-idea" placeholder="例：用AI帮家长诊断孩子学习薄弱点"></textarea>
                <label>启动预算</label>
                <input type="text" id="p-budget" placeholder="例：10万元">
                <button onclick="analyze('plan')">生成计划</button>
                <div id="r-plan"></div>
            </div>
        </div>

        <div id="tab-history" class="tab-content">
            <div class="section">
                <h2>分析历史</h2>
                <div id="history-list">加载中...</div>
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

        function renderScores(scores) {
            if (!scores) return '';
            return '<div class="score-grid">' + Object.entries(scores).map(([k, v]) =>
                '<div class="score-card"><div class="num">' + v + '</div><div class="label">' + k + '</div></div>'
            ).join('') + '</div>';
        }

        async function analyze(type) {
            const resultDiv = document.getElementById('r-'+type);
            resultDiv.innerHTML = '<p class="loading">分析中...</p>';
            let data = {}, endpoint = '';

            if (type === 'market') {
                endpoint = '/api/market';
                data = {
                    industry: document.getElementById('m-industry').value,
                    target_user: document.getElementById('m-user').value,
                    budget: document.getElementById('m-budget').value
                };
            } else if (type === 'competitor') {
                endpoint = '/api/competitor';
                data = {
                    competitors: document.getElementById('c-competitors').value.split(',').map(s=>s.trim()),
                    industry: document.getElementById('c-industry').value
                };
            } else if (type === 'canvas') {
                endpoint = '/api/canvas';
                data = {
                    industry: document.getElementById('cv-industry').value,
                    idea: document.getElementById('cv-idea').value,
                    target_user: document.getElementById('cv-user').value
                };
            } else if (type === 'plan') {
                endpoint = '/api/action-plan';
                data = {
                    industry: document.getElementById('p-industry').value,
                    idea: document.getElementById('p-idea').value,
                    budget: document.getElementById('p-budget').value
                };
            }

            try {
                const resp = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const json = await resp.json();
                if (json.status === 'error') {
                    resultDiv.innerHTML = '<p style="color:red">错误：' + json.message + '</p>';
                    return;
                }
                let html = renderScores(json.data.scores || json.data.viability_score);
                html += '<div class="result">' + JSON.stringify(json.data, null, 2) + '</div>';
                resultDiv.innerHTML = html;
            } catch(e) {
                resultDiv.innerHTML = '<p style="color:red">错误：'+e.message+'</p>';
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
                    '<div style="font-size:0.8rem;color:#888">' + item.created_at + ' | ' + item.analysis_type + ' | ' + item.industry + '</div>' +
                    '</div>'
                ).join('');
            } catch(e) {
                document.getElementById('history-list').innerHTML = '<p style="color:red">加载失败</p>';
            }
        }
    </script>
</body>
</html>"""


@app.post("/api/market")
async def market_analysis(req: MarketRequest):
    try:
        result = analyze_market(req.industry, req.target_user, req.budget)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analyses (analysis_type, industry, input_data, result_json) VALUES (?,?,?,?)",
                ("market", req.industry, json.dumps({"target_user": req.target_user, "budget": req.budget}, ensure_ascii=False), json.dumps(result, ensure_ascii=False))
            )
        return to_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/competitor")
async def competitor_analysis(req: CompetitorRequest):
    try:
        result = analyze_competitors(req.competitors, req.industry)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analyses (analysis_type, industry, input_data, result_json) VALUES (?,?,?,?)",
                ("competitor", req.industry, json.dumps({"competitors": req.competitors}, ensure_ascii=False), json.dumps(result, ensure_ascii=False))
            )
        return to_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/canvas")
async def business_canvas(req: CanvasRequest):
    try:
        result = generate_canvas(req.industry, req.idea, req.target_user)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analyses (analysis_type, industry, input_data, result_json) VALUES (?,?,?,?)",
                ("canvas", req.industry, json.dumps({"idea": req.idea, "target_user": req.target_user}, ensure_ascii=False), json.dumps(result, ensure_ascii=False))
            )
        return to_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/action-plan")
async def action_plan(req: ActionPlanRequest):
    try:
        result = generate_action_plan(req.industry, req.idea, req.budget)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analyses (analysis_type, industry, input_data, result_json) VALUES (?,?,?,?)",
                ("plan", req.industry, json.dumps({"idea": req.idea, "budget": req.budget}, ensure_ascii=False), json.dumps(result, ensure_ascii=False))
            )
        return to_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history():
    with get_db() as conn:
        rows = conn.execute("SELECT analysis_type, industry, created_at FROM analyses ORDER BY id DESC LIMIT 50").fetchall()
    return to_json_response([dict(r) for r in rows])


@app.get("/api/stats")
async def get_stats():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        by_type = conn.execute("SELECT analysis_type, COUNT(*) as cnt FROM analyses GROUP BY analysis_type").fetchall()
    return to_json_response({"total": total, "by_type": {r["analysis_type"]: r["cnt"] for r in by_type}})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
