# AITAS AI 助教系统

AITAS 是一个面向课程教学场景的 AI 教学辅助系统，包含管理员端、教师端和学生端。系统支持班级与课件管理、作业发布与 AI 辅助批改、智能测验、课程知识库问答、学生首页智能助教、教学反馈、讨论区、班级私信和通知中心。

前端使用 Vue 3 + Vite + Pinia，后端使用 Flask + SQLite。AI 能力通过兼容 OpenAI Chat Completions 格式的模型接口调用，默认配置为 DeepSeek `deepseek-chat`。

## 核心功能

### 管理员端

- 查看教师、学生、班级和课件统计数据
- 创建、修改和删除教师或学生账号
- 管理班级、授课教师、班级成员和课件

### 教师端

- 创建和管理班级，审批学生入班申请
- 上传、编辑、预览和删除班级课件
- 为班级课件构建或刷新 RAG 知识库索引
- 使用班级知识库进行课程问答
- 为指定班级发布作业，查看提交进度，使用 AI 生成批改草稿并确认正式成绩
- 手工组题或基于班级知识库使用 AI 生成测验，审核题目后发布到指定班级
- 查看测验提交人数、平均得分率和学生逐题答卷，对简答题进行人工复核并自动重算成绩
- 查看学生课件评价与建议
- 参与班级讨论和私信沟通，通过通知中心跟踪学生反馈、测验提交和新私信

### 学生端

- 注册账号、申请加入班级并切换当前班级
- 在线浏览课件，围绕单份课件进行 AI 问答
- 使用班级知识库进行跨课件检索与总结
- 在首页使用智能助教完成课程问答、课件总结、练习题生成、学习记录回顾和个性化学习建议
- 在富文本编辑器中输入文字、插入或粘贴图片，也可上传本地附件提交作业
- 查看作业提交状态、教师评分和评语；批改前可以重新提交
- 完成班级在线测验，提交后查看自动初判、答案解析和逐题反馈；教师复核简答题后自动显示最新成绩
- 提交课件评价、参与讨论并与同班成员私信
- 在通知中心查看新作业、新测验、新课件、知识库就绪和新私信提醒，并可跳转到对应内容
- 清除首页或知识库问答记录；对应数据库记录会同步删除

## AI 与知识库设计

系统目前提供三类 AI 问答入口，以及作业批改和智能测验两类 AI 教学能力：

1. **单课件问答**：提取当前课件文本，结合该课件的最近对话调用 LLM。
2. **班级知识库问答**：按班级检索 ChromaDB 向量索引；向量依赖不可用时回退到本地词法索引。回答会展示命中的课件来源及预览链接。
3. **学生首页智能助教**：服务端先识别问题意图，再选择回答路径：
   - 课程检索、知识解释和课件总结进入班级知识库分支；
   - 练习题、学习记录、作业查询和个性化建议进入个性化分支；
   - 个性化 Prompt 会汇总该学生在首页助教、知识库和单课件问答中的历史提问。
4. **作业 AI 批改**：教师端将本作业评分标准、作业要求、在线正文和可提取的附件文字拼接为 Prompt。每项作业首次使用时按“课程知识库、历史正式批改、当前作业要求”的顺序生成独立评分标准；模型建议先保存为草稿，教师确认后才写入正式成绩。
5. **智能测验**：教师可指定知识范围、题量和难度，系统先从班级 RAG 索引检索相关课件，再调用模型生成单选、判断和简答题；教师也可以手工添加单选、多选和简答题，审核后再发布。学生提交后，系统对单选、判断和多选题进行规则匹配，对简答题进行文本与关键词初判，并即时返回逐题结果。简答题始终进入教师复核队列，教师可逐题改判、填写备注并重算整份答卷成绩；批量重新自动批改时会保留已保存的人工判定。

学生在提交前获取的测验数据不包含参考答案和解析；提交后才能在结果中查看对应内容。测验提交明细与人工复核接口仅允许该班级教师或管理员访问。

意图识别优先使用 LLM；模型分类不可用时会回退到关键词规则。首页、单课件和知识库对话均持久化到 SQLite。

## 通知与消息同步

- 学生会收到新作业、新测验、新课件和班级知识库索引完成提醒。
- 教师会收到学生课件反馈、测验完成情况和新私信提醒；学生收到私信时同样会产生通知。
- 通知支持未读计数、单条已读、全部已读，并可跳转到关联的业务页面。
- 私信仅允许同班成员之间建立会话；消息页面通过长轮询同步会话和未读状态，通知未读数按固定间隔刷新。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、Vue Router、Pinia、Vite |
| 后端 | Python 3.10+、Flask、Flask-CORS |
| 数据库 | SQLite |
| LLM | OpenAI Chat Completions 兼容接口；默认 DeepSeek |
| RAG | ChromaDB、LangChain Community、Sentence Transformers |
| 文档处理 | pypdf、python-pptx、ZIP/XML 文本提取 |

知识库文本提取支持 PDF、DOCX、PPTX、TXT、Markdown、CSV、JSON、HTML 及常见代码文本文件。

## 环境要求

