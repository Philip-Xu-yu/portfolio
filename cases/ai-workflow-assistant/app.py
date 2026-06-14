"""
AI自动化工作流助手
可视化工作流编辑器，零代码搭建AI自动化流程
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
import json
from typing import Optional
from datetime import datetime

app = FastAPI(title="AI自动化工作流助手")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
scheduler = AsyncIOScheduler()

# 内存存储
workflows = {}
execution_logs = []


class WorkflowStep(BaseModel):
    type: str  # fetch / ai_generate / output
    config: dict


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    trigger_type: str = "manual"  # manual / cron / webhook
    trigger_config: dict = {}
    steps: list[WorkflowStep]


class WorkflowRun(BaseModel):
    input_data: str = ""


# 预置模板
TEMPLATES = {
    "content-assistant": {
        "name": "自媒体内容助手",
        "description": "自动抓取热点、生成选题、生成文案",
        "steps": [
            {"type": "fetch", "config": {"source": "hot_topics"}},
            {"type": "ai_generate", "config": {"prompt": "根据热点生成10个选题", "output_format": "list"}},
            {"type": "ai_generate", "config": {"prompt": "为每个选题生成小红书文案", "output_format": "article"}},
            {"type": "output", "config": {"channel": "console"}},
        ],
    },
    "customer-service": {
        "name": "客服自动回复",
        "description": "接收消息、AI判断意图、生成回复",
        "steps": [
            {"type": "ai_generate", "config": {"prompt": "判断客户消息意图并生成回复", "context": "product_faq"}},
            {"type": "output", "config": {"channel": "console"}},
        ],
    },
    "daily-report": {
        "name": "数据日报生成",
        "description": "定时拉取数据、AI分析、生成报告",
        "steps": [
            {"type": "fetch", "config": {"source": "analytics"}},
            {"type": "ai_generate", "config": {"prompt": "分析数据并生成日报", "output_format": "report"}},
            {"type": "output", "config": {"channel": "feishu"}},
        ],
    },
    "email-classifier": {
        "name": "邮件自动分类",
        "description": "接收邮件、AI分类、标记优先级",
        "steps": [
            {"type": "fetch", "config": {"source": "email"}},
            {"type": "ai_generate", "config": {"prompt": "分类邮件并标记优先级", "categories": ["urgent", "normal", "spam"]}},
            {"type": "output", "config": {"channel": "email_label"}},
        ],
    },
    "product-desc": {
        "name": "商品描述生成",
        "description": "读取商品信息、AI生成描述、批量输出",
        "steps": [
            {"type": "fetch", "config": {"source": "product_info"}},
            {"type": "ai_generate", "config": {"prompt": "生成商品描述", "style": "selling"}},
            {"type": "output", "config": {"channel": "file"}},
        ],
    },
    "meeting-notes": {
        "name": "会议纪要自动化",
        "description": "录音转文字、AI提取要点、生成纪要",
        "steps": [
            {"type": "fetch", "config": {"source": "transcript"}},
            {"type": "ai_generate", "config": {"prompt": "提取会议要点并生成纪要", "format": "structured"}},
            {"type": "output", "config": {"channel": "feishu"}},
        ],
    },
}


async def execute_step(step: dict, input_data: str) -> str:
    """执行单个工作流步骤"""
    step_type = step["type"]
    config = step["config"]

    if step_type == "fetch":
        return f"[数据采集] 来源: {config.get('source', 'unknown')}\n模拟采集到的数据..."

    elif step_type == "ai_generate":
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
            return f"[AI处理错误] {str(e)}"

    elif step_type == "output":
        channel = config.get("channel", "console")
        return f"[输出到 {channel}]\n{input_data}"

    return f"[未知步骤类型] {step_type}"


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>AI自动化工作流助手</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: system-ui, sans-serif; background: #0a0a0a; color: #e5e5e5; padding: 2rem; max-width: 900px; margin: 0 auto; }
            h1 { font-size: 2rem; margin-bottom: 0.5rem; }
            .subtitle { color: #888; margin-bottom: 2rem; }
            .section { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
            .section h2 { margin-bottom: 1rem; }
            .template-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; }
            .template-card { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1rem; cursor: pointer; }
            .template-card:hover { border-color: #3b82f6; }
            .template-card h3 { margin-bottom: 0.3rem; }
            .template-card p { font-size: 0.85rem; color: #888; }
            button { padding: 0.8rem 2rem; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; }
            .result { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; }
            select, input, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e5e5e5; margin-bottom: 1rem; font-family: inherit; }
        </style>
    </head>
    <body>
        <h1>AI自动化工作流助手</h1>
        <p class="subtitle">零代码搭建AI自动化流程</p>

        <div class="section">
            <h2>预置模板</h2>
            <div class="template-grid" id="templates"></div>
        </div>

        <div class="section">
            <h2>执行工作流</h2>
            <select id="workflow-select">
                <option value="">选择工作流或模板</option>
            </select>
            <textarea id="input-data" placeholder="输入数据（可选）" rows="3"></textarea>
            <button onclick="runWorkflow()">执行</button>
            <div id="result"></div>
        </div>

        <script>
            const templates = """ + json.dumps(TEMPLATES, ensure_ascii=False) + """;

            const grid = document.getElementById('templates');
            const select = document.getElementById('workflow-select');

            Object.entries(templates).forEach(([key, t]) => {
                grid.innerHTML += '<div class="template-card" onclick="selectTemplate(\\''+key+'\\')"><h3>'+t.name+'</h3><p>'+t.description+'</p></div>';
                select.innerHTML += '<option value="template:'+key+'">'+t.name+' (模板)</option>';
            });

            function selectTemplate(key) {
                select.value = 'template:'+key;
            }

            async function runWorkflow() {
                const val = select.value;
                const input = document.getElementById('input-data').value;
                const resultDiv = document.getElementById('result');
                if (!val) { alert('请选择工作流'); return; }
                resultDiv.innerHTML = '执行中...';
                try {
                    const resp = await fetch('/api/workflow/run', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({template_key: val.replace('template:',''), input_data: input})
                    });
                    const data = await resp.json();
                    resultDiv.innerHTML = '<div class="result">' + data.result.replace(/\\n/g, '<br>') + '</div>';
                } catch(e) {
                    resultDiv.innerHTML = '<p style="color:red">错误：'+e.message+'</p>';
                }
            }
        </script>
    </body>
    </html>
    """


@app.get("/api/templates")
async def get_templates():
    return {"templates": TEMPLATES}


@app.post("/api/workflow/run")
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
        input_data = result  # 上一步的输出作为下一步的输入

    log = {
        "workflow": template["name"],
        "time": datetime.now().isoformat(),
        "steps": len(results),
        "status": "success",
    }
    execution_logs.append(log)

    return {"result": "\n\n---\n\n".join(results), "log": log}


@app.get("/api/logs")
async def get_logs():
    return {"logs": execution_logs[-20:]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
