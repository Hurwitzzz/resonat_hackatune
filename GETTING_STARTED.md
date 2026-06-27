# 启动指南 — Cochlea

团队怎么把项目跑起来。挑战说明在 [README.md](README.md) / [CHALLENGE.md](CHALLENGE.md)，产品设计在 [PRD-night.md](PRD-night.md)。

## 技术栈

| 部分 | 技术 | 端口 | 包管理 |
|------|------|------|--------|
| 后端 | Python 3.13 + FastAPI | `:8000` | [uv](https://docs.astral.sh/uv/)（管 `backend/.venv`） |
| 前端 | React + TypeScript + Vite | `:5173` | npm（管 `frontend/node_modules`） |
| 记忆 | 两个 markdown 文件，无数据库 | — | 运行时生成于 `backend/memory/` |

## 一次性准备

1. **装工具**：[uv](https://docs.astral.sh/uv/getting-started/installation/) 和 [node](https://nodejs.org/)（≥ 20）。
   ```bash
   uv --version && node --version   # 确认都有
   ```
2. **填 Cyanite 密钥**：把 `.env.sample` 复制成 `.env`，填入主办方发的 key。
   ```bash
   cp .env.sample .env   # 然后编辑 .env，填 CYANITE_API_KEY / CYANITE_ACCOUNT
   ```
   `.env` 已 git-ignore，不会被提交。

## 启动

**一键起整个项目**（装依赖 + 前后端一起跑）：
```bash
./start.sh
```
打印出地址，`Ctrl-C` 一次同时停前后端：

| 地址 | 是什么 |
|------|--------|
| http://localhost:5173 | 前端页面（开发时打开这个） |
| http://localhost:8000 | 后端 API |
| http://localhost:8000/docs | API 文档（Swagger，可直接试端点） |

依赖是幂等安装的：已装过就秒过，不会重复下载。

## 单独起 / 常用命令

`dev.sh` 是更细粒度的入口：
```bash
./dev.sh          # 只装/同步后端依赖
./dev.sh run      # 只起后端 :8000
./dev.sh front    # 只起前端 :5173
```

手动操作：
```bash
# 后端
cd backend
uv sync                                   # 同步依赖到 .venv
uv add <包名>                              # 加依赖
uv run uvicorn app:app --reload           # 起服务
uv run python memory.py                   # 跑记忆模块自检

# 前端
cd frontend
npm install                               # 装依赖
npm run dev                               # 起开发服务器
npm run build                             # 生产构建
npx tsc --noEmit                          # 只类型检查
```

## 验证跑通了

1. `./start.sh`，浏览器开 http://localhost:5173
2. 输入框打一句话（如「背叛」）→ 点「意图编译」
3. 看到后端返回的 Query Card JSON = 前后端连通 ✅

或直接命令行戳后端：
```bash
curl localhost:8000/health                # {"ok":true}
```

## 代码结构

```
backend/
  app.py        FastAPI，4 个端点骨架（/intent /intent/confirm /feedback /your-sound）+ CORS + 内存会话
  memory.py     两个 markdown 的读写（evidence 追加 / memory 重写）
  memory/       运行时生成的每用户记忆文件（已 git-ignore）
frontend/
  src/api.ts    后端端点的 typed 封装
  src/App.tsx   最小连通页面
  vite.config.ts  /api 代理到后端 :8000（避免 CORS）
start.sh / dev.sh  启动脚本
```

端点里标了 `TODO(Bx)` 对应 [PRD-night.md](PRD-night.md) 第 4 节的时间块，按块往里填实现即可。