- Python 3.10 或更高版本
- Node.js 18 或更高版本
- npm
- 使用 AI 问答、AI 批改或 AI 出题时需要可用的 LLM API Key
- 首次构建向量索引时需要下载嵌入模型，需保证网络可用

## 安装依赖

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

npm --prefix frontend ci
```

Windows PowerShell 激活虚拟环境的命令为：

```powershell
.venv\Scripts\Activate.ps1
```

## 环境变量

后端启动时会自动读取项目根目录下的 `.ENV` 文件。可以创建该文件并填写：

```dotenv
API_KEY=你的模型服务密钥
API_URL=https://api.deepseek.com/chat/completions
MODEL_NAME=deepseek-chat
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

| 变量 | 是否必需 | 默认值 | 用途 |
| --- | --- | --- | --- |
| `API_KEY` | 是 | 无 | 调用 LLM 接口 |
| `API_URL` | 否 | `https://api.deepseek.com/chat/completions` | Chat Completions 接口地址 |
| `MODEL_NAME` | 否 | `deepseek-chat` | 对话模型名称 |
| `EMBEDDING_MODEL` | 否 | `paraphrase-multilingual-MiniLM-L12-v2` | RAG 嵌入模型名称 |

直接在终端设置的环境变量优先于 `.ENV` 文件。该文件包含密钥，请勿提交到版本库；不配置 `API_KEY` 时，班级、课件、作业、讨论等非 AI 功能仍可使用。

## 启动方式

### 方式一：构建前端后由 Flask 统一提供服务

```bash
npm --prefix frontend run build
python3 backend/main.py
```

启动后访问：<http://127.0.0.1:8080>

指定其他端口：

```bash
python3 backend/main.py --port 8001
```

### 方式二：前后端开发模式

终端一：

```bash
python3 backend/main.py
```

终端二：

```bash
npm --prefix frontend run dev
```

前端开发地址为 <http://127.0.0.1:5173>。Vite 会把 `/api`、`/uploads`、`/preview`、`/preview-quicklook` 和 `/preview-media` 请求代理到 `http://localhost:8080`。

## 演示账号

数据库首次初始化时会创建以下账号：

| 角色 | 用户名 | 密码 | 备注 |
| --- | --- | --- | --- |
| 管理员 | `admin` | `2026` | 系统管理员 |
| 教师 | `teacher01` | `Teacher@123` | 王老师 |
| 学生 | `student01` | `Student@123` | 李同学，学号 `20260001` |
| 学生 | `student02` | `Student@123` | 陈同学，学号 `20260002` |

默认账号和密码仅用于课程演示，请勿直接用于生产环境。

## 推荐使用流程

1. 使用教师账号创建班级。
2. 使用学生账号申请加入该班级。
3. 教师审批申请并上传课件。
4. 教师在“知识库”页面构建班级索引。
5. 教师发布作业，学生通过富文本或本地附件提交，教师完成评分与评语。
6. 教师手工创建或使用 AI 生成测验，审核发布后由学生在线作答；教师在提交明细中复核简答题并确认最终成绩。
7. 学生在课件页、知识库页或首页智能助教中提问。
8. 学生提交评价，教师在反馈页面查看结果；双方可在通知中心查看相关提醒。

## 数据与文件目录

所有运行时数据都位于 `storage/`：

```text
storage/
├── db/ai_tutor.sqlite3          # SQLite 业务数据库
├── uploads/coursewares/         # 上传的原始课件
├── uploads/assignments/         # 作业正文图片和提交附件
├── processed/rag_indexes/       # 本地词法索引
├── previews/                    # 生成的课件预览
├── vectorstores/chroma/         # ChromaDB 向量索引
└── tmp/                         # 临时文件
```

应用启动时会自动创建缺失的目录和数据表，并执行兼容性迁移。问答历史分别保存在：

- `ai_chat_messages`：单课件问答
- `rag_chat_messages`：班级知识库问答
- `agent_chat_messages`：学生首页智能助教

作业数据保存在 `assignments`、`assignment_submissions` 和 `assignment_submission_files` 表中；每项作业独立的评分标准和 AI 批改记录分别保存在 `assignment_grading_rubrics` 与 `assignment_ai_grading_records`。AI 草稿刷新页面后仍会保留，教师保存后才更新 `assignment_submissions` 中的正式成绩。删除作业、学生账号或班级时，对应记录和文件会同步清理。

测验题目和学生答卷分别保存在 `quiz_templates` 与 `quiz_submissions`。自动批改逐题结果、简答题人工判定、复核备注、复核教师和复核时间统一保存在 `quiz_submissions.ai_feedback` 的 JSON 数据中，无需额外维护复核表。站内通知保存在 `notifications`，并通过 `ref_type` 和 `ref_id` 关联作业、测验、课件、知识库、反馈或私信会话。

## 主要 API

所有业务 API 均使用 `/api` 前缀；除登录和注册外，请求通过 Bearer Token 鉴权。

