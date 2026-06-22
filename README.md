# AI 助教系统

基于需求文档从零搭建的课程教学辅助系统原型，包含教师端和学生端，后端使用 Python 标准库 + `sqlite3`，前端为原生 HTML/CSS/JavaScript。

## 已实现模块

- 用户注册、登录、角色区分
- 班级创建、加入、切换与成员管理
- 教师课件上传、编辑、删除
- 学生按班级浏览课件与下载
- 基于智谱 GLM 的课件问答
- 学生评价问卷提交、教师按班级查看反馈
- 班级讨论区发帖与回复
- 私信会话列表管理、已读状态与自动刷新

## 说明

- 所有业务数据保存在 `storage/db/ai_tutor.sqlite3`（旧版为 `data/ai_tutor.db`，首次启动自动迁移）。
- 上传文件保存在 `storage/uploads/coursewares/{id}/original/`。
- AI 问答当前通过 DeepSeek `deepseek-chat` 调用，服务端需要配置环境变量 `API_KEY`（可在项目根目录 `ENV` 文件中配置，格式见 `ENV` 文件）。
- 可选环境变量 `MODEL_NAME`，默认值为 `deepseek-chat`。

## 启动方式

```bash
API_KEY=你的密钥 python3 backend/main.py
```

启动后访问 [http://127.0.0.1:8080](http://127.0.0.1:8080)。

如果 `8080` 端口已被占用，可以换一个端口启动：

```bash
python3 backend/main.py --port 8001
```

## 演示账号

- 教师：`teacher01 / Teacher@123`
- 学生：`student01 / Student@123`

## 项目结构

```text
AITAS/
├── frontend/                  # Vue 3 前端（构建输出到 frontend/dist/）
│   ├── src/
│   ├── dist/                  # 生产构建 → 由 backend 直接服务
│   └── ...
├── backend/                   # ✅ 模块化后端（推荐）
│   ├── main.py                # 入口 — ThreadingHTTPServer
│   ├── config.py              # 配置中心（路径、AI设置、管理员）
│   ├── database.py            # SQLite 连接、15张表初始化、密码哈希
│   ├── models/                # 数据访问层
│   │   ├── user.py            #    用户 CRUD + 级联删除
│   │   ├── class_.py          #    班级 CRUD + 成员/申请管理
│   │   ├── courseware.py      #    课件 CRUD
│   │   ├── evaluation.py      #    课件评价
│   │   ├── discussion.py      #    讨论 + 回复
│   │   ├── message.py         #    私信 + 联系人
│   │   ├── ai_chat.py         #    AI / RAG 对话历史
│   │   └── access.py          #    权限判断 + 班级范围过滤
│   ├── routers/               # API 路由层
│   │   ├── auth.py            #    /api/auth/* + /api/me
│   │   ├── users.py           #    /api/users/*（管理员）
│   │   ├── classes.py         #    /api/classes/*
│   │   ├── coursewares.py     #    /api/coursewares/*
│   │   ├── evaluations.py     #    /api/evaluations
│   │   ├── discussions.py     #    /api/discussions/*
│   │   ├── messages.py        #    /api/messages/*（私信 + SSE）
│   │   ├── ai_chat.py         #    /api/ai/chat（课件问答）
│   │   ├── rag.py             #    /api/rag/*（知识库问答）
│   │   └── dashboard.py       #    /api/dashboard（统计面板）
│   ├── services/              # 业务逻辑层
│   │   ├── ai_service.py      #    智谱GLM API 调用
│   │   ├── text_service.py    #    课件文本提取
│   │   ├── rag_service.py     #    RAG 知识库索引构建与状态管理
│   │   ├── sync_service.py    #    SSE 实时同步
│   │   ├── preview_service.py #    课件预览生成（AppleScript + QuickLook）
│   │   └── file_server.py     #    静态文件/预览服务
│   ├── middleware/
│   │   └── auth.py            # Bearer Token 认证
│   └── utils/
│       ├── file_utils.py      # 文件路径/清理工具
│       └── response.py        # HTTP 响应工具
├── storage/                   # 运行时数据（自动创建）
│   ├── db/                    # SQLite 数据库
│   ├── uploads/               # 课件文件（按 coursewares/{id}/original/ 组织）
│   ├── previews/              # 系统生成的预览
│   └── vectorstores/chroma/   # ChromaDB 向量库
├── data/                      # 旧版数据目录（兼容过渡）
├── static/                    # 旧版前端（兼容过渡）
├── vendor/pypdf/              # 内置 pypdf 依赖
├── ENV                        # 环境变量配置
└── README.md
```
