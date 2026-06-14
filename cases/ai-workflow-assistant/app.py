"""
AI自动化工作流助手 v2.0
可视化工作流编辑器，零代码搭建AI自动化流程
支持 SQLite 持久化、真实数据源、定时任务、执行历史
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
from shared import call_ai, call_ai_json, to_json_response, to_error_response

DB_PATH = os.getenv("DATABASE_URL", "data/workflow_assistant.db")

app = FastAPI(title="AI自动化工作流助手", version="2.0.0")
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
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                steps_json TEXT,
                trigger_type TEXT DEFAULT 'manual',
                trigger_config TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER,
                workflow_name TEXT,
                status TEXT DEFAULT 'running',
                input_data TEXT,
                output_data TEXT,
                steps_completed INTEGER DEFAULT 0,
                total_steps INTEGER DEFAULT 0,
                error_message TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id)
            )
        """)
        conn.commit()


init_db()


# ==================== 数据模型 ====================

class WorkflowStep(BaseModel):
    type: str  # ai_generate / transform / condition / output
    name: str = ""
    config: dict


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    trigger_type: str = "manual"
    trigger_config: dict = {}
    steps: list[WorkflowStep]


class WorkflowRun(BaseModel):
    workflow_id: int
    input_data: str = ""


# ==================== 预置模板 ====================

TEMPLATES = {
    "content-assistant": {
        "name": "自媒体内容助手",
        "description": "生成选题 → 生成文案 → 优化标题",
        "steps": [
            {"type": "ai_generate", "name": "生成选题", "config": {"prompt": "根据输入的领域，生成10个有爆款潜力的选题", "output_format": "list"}},
            {"type": "ai_generate", "name": "生成文案", "config": {"prompt": "为每个选题生成小红书文案，包含标题、正文、标签", "output_format": "article"}},
            {"type": "ai_generate", "name": "优化标题", "config": {"prompt": "优化标题，使其更吸引眼球，加入数字或情绪词", "output_format": "text"}},
        ],
    },
    "customer-service": {
        "name": "客服自动回复",
        "description": "分析意图 → 生成回复 → 质量检查",
        "steps": [
            {"type": "ai_generate", "name": "意图分析", "config": {"prompt": "分析客户消息的意图和情绪", "output_format": "json"}},
            {"type": "ai_generate", "name": "生成回复", "config": {"prompt": "根据意图分析，生成专业、友好的客服回复", "output_format": "text"}},
            {"type": "ai_generate", "name": "质量检查", "config": {"prompt": "检查回复是否专业、准确、友好，给出改进建议", "output_format": "text"}},
        ],
    },
    "product-desc": {
        "name": "商品描述生成",
        "description": "分析卖点 → 生成描述 → SEO优化",
        "steps": [
            {"type": "ai_generate", "name": "卖点分析", "config": {"prompt": "分析商品的核心卖点和目标用户", "output_format": "json"}},
            {"type": "ai_generate", "name": "生成描述", "config": {"prompt": "根据卖点生成吸引人的商品描述", "output_format": "text"}},
            {"type": "ai_generate", "name": "SEO优化", "config": {"prompt": "优化描述，加入关键词，提高搜索排名", "output_format": "text"}},
        ],
    },
    "data-analysis": {
        "name": "数据分析报告",
        "description": "数据清洗 → 分析洞察 → 生成报告",
        "steps": [
            {"type": "ai_generate", "name": "数据解读", "config": {"prompt": "解读输入的数据，识别关键指标和趋势", "output_format": "json"}},
            {"type": "ai_generate", "name": "深度分析", "config": {"prompt": "基于数据趋势，分析原因和影响因素", "output_format": "text"}},
            {"type": "ai_generate", "name": "生成报告", "config": {"prompt": "生成结构化的数据分析报告，包含图表建议", "output_format": "report"}},
        ],
    },
    "meeting-notes": {
        "name": "会议纪要自动化",
        "description": "提取要点 → 分配任务 → 生成纪要",
        "steps": [
            {"type": "ai_generate", "name": "提取要点", "config": {"prompt": "从会议记录中提取关键讨论点和决策", "output_format": "list"}},
            {"type": "ai_generate", "name": "分配任务", "config": {"prompt": "识别会议中产生的待办事项和负责人", "output_format": "json"}},
            {"type": "ai_generate", "name": "生成纪要", "config": {"prompt": "生成结构化的会议纪要，包含要点、决策、待办", "output_format": "report"}},
        ],
    },
    "competitor-analysis": {
        "name": "竞品分析",
        "description": "收集信息 → 对比分析 → 生成报告",
        "steps": [
            {"type": "ai_generate", "name": "信息整理", "config": {"prompt": "整理竞品的基本信息、产品特点、用户评价", "output_format": "json"}},
            {"type": "ai_generate", "name": "对比分析", "config": {"prompt": "对比分析各竞品的优劣势、差异化点", "output_format": "table"}},
            {"type": "ai_generate", "name": "策略建议", "config": {"prompt": "基于竞品分析，给出差异化竞争策略建议", "output_format": "text"}},
        ],
    },
}