| 模块 | 主要接口 |
| --- | --- |
| 认证 | `/api/auth/login`、`/api/auth/register`、`/api/auth/logout`、`/api/me` |
| 用户 | `/api/users` |
| 班级 | `/api/classes`、`/api/classes/join`、`/api/classes/requests/*` |
| 课件 | `/api/coursewares`、`/api/coursewares/:id` |
| 作业 | `/api/assignments`、`/api/assignments/:id/submit`、`/api/assignments/:id/submissions/:submission_id/grade` |
| 作业 AI 批改 | `/api/assignments/:id/rubric`、`/api/assignments/:id/rubric/regenerate`、`/api/assignments/:id/submissions/:submission_id/ai-grade` |
| 智能测验 | `/api/quizzes`、`/api/quizzes/generate`、`/api/quizzes/:id/submit`、`/api/quizzes/:id/grade` |
| 测验提交与复核 | `/api/quizzes/:id/submissions`、`/api/quizzes/:id/submissions/:submission_id/review` |
| 单课件 AI | `/api/ai/chat`、`/api/ai/messages` |
| 首页智能助教 | `/api/ai/agent`、`/api/ai/agent/messages` |
| 知识库 | `/api/rag/status`、`/api/rag/index`、`/api/rag/ask`、`/api/rag/messages` |
| 评价 | `/api/evaluations` |
| 讨论 | `/api/discussions`、`/api/discussions/:id/replies` |
| 私信 | `/api/messages/contacts`、`/api/messages/conversations`、`/api/messages/events` |
| 通知 | `/api/notifications`、`/api/notifications/unread-count`、`/api/notifications/:id/read`、`/api/notifications/read-all` |
| 统计 | `/api/dashboard` |

## 测试与构建检查

运行后端测试：

```bash
python3 -m unittest discover -s backend/tests -t . -v
```

检查 Python 模块是否可编译：

```bash
python3 -m compileall -q backend
```

构建前端：

```bash
npm --prefix frontend run build
```

## 项目结构

```text
AITAS/
├── backend/
│   ├── app.py                    # Flask 应用工厂与蓝图注册
│   ├── main.py                   # 后端启动入口
│   ├── config.py                 # 路径、模型和系统配置
│   ├── database.py               # SQLite 初始化、迁移和演示数据
│   ├── middleware/auth.py        # Bearer Token 鉴权
│   ├── models/                   # 数据访问层
│   ├── routers/                  # Flask API 蓝图
│   │   ├── agent.py              # 学生首页智能助教
│   │   ├── ai_chat.py            # 单课件 AI 问答
│   │   ├── assignments.py        # 作业发布、提交、批改和文件访问
│   │   ├── quiz.py               # AI 出题、测验发布、答题与自动批改
│   │   ├── notifications.py      # 通知列表与已读状态
│   │   └── rag.py                # 班级知识库问答
│   ├── services/
│   │   ├── ai_service.py         # LLM API 调用
│   │   ├── agent_service.py      # 意图识别与个性化 Prompt
│   │   ├── assignment_grading_service.py # 评价标准生成与 AI 批改
│   │   ├── assignment_service.py # 作业富文本清洗与文件管理
│   │   ├── quiz_service.py       # 测验生成与自动批改
│   │   ├── notification_service.py # 业务通知分发
│   │   ├── rag_service.py        # 向量/词法索引构建与检索
│   │   ├── rag_answer_service.py # 知识库上下文与来源构造
│   │   ├── text_service.py       # 课件文本提取
│   │   └── preview_service.py    # 课件预览生成
│   └── tests/                    # 后端测试
├── frontend/
│   ├── src/
│   │   ├── api/                  # 前端 API 封装
│   │   ├── components/           # 通用与业务组件
│   │   ├── pages/                # 页面组件
│   │   ├── router/               # Vue Router
│   │   └── store/                # Pinia 状态管理
│   ├── vite.config.js            # Vite 与开发代理配置
│   └── dist/                     # 生产构建产物
├── storage/                      # 数据库、上传文件、索引和预览
├── requirements.txt              # Python 依赖
└── README.md
```

## 注意事项

- 当前后端使用 Flask 开发服务器并启用了调试模式，适合课程设计、演示和本地开发，不应直接作为生产部署方案。
- 当前默认管理员密码固定为 `2026`，正式部署前必须修改配置和初始化策略。
- API CORS 当前允许所有来源，生产环境应限制可信域名。
- 首次加载 Sentence Transformers 模型可能耗时较长。
- 作业单个文件上限为 20 MB，正文图片与附件合计每次最多上传 10 个，整次请求上限为 60 MB。
- 作业 AI 批改会读取正文和可提取的文档文字；当前文本模型不会识别提交图片，只有图片而没有可提取文字时需要教师人工批改。
- 智能测验定位为练习和随堂自测：简答题的自动结果属于初判，需由教师在提交明细页人工复核；每题当前按 1 分等权计分。
- PPT/PPTX 在 macOS 上可尝试通过 Microsoft PowerPoint、Keynote 或 Quick Look 生成更高质量预览；其他环境会使用系统内置的浏览器预览回退方案。
- 知识库没有命中相关课件时，系统会明确标注回答由大模型生成。
