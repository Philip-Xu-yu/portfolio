"""
深度案例3：AI自动化工作流平台
可视化编辑、定时触发、多渠道输出、预置模板
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
import json
from datetime import datetime

app = FastAPI(title="AI自动化工作流平台")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
scheduler = AsyncIOScheduler()

# 存储
workflows = {}
execution_logs = []


TEMPLATES = {
    "content-assistant": {
        "name": "自媒体内容助手",
        "desc": "自动抓取热点、生成选题、生成文案",
        "steps": [
            {"type": "fetch", "config": {"source": "hot_topics"}},
            {"type": "ai", "config": {"prompt": "生成10个选题"}},
            {"type": "ai", "config": {"prompt": "为每个选题生成文案"}},
            {"type": "output", "config": {"channel": "console"}},
        ],
    },
    "customer-service": {
        "name": "客服自动回复",
        "desc": "接收消息、AI判断、生成回复",
        "steps": [
            {"type": "ai", "config": {"prompt": "判断意图并生成回复"}},
            {"type": "output", "config": {"channel": "console"}},
        ],
    },
    "daily-report": {
        "name": "数据日报",
        "desc": "拉取数据、AI分析、生成报告",
        "steps": [
            {"type": "fetch", "config": {"source": "analytics"}},
            {"type": "ai", "config": {"prompt": "分析数据生成日报"}},
            {"type": "output", "config": {"channel": "console"}},
        ],
    },
    "email-classifier": {
        "name": "邮件分类",
        "desc": "接收邮件、AI分类、标记优先级",
        "steps": [
            {"type": "fetch", "config": {"source": "email"}},
            {"type": "ai", "config": {"prompt": "分类邮件标记优先级"}},
            {"type": "output", "config": {"channel": "console"}},
        ],
    },
    "product-desc": {
        "name": "商品描述",
        "desc": "读取商品信息、AI生成描述",
        "steps": [
            {"type": "fetch", "config": {"source": "product"}},
            {"type": "ai", "config": {"prompt": "生成商品描述"}},
            {"type": "output", "config": {"channel": "console"}},
        ],
    },
    "meeting-notes": {
        "name": "会议纪要",
        "desc": "录音转文字、AI提取要点",
        "steps": [
            {"type": "fetch", "config": {"source": "transcript"}},
            {"type": "ai", "config": {"prompt": "提取会议要点生成纪要"}},
            {"type": "output", "config": {"channel": "console"}},
        ],
    },
}


async def execute_step(step: dict, input_data: str) -> str:
    step_type = step["type"]
    config = step["config"]

    if step_type == "fetch":
        return f"[数据采集] 来源: {config.get('source', 'unknown')}\n模拟采集到的数据..."

    elif step_type == "ai":
        prompt = config.get("prompt", "")
        system = f"你是一个AI助手。请根据以下指令处理输入数据。\n指令：{prompt}"
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": input_data or "请处理"},
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[AI错误] {str(e)}"

    elif step_type == "output":
        channel = config.get("channel", "console")
        return f"[输出到 {channel}]\n{input_data}"

    return f"[未知步骤] {step_type}"


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>AI自动化工作流平台</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: system-ui, sans-serif; background: #0a0a0a; color: #e5e5e5; }
            .container { max-width: 900px; margin: 0 auto; padding: 2rem; }
            h1 { font-size: 2rem; margin-bottom: 0.5rem; }
            .subtitle { color: #888; margin-bottom: 2rem; }
            .section { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
            .section h2 { margin-bottom: 1rem; }
            .template-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; }
            .template-card { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1rem; cursor: pointer; }
            .template-card:hover { border-color: #3b82f6; }
            .template-card h3 { margin-bottom: 0.3rem; font-size: 1rem; }
            .template-card p { font-size: 0.85rem; color: #888; }
            .workflow-vis { display: flex; flex-direction: column; gap: 0.5rem; margin: 1rem 0; }
            .wf-node { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 0.8rem 1rem; display: flex; align-items: center; gap: 0.8rem; }
            .wf-node .icon { font-size: 1.2rem; }
            .wf-node .info .name { font-weight: 600; font-size: 0.9rem; }
            .wf-node .info .desc { font-size: 0.8rem; color: #888; }
            .wf-arrow { text-align: center; color: #555; }
            select { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e5e5e5; margin-bottom: 1rem; }
            textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e5e5e5; margin-bottom: 1rem; font-family: inherit; min-height: 80px; }
            button { padding: 0.8rem 2rem; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; }
            .result { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; line-height: 1.8; font-size: 0.9rem; }
            .log-item { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 0.8rem; margin-bottom: 0.5rem; font-size: 0.85rem; }
            .log-item .time { color: #888; font-size: 0.75rem; }
            .log-item .status { color: #22c55e; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AI自动化工作流平台</h1>
            <p class="subtitle">零代码搭建AI自动化流程</p>

            <div class="section">
                <h2>预置模板</h2>
                <div class="template-grid" id="templates"></div>
            </div>

            <div class="section">
                <h2>工作流可视化</h2>
                <select id="wf-select" onchange="showWorkflow()">
                    <option value="">选择模板查看流程</option>
                </select>
                <div id="wf-visual"></div>
            </div>

            <div class="section">
                <h2>执行工作流</h2>
                <textarea id="input-data" placeholder="输入数据（可选）"></textarea>
                <button onclick="runWorkflow()">执行</button>
                <div id="run-result"></div>
            </div>

            <div class="section">
                <h2>执行日志</h2>
                <div id="logs"></div>
            </div>
        </div>

        <script>
            const templates = """ + json.dumps(TEMPLATES, ensure_ascii=False) + """;

            const grid = document.getElementById('templates');
            const select = document.getElementById('wf-select');

            Object.entries(templates).forEach(([key, t]) => {
                grid.innerHTML += '<div class="template-card" onclick="selectTemplate(\\''+key+'\\')"><h3>'+t.name+'</h3><p>'+t.desc+'</p></div>';
                select.innerHTML += '<option value="'+key+'">'+t.name+'</option>';
            });

            function selectTemplate(key) {
                select.value = key;
                showWorkflow();
            }

            function showWorkflow() {
                const key = select.value;
                if (!key) return;
                const t = templates[key];
                const icons = {fetch:'📥',ai:'🤖',output:'📤'};
                let html = '<div class="workflow-vis">';
                t.steps.forEach((s, i) => {
                    if (i > 0) html += '<div class="wf-arrow">↓</div>';
                    html += '<div class="wf-node"><div class="icon">'+(icons[s.type]||'⚙️')+'</div><div class="info"><div class="name">'+s.type+'</div><div class="desc">'+JSON.stringify(s.config)+'</div></div></div>';
                });
                html += '</div>';
                document.getElementById('wf-visual').innerHTML = html;
            }

            async function runWorkflow() {
                const key = select.value;
                if (!key) { alert('请先选择模板'); return; }
                const input = document.getElementById('input-data').value;
                const div = document.getElementById('run-result');
                div.innerHTML = '<div class="result">执行中...</div>';
                try {
                    const resp = await fetch('/api/run', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({template_key: key, input_data: input})
                    });
                    const data = await resp.json();
                    div.innerHTML = '<div class="result">' + data.result.replace(/\\n/g, '<br>') + '</div>';
                    loadLogs();
                } catch(e) {
                    div.innerHTML = '<p style="color:red">错误：'+e.message+'</p>';
                }
            }

            async function loadLogs() {
                const resp = await fetch('/api/logs');
                const data = await resp.json();
                document.getElementById('logs').innerHTML = data.logs.map(l =>
                    '<div class="log-item"><span class="time">'+l.time+'</span> — <span class="status">'+l.status+'</span> — '+l.workflow+' ('+l.steps+'步)</div>'
                ).reverse().join('');
            }

            loadLogs();
        </script>
    </body>
    </html>
    """


@app.post("/api/run")
async def run_workflow(data: dict):
    template_key = data.get("template_key", "")
    input_data = data.get("input_data", "")

    if template_key not in TEMPLATES:
        raise HTTPException(status_code=404, detail="模板不存在")

    template = TEMPLATES[template_key]
    results = []

    for step in template["steps"]:
        result = await execute_step(step, input_data)
        results.append(result)
        input_data = result

    log = {
        "workflow": template["name"],
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "steps": len(results),
        "status": "成功",
    }
    execution_logs.append(log)

    return {"result": "\n\n---\n\n".join(results), "log": log}


@app.get("/api/logs")
async def get_logs():
    return {"logs": execution_logs[-20:]}


@app.get("/api/templates")
async def get_templates():
    return {"templates": TEMPLATES}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