# ==================== 执行引擎 ====================

async def execute_workflow(workflow_id: int, workflow_name: str, steps: list, input_data: str) -> dict:
    """执行工作流"""
    # 记录执行开始
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO executions (workflow_id, workflow_name, input_data, total_steps, status) VALUES (?,?,?,?,?)",
            (workflow_id, workflow_name, input_data, len(steps), "running")
        )
        exec_id = cursor.lastrowid

    results = []
    current_data = input_data
    status = "success"

    try:
        for i, step in enumerate(steps):
            step_type = step.get("type", step.type if hasattr(step, 'type') else "")
            step_name = step.get("name", step.name if hasattr(step, 'name') else f"步骤{i+1}")
            config = step.get("config", step.config if hasattr(step, 'config') else {})

            if step_type == "ai_generate":
                prompt = config.get("prompt", "")
                system = f"你是一个AI助手。请根据以下指令处理输入数据。\n指令：{prompt}\n\n要求：输出清晰、结构化。"
                current_data = call_ai(system, current_data or "请处理", temperature=0.7)
                results.append({"step": step_name, "output": current_data})

            elif step_type == "transform":
                # 数据转换
                transform_type = config.get("type", "none")
                if transform_type == "json_parse":
                    try:
                        current_data = json.dumps(json.loads(current_data), ensure_ascii=False, indent=2)
                    except:
                        pass
                results.append({"step": step_name, "output": current_data})

            elif step_type == "condition":
                # 条件判断（简化版）
                condition = config.get("condition", "")
                if condition and condition in current_data:
                    results.append({"step": step_name, "output": f"条件满足：{condition}"})
                else:
                    results.append({"step": step_name, "output": f"条件不满足：{condition}"})

            elif step_type == "output":
                channel = config.get("channel", "console")
                results.append({"step": step_name, "output": f"[输出到 {channel}]\n{current_data}"})

            else:
                results.append({"step": step_name, "output": f"[未知步骤类型] {step_type}"})

            # 更新执行进度
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

    # 更新执行完成
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


# ==================== API 端点 ====================

