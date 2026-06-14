"""
深度案例3：AI自动化平台 v2.0
可视化工作流编排、多步骤AI处理、定时任务、执行监控
支持 SQLite 持久化、真实执行、历史记录
"""

import sys
import os
import json
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import call_ai, call_ai_json, to_json_response

DB_PATH = os.getenv("DATABASE_URL", "data/automation_platform.db")

app = FastAPI(title="AI自动化平台", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def get_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipelines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                steps_json TEXT NOT NULL,
                trigger_type TEXT DEFAULT 'manual',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id INTEGER,
                pipeline_name TEXT,
                status TEXT DEFAULT 'running',
                input_data TEXT,
                output_data TEXT,
                steps_completed INTEGER DEFAULT 0,
                total_steps INTEGER,
                error_message TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
            )
        """)
        conn.commit()


init_db()


class PipelineStep(BaseModel):
    name: str
    type: str  # ai_process / data_transform / condition / output
    config: dict


class PipelineCreate(BaseModel):
    name: str
    description: str = ""
    steps: list[PipelineStep]
    trigger_type: str = "manual"


class PipelineRun(BaseModel):
    pipeline_id: int
    input_data: str = ""


# 预置模板
TEMPLATES = {
    "content_pipeline": {
        "name": "内容生产流水线",
        "description": "选题生成 → 内容创作 → 质量检查 → SEO优化",
        "steps": [
            {"name": "选题生成", "type": "ai_process", "config": {"prompt": "根据输入的领域，生成5个有爆款潜力的选题"}},
            {"name": "内容创作", "type": "ai_process", "config": {"prompt": "为选题创作完整的小红书文案，包含标题、正文、标签"}},
            {"name": "质量检查", "type": "ai_process", "config": {"prompt": "检查内容质量，评分1-10，给出改进建议"}},
            {"name": "SEO优化", "type": "ai_process", "config": {"prompt": "优化标题和标签，提高搜索排名"}},
        ]
    },
    "customer_analysis": {
        "name": "客户分析流水线",
        "description": "数据收集 → 用户画像 → 需求分析 → 策略建议",
        "steps": [
            {"name": "数据整理", "type": "ai_process", "config": {"prompt": "整理和清洗输入的客户数据"}},
            {"name": "用户画像", "type": "ai_process", "config": {"prompt": "基于数据生成用户画像，包含 demographics、行为、偏好"}},
            {"name": "需求分析", "type": "ai_process", "config": {"prompt": "分析用户核心需求和痛点"}},
            {"name": "策略建议", "type": "ai_process", "config": {"prompt": "基于分析结果，给出营销策略建议"}},
        ]
    },
    "report_generator": {
        "name": "报告生成器",
        "description": "数据解读 → 趋势分析 → 洞察提炼 → 报告生成",
        "steps": [
            {"name": "数据解读", "type": "ai_process", "config": {"prompt": "解读输入的数据，识别关键指标"}},
            {"name": "趋势分析", "type": "ai_process", "config": {"prompt": "分析数据趋势，识别增长/下降模式"}},
            {"name": "洞察提炼", "type": "ai_process", "config": {"prompt": "提炼关键洞察和 actionable 建议"}},
            {"name": "报告生成", "type": "ai_process", "config": {"prompt": "生成结构化的分析报告，包含图表建议"}},
        ]
    },
    "product_optimizer": {
        "name": "产品优化器",
        "description": "竞品分析 → 差异化定位 → 功能建议 → 定价策略",
        "steps": [
            {"name": "竞品分析", "type": "ai_process", "config": {"prompt": "分析竞品的优劣势、定价、用户评价"}},
            {"name": "差异化定位", "type": "ai_process", "config": {"prompt": "基于竞品分析，找出差异化机会"}},
            {"name": "功能建议", "type": "ai_process", "config": {"prompt": "基于差异化定位，建议产品功能优先级"}},
            {"name": "定价策略", "type": "ai_process", "config": {"prompt": "基于竞品和定位，建议定价策略"}},
        ]
    },
}


async def execute_pipeline(pipeline_id: int, pipeline_name: str, steps: list, input_data: str) -> dict:
    """执行流水线"""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO executions (pipeline_id, pipeline_name, input_data, total_steps, status) VALUES (?,?,?,?,?)",
            (pipeline_id, pipeline_name, input_data, len(steps), "running")
        )
        exec_id = cursor.lastrowid

    results = []
    current_data = input_data
    status = "success"

    try:
        for i, step in enumerate(steps):
            step_name = step.get("name", f"步骤{i+1}")
            step_type = step.get("type", "ai_process")
            config = step.get("config", {})

            if step_type == "ai_process":
                prompt = config.get("prompt", "")
                system = f"你是一个AI助手。请根据以下指令处理输入数据。\n指令：{prompt}\n\n要求：输出清晰、结构化。"
                current_data = call_ai(system, current_data or "请处理", temperature=0.7)
                results.append({"step": step_name, "status": "success", "output": current_data[:500]})

            elif step_type == "data_transform":
                transform = config.get("transform", "")
                if transform == "json_format":
                    try:
                        current_data = json.dumps(json.loads(current_data), ensure_ascii=False, indent=2)
                    except:
                        pass
                results.append({"step": step_name, "status": "success", "output": current_data[:500]})

            elif step_type == "condition":
                condition = config.get("condition", "")
                results.append({"step": step_name, "status": "success", "output": f"条件判断：{condition}"})

            elif step_type == "output":
                results.append({"step": step_name, "status": "success", "output": current_data[:500]})

            with get_db() as conn:
                conn.execute(
                    "UPDATE executions SET steps_completed=?, output_data=? WHERE id=?",
                    (i + 1, json.dumps(results, ensure_ascii=False), exec_id)
                )

    except Exception as e:
        status = "error"
        with get_db() as conn:
            conn.execute(
                "UPDATE executions SET status=?, error_message=?, completed_at=? WHERE id=?",
                ("error", str(e), datetime.now().isoformat(), exec_id)
            )
        raise

    with get_db() as conn:
        conn.execute(
            "UPDATE executions SET status=?, completed_at=? WHERE id=?",
            ("success", datetime.now().isoformat(), exec_id)
        )

    return {
        "execution_id": exec_id,
        "status": status,
        "results": results,
        "final_output": current_data
    }


@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI自动化平台 v2.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --bg: #0a0a0a; --surface: #141414; --border: #222; --text: #e5e5e5; --text-2: #888; --accent: #3b82f6; --success: #22c55e; }
        body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }
        .container { max-width: 1000px; margin: 0 auto; padding: 2rem; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .subtitle { color: var(--text-2); margin-bottom: 2rem; }
        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
        .section h2 { margin-bottom: 1rem; }
        .template-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
        .template-card { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; cursor: pointer; transition: border-color 0.2s; }
        .template-card:hover { border-color: var(--accent); }
        .template-card h3 { margin-bottom: 0.3rem; }
        .template-card p { font-size: 0.85rem; color: var(--text-2); }
        .template-card .steps { font-size: 0.8rem; color: var(--accent); margin-top: 0.5rem; }
        button { padding: 0.8rem 2rem; background: var(--accent); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; }
        button:hover { background: #2563eb; }
        select, input, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; color: var(--text); margin-bottom: 1rem; font-family: inherit; }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
        .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: var(--text-2); }
        .tab.active { background: var(--accent); border-color: var(--accent); color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .exec-item { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; }
        .status { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; }
        .status-success { background: rgba(34,197,94,0.2); color: var(--success); }
        .status-error { background: rgba(239,68,68,0.2); color: #ef4444; }
        .status-running { background: rgba(59,130,246,0.2); color: var(--accent); }
        .step-result { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; }
        .step-result .step-name { font-weight: 600; margin-bottom: 0.5rem; }
        .step-result .step-output { font-size: 0.9rem; color: var(--text-2); white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI自动化平台 v2.0</h1>
        <p class="subtitle">可视化AI流水线编排，多步骤自动化处理</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('templates')">📦 流水线模板</div>
            <div class="tab" onclick="switchTab('run')">▶️ 执行流水线</div>
            <div class="tab" onclick="switchTab('history')">📋 执行历史</div>
        </div>

        <div id="tab-templates" class="tab-content active">
            <div class="section">
                <h2>选择流水线模板</h2>
                <div class="template-grid" id="templates"></div>
            </div>
        </div>

        <div id="tab-run" class="tab-content">
            <div class="section">
                <h2>执行流水线</h2>
                <label>选择流水线</label>
                <select id="pipeline-select">
                    <option value="">选择流水线</option>
                </select>
                <label>输入数据</label>
                <textarea id="input-data" placeholder="输入数据（可选）" rows="4"></textarea>
                <button onclick="runPipeline()">执行</button>
                <div id="result"></div>
            </div>
        </div>

        <div id="tab-history" class="tab-content">
            <div class="section">
                <h2>执行历史</h2>
                <div id="history-list">加载中...</div>
            </div>
        </div>
    </div>

    <script>
        const templates = """ + json.dumps(TEMPLATES, ensure_ascii=False) + """;

        function switchTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-'+name).classList.add('active');
            if (name === 'history') loadHistory();
        }

        const grid = document.getElementById('templates');
        const select = document.getElementById('pipeline-select');

        Object.entries(templates).forEach(([key, t]) => {
            grid.innerHTML += '<div class="template-card" onclick="selectTemplate(\\''+key+'\\')">' +
                '<h3>'+t.name+'</h3>' +
                '<p>'+t.description+'</p>' +
                '<div class="steps">步骤：'+t.steps.map(s => s.name).join(' → ')+'</div>' +
                '</div>';
            select.innerHTML += '<option value="'+key+'">'+t.name+'</option>';
        });

        function selectTemplate(key) {
            select.value = key;
            document.querySelectorAll('.tab')[1].click();
        }

        async function runPipeline() {
            const val = select.value;
            const input = document.getElementById('input-data').value;
            const resultDiv = document.getElementById('result');
            if (!val) { alert('请选择流水线'); return; }
            resultDiv.innerHTML = '<p style="color:var(--text-2)">执行中...</p>';
            try {
                const resp = await fetch('/api/pipeline/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({template_key: val, input_data: input})
                });
                const data = await resp.json();
                if (data.status === 'error') { resultDiv.innerHTML = '<p style="color:red">错误：'+data.message+'</p>'; return; }
                let html = '<div style="margin-bottom:1rem"><span class="status status-'+data.data.status+'">'+data.data.status+'</span> | 执行ID: '+data.data.execution_id+'</div>';
                data.data.results.forEach(r => {
                    html += '<div class="step-result"><div class="step-name">'+r.step+'</div><div class="step-output">'+r.output+'</div></div>';
                });
                resultDiv.innerHTML = html;
            } catch(e) { resultDiv.innerHTML = '<p style="color:red">错误：'+e.message+'</p>'; }
        }

        async function loadHistory() {
            try {
                const resp = await fetch('/api/executions');
                const json = await resp.json();
                const div = document.getElementById('history-list');
                if (!json.data || json.data.length === 0) { div.innerHTML = '<p style="color:var(--text-2)">暂无执行记录</p>'; return; }
                div.innerHTML = json.data.map(item =>
                    '<div class="exec-item">' +
                    '<div><span class="status status-'+item.status+'">'+item.status+'</span> | ' +
                    item.pipeline_name + ' | ' + item.started_at + '</div>' +
                    '<div style="font-size:0.85rem;color:var(--text-2);margin-top:0.5rem">步骤：' + item.steps_completed + '/' + item.total_steps + '</div>' +
                    '</div>'
                ).join('');
            } catch(e) { document.getElementById('history-list').innerHTML = '<p style="color:red">加载失败</p>'; }
        }
    </script>
</body>
</html>"""


@app.get("/api/templates")
async def get_templates():
    return to_json_response(TEMPLATES)


@app.post("/api/pipeline/run")
async def run_pipeline(data: dict):
    template_key = data.get("template_key", "")
    input_data = data.get("input_data", "")

    if template_key not in TEMPLATES:
        raise HTTPException(status_code=404, detail="模板不存在")

    template = TEMPLATES[template_key]
    try:
        result = await execute_pipeline(0, template["name"], template["steps"], input_data)
        return to_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/executions")
async def get_executions():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM executions ORDER BY id DESC LIMIT 50").fetchall()
    return to_json_response([dict(r) for r in rows])


@app.get("/api/stats")
async def get_stats():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
        success = conn.execute("SELECT COUNT(*) FROM executions WHERE status='success'").fetchone()[0]
    return to_json_response({"total": total, "success": success, "error": total - success})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
