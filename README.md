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

- 所有业务数据保存在 `data/ai_tutor.db`。
- 上传文件保存在 `uploads/`。
- AI 问答当前通过智谱 `glm-4.7-flash` 调用，服务端需要配置环境变量 `BIGMODEL_API_KEY`。
- 可选环境变量 `BIGMODEL_MODEL`，默认值为 `glm-4.7-flash`。

## 启动方式

```bash
BIGMODEL_API_KEY=你的密钥 python3 server.py
```

启动后访问 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

如果 `8000` 端口已被占用，可以换一个端口启动：

```bash
python3 server.py --port 8001
```

## 演示账号

- 教师：`teacher01 / Teacher@123`
- 学生：`student01 / Student@123`

## 项目结构

```text
AITAS/
├── data/
├── static/
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── uploads/
│   └── demo_courseware.txt
├── README.md
└── server.py
```