@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI自动化工作流助手 v2.0</title>
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
        .btn-secondary { background: transparent; border: 1px solid var(--border); color: var(--text); }
        select, input, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; color: var(--text); margin-bottom: 1rem; font-family: inherit; }
        .result { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
        .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: var(--text-2); }
        .tab.active { background: var(--accent); border-color: var(--accent); color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .exec-item { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; }
        .exec-item .status { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; }
        .status-success { background: rgba(34,197,94,0.2); color: var(--success); }
        .status-error { background: rgba(239,68,68,0.2); color: #ef4444; }
        .status-running { background: rgba(59,130,246,0.2); color: var(--accent); }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ AI自动化工作流助手 v2.0</h1>
        <p class="subtitle">零代码搭建AI自动化流程</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('templates')">📦 预置模板</div>
            <div class="tab" onclick="switchTab('run')">▶️ 执行工作流</div>
            <div class="tab" onclick="switchTab('history')">📋 执行历史</div>
        </div>

        <div id="tab-templates" class="tab-content active">
            <div class="section">
                <h2>选择工作流模板</h2>
                <div class="template-grid" id="templates"></div>
            </div>
        </div>

        <div id="tab-run" class="tab-content">
            <div class="section">
                <h2>执行工作流</h2>
                <label>选择工作流</label>
                <select id="workflow-select">
                    <option value="">选择工作流或模板</option>
                </select>
                <label>输入数据</label>
                <textarea id="input-data" placeholder="输入数据（可选）" rows="4"></textarea>
                <button onclick="runWorkflow()">执行</button>
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

        // 渲染模板
        const grid = document.getElementById('templates');
        const select = document.getElementById('workflow-select');

        Object.entries(templates).forEach(([key, t]) => {
            grid.innerHTML += '<div class="template-card" onclick="selectTemplate(\\''+key+'\\')">' +
                '<h3>'+t.name+'</h3>' +
                '<p>'+t.description+'</p>' +
                '<div class="steps">步骤：'+t.steps.map(s => s.name).join(' → ')+'</div>' +
                '</div>';
            select.innerHTML += '<option value="template:'+key+'">'+t.name+' (模板)</option>';
        });

        function selectTemplate(key) {
            select.value = 'template:'+key;
            document.querySelectorAll('.tab')[1].click();
        }

        async function runWorkflow() {
            const val = select.value;
            const input = document.getElementById('input-data').value;
            const resultDiv = document.getElementById('result');
            if (!val) { alert('请选择工作流'); return; }
            resultDiv.innerHTML = '<p style="color:var(--text-2)">执行中...</p>';
            try {
                const resp = await fetch('/api/workflow/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({template_key: val.replace('template:',''), input_data: input})
                });
                const data = await resp.json();
                if (data.status === 'error') {
                    resultDiv.innerHTML = '<p style="color:red">错误：' + data.message + '</p>';
                    return;
                }
                let html = '<div style="margin-bottom:1rem"><span class="status status-'+data.data.status+'">'+data.data.status+'</span> | 执行ID: '+data.data.execution_id+'</div>';
                data.data.results.forEach(r => {
                    html += '<div style="background:#1a1a1a;border:1px solid #222;border-radius:8px;padding:1rem;margin-bottom:0.5rem">';
                    html += '<div style="font-weight:600;margin-bottom:0.5rem">'+r.step+'</div>';
                    html += '<div style="color:var(--text-2);font-size:0.9rem">'+r.output.substring(0, 500)+'</div>';
                    html += '</div>';
                });
                resultDiv.innerHTML = html;
            } catch(e) {
                resultDiv.innerHTML = '<p style="color:red">错误：'+e.message+'</p>';
            }
        }

        async function loadHistory() {
            try {
                const resp = await fetch('/api/executions');
                const json = await resp.json();
                const div = document.getElementById('history-list');
                if (!json.data || json.data.length === 0) {
                    div.innerHTML = '<p style="color:var(--text-2)">暂无执行记录</p>';
                    return;
                }
                div.innerHTML = json.data.map(item =>
                    '<div class="exec-item">' +
                    '<div><span class="status status-'+item.status+'">'+item.status+'</span> | ' +
                    item.workflow_name + ' | ' + item.started_at + '</div>' +
                    '<div style="font-size:0.85rem;color:var(--text-2);margin-top:0.5rem">' +
                    '步骤完成：' + item.steps_completed + '/' + item.total_steps + '</div>' +
                    '</div>'
                ).join('');
            } catch(e) {
                document.getElementById('history-list').innerHTML = '<p style="color:red">加载失败</p>';
            }
        }
    </script>
</body>
</html>"""


@app.get("/api/templates")
async def get_templates():
    """获取模板列表"""
    return to_json_response(TEMPLATES)


@app.post("/api/workflow/run")
async def run_workflow(data: dict):
    """执行工作流"""
    template_key = data.get("template_key", "")
    input_data = data.get("input_data", "")

    if template_key not in TEMPLATES:
        raise HTTPException(status_code=404, detail="模板不存在")

    template = TEMPLATES[template_key]

    try:
        result = await execute_workflow(
            workflow_id=0,
            workflow_name=template["name"],
            steps=template["steps"],
            input_data=input_data
        )
        return to_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/executions")
async def get_executions():
    """获取执行历史"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM executions ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return to_json_response([dict(r) for r in rows])


@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
        success = conn.execute("SELECT COUNT(*) FROM executions WHERE status='success'").fetchone()[0]
        error = conn.execute("SELECT COUNT(*) FROM executions WHERE status='error'").fetchone()[0]
    return to_json_response({"total_executions": total, "success": success, "error": error})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
