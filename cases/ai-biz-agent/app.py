"""
AI商业机会分析Agent
输入行业和条件，AI自动输出市场分析、竞品对比、商业模式画布和行动建议
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI(title="AI商业机会分析Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


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


def call_ai(system: str, user: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>AI商业机会分析Agent</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: system-ui, sans-serif; background: #0a0a0a; color: #e5e5e5; }
            .container { max-width: 800px; margin: 0 auto; padding: 2rem; }
            h1 { font-size: 2rem; margin-bottom: 0.5rem; }
            .subtitle { color: #888; margin-bottom: 2rem; }
            .section { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
            .section h2 { margin-bottom: 1rem; }
            label { display: block; font-size: 0.9rem; color: #888; margin-bottom: 0.3rem; }
            input, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e5e5e5; font-size: 1rem; margin-bottom: 1rem; font-family: inherit; }
            textarea { min-height: 60px; resize: vertical; }
            button { padding: 0.8rem 2rem; background: #3b82f6; color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
            button:hover { background: #2563eb; }
            .result { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; line-height: 1.8; }
            .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
            .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; cursor: pointer; font-size: 0.9rem; }
            .tab.active { background: #3b82f6; border-color: #3b82f6; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AI商业机会分析Agent</h1>
            <p class="subtitle">输入行业和想法，AI帮你分析商业机会</p>

            <div class="tabs">
                <div class="tab active" onclick="switchTab('market')">市场分析</div>
                <div class="tab" onclick="switchTab('competitor')">竞品分析</div>
                <div class="tab" onclick="switchTab('canvas')">商业画布</div>
                <div class="tab" onclick="switchTab('plan')">行动计划</div>
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
        </div>

        <script>
            function switchTab(name) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById('tab-'+name).classList.add('active');
            }

            async function analyze(type) {
                const resultDiv = document.getElementById('r-'+type);
                resultDiv.innerHTML = '<div class="result">分析中...</div>';

                let data = {};
                let endpoint = '';

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
                    resultDiv.innerHTML = '<div class="result">' + json.result.replace(/\\n/g, '<br>') + '</div>';
                } catch(e) {
                    resultDiv.innerHTML = '<p style="color:red">错误：'+e.message+'</p>';
                }
            }
        </script>
    </body>
    </html>
    """


@app.post("/api/market")
async def market_analysis(req: MarketRequest):
    system = """你是一个商业分析师。请分析用户提供的行业市场机会。
输出格式：
1. 市场概况（规模、增长率、驱动因素）
2. 目标用户画像（痛点、需求、行为）
3. 机会点（具体的机会方向）
4. 风险提示
5. 机会评分（5个维度各1-10分）
请使用emoji和清晰的格式。"""
    user = f"行业：{req.industry}\n目标用户：{req.target_user}\n预算：{req.budget}"
    result = call_ai(system, user)
    return {"result": result}


@app.post("/api/competitor")
async def competitor_analysis(req: CompetitorRequest):
    system = """你是一个竞品分析专家。请对比分析用户提供的竞品。
输出格式：
1. 竞品对比表格（功能、用户规模、营收模式、优劣势）
2. 差异化机会
3. 建议切入点
请使用表格和清晰的格式。"""
    user = f"竞品：{', '.join(req.competitors)}\n行业：{req.industry}"
    result = call_ai(system, user)
    return {"result": result}


@app.post("/api/canvas")
async def business_canvas(req: CanvasRequest):
    system = """你是一个商业模式设计专家。请根据用户的想法生成商业模式画布。
输出标准9格画布：
1. 关键合作伙伴
2. 关键活动
3. 核心资源
4. 价值主张
5. 客户关系
6. 渠道
7. 目标客户
8. 成本结构
9. 收入来源
请使用清晰的格式。"""
    user = f"行业：{req.industry}\n想法：{req.idea}\n目标用户：{req.target_user}"
    result = call_ai(system, user)
    return {"result": result}


@app.post("/api/action-plan")
async def action_plan(req: ActionPlanRequest):
    system = """你是一个创业导师。请根据用户的想法制定30天行动计划。
输出格式：
- 第1周：验证需求（具体任务+预算）
- 第2周：搭建MVP（具体任务+预算）
- 第3周：小范围测试（具体任务+预算）
- 第4周：规模化（具体任务+预算）
每周包含具体任务清单和里程碑目标。"""
    user = f"行业：{req.industry}\n想法：{req.idea}\n预算：{req.budget}"
    result = call_ai(system, user)
    return {"result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
