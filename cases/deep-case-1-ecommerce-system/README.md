# AI电商客服系统

> 完整电商客服解决方案

## ✨ v2.0 新特性

- **SQLite 持久化** - 数据重启不丢失
- **结构化 JSON 输出** - 分析结果可量化
- **历史记录** - 查看之前的生成/分析记录
- **统一 API 格式** - 标准化的请求/响应格式
- **错误重试** - 自动重试失败的 AI 调用
- **内存缓存** - 相同请求不重复调用 AI

## 功能

- 智能客服对话
- 知识库管理（分类/CRUD）
- 用户意图分析
- 对话历史记录
- 数据统计面板

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

### 3. 启动服务

```bash
python app.py
```

访问 http://localhost:8000 查看应用

## API 文档

启动后访问 http://localhost:8000/docs 查看 API 文档

## 技术栈

- **后端**: FastAPI + SQLite
- **AI**: OpenAI 兼容 API（支持多种模型）
- **部署**: 支持 Docker / Render / Railway

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| AI_BASE_URL | AI API 地址 | https://token-plan-cn.xiaomimimo.com/v1 |
| AI_API_KEY | AI API Key | - |
| AI_MODEL | 模型名称 | mimo-v2.5-pro |
| DATABASE_URL | 数据库路径 | data/app.db |
| PORT | 服务端口 | 8000 |

## License

MIT
