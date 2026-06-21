const state = {
  token: localStorage.getItem("ai_tutor_token") || "",
  user: null,
  authMode: "login",
  route: "overview",
  status: "",
  statusType: "",
  statusTimer: null,
  dialog: null,
  sheet: null,
  aiDrawerOpen: false,
  coursewares: [],
  dashboard: null,
  evaluations: [],
  discussions: [],
  classes: [],
  availableClasses: [],
  currentClassId: Number(localStorage.getItem("ai_tutor_current_class") || 0) || null,
  users: [],
  conversations: [],
  activeCoursewareId: null,
  editingCoursewareId: null,
  editingManagedUserId: null,
  activeConversationId: null,
  activeDiscussionId: null,
  threadMessages: [],
  messageSyncEnabled: false,
  messageSyncLoop: null,
  messageSyncAbortController: null,
  messageEventCursor: 0,
  qaMessages: [],
  qaLoading: false,
  qaDraft: "",
  ragMessages: [],
  ragLoading: false,
  ragDraft: "",
  ragIndexStatus: null,
};

const app = document.getElementById("app");
let dialogResolver = null;

const routeMap = {
  admin: [
    { id: "overview", label: "总览" },
    { id: "users", label: "用户" },
    { id: "classes", label: "班级" },
    { id: "coursewares", label: "课件" },
  ],
  teacher: [
    { id: "overview", label: "总览" },
    { id: "classes", label: "班级" },
    { id: "coursewares", label: "课件" },
    { id: "rag", label: "知识库" },
    { id: "evaluations", label: "反馈" },
    { id: "discussions", label: "讨论" },
    { id: "messages", label: "私信" },
  ],
  student: [
    { id: "overview", label: "总览" },
    { id: "classes", label: "班级" },
    { id: "coursewares", label: "课件" },
    { id: "rag", label: "知识库" },
    { id: "survey", label: "反馈" },
    { id: "discussions", label: "讨论" },
    { id: "messages", label: "私信" },
  ],
};

const pageMeta = {
  admin: {
    overview: {
      kicker: "管理员",
      title: "平台总览",
      description: "平台管理中心",
    },
    users: {
      kicker: "管理员",
      title: "用户管理",
      description: "教师与学生账号",
    },
    classes: {
      kicker: "管理员",
      title: "班级管理",
      description: "班级与成员",
    },
    coursewares: {
      kicker: "管理员",
      title: "课件管理",
      description: "平台课件资源",
    },
  },
  teacher: {
    overview: {
      kicker: "教师端",
      title: "教学总览",
      description: "班级与教学状态",
    },
    classes: {
      kicker: "教师端",
      title: "班级管理",
      description: "班级与成员",
    },
    coursewares: {
      kicker: "教师端",
      title: "课件管理",
      description: "班级课件",
    },
    evaluations: {
      kicker: "教师端",
      title: "反馈分析",
      description: "课件反馈",
    },
    discussions: {
      kicker: "教师端",
      title: "讨论区",
      description: "主题交流",
    },
    rag: {
      kicker: "教师端",
      title: "知识库问答",
      description: "跨课件 RAG 智能问答",
    },
    messages: {
      kicker: "教师端",
      title: "消息中心",
      description: "会话与消息",
    },
  },
  student: {
    overview: {
      kicker: "学生端",
      title: "学习总览",
      description: "当前班级学习入口",
    },
    classes: {
      kicker: "学生端",
      title: "班级列表",
      description: "加入与切换班级",
    },
    coursewares: {
      kicker: "学生端",
      title: "课件学习",
      description: "课件阅读与问答",
    },
    survey: {
      kicker: "学生端",
      title: "使用反馈",
      description: "课件评价",
    },
    discussions: {
      kicker: "学生端",
      title: "讨论区",
      description: "课程讨论",
    },
    rag: {
      kicker: "学生端",
      title: "知识库问答",
      description: "跨课件 RAG 智能问答",
    },
    messages: {
      kicker: "学生端",
      title: "消息中心",
      description: "班级会话",
    },
  },
};

function roleLabel(role) {
  if (role === "admin") {
    return "管理员";
  }
  return role === "teacher" ? "教师" : "学生";
}

function routeIcon(routeId) {
  const icons = {
    overview: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3 12.5 12 4l9 8.5"></path>
        <path d="M6.5 10.5V20h11V10.5"></path>
      </svg>
    `,
    users: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"></path>
        <circle cx="9.5" cy="7.5" r="3.5"></circle>
        <path d="M21 21v-2a4 4 0 0 0-3-3.87"></path>
        <path d="M15 4.13a3.5 3.5 0 0 1 0 6.74"></path>
      </svg>
    `,
    classes: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3 7.5 12 3l9 4.5-9 4.5Z"></path>
        <path d="M7 10.5v4.5c0 1.66 2.24 3 5 3s5-1.34 5-3v-4.5"></path>
      </svg>
    `,
    coursewares: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"></path>
        <path d="M14 3v5h5"></path>
        <path d="M9 13h6"></path>
        <path d="M9 17h6"></path>
      </svg>
    `,
    evaluations: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 20 5.5 23l1.5-7.5L2 10.8l7.8-.9L12 3l2.2 6.9 7.8.9-5 4.7 1.5 7.5Z"></path>
      </svg>
    `,
    survey: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M9 11h9"></path>
        <path d="M9 16h9"></path>
        <path d="M9 6h9"></path>
        <path d="m5 6 .5.5L7 5"></path>
        <path d="m5 11 .5.5L7 10"></path>
        <path d="m5 16 .5.5L7 15"></path>
      </svg>
    `,
    discussions: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 5h16v10H8l-4 4Z"></path>
      </svg>
    `,
    messages: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 5h16v11H8l-4 4Z"></path>
      </svg>
    `,
    rag: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
        <path d="M3 5v4c0 1.66 4.03 3 9 3s9-1.34 9-3V5"></path>
        <path d="M3 9v4c0 1.66 4.03 3 9 3s9-1.34 9-3V9"></path>
        <path d="M3 13v4c0 1.66 4.03 3 9 3s9-1.34 9-3v-4"></path>
      </svg>
    `,
  };
  return icons[routeId] || icons.overview;
}

function joinRequestLabel(status) {
  if (status === "pending") {
    return "待审核";
  }
  if (status === "rejected") {
    return "已拒绝";
  }
  if (status === "approved") {
    return "已通过";
  }
  return "可申请";
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function displayCoursewareTitle(value = "") {
  const text = String(value || "").trim();
  if (!text) {
    return "";
  }
  return text
    .replace(/^[0-9a-f]{12,}_/i, "")
    .replace(/^\d+[._-]+/, "")
    .trim();
}

function buildPath(path, params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, value);
    }
  });
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

function formatCount(value) {
  return value == null ? "-" : String(value);
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function getPageMeta() {
  return pageMeta[state.user.role][state.route];
}

function setStatus(message = "", type = "") {
  state.status = message;
  state.statusType = type;
  if (state.statusTimer) {
    window.clearTimeout(state.statusTimer);
    state.statusTimer = null;
  }

  renderFloatingUi();

  if (message) {
    state.statusTimer = window.setTimeout(() => {
      state.status = "";
      state.statusType = "";
      state.statusTimer = null;
      renderFloatingUi();
    }, type === "error" ? 4200 : 2600);
  }
}

function renderFloatingUi() {
  const host = document.getElementById("floating-ui");
  if (!host) {
    return;
  }

  host.innerHTML = `
    ${
      state.status
        ? `
          <div class="toast-region">
            <div class="toast-card ${state.statusType || "info"}">
              <div class="toast-accent"></div>
              <div class="toast-copy">
                <strong>${state.statusType === "error" ? "操作提示" : "系统提示"}</strong>
                <span>${escapeHtml(state.status)}</span>
              </div>
              <button class="toast-close" type="button" data-dismiss-toast>&times;</button>
            </div>
          </div>
        `
        : ""
    }
    ${
      state.dialog
        ? `
          <div class="dialog-overlay">
            <div class="dialog-card ${state.dialog.tone || ""}">
              <div class="dialog-head">
                <div>
                  <span class="eyebrow">${escapeHtml(state.dialog.eyebrow || "操作确认")}</span>
                  <h3>${escapeHtml(state.dialog.title)}</h3>
                </div>
                <button class="toast-close" type="button" data-dialog-cancel>&times;</button>
              </div>
              <p>${escapeHtml(state.dialog.description)}</p>
              <div class="button-row">
                <button class="ghost-btn" type="button" data-dialog-cancel>${escapeHtml(state.dialog.cancelText || "取消")}</button>
                <button class="${state.dialog.confirmClass || "primary-btn"}" type="button" data-dialog-confirm>${escapeHtml(
                  state.dialog.confirmText || "确认"
                )}</button>
              </div>
            </div>
          </div>
        `
        : ""
    }
  `;

  host.querySelector("[data-dismiss-toast]")?.addEventListener("click", () => setStatus(""));
  host.querySelector("[data-dialog-cancel]")?.addEventListener("click", () => settleDialog(false));
  host.querySelector("[data-dialog-confirm]")?.addEventListener("click", () => settleDialog(true));
}

function settleDialog(confirmed) {
  state.dialog = null;
  renderFloatingUi();
  if (dialogResolver) {
    dialogResolver(confirmed);
    dialogResolver = null;
  }
}

function showDialog(config) {
  state.dialog = config;
  renderFloatingUi();
  return new Promise((resolve) => {
    dialogResolver = resolve;
  });
}

function renderToastHost() {
  return `<div id="floating-ui"></div>`;
}

function renderSheetShell({ eyebrow = "编辑面板", title, description = "", body, wide = false }) {
  return `
    <div class="sheet-overlay" data-close-sheet></div>
    <aside class="sheet-panel ${wide ? "wide" : ""}">
      <div class="sheet-panel-head">
        <div>
          <span class="eyebrow">${escapeHtml(eyebrow)}</span>
          <h3>${escapeHtml(title)}</h3>
          ${description ? `<p>${escapeHtml(description)}</p>` : ""}
        </div>
        <button class="toast-close" type="button" data-close-sheet>&times;</button>
      </div>
      <div class="sheet-panel-body">
        ${body}
      </div>
    </aside>
  `;
}

function bindSheetClose(onClose) {
  document.querySelectorAll("[data-close-sheet]").forEach((node) => {
    node.addEventListener("click", () => {
      onClose();
    });
  });
}

function closeSheet() {
  state.sheet = null;
  state.editingManagedUserId = null;
  state.editingCoursewareId = null;
}

function renderManagedUserForm(editing = null) {
  return `
    <form id="managed-user-form" class="form-grid">
      <div class="field split-field">
        <div class="field">
          <label for="managed-user-display-name">姓名</label>
          <input id="managed-user-display-name" name="display_name" value="${escapeHtml(editing?.display_name || "")}" required>
        </div>
        <div class="field">
          <label for="managed-user-username">用户名</label>
          <input id="managed-user-username" name="username" value="${escapeHtml(editing?.username || "")}" required>
        </div>
      </div>
      <div class="field split-field">
        <div class="field">
          <label for="managed-user-role">角色</label>
          <select id="managed-user-role" name="role">
            <option value="teacher" ${editing?.role === "teacher" ? "selected" : ""}>教师</option>
            <option value="student" ${!editing || editing?.role === "student" ? "selected" : ""}>学生</option>
          </select>
        </div>
        <div class="field">
          <label for="managed-user-password">${editing ? "重置密码" : "登录密码"}</label>
          <input
            id="managed-user-password"
            name="password"
            type="password"
            placeholder="${editing ? "留空则保持原密码" : "输入登录密码"}"
            ${editing ? "" : "required"}
          >
        </div>
      </div>
      <div class="field" id="managed-user-student-field">
        <label for="managed-user-student-number">学号</label>
        <input
          id="managed-user-student-number"
          name="student_number"
          value="${escapeHtml(editing?.student_number || "")}"
          placeholder="输入学号"
        >
      </div>
      <div class="button-row sheet-actions">
        <button class="primary-btn" type="submit">${editing ? "保存账号" : "创建账号"}</button>
        <button class="ghost-btn" type="button" data-close-sheet>取消</button>
      </div>
    </form>
  `;
}

function renderClassForm({ mode, currentClass = null, teacherOptions = [] }) {
  const isEdit = mode === "edit";
  return `
    <form id="${isEdit ? "update-class-form" : "create-class-form"}" class="form-grid">
      <div class="field">
        <label for="${isEdit ? "current-class-name" : "class-name"}">班级名称</label>
        <input
          id="${isEdit ? "current-class-name" : "class-name"}"
          name="name"
          value="${escapeHtml(currentClass?.name || "")}"
          placeholder="例如：软件工程 1 班"
          required
        >
      </div>
      ${
        state.user.role === "admin"
          ? `
            <div class="field">
              <label for="${isEdit ? "current-class-teacher-id" : "class-teacher-id"}">授课教师</label>
              <select id="${isEdit ? "current-class-teacher-id" : "class-teacher-id"}" name="teacher_id" required>
                <option value="">请选择教师</option>
                ${teacherOptions
                  .map(
                    (item) => `
                      <option
                        value="${item.id}"
                        ${item.id === currentClass?.teacher_id ? "selected" : ""}
                      >
                        ${escapeHtml(item.display_name)} · ${escapeHtml(item.username)}
                      </option>
                    `
                  )
                  .join("")}
              </select>
            </div>
          `
          : ""
      }
      <div class="field">
        <label for="${isEdit ? "current-class-description" : "class-description"}">班级说明</label>
        <textarea
          id="${isEdit ? "current-class-description" : "class-description"}"
          name="description"
          placeholder="输入班级说明"
        >${escapeHtml(currentClass?.description || "")}</textarea>
      </div>
      <div class="button-row sheet-actions">
        <button class="primary-btn" type="submit">${isEdit ? "保存班级信息" : "创建班级"}</button>
        <button class="ghost-btn" type="button" data-close-sheet>取消</button>
      </div>
    </form>
  `;
}

function renderCoursewareForm(editing = null) {
  return `
    <form id="courseware-form" class="form-grid">
      <div class="field">
        <label for="cw-title">课件标题</label>
        <input id="cw-title" name="title" value="${escapeHtml(editing?.title || "")}" required>
      </div>
      <div class="field ${editing ? "" : "split-field"}">
        <div class="field">
          <label for="cw-course-name">课程名称</label>
          <input id="cw-course-name" name="course_name" value="${escapeHtml(editing?.course_name || "")}" required>
        </div>
        ${
          editing
            ? ""
            : `
              <div class="field">
                <label for="cw-file">课件文件</label>
                <input id="cw-file" name="file" type="file" required>
              </div>
            `
        }
      </div>
      <div class="field">
        <label for="cw-description">课件简介</label>
        <textarea id="cw-description" name="description" placeholder="输入课件简介">${escapeHtml(editing?.description || "")}</textarea>
      </div>
      ${
        editing
          ? '<div class="inline-hint">当前编辑会更新标题、课程名称与简介，文件本体保持不变。</div>'
          : ""
      }
      <div class="button-row sheet-actions">
        <button class="primary-btn" type="submit">${editing ? "保存修改" : "上传课件"}</button>
        <button class="ghost-btn" type="button" data-close-sheet>取消</button>
      </div>
    </form>
  `;
}

function renderDiscussionForm() {
  return `
    <form id="discussion-form" class="form-grid">
      <div class="field">
        <label for="discussion-title">标题</label>
        <input id="discussion-title" name="title" placeholder="输入标题" required>
      </div>
      <div class="field">
        <label for="discussion-body">内容</label>
        <textarea id="discussion-body" name="body" placeholder="输入讨论内容" required></textarea>
      </div>
      <div class="button-row sheet-actions">
        <button class="primary-btn" type="submit">发布主题</button>
        <button class="ghost-btn" type="button" data-close-sheet>取消</button>
      </div>
    </form>
  `;
}

function renderEvaluationForm() {
  return `
    <form id="evaluation-form" class="form-grid">
      <div class="field">
        <label for="evaluation-courseware">课件</label>
        <select id="evaluation-courseware" name="courseware_id" required>
          <option value="">请选择课件</option>
          ${state.coursewares
            .map((item) => `<option value="${item.id}">${escapeHtml(item.course_name)} · ${escapeHtml(displayCoursewareTitle(item.title))}</option>`)
            .join("")}
        </select>
      </div>
      <div class="field">
        <label>内容难度</label>
        <div class="rating-grid">
          ${renderRatingOptions("difficulty")}
        </div>
      </div>
      <div class="field">
        <label>可读性</label>
        <div class="rating-grid">
          ${renderRatingOptions("readability")}
        </div>
      </div>
      <div class="field">
        <label>适用性</label>
        <div class="rating-grid">
          ${renderRatingOptions("suitability")}
        </div>
      </div>
      <div class="field">
        <label>实用性</label>
        <div class="rating-grid">
          ${renderRatingOptions("practicality")}
        </div>
      </div>
      <div class="field">
        <label for="evaluation-suggestion">改进建议</label>
        <textarea id="evaluation-suggestion" name="suggestion" placeholder="输入你的建议"></textarea>
      </div>
      <div class="button-row sheet-actions">
        <button class="primary-btn" type="submit">提交反馈</button>
        <button class="ghost-btn" type="button" data-close-sheet>取消</button>
      </div>
    </form>
  `;
}

function syncRegisterRoleField() {
  const roleSelect = document.getElementById("register-role");
  const studentField = document.getElementById("register-student-field");
  const studentInput = document.getElementById("register-student-number");
  if (!roleSelect || !studentField || !studentInput) {
    return;
  }

  const isStudent = roleSelect.value === "student";
  studentField.classList.toggle("hidden", !isStudent);
  studentInput.required = isStudent;
  if (!isStudent) {
    studentInput.value = "";
  }
}

function syncManagedUserRoleField() {
  const roleSelect = document.getElementById("managed-user-role");
  const studentField = document.getElementById("managed-user-student-field");
  const studentInput = document.getElementById("managed-user-student-number");
  if (!roleSelect || !studentField || !studentInput) {
    return;
  }

  const isStudent = roleSelect.value === "student";
  studentField.classList.toggle("hidden", !isStudent);
  studentInput.required = isStudent;
  if (!isStudent) {
    studentInput.value = "";
  }
}

async function api(path, options = {}) {
  const config = { method: "GET", ...options };
  config.headers = { ...(config.headers || {}) };

  if (state.token) {
    config.headers.Authorization = `Bearer ${state.token}`;
  }

  if (config.body && !(config.body instanceof FormData)) {
    config.headers["Content-Type"] = "application/json";
    config.body = JSON.stringify(config.body);
  }

  const response = await fetch(path, config);
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    throw new Error(payload?.error || "请求失败，请稍后重试。");
  }

  return payload;
}

function getCurrentCourseware() {
  const courseware = state.coursewares.find((item) => item.id === state.activeCoursewareId);
  return courseware || state.coursewares[0] || null;
}

function getConversationTarget() {
  const contactUser = state.users.find((item) => item.id === state.activeConversationId);
  if (contactUser) {
    return contactUser;
  }
  const conversationUser = state.conversations.find((item) => item.user.id === state.activeConversationId)?.user;
  return conversationUser || state.users[0] || null;
}

function renderEmpty(message) {
  return `
    <div class="empty-state">
      <div class="empty-illustration"></div>
      <div class="empty-copy">
        <strong>当前还没有内容</strong>
        <span>${escapeHtml(message)}</span>
      </div>
    </div>
  `;
}

function renderMetricCard(value, label, tone = "") {
  const icons = {
    blue: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 19h16"></path>
        <path d="M7 16V9"></path>
        <path d="M12 16V5"></path>
        <path d="M17 16v-4"></path>
      </svg>
    `,
    green: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 12h16"></path>
        <path d="m13 5 7 7-7 7"></path>
      </svg>
    `,
    amber: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3v18"></path>
        <path d="M5 10h14"></path>
        <path d="M7 21h10"></path>
      </svg>
    `,
    red: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m4 6 8 6 8-6"></path>
        <path d="M4 6h16v12H4z"></path>
      </svg>
    `,
  };
  return `
    <article class="metric-card ${tone}">
      <div class="metric-icon ${tone}">
        ${icons[tone] || icons.blue}
      </div>
      <div class="metric-copy">
        <strong>${escapeHtml(formatCount(value))}</strong>
        <span>${escapeHtml(label)}</span>
      </div>
    </article>
  `;
}

function renderSectionTitle(title, subline = "") {
  return `
    <div class="section-title">
      <h3>${escapeHtml(title)}</h3>
      ${subline ? `<p>${escapeHtml(subline)}</p>` : ""}
    </div>
  `;
}

function renderInlineRichText(text = "") {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
}

function truncateText(text = "", limit = 120) {
  const value = String(text || "").trim();
  if (value.length <= limit) {
    return value;
  }
  return `${value.slice(0, limit).trimEnd()}...`;
}

function renderRichText(content = "") {
  const lines = String(content).replace(/\r\n?/g, "\n").split("\n");
  const blocks = [];
  let paragraph = [];
  let listItems = [];
  let listTag = "";

  const flushParagraph = () => {
    if (!paragraph.length) {
      return;
    }
    blocks.push(`<p>${renderInlineRichText(paragraph.join(" "))}</p>`);
    paragraph = [];
  };

  const flushList = () => {
    if (!listItems.length || !listTag) {
      return;
    }
    blocks.push(
      `<${listTag}>${listItems.map((item) => `<li>${renderInlineRichText(item)}</li>`).join("")}</${listTag}>`
    );
    listItems = [];
    listTag = "";
  };

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      flushList();
      return;
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      const level = Math.min(5, 2 + headingMatch[1].length);
      blocks.push(`<h${level}>${renderInlineRichText(headingMatch[2])}</h${level}>`);
      return;
    }

    const unorderedMatch = trimmed.match(/^[-*]\s+(.*)$/);
    if (unorderedMatch) {
      flushParagraph();
      if (listTag && listTag !== "ul") {
        flushList();
      }
      listTag = "ul";
      listItems.push(unorderedMatch[1]);
      return;
    }

    const orderedMatch = trimmed.match(/^\d+\.\s+(.*)$/);
    if (orderedMatch) {
      flushParagraph();
      if (listTag && listTag !== "ol") {
        flushList();
      }
      listTag = "ol";
      listItems.push(orderedMatch[1]);
      return;
    }

    paragraph.push(trimmed);
  });

  flushParagraph();
  flushList();

  return blocks.join("") || `<p>${renderInlineRichText(content)}</p>`;
}

function renderAiMessageBubble(message) {
  const isAssistant = message.role === "assistant";
  const label = isAssistant ? "AI 助教" : "我的问题";
  const timestamp = message.created_at || (isAssistant ? "刚刚生成" : "刚刚发送");
  const contentMarkup = isAssistant
    ? `<div class="ai-rich-text">${renderRichText(message.content)}</div>`
    : `<div class="user-rich-text"><p>${escapeHtml(message.content)}</p></div>`;

  if (isAssistant) {
    return `
      <article class="chat-entry assistant-entry">
        <div class="chat-message-meta assistant-meta">
          <span class="chat-role-pill assistant">${label}</span>
          <time>${escapeHtml(timestamp)}</time>
        </div>
        ${contentMarkup}
      </article>
    `;
  }

  return `
    <article class="chat-bubble ${message.role}">
      <div class="chat-message-meta">
        <span class="chat-role-pill ${message.role}">${label}</span>
        <time>${escapeHtml(timestamp)}</time>
      </div>
      ${contentMarkup}
    </article>
  `;
}

function renderAiConversationMarkup() {
  const messages = [...state.qaMessages];

  if (!messages.length) {
    return `
      <article class="chat-entry assistant-entry onboarding-bubble">
        <div class="chat-message-meta assistant-meta">
          <span class="chat-role-pill assistant">AI 助教</span>
          <time>准备就绪</time>
        </div>
        <div class="ai-rich-text">
          <p>可以直接围绕当前课件提问，我会优先依据课件内容给出结构化回答。</p>
          <ul>
            <li>适合做总结、梳理目录、提炼重点。</li>
            <li>如果课件内容不足，我会明确说明资料限制。</li>
          </ul>
        </div>
      </article>
    `;
  }

  return `${messages.map((message) => renderAiMessageBubble(message)).join("")}${
    state.qaLoading
      ? `
        <article class="chat-entry assistant-entry loading-bubble">
          <div class="chat-message-meta assistant-meta">
            <span class="chat-role-pill assistant">AI 助教</span>
            <time>生成中</time>
          </div>
          <div class="ai-rich-text">
            <p>正在整理课件内容并生成回答，请稍候...</p>
          </div>
        </article>
      `
      : ""
  }`;
}

async function setAiDrawerOpen(open) {
  state.aiDrawerOpen = open;
  await renderCoursewares();
}

function syncAiConversationUi() {
  const stream = document.getElementById("ai-chat-stream");
  if (!stream) {
    return;
  }
  const nearBottom = stream.scrollHeight - stream.scrollTop - stream.clientHeight < 120;
  stream.innerHTML = renderAiConversationMarkup();
  if (nearBottom || state.qaLoading) {
    stream.scrollTop = stream.scrollHeight;
  }
}

function syncAiComposerUi() {
  const textarea = document.getElementById("qa-question");
  if (textarea && textarea.value !== state.qaDraft && document.activeElement !== textarea) {
    textarea.value = state.qaDraft;
  }
  const submitButton = document.querySelector("#qa-form button[type='submit']");
  if (submitButton) {
    submitButton.disabled = state.qaLoading;
    submitButton.textContent = state.qaLoading ? "生成中..." : "发送问题";
  }
}

function persistCurrentClass() {
  if (state.currentClassId) {
    localStorage.setItem("ai_tutor_current_class", String(state.currentClassId));
  } else {
    localStorage.removeItem("ai_tutor_current_class");
  }
}

function getCurrentClass() {
  return state.classes.find((item) => item.id === state.currentClassId) || state.classes[0] || null;
}

async function loadClasses() {
  if (!state.user) {
    state.classes = [];
    state.currentClassId = null;
    persistCurrentClass();
    return;
  }

  const data = await api("/api/classes");
  state.classes = data.classes;

  if (!state.classes.find((item) => item.id === state.currentClassId)) {
    state.currentClassId = state.classes[0]?.id || null;
    persistCurrentClass();
  }
}

function stopMessagePolling() {
  state.messageSyncEnabled = false;
  if (state.messageSyncAbortController) {
    state.messageSyncAbortController.abort();
    state.messageSyncAbortController = null;
  }
}

async function runMessageSyncLoop() {
  while (state.messageSyncEnabled && state.route === "messages" && state.token) {
    const controller = new AbortController();
    state.messageSyncAbortController = controller;

    try {
      const data = await api(buildPath("/api/messages/events", { cursor: state.messageEventCursor }), {
        signal: controller.signal,
      });
      if (!state.messageSyncEnabled || state.route !== "messages") {
        break;
      }
      if (typeof data.cursor === "number") {
        state.messageEventCursor = data.cursor;
      }
      if (data.changed) {
        await syncMessagesSilently();
      }
    } catch (error) {
      if (!state.messageSyncEnabled || error.name === "AbortError") {
        break;
      }
      await sleep(1200);
    } finally {
      if (state.messageSyncAbortController === controller) {
        state.messageSyncAbortController = null;
      }
    }
  }

  state.messageSyncLoop = null;
}

function ensureMessagePolling() {
  if (state.messageSyncLoop) {
    return;
  }

  state.messageSyncEnabled = true;
  state.messageSyncLoop = runMessageSyncLoop();
}

function renderNoClassState(title, description, buttonLabel = "进入班级页") {
  const content = document.getElementById("content-area");
  if (!content) {
    return;
  }

  content.innerHTML = `
    <section class="surface empty-surface">
      <div class="section-title">
        <h3>${escapeHtml(title)}</h3>
      </div>
      <p class="empty-copy">${escapeHtml(description)}</p>
      <div class="button-row">
        <button class="primary-btn" id="open-classes-route-btn">${escapeHtml(buttonLabel)}</button>
      </div>
    </section>
  `;

  document.getElementById("open-classes-route-btn").addEventListener("click", async () => {
    state.route = "classes";
    await renderApp();
  });
}

async function bootstrap() {
  if (!state.token) {
    stopMessagePolling();
    renderAuth();
    return;
  }

  try {
    const data = await api("/api/me");
    state.user = data.user;
    state.route = "overview";
    await renderApp();
  } catch (error) {
    stopMessagePolling();
    state.token = "";
    state.user = null;
    localStorage.removeItem("ai_tutor_token");
    renderAuth();
  }
}

function renderAuth() {
  stopMessagePolling();
  app.innerHTML = `
    ${renderToastHost()}
    <div class="page-shell auth-shell">
      <section class="auth-stage">
        <div class="brand-tag">INTELLIGENT COURSE WORKSPACE</div>
        <h1>AI 助教系统</h1>
        <p>课程教学工作台</p>
      </section>
      <section class="auth-card">
        <div class="auth-card-head">
          <div>
            <span class="eyebrow">欢迎使用</span>
            <h2>${state.authMode === "login" ? "登录账号" : "创建账号"}</h2>
          </div>
          <div class="tab-switch">
            <button class="${state.authMode === "login" ? "active" : ""}" data-auth-tab="login">登录</button>
            <button class="${state.authMode === "register" ? "active" : ""}" data-auth-tab="register">注册</button>
          </div>
        </div>
        <div id="auth-form-area"></div>
      </section>
    </div>
  `;

  renderFloatingUi();
  renderAuthForm();

  document.querySelectorAll("[data-auth-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.authMode = button.dataset.authTab;
      setStatus("");
      renderAuth();
    });
  });
}

function renderAuthForm() {
  const area = document.getElementById("auth-form-area");
  if (!area) {
    return;
  }

  area.innerHTML =
    state.authMode === "login"
      ? `
        <form id="login-form" class="form-grid auth-form">
          <div class="field">
            <label for="login-username">用户名</label>
            <input id="login-username" name="username" placeholder="输入用户名" required>
          </div>
          <div class="field">
            <label for="login-password">密码</label>
            <input id="login-password" name="password" type="password" placeholder="输入密码" required>
          </div>
          <button class="primary-btn block-btn" type="submit">进入系统</button>
        </form>
      `
      : `
        <form id="register-form" class="form-grid auth-form">
          <div class="field">
            <label for="register-display-name">姓名</label>
            <input id="register-display-name" name="display_name" placeholder="输入姓名" required>
          </div>
          <div class="field">
            <label for="register-username">用户名</label>
            <input id="register-username" name="username" placeholder="输入用户名" required>
          </div>
          <div class="field split-field">
            <div class="field">
              <label for="register-role">角色</label>
              <select id="register-role" name="role">
                <option value="student">学生</option>
                <option value="teacher">教师</option>
              </select>
            </div>
            <div class="field">
              <label for="register-password">密码</label>
              <input id="register-password" name="password" type="password" placeholder="输入密码" required>
            </div>
          </div>
          <div class="field" id="register-student-field">
            <label for="register-student-number">学号</label>
            <input id="register-student-number" name="student_number" placeholder="输入学号" required>
          </div>
          <button class="primary-btn block-btn" type="submit">创建账号</button>
        </form>
      `;

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLogin);
  }

  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    document.getElementById("register-role")?.addEventListener("change", syncRegisterRoleField);
    syncRegisterRoleField();
    registerForm.addEventListener("submit", handleRegister);
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  try {
    setStatus("登录中...");
    const data = await api("/api/auth/login", {
      method: "POST",
      body: {
        username: formData.get("username"),
        password: formData.get("password"),
      },
    });
    state.token = data.token;
    state.user = data.user;
    state.messageEventCursor = 0;
    state.editingManagedUserId = null;
    localStorage.setItem("ai_tutor_token", state.token);
    state.route = "overview";
    setStatus("");
    await renderApp();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  try {
    setStatus("创建中...");
    const data = await api("/api/auth/register", {
      method: "POST",
      body: {
        display_name: formData.get("display_name"),
        username: formData.get("username"),
        role: formData.get("role"),
        student_number: formData.get("student_number"),
        password: formData.get("password"),
      },
    });
    state.token = data.token;
    state.user = data.user;
    state.messageEventCursor = 0;
    state.editingManagedUserId = null;
    localStorage.setItem("ai_tutor_token", state.token);
    state.route = "overview";
    setStatus("");
    await renderApp();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleLogout() {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch (error) {
  }

  stopMessagePolling();
  closeSheet();
  state.aiDrawerOpen = false;
  state.token = "";
  state.user = null;
  state.messageEventCursor = 0;
  state.editingManagedUserId = null;
  localStorage.removeItem("ai_tutor_token");
  renderAuth();
}

async function renderApp() {
  await loadClasses();
  const meta = getPageMeta();
  const currentClass = getCurrentClass();
  const currentLabel = currentClass?.name || "未选择班级";
  const userInitial = escapeHtml((state.user.display_name || state.user.username || "U").slice(0, 1).toUpperCase());
  const isCoursewareFocus = state.route === "coursewares" && ["student", "teacher"].includes(state.user.role);
  const isMessageFocus = state.route === "messages";
  const isDiscussionFocus = state.route === "discussions";
  const isOverviewFocus = state.route === "overview";
  const showOverviewToolbar = isOverviewFocus && state.user.role !== "admin";
  const isImmersiveWorkspace = isCoursewareFocus || isMessageFocus;
  app.innerHTML = `
    ${renderToastHost()}
    <div class="page-shell app-shell ${isCoursewareFocus ? "courseware-page-shell" : ""} ${isMessageFocus ? "message-page-shell" : ""} ${isDiscussionFocus ? "discussion-page-shell" : ""} ${isOverviewFocus ? "overview-page-shell" : ""}">
      <aside class="sidebar rail-shell" aria-label="主导航">
        <div class="rail-top">
          <button class="brand-mark rail-brand" type="button" title="AI 助教系统">
            <span>AI</span>
          </button>
          <nav class="nav-list slim-rail">
            ${routeMap[state.user.role]
              .map(
                (item) => `
                  <button
                    class="nav-btn rail-btn ${state.route === item.id ? "active" : ""}"
                    data-route="${item.id}"
                    title="${item.label}"
                    data-tooltip="${item.label}"
                    aria-label="${item.label}"
                    type="button"
                  >
                    <span class="nav-indicator"></span>
                    <span class="nav-icon">${routeIcon(item.id)}</span>
                    <span class="sr-only">${item.label}</span>
                  </button>
                `
              )
              .join("")}
          </nav>
        </div>
        <div class="rail-bottom">
          <div class="rail-profile" title="${escapeHtml(state.user.display_name)} · ${roleLabel(state.user.role)}">
            <span>${userInitial}</span>
          </div>
          <button class="rail-logout" id="logout-btn" type="button" title="退出登录" aria-label="退出登录">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <path d="m16 17 5-5-5-5"></path>
              <path d="M21 12H9"></path>
            </svg>
          </button>
        </div>
      </aside>
      <section class="workspace ${isCoursewareFocus ? "courseware-focus-workspace" : ""} ${isMessageFocus ? "message-focus-workspace" : ""} ${isDiscussionFocus ? "discussion-focus-workspace" : ""} ${isOverviewFocus ? "overview-focus-workspace" : ""}">
        ${
          isImmersiveWorkspace
            ? ""
            : `
              <header class="workspace-header minimal-header">
                <div class="workspace-copy">
                  <div class="eyebrow">${escapeHtml(meta.kicker)}</div>
                  <h2>${escapeHtml(meta.title)}</h2>
                  <p>${escapeHtml(meta.description)}</p>
                </div>
                ${
                  showOverviewToolbar
                    ? `
                      <div class="overview-toolbar">
                        <label class="overview-inline-switch">
                          <span class="overview-toolbar-label">当前班级</span>
                          <select id="overview-class-switch" aria-label="当前班级">
                            ${state.classes
                              .map(
                                (item) => `
                                  <option value="${item.id}" ${item.id === state.currentClassId ? "selected" : ""}>${escapeHtml(item.name)}</option>
                                `
                              )
                              .join("")}
                          </select>
                        </label>
                        <button class="icon-btn overview-bell-btn overview-bell-card" id="overview-notification-btn" type="button" aria-label="打开消息中心" title="打开消息中心">
                          <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5"></path>
                            <path d="M9 17a3 3 0 0 0 6 0"></path>
                          </svg>
                        </button>
                      </div>
                    `
                    : ""
                }
              </header>
              <div class="workspace-banner">
                <div class="workspace-summary">
                  <span class="soft-badge">${escapeHtml(roleLabel(state.user.role))}</span>
                  <strong>${escapeHtml(state.user.display_name)}</strong>
                  <span>${escapeHtml(currentLabel)}</span>
                </div>
                ${
                  state.user.role === "student" && state.user.student_number
                    ? `<span class="subtle-text">学号 ${escapeHtml(state.user.student_number)}</span>`
                    : `<span class="subtle-text">${escapeHtml(state.user.username)}</span>`
                }
              </div>
            `
        }
        <div id="content-area" class="workspace-content ${isMessageFocus ? "message-workspace-content" : ""} ${isDiscussionFocus ? "discussion-workspace-content" : ""} ${isOverviewFocus ? "overview-workspace-content" : ""}"></div>
      </section>
    </div>
  `;

  renderFloatingUi();
  document.querySelectorAll("[data-route]").forEach((button) => {
    button.addEventListener("click", async () => {
      closeSheet();
      state.aiDrawerOpen = false;
      state.route = button.dataset.route;
      setStatus("");
      await renderApp();
    });
  });

  document.getElementById("refresh-btn")?.addEventListener("click", renderCurrentRoute);
  document.getElementById("logout-btn").addEventListener("click", handleLogout);
  await renderCurrentRoute();
}

async function renderCurrentRoute() {
  if (state.route !== "messages") {
    stopMessagePolling();
  }
  if (
    (state.sheet?.type === "managed-user" && state.route !== "users") ||
    (String(state.sheet?.type || "").startsWith("class") && state.route !== "classes") ||
    (state.sheet?.type === "courseware" && state.route !== "coursewares") ||
    (state.sheet?.type === "discussion" && state.route !== "discussions") ||
    (state.sheet?.type === "evaluation" && !["evaluations", "survey"].includes(state.route))
  ) {
    closeSheet();
  }
  if (state.route !== "coursewares") {
    state.aiDrawerOpen = false;
  }
  const content = document.getElementById("content-area");
  if (!content) {
    return;
  }

  content.innerHTML = `
    <section class="loading-card">
      <div class="loading-dot"></div>
      <span>正在加载内容...</span>
    </section>
  `;

  try {
    if (state.route === "overview") {
      await renderOverview();
    } else if (state.route === "users") {
      await renderUsers();
    } else if (state.route === "classes") {
      await renderClasses();
    } else if (state.route === "coursewares") {
      await renderCoursewares();
    } else if (state.route === "evaluations" || state.route === "survey") {
      await renderEvaluations();
    } else if (state.route === "discussions") {
      await renderDiscussions();
    } else if (state.route === "messages") {
      await renderMessages();
    } else if (state.route === "rag") {
      await renderRag();
    }
  } catch (error) {
    setStatus(error.message, "error");
    content.innerHTML = `
      <section class="surface empty-surface">
        ${renderSectionTitle("当前页面暂时不可用")}
        <p class="empty-copy">页面主体已保留，你可以点击右上角刷新继续尝试。</p>
      </section>
    `;
  }
}

async function renderUsers() {
  const data = await api("/api/users");
  state.users = data.users;

  const managedUsers = state.users.filter((item) => item.role !== "admin");
  const editing = managedUsers.find((item) => item.id === state.editingManagedUserId) || null;
  const teacherCount = managedUsers.filter((item) => item.role === "teacher").length;
  const studentCount = managedUsers.filter((item) => item.role === "student").length;
  const content = document.getElementById("content-area");
  const showSheet = state.sheet?.type === "managed-user";

  content.innerHTML = `
    <section class="admin-split-layout admin-users-layout">
      <aside class="admin-side-stack">
        <article class="surface section-shell admin-context-card">
          ${renderSectionTitle("账号总览")}
          <div class="admin-stat-grid">
            ${renderMetricCard(teacherCount, "教师账号", "blue")}
            ${renderMetricCard(studentCount, "学生账号", "green")}
            ${renderMetricCard(managedUsers.length, "管理总数", "amber")}
          </div>
          <div class="admin-note-stack">
            <div class="focus-item compact">
              <strong>管理员账号受保护</strong>
              <span>系统保留的管理员账号不会出现在可编辑列表中，避免误删或误改。</span>
            </div>
            <div class="focus-item compact">
              <strong>学生学号唯一</strong>
              <span>学生账号要求唯一学号，教师账号不会显示该字段。</span>
            </div>
          </div>
          <div class="button-row">
            <button class="primary-btn" id="open-managed-user-sheet" type="button">新建账号</button>
          </div>
        </article>
      </aside>
      <section class="surface section-shell admin-main-panel">
        <div class="section-toolbar">
          ${renderSectionTitle("账号列表")}
        </div>
        <div class="list-stack separated-list teacher-scroll-list">
          ${
            managedUsers.length
              ? managedUsers
                  .map(
                    (item) => `
                      <article class="list-row entity-row">
                        <div class="row-main">
                          <div class="card-line">
                            <strong>${escapeHtml(item.display_name)}</strong>
                            <span class="soft-badge">${roleLabel(item.role)}</span>
                          </div>
                          <span>${escapeHtml(item.username)}${item.student_number ? ` · 学号 ${escapeHtml(item.student_number)}` : ""}</span>
                          <small>创建于 ${escapeHtml(item.created_at)}</small>
                        </div>
                        <div class="row-actions">
                          <button class="secondary-btn slim-btn" data-edit-user="${item.id}" type="button">编辑</button>
                          <button class="danger-btn slim-btn" data-delete-user="${item.id}" data-user-name="${escapeHtml(item.display_name)}" type="button">删除</button>
                        </div>
                      </article>
                    `
                  )
                  .join("")
              : renderEmpty("当前没有可管理的教师或学生账号")
          }
        </div>
      </section>
    </section>
    ${
      showSheet
        ? `
          <div class="sheet-shell">
            ${renderSheetShell({
              eyebrow: editing ? "编辑账号" : "新增账号",
              title: editing ? editing.display_name : "创建教师或学生账号",
              description: editing ? "更新基础信息、角色与登录密码。" : "创建后用户即可使用自己的身份进入系统。",
              body: renderManagedUserForm(editing),
            })}
          </div>
        `
        : ""
    }
  `;

  document.getElementById("open-managed-user-sheet")?.addEventListener("click", async () => {
    state.editingManagedUserId = null;
    state.sheet = { type: "managed-user" };
    await renderUsers();
  });

  document.querySelectorAll("[data-edit-user]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.editingManagedUserId = Number(button.dataset.editUser);
      state.sheet = { type: "managed-user" };
      await renderUsers();
    });
  });

  document.querySelectorAll("[data-delete-user]").forEach((button) => {
    button.addEventListener("click", async () => {
      const confirmed = await showDialog({
        eyebrow: "用户管理",
        title: "删除该账号？",
        description: `${button.dataset.userName} 相关的班级归属、课件或沟通记录可能会一并清理，请确认后继续。`,
        confirmText: "确认删除",
        confirmClass: "danger-btn",
      });
      if (!confirmed) {
        return;
      }
      try {
        await api(`/api/users/${button.dataset.deleteUser}`, { method: "DELETE" });
        state.editingManagedUserId = null;
        await loadClasses();
        setStatus("账号已删除。");
        await renderApp();
      } catch (error) {
        setStatus(error.message, "error");
      }
    });
  });

  if (showSheet) {
    document.getElementById("managed-user-form")?.addEventListener("submit", handleManagedUserSubmit);
    document.getElementById("managed-user-role")?.addEventListener("change", syncManagedUserRoleField);
    syncManagedUserRoleField();
    bindSheetClose(async () => {
      closeSheet();
      await renderUsers();
    });
  }
}

async function handleManagedUserSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const payload = {
    display_name: formData.get("display_name"),
    username: formData.get("username"),
    role: formData.get("role"),
    student_number: formData.get("student_number"),
    password: formData.get("password"),
  };

  try {
    if (state.editingManagedUserId) {
      await api(`/api/users/${state.editingManagedUserId}`, {
        method: "PUT",
        body: payload,
      });
      setStatus("账号信息已更新。");
    } else {
      await api("/api/users", {
        method: "POST",
        body: payload,
      });
      setStatus("账号已创建。");
    }
    closeSheet();
    await renderUsers();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function renderClasses() {
  const joinedData = await api("/api/classes");
  state.classes = joinedData.classes;
  if (!state.classes.find((item) => item.id === state.currentClassId)) {
    state.currentClassId = state.classes[0]?.id || null;
    persistCurrentClass();
  }

  const currentClass = getCurrentClass();
  const membersData = currentClass ? await api(`/api/classes/${currentClass.id}/members`) : null;
  const availableData = state.user.role === "student" ? await api("/api/classes/available") : { classes: [] };
  const userData = state.user.role === "admin" ? await api("/api/users") : { users: [] };
  const teacherOptions = userData.users.filter((item) => item.role === "teacher");
  state.availableClasses = availableData.classes;
  const content = document.getElementById("content-area");
  const showCreateSheet = state.sheet?.type === "class-create";
  const showEditSheet = state.sheet?.type === "class-edit" && currentClass;

  if (state.user.role === "admin") {
    content.innerHTML = `
      <section class="admin-split-layout admin-class-layout">
        <aside class="admin-side-stack">
          <article class="surface section-shell admin-context-card admin-class-switcher">
            <div class="section-toolbar">
              ${renderSectionTitle("全部班级")}
              <div class="button-row">
                <button class="primary-btn" id="open-create-class-sheet" type="button">新建班级</button>
                ${currentClass ? `<button class="secondary-btn" id="open-edit-class-sheet" type="button">编辑当前班级</button>` : ""}
                ${currentClass ? '<button class="danger-btn" type="button" id="delete-class-btn">删除当前班级</button>' : ""}
              </div>
            </div>
            <div class="class-card-rail teacher-class-rail">
              ${
                state.classes.length
                  ? state.classes
                      .map(
                        (item) => `
                          <article class="class-tile ${item.id === currentClass?.id ? "active" : ""}">
                            <div class="row-main class-tile-main">
                              <div class="card-line">
                                <strong>${escapeHtml(item.name)}</strong>
                                ${
                                  item.pending_request_count
                                    ? `<span class="request-pill pending">${item.pending_request_count} 条待审</span>`
                                    : ""
                                }
                              </div>
                              <span>${escapeHtml(item.teacher_name)} · ${item.student_count} 名学生</span>
                              <small>${escapeHtml(item.description || "暂无班级说明")}</small>
                            </div>
                            <div class="row-actions">
                              <button class="secondary-btn slim-btn" data-class-switch="${item.id}" type="button">${item.id === currentClass?.id ? "当前班级" : "切换"}</button>
                            </div>
                          </article>
                        `
                      )
                      .join("")
                  : renderEmpty("还没有班级")
              }
            </div>
          </article>
        </aside>
        <section class="admin-main-stack">
          <article class="surface section-shell admin-class-current-panel">
            <div class="teacher-class-current-head">
              <div class="teacher-class-current-copy">
                <span class="eyebrow">当前班级</span>
                <h3>${escapeHtml(currentClass?.name || "尚未选择班级")}</h3>
                ${currentClass?.description ? `<p>${escapeHtml(currentClass.description)}</p>` : ""}
              </div>
              <div class="teacher-class-meta-strip">
                <article class="teacher-mini-stat">
                  <span>班级成员</span>
                  <strong>${membersData?.members?.length || 0}</strong>
                </article>
                <article class="teacher-mini-stat">
                  <span>待审核</span>
                  <strong>${membersData?.pending_requests?.length || 0}</strong>
                </article>
                <article class="teacher-mini-stat">
                  <span>候选学生</span>
                  <strong>${membersData?.available_students?.length || 0}</strong>
                </article>
              </div>
            </div>
          </article>
          <div class="teacher-class-board admin-class-board">
            <article class="surface section-shell teacher-class-panel">
              ${renderSectionTitle(currentClass ? `${currentClass.name} · 入班申请` : "入班申请")}
              <div class="list-stack separated-list teacher-scroll-list">
                ${
                  membersData?.pending_requests?.length
                    ? membersData.pending_requests
                        .map(
                          (request) => `
                            <article class="list-row entity-row">
                              <div class="row-main">
                                <strong>${escapeHtml(request.display_name)}</strong>
                                <span>学生 · ${escapeHtml(request.username)}${request.student_number ? ` · 学号 ${escapeHtml(request.student_number)}` : ""}</span>
                                <small>申请时间 ${escapeHtml(request.requested_at)}</small>
                              </div>
                              <div class="row-actions">
                                <button class="secondary-btn slim-btn" data-approve-request="${request.id}" type="button">通过</button>
                                <button class="danger-btn slim-btn" data-reject-request="${request.id}" type="button">拒绝</button>
                              </div>
                            </article>
                          `
                        )
                        .join("")
                    : renderEmpty("当前班级暂无待审核申请")
                }
              </div>
            </article>
            <article class="surface section-shell teacher-class-panel">
              ${renderSectionTitle(currentClass ? `${currentClass.name} · 班级成员` : "班级成员")}
              <div class="list-stack separated-list teacher-scroll-list">
                ${
                  membersData?.members?.length
                    ? membersData.members
                        .map(
                          (member) => `
                            <article class="list-row entity-row">
                              <div class="row-main">
                                <strong>${escapeHtml(member.display_name)}</strong>
                                <span>${member.role === "teacher" ? "教师" : "学生"} · ${escapeHtml(member.username)}${
                                  member.student_number ? ` · 学号 ${escapeHtml(member.student_number)}` : ""
                                }</span>
                              </div>
                              <div class="row-actions">
                                ${
                                  member.role === "student"
                                    ? `<button class="danger-btn slim-btn" data-remove-member="${member.id}" type="button">移除</button>`
                                    : `<span class="soft-badge">${member.id === currentClass?.teacher_id ? "授课教师" : "教师"}</span>`
                                }
                              </div>
                            </article>
                          `
                        )
                        .join("")
                    : renderEmpty("当前班级还没有成员")
                }
              </div>
            </article>
            <article class="surface section-shell teacher-class-panel">
              ${renderSectionTitle("候选学生")}
              <div class="list-stack separated-list teacher-scroll-list">
                ${
                  membersData?.available_students?.length
                    ? membersData.available_students
                        .map(
                          (student) => `
                            <article class="list-row entity-row">
                              <div class="row-main">
                                <strong>${escapeHtml(student.display_name)}</strong>
                                <span>${escapeHtml(student.username)}${student.student_number ? ` · 学号 ${escapeHtml(student.student_number)}` : ""}</span>
                              </div>
                              <div class="row-actions">
                                <button class="secondary-btn slim-btn" data-add-member="${student.id}" type="button">直接加入</button>
                              </div>
                            </article>
                          `
                        )
                        .join("")
                    : renderEmpty("没有可加入的学生")
                }
              </div>
            </article>
          </div>
        </section>
      </section>
      ${
        showCreateSheet
          ? `
            <div class="sheet-shell">
              ${renderSheetShell({
                eyebrow: "新建班级",
                title: "创建新的教学班级",
                description: state.user.role === "admin" ? "创建班级并指定授课教师。" : "创建班级后即可上传课件并管理学生。",
                body: renderClassForm({ mode: "create", teacherOptions }),
              })}
            </div>
          `
          : ""
      }
      ${
        showEditSheet
          ? `
            <div class="sheet-shell">
              ${renderSheetShell({
                eyebrow: "编辑班级",
                title: currentClass.name,
                description: "更新班级名称、说明及授课教师配置。",
                body: renderClassForm({ mode: "edit", currentClass, teacherOptions }),
              })}
            </div>
          `
          : ""
      }
    `;

    document.getElementById("open-create-class-sheet")?.addEventListener("click", async () => {
      state.sheet = { type: "class-create" };
      await renderClasses();
    });
    document.getElementById("open-edit-class-sheet")?.addEventListener("click", async () => {
      if (!currentClass) {
        return;
      }
      state.sheet = { type: "class-edit" };
      await renderClasses();
    });
    const deleteClassButton = document.getElementById("delete-class-btn");
    if (deleteClassButton && currentClass) {
      deleteClassButton.addEventListener("click", async () => {
        const confirmed = await showDialog({
          eyebrow: "班级管理",
          title: "删除当前班级？",
          description: "删除后该班级下的课件、反馈与讨论数据会一并移除。",
          confirmText: "确认删除",
          confirmClass: "danger-btn",
        });
        if (!confirmed) {
          return;
        }
        try {
          await api(`/api/classes/${currentClass.id}`, { method: "DELETE" });
          state.currentClassId = null;
          persistCurrentClass();
          setStatus("班级已删除。");
          await renderApp();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    }
    document.querySelectorAll("[data-class-switch]").forEach((button) => {
      button.addEventListener("click", async () => {
        state.currentClassId = Number(button.dataset.classSwitch);
        persistCurrentClass();
        state.sheet = null;
        await renderApp();
      });
    });
    document.querySelectorAll("[data-approve-request]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await api(`/api/classes/requests/${button.dataset.approveRequest}/approve`, { method: "POST" });
          setStatus("已通过入班申请。");
          await renderClasses();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    });
    document.querySelectorAll("[data-reject-request]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await api(`/api/classes/requests/${button.dataset.rejectRequest}/reject`, { method: "POST" });
          setStatus("已拒绝入班申请。");
          await renderClasses();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    });
    document.querySelectorAll("[data-remove-member]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await api(`/api/classes/${currentClass.id}/members/${button.dataset.removeMember}`, { method: "DELETE" });
          setStatus("成员已移除。");
          await renderClasses();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    });
    document.querySelectorAll("[data-add-member]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await api(`/api/classes/${currentClass.id}/members`, {
            method: "POST",
            body: { student_id: button.dataset.addMember },
          });
          setStatus("学生已加入班级。");
          await renderClasses();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    });
    const createClassForm = document.getElementById("create-class-form");
    if (createClassForm) {
      createClassForm.addEventListener("submit", handleCreateClass);
    }
    const updateClassForm = document.getElementById("update-class-form");
    if (updateClassForm) {
      updateClassForm.addEventListener("submit", handleUpdateClass);
    }
    if (showCreateSheet || showEditSheet) {
      bindSheetClose(async () => {
        closeSheet();
        await renderClasses();
      });
    }
    return;
  }

  if (state.user.role === "teacher") {
    const pendingCount = membersData?.pending_requests?.length || 0;
    const memberCount = membersData?.members?.length || 0;
    const candidateCount = membersData?.available_students?.length || 0;

    content.innerHTML = `
      <section class="teacher-class-layout">
        <aside class="teacher-class-sidebar">
          <article class="surface section-shell teacher-class-panel teacher-class-switcher">
            <div class="section-toolbar">
              ${renderSectionTitle("我的班级")}
              <div class="button-row">
                <button class="primary-btn" id="open-create-class-sheet" type="button">新建班级</button>
                ${
                  currentClass
                    ? `<button class="secondary-btn" id="open-edit-class-sheet" type="button">编辑当前班级</button>`
                    : ""
                }
              </div>
            </div>
            <div class="class-card-rail teacher-class-rail">
              ${
                state.classes.length
                  ? state.classes
                      .map(
                        (item) => `
                          <article class="class-tile ${item.id === currentClass?.id ? "active" : ""}">
                            <div class="row-main class-tile-main">
                              <div class="card-line">
                                <strong>${escapeHtml(item.name)}</strong>
                                ${
                                  item.pending_request_count
                                    ? `<span class="request-pill pending">${item.pending_request_count} 条待审</span>`
                                    : ""
                                }
                              </div>
                              <span>${escapeHtml(item.teacher_name)} · ${item.student_count} 名学生</span>
                              <small>${escapeHtml(item.description || "暂无班级说明")}</small>
                            </div>
                            <div class="row-actions">
                              <button class="secondary-btn slim-btn" data-class-switch="${item.id}" type="button">${item.id === currentClass?.id ? "当前班级" : "切换"}</button>
                            </div>
                          </article>
                        `
                      )
                      .join("")
                  : renderEmpty("你还没有创建任何班级")
              }
            </div>
          </article>
        </aside>
        <section class="teacher-class-main">
          <article class="surface section-shell teacher-class-current-panel">
            <div class="teacher-class-current-head">
              <div class="teacher-class-current-copy">
                <span class="eyebrow">当前班级</span>
                <h3>${escapeHtml(currentClass?.name || "尚未选择班级")}</h3>
                ${currentClass?.description ? `<p>${escapeHtml(currentClass.description)}</p>` : ""}
              </div>
              <div class="teacher-class-meta-strip">
                <article class="teacher-mini-stat">
                  <span>班级成员</span>
                  <strong>${memberCount}</strong>
                </article>
                <article class="teacher-mini-stat">
                  <span>待审核</span>
                  <strong>${pendingCount}</strong>
                </article>
                <article class="teacher-mini-stat">
                  <span>候选学生</span>
                  <strong>${candidateCount}</strong>
                </article>
              </div>
            </div>
          </article>
          <div class="teacher-class-board">
            <article class="surface section-shell teacher-class-panel">
              ${renderSectionTitle(currentClass ? `${currentClass.name} · 入班申请` : "入班申请")}
              <div class="list-stack separated-list teacher-scroll-list">
                ${
                  membersData?.pending_requests?.length
                    ? membersData.pending_requests
                        .map(
                          (request) => `
                            <article class="list-row entity-row">
                              <div class="row-main">
                                <strong>${escapeHtml(request.display_name)}</strong>
                                <span>学生 · ${escapeHtml(request.username)}${request.student_number ? ` · 学号 ${escapeHtml(request.student_number)}` : ""}</span>
                                <small>申请时间 ${escapeHtml(request.requested_at)}</small>
                              </div>
                              <div class="row-actions">
                                <button class="secondary-btn slim-btn" data-approve-request="${request.id}" type="button">通过</button>
                                <button class="danger-btn slim-btn" data-reject-request="${request.id}" type="button">拒绝</button>
                              </div>
                            </article>
                          `
                        )
                        .join("")
                    : renderEmpty("当前班级暂无待审核申请")
                }
              </div>
            </article>
            <article class="surface section-shell teacher-class-panel">
              ${renderSectionTitle(currentClass ? `${currentClass.name} · 班级成员` : "班级成员")}
              <div class="list-stack separated-list teacher-scroll-list">
                ${
                  membersData?.members?.length
                    ? membersData.members
                        .map(
                          (member) => `
                            <article class="list-row entity-row">
                              <div class="row-main">
                                <strong>${escapeHtml(member.display_name)}</strong>
                                <span>${member.role === "teacher" ? "教师" : "学生"} · ${escapeHtml(member.username)}${
                                  member.student_number ? ` · 学号 ${escapeHtml(member.student_number)}` : ""
                                }</span>
                              </div>
                              <div class="row-actions">
                                ${
                                  member.role === "student"
                                    ? `<button class="danger-btn slim-btn" data-remove-member="${member.id}" type="button">移除</button>`
                                    : `<span class="soft-badge">${member.id === currentClass?.teacher_id ? "授课教师" : "教师"}</span>`
                                }
                              </div>
                            </article>
                          `
                        )
                        .join("")
                    : renderEmpty("当前班级还没有成员")
                }
              </div>
            </article>
            <article class="surface section-shell teacher-class-panel">
              ${renderSectionTitle("候选学生")}
              <div class="list-stack separated-list teacher-scroll-list">
                ${
                  membersData?.available_students?.length
                    ? membersData.available_students
                        .map(
                          (student) => `
                            <article class="list-row entity-row">
                              <div class="row-main">
                                <strong>${escapeHtml(student.display_name)}</strong>
                                <span>${escapeHtml(student.username)}${student.student_number ? ` · 学号 ${escapeHtml(student.student_number)}` : ""}</span>
                              </div>
                              <div class="row-actions">
                                <button class="secondary-btn slim-btn" data-add-member="${student.id}" type="button">直接加入</button>
                              </div>
                            </article>
                          `
                        )
                        .join("")
                    : renderEmpty("没有可加入的学生")
                }
              </div>
            </article>
          </div>
        </section>
      </section>
      ${
        showCreateSheet
          ? `
            <div class="sheet-shell">
              ${renderSheetShell({
                eyebrow: "新建班级",
                title: "创建新的教学班级",
                description: "创建班级后即可上传课件并管理学生。",
                body: renderClassForm({ mode: "create", teacherOptions }),
              })}
            </div>
          `
          : ""
      }
      ${
        showEditSheet
          ? `
            <div class="sheet-shell">
              ${renderSheetShell({
                eyebrow: "编辑班级",
                title: currentClass.name,
                description: "更新班级名称、说明及授课信息。",
                body: renderClassForm({ mode: "edit", currentClass, teacherOptions }),
              })}
            </div>
          `
          : ""
      }
    `;

    document.getElementById("open-create-class-sheet")?.addEventListener("click", async () => {
      state.sheet = { type: "class-create" };
      await renderClasses();
    });
    document.getElementById("open-edit-class-sheet")?.addEventListener("click", async () => {
      if (!currentClass) {
        return;
      }
      state.sheet = { type: "class-edit" };
      await renderClasses();
    });
    document.querySelectorAll("[data-class-switch]").forEach((button) => {
      button.addEventListener("click", async () => {
        state.currentClassId = Number(button.dataset.classSwitch);
        persistCurrentClass();
        state.sheet = null;
        await renderApp();
      });
    });
    document.querySelectorAll("[data-approve-request]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await api(`/api/classes/requests/${button.dataset.approveRequest}/approve`, { method: "POST" });
          setStatus("已通过入班申请。");
          await renderClasses();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    });
    document.querySelectorAll("[data-reject-request]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await api(`/api/classes/requests/${button.dataset.rejectRequest}/reject`, { method: "POST" });
          setStatus("已拒绝入班申请。");
          await renderClasses();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    });
    document.querySelectorAll("[data-remove-member]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await api(`/api/classes/${currentClass.id}/members/${button.dataset.removeMember}`, { method: "DELETE" });
          setStatus("成员已移除。");
          await renderClasses();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    });
    document.querySelectorAll("[data-add-member]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await api(`/api/classes/${currentClass.id}/members`, {
            method: "POST",
            body: { student_id: button.dataset.addMember },
          });
          setStatus("学生已加入班级。");
          await renderClasses();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    });
    const createClassForm = document.getElementById("create-class-form");
    if (createClassForm) {
      createClassForm.addEventListener("submit", handleCreateClass);
    }
    const updateClassForm = document.getElementById("update-class-form");
    if (updateClassForm) {
      updateClassForm.addEventListener("submit", handleUpdateClass);
    }
    if (showCreateSheet || showEditSheet) {
      bindSheetClose(async () => {
        closeSheet();
        await renderClasses();
      });
    }
    return;
  }

  content.innerHTML = `
    <section class="student-class-layout">
      <section class="surface section-shell">
        ${renderSectionTitle("已加入班级")}
        <div class="class-card-rail">
          ${
            state.classes.length
              ? state.classes
                  .map(
                    (item) => `
                      <article class="class-tile ${item.id === currentClass?.id ? "active" : ""}">
                        <div class="row-main">
                          <strong>${escapeHtml(item.name)}</strong>
                          <span>${escapeHtml(item.teacher_name)} · ${item.student_count} 名学生</span>
                        </div>
                        <div class="row-actions">
                          <button class="secondary-btn slim-btn" data-class-switch="${item.id}" type="button">切换</button>
                          <button class="danger-btn slim-btn" data-leave-class="${item.id}" type="button">退出</button>
                        </div>
                      </article>
                    `
                  )
                  .join("")
              : renderEmpty("你还没有加入任何班级")
          }
        </div>
      </section>
      <section class="surface section-shell">
        ${renderSectionTitle("可申请班级")}
        <div class="class-card-rail">
          ${
            state.availableClasses.length
              ? state.availableClasses
                  .map(
                    (item) => `
                      <article class="class-tile class-tile-inline class-apply-tile">
                        <div class="row-main class-tile-main">
                          <strong>${escapeHtml(item.name)}</strong>
                          <span>${escapeHtml(item.teacher_name)} · ${item.student_count} 名学生</span>
                        </div>
                        <div class="class-tile-side">
                          <div class="status-meta class-status-meta">
                            <span class="request-pill ${item.join_request_status || "open"}">${joinRequestLabel(item.join_request_status)}</span>
                            ${
                              item.join_requested_at
                                ? `<small>${item.join_request_status === "rejected" ? "最近拒绝" : "申请提交"} ${escapeHtml(
                                    item.join_requested_at
                                  )}</small>`
                                : '<small>提交申请后由教师审核</small>'
                            }
                          </div>
                          <div class="row-actions">
                            <button
                              class="${item.join_request_status === "rejected" ? "secondary-btn" : "primary-btn"} slim-btn"
                              data-join-class="${item.id}"
                              type="button"
                              ${item.join_request_status === "pending" ? "disabled" : ""}
                            >
                              ${item.join_request_status === "pending" ? "审核中" : item.join_request_status === "rejected" ? "重新申请" : "申请加入"}
                            </button>
                          </div>
                        </div>
                      </article>
                    `
                  )
                  .join("")
              : renderEmpty("当前没有可加入的新班级")
          }
        </div>
      </section>
    </section>
  `;

  document.querySelectorAll("[data-class-switch]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.currentClassId = Number(button.dataset.classSwitch);
      persistCurrentClass();
      await renderApp();
    });
  });
  document.querySelectorAll("[data-join-class]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await api("/api/classes/join", {
          method: "POST",
          body: { class_id: button.dataset.joinClass },
        });
        setStatus("申请已提交，等待教师审核。");
        await renderClasses();
      } catch (error) {
        setStatus(error.message, "error");
      }
    });
  });
  document.querySelectorAll("[data-leave-class]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await api(`/api/classes/${button.dataset.leaveClass}/members/${state.user.id}`, { method: "DELETE" });
        if (state.currentClassId === Number(button.dataset.leaveClass)) {
          state.currentClassId = null;
          persistCurrentClass();
        }
        setStatus("已退出班级。");
        await renderApp();
      } catch (error) {
        setStatus(error.message, "error");
      }
    });
  });
}

async function renderOverview() {
  if (state.user.role === "admin") {
    const data = await api("/api/dashboard");
    state.dashboard = data;
    document.getElementById("content-area").innerHTML = `
      <section class="overview-shell admin-overview-shell">
        <article class="surface hero-panel overview-lead">
          <div class="hero-copy">
            <span class="eyebrow">Platform Control</span>
            <h3>把用户、班级与教学资源收束到一个干净的管理视图里。</h3>
            <p>保留必要信息密度，减少装饰干扰，让平台治理、日常维护和后续功能扩展都落在统一的工作台节奏里。</p>
            <div class="button-row">
              <button class="primary-btn" id="overview-primary-btn">管理用户</button>
              <button class="ghost-btn" id="overview-secondary-btn">管理班级</button>
            </div>
          </div>
          <div class="hero-side">
            ${[
              { value: data.stats.teachers, label: "教师账号", tone: "blue" },
              { value: data.stats.students, label: "学生账号", tone: "green" },
              { value: data.stats.classes, label: "班级总数", tone: "amber" },
              { value: data.stats.coursewares, label: "课件总数", tone: "red" },
            ]
              .map((item) => renderMetricCard(item.value, item.label, item.tone))
              .join("")}
          </div>
        </article>
      </section>
    `;

    document.getElementById("overview-primary-btn").addEventListener("click", async () => {
      state.route = "users";
      await renderApp();
    });

    document.getElementById("overview-secondary-btn").addEventListener("click", async () => {
      state.route = "classes";
      await renderApp();
    });
    return;
  }

  if (!state.currentClassId) {
    renderNoClassState("暂无班级", "先创建班级或加入班级后再开始使用系统。");
    return;
  }

  const currentClass = getCurrentClass();
  const data = await api(buildPath("/api/dashboard", { class_id: state.currentClassId }));
  state.dashboard = data;

  const metrics =
    state.user.role === "teacher"
      ? [
          { value: data.stats.coursewares, label: "课件总数", tone: "blue" },
          { value: data.stats.evaluations, label: "反馈总数", tone: "green" },
          { value: data.stats.discussions, label: "讨论主题", tone: "amber" },
          { value: data.stats.unread_messages, label: "未读消息", tone: "red" },
        ]
      : [
          { value: data.stats.coursewares, label: "可学课件", tone: "blue" },
          { value: data.stats.completed_surveys, label: "已交反馈", tone: "green" },
          { value: data.stats.discussions, label: "讨论主题", tone: "amber" },
          { value: data.stats.unread_messages, label: "未读消息", tone: "red" },
        ];
  document.getElementById("content-area").innerHTML = `
    <section class="overview-shell ${state.user.role !== "admin" ? "learning-overview-shell" : ""} ${state.user.role === "teacher" ? "teacher-overview-shell" : ""}">
      <article class="surface hero-panel overview-lead">
        <div class="hero-copy">
          <span class="eyebrow">${state.user.role === "teacher" ? "Teaching Desk" : "Learning Desk"}</span>
          <h3>${escapeHtml(currentClass?.name || "当前班级")}</h3>
          <p>${state.user.role === "teacher" ? "课件、反馈、讨论和消息" : "课件、讨论、反馈和消息"}</p>
          <div class="button-row">
            <button class="primary-btn" id="overview-primary-btn">${state.user.role === "teacher" ? "管理课件" : "进入课件"}</button>
            <button class="ghost-btn" id="overview-secondary-btn">${state.user.role === "teacher" ? "查看消息" : "查看讨论"}</button>
          </div>
        </div>
        <div class="hero-side">
          ${metrics.map((item) => renderMetricCard(item.value, item.label, item.tone)).join("")}
        </div>
      </article>
    </section>
  `;

  document.getElementById("overview-primary-btn").addEventListener("click", async () => {
    state.route = "coursewares";
    await renderApp();
  });

  document.getElementById("overview-secondary-btn").addEventListener("click", async () => {
    state.route = state.user.role === "teacher" ? "messages" : "discussions";
    await renderApp();
  });

  document.getElementById("overview-class-switch")?.addEventListener("change", async (event) => {
    state.currentClassId = Number(event.target.value) || null;
    persistCurrentClass();
    await renderApp();
  });

  document.getElementById("overview-notification-btn")?.addEventListener("click", async () => {
    state.route = "messages";
    await renderApp();
  });
}

async function renderCoursewares() {
  if (!state.currentClassId) {
    renderNoClassState("暂无班级", state.user.role === "admin" ? "先在班级页创建班级，再维护课件资源。" : "先在班级页创建或加入班级，再管理课件。");
    return;
  }

  const currentClass = getCurrentClass();
  const data = await api(buildPath("/api/coursewares", { class_id: state.currentClassId }));
  state.coursewares = data.coursewares;

  if (!state.coursewares.find((item) => item.id === state.activeCoursewareId)) {
    state.activeCoursewareId = state.coursewares[0]?.id || null;
  }

  const content = document.getElementById("content-area");

  if (state.user.role === "admin") {
    const editing = state.coursewares.find((item) => item.id === state.editingCoursewareId) || null;
    const showSheet = state.sheet?.type === "courseware";

    content.innerHTML = `
      <section class="admin-split-layout admin-courseware-layout">
        <aside class="admin-side-stack">
          <article class="surface section-shell admin-context-card">
            ${renderSectionTitle("课件总览")}
            <div class="admin-stat-grid">
              ${renderMetricCard(state.coursewares.length, "已发布课件", "blue")}
              ${renderMetricCard(currentClass?.name || "-", "当前班级", "green")}
              ${renderMetricCard(state.classes.length, "班级总数", "amber")}
            </div>
            <div class="button-row">
              <button class="primary-btn" id="open-courseware-sheet" type="button">上传课件</button>
            </div>
          </article>
        </aside>
        <section class="surface section-shell admin-main-panel">
          <div class="section-toolbar">
            ${renderSectionTitle("班级课件")}
          </div>
          <div class="list-stack separated-list teacher-scroll-list">
            ${
              state.coursewares.length
                ? state.coursewares
                    .map(
                      (item) => `
                        <article class="list-row resource-row ${editing?.id === item.id ? "active" : ""}">
                          <div class="row-main">
                            <div class="resource-head">
                              <div>
                                <h4>${escapeHtml(displayCoursewareTitle(item.title))}</h4>
                                <span>${escapeHtml(item.course_name)}</span>
                              </div>
                              <time>${escapeHtml(item.uploaded_at)}</time>
                            </div>
                            <p>${escapeHtml(item.description || "暂无简介")}</p>
                          </div>
                          <div class="row-actions">
                            <a class="ghost-btn slim-btn" href="${item.viewer_url}" target="_blank" rel="noreferrer">查看</a>
                            <button class="secondary-btn slim-btn" data-edit-courseware="${item.id}" type="button">编辑</button>
                            <button class="danger-btn slim-btn" data-delete-courseware="${item.id}" type="button">删除</button>
                          </div>
                        </article>
                      `
                    )
                    .join("")
                : renderEmpty("还没有课件")
            }
          </div>
        </section>
      </section>
      ${
        showSheet
          ? `
            <div class="sheet-shell">
              ${renderSheetShell({
                eyebrow: editing ? "编辑课件" : "上传课件",
                title: editing ? editing.title : "新增课件",
                description: editing ? "更新当前课件的标题、课程名称与简介。" : "上传新课件后，当前班级学生可立即查看。",
                body: renderCoursewareForm(editing),
                wide: true,
              })}
            </div>
          `
          : ""
      }
    `;

    document.getElementById("open-courseware-sheet")?.addEventListener("click", async () => {
      state.editingCoursewareId = null;
      state.sheet = { type: "courseware" };
      setStatus("");
      await renderCoursewares();
    });

    document.querySelectorAll("[data-edit-courseware]").forEach((button) => {
      button.addEventListener("click", async () => {
        state.editingCoursewareId = Number(button.dataset.editCourseware);
        state.sheet = { type: "courseware" };
        setStatus("");
        await renderCoursewares();
      });
    });

    document.querySelectorAll("[data-delete-courseware]").forEach((button) => {
      button.addEventListener("click", async () => {
        const confirmed = await showDialog({
          eyebrow: "课件操作",
          title: "删除当前课件？",
          description: "删除后该班级下的学生将无法继续查看这份课件，相关反馈记录会一并失效。",
          confirmText: "确认删除",
          confirmClass: "danger-btn",
        });
        if (!confirmed) {
          return;
        }
        try {
          await api(`/api/coursewares/${button.dataset.deleteCourseware}`, { method: "DELETE" });
          state.editingCoursewareId = null;
          setStatus("课件已删除。");
          await renderCoursewares();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    });
    document.getElementById("courseware-form")?.addEventListener("submit", editing ? handleCoursewareUpdate : handleCoursewareCreate);
    if (showSheet) {
      bindSheetClose(async () => {
        closeSheet();
        setStatus("");
        await renderCoursewares();
      });
    }
    return;
  }

  if (state.user.role === "teacher") {
    const editing = state.coursewares.find((item) => item.id === state.editingCoursewareId) || null;
    const showSheet = state.sheet?.type === "courseware";

    content.innerHTML = `
      <section class="teacher-courseware-layout">
        <aside class="teacher-courseware-sidebar">
          <div class="course-sidebar-head course-page-head teacher-courseware-head">
            <span class="eyebrow">${escapeHtml(pageMeta.teacher.coursewares.kicker)}</span>
            <h2>${escapeHtml(pageMeta.teacher.coursewares.title)}</h2>
            <p>${escapeHtml(pageMeta.teacher.coursewares.description)}</p>
            <div class="workspace-summary compact-summary">
              <span class="soft-badge">${escapeHtml(roleLabel(state.user.role))}</span>
              <strong>${escapeHtml(currentClass?.name || "当前班级")}</strong>
            </div>
          </div>
          <article class="surface section-shell teacher-courseware-summary">
            <div class="teacher-courseware-stats">
              <article class="teacher-mini-stat">
                <span>已发布课件</span>
                <strong>${state.coursewares.length}</strong>
              </article>
              <article class="teacher-mini-stat">
                <span>当前班级</span>
                <strong>${escapeHtml(currentClass?.name || "-")}</strong>
              </article>
            </div>
            <div class="button-row">
              <button class="primary-btn" id="open-courseware-sheet" type="button">上传课件</button>
            </div>
          </article>
        </aside>
        <section class="surface section-shell teacher-courseware-panel">
          <div class="section-toolbar">
            ${renderSectionTitle("课件列表")}
          </div>
          <div class="list-stack separated-list teacher-scroll-list teacher-courseware-list">
            ${
              state.coursewares.length
                ? state.coursewares
                    .map(
                      (item) => `
                        <article class="list-row resource-row ${editing?.id === item.id ? "active" : ""}">
                          <div class="row-main">
                            <div class="resource-head">
                              <div>
                                <h4>${escapeHtml(displayCoursewareTitle(item.title))}</h4>
                                <span>${escapeHtml(item.course_name)}</span>
                              </div>
                              <time>${escapeHtml(item.uploaded_at)}</time>
                            </div>
                            <p>${escapeHtml(item.description || "暂无简介")}</p>
                          </div>
                          <div class="row-actions">
                            <a class="ghost-btn slim-btn" href="${item.viewer_url}" target="_blank" rel="noreferrer">查看</a>
                            <button class="secondary-btn slim-btn" data-edit-courseware="${item.id}" type="button">编辑</button>
                            <button class="danger-btn slim-btn" data-delete-courseware="${item.id}" type="button">删除</button>
                          </div>
                        </article>
                      `
                    )
                    .join("")
                : renderEmpty("当前班级还没有课件")
            }
          </div>
        </section>
        ${
          showSheet
            ? `
              <div class="sheet-shell">
                ${renderSheetShell({
                  eyebrow: editing ? "编辑课件" : "上传课件",
                  title: editing ? editing.title : "新增课件",
                  description: editing ? "更新当前课件的标题、课程名称与简介。" : "上传新课件后，班级学生可立即查看。",
                  body: renderCoursewareForm(editing),
                  wide: true,
                })}
              </div>
            `
            : ""
        }
      </section>
    `;

    document.getElementById("open-courseware-sheet")?.addEventListener("click", async () => {
      state.editingCoursewareId = null;
      state.sheet = { type: "courseware" };
      setStatus("");
      await renderCoursewares();
    });

    document.querySelectorAll("[data-edit-courseware]").forEach((button) => {
      button.addEventListener("click", async () => {
        state.editingCoursewareId = Number(button.dataset.editCourseware);
        state.sheet = { type: "courseware" };
        setStatus("");
        await renderCoursewares();
      });
    });

    document.querySelectorAll("[data-delete-courseware]").forEach((button) => {
      button.addEventListener("click", async () => {
        const confirmed = await showDialog({
          eyebrow: "课件操作",
          title: "删除当前课件？",
          description: "删除后该班级下的学生将无法继续查看这份课件，相关反馈记录会一并失效。",
          confirmText: "确认删除",
          confirmClass: "danger-btn",
        });
        if (!confirmed) {
          return;
        }
        try {
          await api(`/api/coursewares/${button.dataset.deleteCourseware}`, { method: "DELETE" });
          state.editingCoursewareId = null;
          setStatus("课件已删除。");
          await renderCoursewares();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });
    });
    document.getElementById("courseware-form")?.addEventListener("submit", editing ? handleCoursewareUpdate : handleCoursewareCreate);
    if (showSheet) {
      bindSheetClose(async () => {
        closeSheet();
        setStatus("");
        await renderCoursewares();
      });
    }
    return;
  }

  const current = getCurrentCourseware();
  if (current) {
    const qaData = await api(buildPath("/api/ai/messages", { courseware_id: current.id }));
    state.qaMessages = qaData.messages;
  } else {
    state.qaMessages = [];
  }

  content.innerHTML = `
    <section class="course-shell course-learning-layout">
      <section class="course-sidebar-stack">
        <div class="course-sidebar-head course-page-head">
          <span class="eyebrow">${escapeHtml(pageMeta.student.coursewares.kicker)}</span>
          <h2>${escapeHtml(pageMeta.student.coursewares.title)}</h2>
          <p>${escapeHtml(pageMeta.student.coursewares.description)}</p>
          <div class="workspace-summary compact-summary">
            <span class="soft-badge">${escapeHtml(roleLabel(state.user.role))}</span>
            <strong>${escapeHtml(currentClass?.name || "当前班级")}</strong>
          </div>
        </div>
        <aside class="surface section-shell library-sidebar course-sidebar">
        <div class="course-sidebar-title">
          <strong>课件目录</strong>
          <span>左侧浏览当前班级课件</span>
        </div>
        <div class="list-stack separated-list library-sidebar-list">
          ${
            state.coursewares.length
              ? state.coursewares
                  .map(
                    (item, index) => `
                      <button class="library-list-item ${item.id === current?.id ? "active" : ""}" data-courseware-select="${item.id}" type="button">
                        <span class="library-list-index">${String(index + 1).padStart(2, "0")}</span>
                        <span class="library-list-copy">
                          <strong>${escapeHtml(displayCoursewareTitle(item.title))}</strong>
                        </span>
                      </button>
                    `
                  )
                  .join("")
              : renderEmpty("暂无可查看课件")
          }
        </div>
        </aside>
      </section>
      ${
        current
          ? `
            <section class="course-reading-stage">
              <article class="reader-panel panel-card">
                <div class="preview-shell">
                  <div class="preview-toolbar">
                    <span class="preview-label">沉浸阅读区</span>
                    <div class="preview-toolbar-actions">
                      <a class="ghost-btn slim-btn" href="${current.viewer_url}" target="_blank" rel="noreferrer">新窗口打开</a>
                      <button class="primary-btn slim-btn" data-ai-toggle-drawer type="button">${state.aiDrawerOpen ? "收起 AI 助教" : "✨ 唤醒 AI 助教"}</button>
                    </div>
                  </div>
                  <iframe
                    class="courseware-frame"
                    src="${current.viewer_url}"
                    title="${escapeHtml(displayCoursewareTitle(current.title))}"
                  ></iframe>
                </div>
                <div class="course-pagination-shell">
                  <span class="course-pagination-label">切换课件</span>
                  <div class="course-pagination">
                    ${state.coursewares
                      .map(
                        (item, index) => `
                          <button class="course-page-btn ${item.id === current.id ? "active" : ""}" data-courseware-select="${item.id}" type="button">
                            <span class="page-index">${index + 1}</span>
                            <span class="page-copy">${escapeHtml(displayCoursewareTitle(item.title))}</span>
                          </button>
                        `
                      )
                      .join("")}
                  </div>
                </div>
              </article>
              <button class="ai-fab ${state.aiDrawerOpen ? "hidden" : ""}" data-ai-open-drawer type="button">✨ 唤醒 AI 助教</button>
              ${
                state.aiDrawerOpen
                  ? `
                    <div class="ai-drawer-backdrop" data-close-ai-drawer></div>
                    <aside class="assistant-drawer open">
                      <div class="assistant-drawer-head">
                        <div>
                          <span class="eyebrow">AI Tutor</span>
                          <h4>围绕当前课件即时提问</h4>
                        </div>
                        <div class="button-row">
                          <span class="soft-badge">GLM 在线</span>
                          <button class="toast-close" type="button" data-close-ai-drawer>&times;</button>
                        </div>
                      </div>
                      <div class="ai-assistant-toolbar">
                        <div class="suggestion-row">
                          ${[
                            "请总结这份课件的核心内容。",
                            "请梳理这份课件的知识结构。",
                            "请给出这份课件的学习建议。",
                          ]
                            .map(
                              (item) => `
                                <button class="suggestion-chip" type="button" data-ai-suggestion="${escapeHtml(item)}">
                                  ${escapeHtml(item.replace("请", "").replace("这份课件的", "").replace("。", ""))}
                                </button>
                              `
                            )
                            .join("")}
                        </div>
                        <p class="ai-panel-note">回答会优先结合当前课件内容生成，并自动保留本课件下的问答记录。</p>
                      </div>
                      <div class="chat-stream" id="ai-chat-stream">
                        ${renderAiConversationMarkup()}
                      </div>
                      <div class="prompt-shell assistant-prompt-shell">
                        <form id="qa-form" class="form-grid chat-composer">
                          <div class="field prompt-field">
                            <label for="qa-question">问题内容</label>
                            <textarea id="qa-question" name="question" placeholder="输入你的问题">${escapeHtml(state.qaDraft)}</textarea>
                          </div>
                          <div class="button-row prompt-actions">
                            <button class="ghost-btn" type="button" id="clear-qa-btn">清空记录</button>
                            <button class="primary-btn send-btn" type="submit" ${state.qaLoading ? "disabled" : ""}>${state.qaLoading ? "生成中..." : "发送问题"}</button>
                          </div>
                        </form>
                      </div>
                    </aside>
                  `
                  : ""
              }
            </section>
          `
          : `
            <article class="course-empty-panel panel-card">
              ${renderEmpty("选择一份课件后查看详情")}
            </article>
          `
      }
    </section>
  `;

  document.querySelectorAll("[data-courseware-select]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.activeCoursewareId = Number(button.dataset.coursewareSelect);
      state.aiDrawerOpen = false;
      await renderCoursewares();
    });
  });

  document.querySelectorAll("[data-ai-toggle-drawer]").forEach((node) => {
    node.addEventListener("click", async () => {
      await setAiDrawerOpen(!state.aiDrawerOpen);
    });
  });
  document.querySelectorAll("[data-ai-open-drawer]").forEach((node) => {
    node.addEventListener("click", async () => {
      await setAiDrawerOpen(true);
    });
  });
  document.querySelectorAll("[data-close-ai-drawer]").forEach((node) => {
    node.addEventListener("click", async () => {
      await setAiDrawerOpen(false);
    });
  });

  const qaForm = document.getElementById("qa-form");
  if (qaForm) {
    qaForm.addEventListener("submit", handleAiQaSubmit);
  }

  const qaTextarea = document.getElementById("qa-question");
  if (qaTextarea) {
    qaTextarea.addEventListener("input", (event) => {
      state.qaDraft = event.currentTarget.value;
    });
  }

  document.querySelectorAll("[data-ai-suggestion]").forEach((button) => {
    button.addEventListener("click", () => {
      state.qaDraft = button.dataset.aiSuggestion;
      const textarea = document.getElementById("qa-question");
      if (textarea) {
        textarea.value = state.qaDraft;
        textarea.focus();
      }
    });
  });

  const clearQaBtn = document.getElementById("clear-qa-btn");
  if (clearQaBtn && current) {
    clearQaBtn.addEventListener("click", async () => {
      try {
        await api(buildPath("/api/ai/messages", { courseware_id: current.id }), { method: "DELETE" });
        state.qaMessages = [];
        state.qaDraft = "";
        setStatus("问答记录已清空。");
        await renderCoursewares();
      } catch (error) {
        setStatus(error.message, "error");
      }
    });
  }
}

async function handleCoursewareCreate(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  try {
    setStatus("课件上传中...");
    await api("/api/coursewares", {
      method: "POST",
      body: (() => {
        formData.set("class_id", String(state.currentClassId));
        return formData;
      })(),
    });
    closeSheet();
    setStatus("课件上传成功。");
    await renderCoursewares();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleCoursewareUpdate(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  try {
    setStatus("保存中...");
    await api(`/api/coursewares/${state.editingCoursewareId}`, {
      method: "PUT",
      body: {
        title: formData.get("title"),
        course_name: formData.get("course_name"),
        description: formData.get("description"),
      },
    });
    closeSheet();
    setStatus("课件信息已更新。");
    await renderCoursewares();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleCreateClass(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  try {
    setStatus("创建班级中...");
    await api("/api/classes", {
      method: "POST",
      body: {
        name: formData.get("name"),
        description: formData.get("description"),
        teacher_id: state.user.role === "admin" ? formData.get("teacher_id") : undefined,
      },
    });
    await loadClasses();
    state.currentClassId = state.classes[0]?.id || state.currentClassId;
    persistCurrentClass();
    closeSheet();
    setStatus("班级已创建。");
    await renderApp();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleUpdateClass(event) {
  event.preventDefault();
  const currentClass = getCurrentClass();
  if (!currentClass) {
    return;
  }
  const formData = new FormData(event.currentTarget);
  try {
    setStatus("保存中...");
    await api(`/api/classes/${currentClass.id}`, {
      method: "PUT",
      body: {
        name: formData.get("name"),
        description: formData.get("description"),
        teacher_id: state.user.role === "admin" ? formData.get("teacher_id") : undefined,
      },
    });
    await loadClasses();
    closeSheet();
    setStatus("班级信息已更新。");
    await renderApp();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleAiQaSubmit(event) {
  event.preventDefault();
  const current = getCurrentCourseware();
  if (!current) {
    return;
  }

  const textarea = event.currentTarget.querySelector("textarea");
  const question = textarea.value.trim();
  if (!question) {
    return;
  }

  try {
    state.qaLoading = true;
    state.qaDraft = "";
    await renderCoursewares();
    const data = await api("/api/ai/messages", {
      method: "POST",
      body: { courseware_id: current.id, question },
    });
    state.qaLoading = false;
    state.qaMessages = data.messages || [];
    if (textarea) {
      textarea.value = "";
    }
    syncAiConversationUi();
    syncAiComposerUi();
  } catch (error) {
    state.qaLoading = false;
    state.qaDraft = question;
    setStatus(error.message, "error");
    if (state.activeCoursewareId === current.id) {
      syncAiConversationUi();
      syncAiComposerUi();
    }
  }
}

async function renderEvaluations() {
  if (!state.currentClassId) {
    renderNoClassState("暂无班级", "先在班级页创建或加入班级，再查看反馈。");
    return;
  }

  const [coursewareData, evaluationData] = await Promise.all([
    api(buildPath("/api/coursewares", { class_id: state.currentClassId })),
    api(buildPath("/api/evaluations", { class_id: state.currentClassId })),
  ]);
  state.coursewares = coursewareData.coursewares;
  state.evaluations = evaluationData.evaluations;

  const content = document.getElementById("content-area");

  if (state.user.role === "teacher") {
    const difficultyAverage = state.evaluations.length
      ? (state.evaluations.reduce((sum, item) => sum + item.difficulty, 0) / state.evaluations.length).toFixed(1)
      : "-";
    const readabilityAverage = state.evaluations.length
      ? (state.evaluations.reduce((sum, item) => sum + item.readability, 0) / state.evaluations.length).toFixed(1)
      : "-";
    const suitabilityAverage = state.evaluations.length
      ? (state.evaluations.reduce((sum, item) => sum + item.suitability, 0) / state.evaluations.length).toFixed(1)
      : "-";
    const practicalityAverage = state.evaluations.length
      ? (state.evaluations.reduce((sum, item) => sum + item.practicality, 0) / state.evaluations.length).toFixed(1)
      : "-";

    content.innerHTML = `
      <section class="stats-strip">
        ${renderMetricCard(state.evaluations.length, "反馈总数", "blue")}
        ${renderMetricCard(difficultyAverage, "内容难度", "green")}
        ${renderMetricCard(readabilityAverage, "可读性", "amber")}
        ${renderMetricCard(suitabilityAverage, "适用性", "blue")}
        ${renderMetricCard(practicalityAverage, "实用性", "red")}
      </section>
      <section class="surface">
        ${renderSectionTitle("反馈记录")}
        <div class="list-stack">
          ${
            state.evaluations.length
              ? state.evaluations
                  .map(
                    (item) => `
                      <div class="feedback-card">
                        <div class="resource-head">
                          <div>
                            <h4>${escapeHtml(displayCoursewareTitle(item.courseware_title))}</h4>
                            <span>${escapeHtml(item.course_name)} · ${escapeHtml(item.student_name)}</span>
                          </div>
                          <time>${escapeHtml(item.created_at)}</time>
                        </div>
                        <div class="score-row">
                          <span>内容难度 ${item.difficulty}/5</span>
                          <span>可读性 ${item.readability}/5</span>
                          <span>适用性 ${item.suitability}/5</span>
                          <span>实用性 ${item.practicality}/5</span>
                        </div>
                        <p>${escapeHtml(item.suggestion || "未填写改进建议")}</p>
                      </div>
                    `
                  )
                  .join("")
              : renderEmpty("暂无反馈记录")
          }
        </div>
      </section>
    `;
    return;
  }

  const showSheet = state.sheet?.type === "evaluation";
  content.innerHTML = `
    <section class="surface section-shell">
      <div class="section-toolbar">
        ${renderSectionTitle("我的反馈记录")}
        <div class="button-row">
          <button class="primary-btn" id="open-evaluation-sheet" type="button" ${state.coursewares.length ? "" : "disabled"}>提交反馈</button>
        </div>
      </div>
      <div class="list-stack separated-list">
        ${
          state.evaluations.length
            ? state.evaluations
                .map(
                  (item) => `
                    <article class="feedback-card">
                      <div class="resource-head">
                        <div>
                          <h4>${escapeHtml(displayCoursewareTitle(item.courseware_title))}</h4>
                          <span>${escapeHtml(item.course_name)}</span>
                        </div>
                        <time>${escapeHtml(item.created_at)}</time>
                      </div>
                      <div class="score-row">
                        <span>内容难度 ${item.difficulty}/5</span>
                        <span>可读性 ${item.readability}/5</span>
                        <span>适用性 ${item.suitability}/5</span>
                        <span>实用性 ${item.practicality}/5</span>
                      </div>
                      <p>${escapeHtml(item.suggestion || "未填写改进建议")}</p>
                    </article>
                  `
                )
                .join("")
            : renderEmpty("还没有提交反馈")
        }
      </div>
    </section>
    ${
      showSheet
        ? `
          <div class="sheet-shell">
            ${renderSheetShell({
              eyebrow: "提交反馈",
              title: "围绕课件完成学习评价",
              description: "每份课件限提交一次，建议在阅读完成后提交。",
              body: renderEvaluationForm(),
            })}
          </div>
        `
        : ""
    }
  `;

  document.getElementById("open-evaluation-sheet")?.addEventListener("click", async () => {
    state.sheet = { type: "evaluation" };
    await renderEvaluations();
  });
  document.getElementById("evaluation-form")?.addEventListener("submit", handleEvaluationSubmit);
  if (showSheet) {
    bindSheetClose(async () => {
      closeSheet();
      await renderEvaluations();
    });
  }
}

function renderRatingOptions(name) {
  return [1, 2, 3, 4, 5]
    .map(
      (score) => `
        <label class="rating-option">
          <input type="radio" name="${name}" value="${score}" ${score === 3 ? "checked" : ""}>
          <span class="rating-chip">
            <strong>${score}</strong>
            <small>分</small>
          </span>
        </label>
      `
    )
    .join("");
}

async function handleEvaluationSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  try {
    setStatus("提交中...");
    await api("/api/evaluations", {
      method: "POST",
      body: {
        courseware_id: formData.get("courseware_id"),
        difficulty: formData.get("difficulty"),
        readability: formData.get("readability"),
        suitability: formData.get("suitability"),
        practicality: formData.get("practicality"),
        suggestion: formData.get("suggestion"),
      },
    });
    closeSheet();
    setStatus("反馈提交成功。");
    await renderEvaluations();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function renderDiscussions() {
  if (!state.currentClassId) {
    renderNoClassState("暂无班级", "先在班级页创建或加入班级，再参与讨论。");
    return;
  }

  const data = await api(buildPath("/api/discussions", { class_id: state.currentClassId }));
  state.discussions = data.discussions;
  if (!state.discussions.find((item) => item.id === state.activeDiscussionId)) {
    state.activeDiscussionId = null;
  }
  const activeDiscussion = state.discussions.find((item) => item.id === state.activeDiscussionId) || null;

  const content = document.getElementById("content-area");
  const showSheet = state.sheet?.type === "discussion";
  content.innerHTML = `
    <section class="discussion-page-layout">
      ${
        activeDiscussion
          ? `
            <article class="surface section-shell discussion-detail-panel">
              <div class="discussion-detail-body">
                <aside class="discussion-body-card">
                  <div class="discussion-side-top">
                    <button class="ghost-btn slim-btn" id="close-discussion-detail" type="button">返回列表</button>
                    <button class="secondary-btn slim-btn" id="open-discussion-sheet" type="button">发布主题</button>
                  </div>
                  <div class="discussion-side-meta">
                    <span class="soft-badge">当前主题</span>
                    <div class="discussion-side-title">${escapeHtml(activeDiscussion.title)}</div>
                    <div class="discussion-side-chip-row">
                      <span class="soft-badge">${activeDiscussion.author_role === "teacher" ? "教师" : "学生"}</span>
                      <strong>${escapeHtml(activeDiscussion.author_name)}</strong>
                    </div>
                    <div class="discussion-side-stats">
                      <time>${escapeHtml(activeDiscussion.created_at)}</time>
                      <span class="soft-badge">${activeDiscussion.replies.length} 条回复</span>
                    </div>
                  </div>
                  <div class="discussion-body-block">
                    <span class="discussion-body-kicker">主题内容</span>
                    <div class="discussion-body-content">${escapeHtml(activeDiscussion.body).replaceAll("\n", "<br>")}</div>
                  </div>
                </aside>
                <section class="discussion-reply-shell">
                  <div class="discussion-reply-toolbar-line">
                    <div class="section-title">
                      <h3>主题回复</h3>
                      <p>${activeDiscussion.replies.length ? `共 ${activeDiscussion.replies.length} 条回复` : "暂无回复"}</p>
                    </div>
                  </div>
                  <div class="reply-list discussion-reply-list">
                    ${
                      activeDiscussion.replies.length
                        ? activeDiscussion.replies
                            .map(
                              (reply) => `
                                <div class="reply-item discussion-reply-item">
                                  <div class="card-line">
                                    <strong>${escapeHtml(reply.author_name)}</strong>
                                    <span>${escapeHtml(reply.created_at || "")}</span>
                                  </div>
                                  <span>${escapeHtml(reply.body)}</span>
                                </div>
                              `
                            )
                            .join("")
                        : '<div class="subtle-text">暂无回复</div>'
                    }
                  </div>
                  <form class="reply-form discussion-detail-form" data-discussion-id="${activeDiscussion.id}">
                    <input name="body" placeholder="输入回复内容">
                    <button class="primary-btn" type="submit">发送回复</button>
                  </form>
                </section>
              </div>
            </article>
          `
          : `
            <article class="surface section-shell discussion-list-panel">
              <div class="section-toolbar">
                ${renderSectionTitle("讨论列表")}
                <div class="button-row">
                  <button class="primary-btn" id="open-discussion-sheet" type="button">发布主题</button>
                </div>
              </div>
              <div class="list-stack separated-list discussion-topic-list teacher-scroll-list">
                ${
                  state.discussions.length
                    ? state.discussions
                        .map(
                          (item) => `
                            <article class="discussion-topic-card" data-open-discussion="${item.id}" tabindex="0" role="button">
                              <div class="resource-head">
                                <div>
                                  <h4>${escapeHtml(item.title)}</h4>
                                  <span>${escapeHtml(item.author_name)} · ${item.author_role === "teacher" ? "教师" : "学生"}</span>
                                </div>
                                <time>${escapeHtml(item.created_at)}</time>
                              </div>
                              <p>${escapeHtml(truncateText(item.body, 140))}</p>
                              <div class="discussion-topic-foot">
                                <span class="soft-badge">${item.replies.length} 条回复</span>
                                <button class="secondary-btn slim-btn" data-open-discussion-trigger="${item.id}" type="button">查看主题</button>
                              </div>
                            </article>
                          `
                        )
                        .join("")
                    : renderEmpty("当前没有讨论内容")
                }
              </div>
            </article>
          `
      }
    </section>
    ${
      showSheet
        ? `
          <div class="sheet-shell">
            ${renderSheetShell({
              eyebrow: "发布主题",
              title: "创建新的讨论内容",
              description: "发布后班级内师生都可以查看并继续回复。",
              body: renderDiscussionForm(),
            })}
          </div>
        `
        : ""
    }
  `;

  document.getElementById("open-discussion-sheet")?.addEventListener("click", async () => {
    state.sheet = { type: "discussion" };
    await renderDiscussions();
  });

  document.getElementById("discussion-form")?.addEventListener("submit", handleDiscussionSubmit);
  document.querySelectorAll("[data-open-discussion]").forEach((node) => {
    const openDiscussion = async () => {
      state.activeDiscussionId = Number(node.dataset.openDiscussion);
      await renderDiscussions();
    };
    node.addEventListener("click", openDiscussion);
    if (node.tagName !== "BUTTON") {
      node.addEventListener("keydown", async (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          await openDiscussion();
        }
      });
    }
  });
  document.getElementById("close-discussion-detail")?.addEventListener("click", async () => {
    state.activeDiscussionId = null;
    await renderDiscussions();
  });
  document.querySelectorAll(".reply-form").forEach((form) => {
    form.addEventListener("submit", handleReplySubmit);
  });
  if (showSheet) {
    bindSheetClose(async () => {
      closeSheet();
      await renderDiscussions();
    });
  }
}

async function handleDiscussionSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  try {
    setStatus("发布中...");
    await api("/api/discussions", {
      method: "POST",
      body: {
        title: formData.get("title"),
        body: formData.get("body"),
        class_id: state.currentClassId,
      },
    });
    closeSheet();
    setStatus("主题已发布。");
    await renderDiscussions();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleReplySubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  try {
    await api(`/api/discussions/${event.currentTarget.dataset.discussionId}/replies`, {
      method: "POST",
      body: { body: formData.get("body") },
    });
    setStatus("回复已发布。");
    await renderDiscussions();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function renderConversationListMarkup() {
  if (!state.conversations.length) {
    return renderEmpty("会话列表为空");
  }

  return state.conversations
    .map(
      (conversation) => `
        <div class="conversation-row compact-contact-row ${state.activeConversationId === conversation.user.id ? "active" : ""}">
          <button class="contact-card" data-conversation-id="${conversation.user.id}">
            <div class="contact-meta">
              <strong>${escapeHtml(conversation.user.display_name)}</strong>
            </div>
          </button>
          <div class="conversation-tools">
            ${conversation.unread_count ? `<span class="count-badge">${conversation.unread_count}</span>` : ""}
            <div class="row-actions">
              <button class="danger-btn slim-btn" data-remove-conversation="${conversation.user.id}">移除</button>
            </div>
          </div>
        </div>
      `
    )
    .join("");
}

function renderMessageContactsMarkup() {
  if (!state.users.length) {
    return renderEmpty("当前班级没有其他联系人");
  }

  return state.users
    .map(
      (contact) => `
        <div class="member-card compact-contact-row">
          <div class="contact-meta">
            <strong>${escapeHtml(contact.display_name)}</strong>
          </div>
          <div class="row-actions">
            ${
              contact.has_conversation
                ? '<span class="soft-badge">已在列表</span>'
                : `<button class="secondary-btn slim-btn" data-add-conversation="${contact.id}">添加</button>`
            }
          </div>
        </div>
      `
    )
    .join("");
}

function renderMessageStreamMarkup() {
  if (!state.threadMessages.length) {
    return renderEmpty("还没有消息");
  }

  return state.threadMessages
    .map(
      (message) => `
        <div class="message-bubble ${message.sender_id === state.user.id ? "mine" : "other"}">
          <p>${escapeHtml(message.body)}</p>
          <time>
            ${escapeHtml(message.created_at)}
            ${message.sender_id === state.user.id ? ` · ${message.is_read ? "已读" : "未读"}` : ""}
          </time>
        </div>
      `
    )
    .join("");
}

async function syncMessagesSilently() {
  if (state.route !== "messages" || !state.currentClassId) {
    return;
  }

  const draft = document.getElementById("message-body")?.value || "";
  const stream = document.getElementById("message-stream");
  const nearBottom = stream ? stream.scrollHeight - stream.scrollTop - stream.clientHeight < 80 : true;

  const [contactsData, conversationsData] = await Promise.all([
    api(buildPath("/api/messages/contacts", { class_id: state.currentClassId })),
    api("/api/messages/conversations"),
  ]);
  state.users = contactsData.contacts;
  state.conversations = conversationsData.conversations;

  const visibleUsers = state.conversations.map((item) => item.user);
  if (!visibleUsers.find((item) => item.id === state.activeConversationId)) {
    state.activeConversationId = visibleUsers[0]?.id || null;
  }

  const target = getConversationTarget();
  if (target) {
    const threadData = await api(`/api/messages/thread/${target.id}`);
    state.threadMessages = threadData.messages;
  } else {
    state.threadMessages = [];
    const chatPanel = document.getElementById("message-stream");
    if (chatPanel) {
      await renderMessages({ preserveDraft: draft });
      return;
    }
  }

  const conversationList = document.getElementById("conversation-list");
  if (conversationList) {
    conversationList.innerHTML = renderConversationListMarkup();
  }

  const contactsList = document.getElementById("contact-list");
  if (contactsList) {
    contactsList.innerHTML = renderMessageContactsMarkup();
  }

  const targetName = document.getElementById("message-target-name");
  const targetRole = document.getElementById("message-target-role");
  if (targetName && targetRole && target) {
    targetName.textContent = target.display_name;
    targetRole.textContent = target.role === "teacher" ? "教师" : "学生";
  }

  const streamNode = document.getElementById("message-stream");
  if (streamNode) {
    streamNode.innerHTML = renderMessageStreamMarkup();
    if (nearBottom) {
      streamNode.scrollTop = streamNode.scrollHeight;
    }
  }
}

async function renderMessages(options = {}) {
  if (!state.currentClassId) {
    stopMessagePolling();
    renderNoClassState("暂无班级", "先在班级页加入班级，再开始私信沟通。");
    return;
  }

  const meta = getPageMeta();
  const currentClass = getCurrentClass();
  const [contactsData, conversationsData] = await Promise.all([
    api(buildPath("/api/messages/contacts", { class_id: state.currentClassId })),
    api("/api/messages/conversations"),
  ]);
  state.users = contactsData.contacts;
  state.conversations = conversationsData.conversations;

  const visibleUsers = state.conversations.map((item) => item.user);
  if (!visibleUsers.find((item) => item.id === state.activeConversationId)) {
    state.activeConversationId = visibleUsers[0]?.id || null;
  }

  const target = getConversationTarget();
  if (target) {
    const threadData = await api(`/api/messages/thread/${target.id}`);
    state.threadMessages = threadData.messages;
  } else {
    state.threadMessages = [];
  }

  document.getElementById("content-area").innerHTML = `
    <section class="message-layout message-focus-layout">
      <section class="message-sidebar-stack">
        <div class="message-panel-head message-page-head">
          <span class="eyebrow">${escapeHtml(meta.kicker)}</span>
          <h2>${escapeHtml(meta.title)}</h2>
          <p>${escapeHtml(meta.description)}</p>
          <div class="workspace-summary compact-summary">
            <span class="soft-badge">${escapeHtml(roleLabel(state.user.role))}</span>
            <strong>${escapeHtml(currentClass?.name || "当前班级")}</strong>
          </div>
        </div>
        <article class="surface contact-panel message-contact-panel">
        ${renderSectionTitle("会话列表")}
        <div class="message-pane-scroll">
          <div class="list-stack conversation-stack" id="conversation-list">
            ${renderConversationListMarkup()}
          </div>
        </div>
        <div class="inline-divider"></div>
        ${renderSectionTitle("班级联系人")}
        <div class="message-pane-scroll">
          <div class="list-stack" id="contact-list">
            ${renderMessageContactsMarkup()}
          </div>
        </div>
        </article>
      </section>
      <article class="surface chat-panel">
        ${
          target
            ? `
              <div class="chat-header">
                <div>
                  <h3 id="message-target-name">${escapeHtml(target.display_name)}</h3>
                  <span id="message-target-role">${target.role === "teacher" ? "教师" : "学生"}</span>
                </div>
              </div>
              <div class="message-stream" id="message-stream">
                ${renderMessageStreamMarkup()}
              </div>
              <form id="message-form" class="message-composer">
                <textarea id="message-body" name="body" placeholder="输入消息内容"></textarea>
                <button class="primary-btn" type="submit">发送</button>
              </form>
            `
            : renderEmpty("先从左侧添加或选择一个会话")
        }
      </article>
    </section>
  `;

  const conversationList = document.getElementById("conversation-list");
  if (conversationList) {
    conversationList.addEventListener("click", async (event) => {
      const openButton = event.target.closest("[data-conversation-id]");
      if (openButton) {
        state.activeConversationId = Number(openButton.dataset.conversationId);
        await renderMessages();
        return;
      }

      const removeButton = event.target.closest("[data-remove-conversation]");
      if (removeButton) {
        try {
          await api(`/api/messages/conversations/${removeButton.dataset.removeConversation}`, {
            method: "DELETE",
          });
          if (state.activeConversationId === Number(removeButton.dataset.removeConversation)) {
            state.activeConversationId = null;
          }
          setStatus("会话已移除。");
          await renderMessages();
        } catch (error) {
          setStatus(error.message, "error");
      }
    }
  });
  document.querySelectorAll("[data-open-discussion-trigger]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      state.activeDiscussionId = Number(button.dataset.openDiscussionTrigger);
      await renderDiscussions();
    });
  });
  }

  const contactList = document.getElementById("contact-list");
  if (contactList) {
    contactList.addEventListener("click", async (event) => {
      const addButton = event.target.closest("[data-add-conversation]");
      if (!addButton) {
        return;
      }
      try {
        await api("/api/messages/conversations", {
          method: "POST",
          body: { contact_id: addButton.dataset.addConversation },
        });
        state.activeConversationId = Number(addButton.dataset.addConversation);
        setStatus("会话已加入列表。");
        await renderMessages();
      } catch (error) {
        setStatus(error.message, "error");
      }
    });
  }

  const messageForm = document.getElementById("message-form");
  if (messageForm && target) {
    messageForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const textarea = document.getElementById("message-body");
      const body = (textarea?.value || "").trim();
      try {
        await api("/api/messages", {
          method: "POST",
          body: {
            receiver_id: target.id,
            body,
          },
        });
        if (textarea) {
          textarea.value = "";
        }
        setStatus("消息已发送。");
        await syncMessagesSilently();
      } catch (error) {
        setStatus(error.message, "error");
      }
    });
  }

  if (options.preserveDraft) {
    const textarea = document.getElementById("message-body");
    if (textarea) {
      textarea.value = options.preserveDraft;
    }
  }

  ensureMessagePolling();
}

// ---------------------------------------------------------------------------
// RAG Q&A page
// ---------------------------------------------------------------------------

function renderRagMessageBubble(message) {
  const isAssistant = message.role === "assistant";
  const label = isAssistant ? "知识库 AI" : "我的问题";
  const timestamp = message.created_at || (isAssistant ? "刚刚生成" : "刚刚发送");
  const sources = Array.isArray(message.sources) ? message.sources : [];

  const contentMarkup = isAssistant
    ? `<div class="ai-rich-text">${renderRichText(message.content)}</div>
       ${
         sources.length
           ? `<div class="rag-sources">
                <span class="rag-sources-label">参考来源：</span>
                ${sources.map((s) => `<span class="rag-source-chip">${escapeHtml(s)}</span>`).join("")}
              </div>`
           : ""
       }`
    : `<div class="user-rich-text"><p>${escapeHtml(message.content)}</p></div>`;

  if (isAssistant) {
    return `
      <article class="chat-entry assistant-entry">
        <div class="chat-message-meta assistant-meta">
          <span class="chat-role-pill assistant">${label}</span>
          <time>${escapeHtml(timestamp)}</time>
        </div>
        ${contentMarkup}
      </article>
    `;
  }

  return `
    <article class="chat-bubble ${message.role}">
      <div class="chat-message-meta">
        <span class="chat-role-pill ${message.role}">${label}</span>
        <time>${escapeHtml(timestamp)}</time>
      </div>
      ${contentMarkup}
    </article>
  `;
}

function renderRagConversationMarkup() {
  const messages = [...state.ragMessages];

  if (!messages.length) {
    return `
      <article class="chat-entry assistant-entry onboarding-bubble">
        <div class="chat-message-meta assistant-meta">
          <span class="chat-role-pill assistant">知识库 AI</span>
          <time>准备就绪</time>
        </div>
        <div class="ai-rich-text">
          <p>可以围绕当前班级所有课件提问，我会从知识库中检索相关内容再回答。</p>
          <ul>
            <li>建立索引后才能使用（教师点击"建立索引"）。</li>
            <li>回答来源于真实课件内容，并标注参考来源。</li>
            <li>可跨多份课件综合查询。</li>
          </ul>
        </div>
      </article>
    `;
  }

  return `${messages.map((m) => renderRagMessageBubble(m)).join("")}${
    state.ragLoading
      ? `
        <article class="chat-entry assistant-entry loading-bubble">
          <div class="chat-message-meta assistant-meta">
            <span class="chat-role-pill assistant">知识库 AI</span>
            <time>检索中</time>
          </div>
          <div class="ai-rich-text">
            <p>正在检索知识库并生成回答，请稍候...</p>
          </div>
        </article>
      `
      : ""
  }`;
}

async function renderRag() {
  if (!state.currentClassId) {
    renderNoClassState("暂无班级", "先在班级页创建或加入班级，再使用知识库问答。");
    return;
  }

  const currentClass = getCurrentClass();
  const content = document.getElementById("content-area");

  // Load index status
  try {
    const statusData = await api(buildPath("/api/rag/status", { class_id: state.currentClassId }));
    state.ragIndexStatus = statusData;
  } catch {
    state.ragIndexStatus = { available: false, building: false, indexed: false, chunk_count: 0 };
  }

  // Load existing messages
  try {
    const msgData = await api(buildPath("/api/rag/messages", { class_id: state.currentClassId }));
    state.ragMessages = msgData.messages || [];
  } catch {
    state.ragMessages = [];
  }

  const indexStatus = state.ragIndexStatus || {};
  const isTeacher = state.user.role === "teacher" || state.user.role === "admin";
  const statusLabel = indexStatus.building
    ? "⏳ 索引构建中..."
    : indexStatus.indexed
    ? `已建立索引（${indexStatus.chunk_count} 个片段）`
    : "未建立索引";
  const statusTone = indexStatus.building ? "amber" : indexStatus.indexed ? "green" : "red";

  content.innerHTML = `
    <section class="rag-page-layout">
      <aside class="rag-sidebar">
        <div class="course-sidebar-head course-page-head">
          <span class="eyebrow">${isTeacher ? "教师端" : "学生端"}</span>
          <h2>知识库问答</h2>
          <p>基于班级全部课件的 RAG 智能问答</p>
          <div class="workspace-summary compact-summary">
            <span class="soft-badge">${escapeHtml(roleLabel(state.user.role))}</span>
            <strong>${escapeHtml(currentClass?.name || "当前班级")}</strong>
          </div>
        </div>
        <article class="surface section-shell rag-status-card">
          <div class="section-title">
            <h3>知识库状态</h3>
          </div>
          <div class="rag-status-row">
            <span class="soft-badge ${statusTone}">${statusLabel}</span>
          </div>
          ${
            isTeacher
              ? `
                <div class="button-row">
                  <button class="primary-btn" id="rag-build-btn" type="button" ${indexStatus.building ? "disabled" : ""}>
                    ${indexStatus.building ? "构建中..." : indexStatus.indexed ? "重建索引" : "建立索引"}
                  </button>
                  <button class="ghost-btn" id="rag-refresh-status-btn" type="button">刷新状态</button>
                </div>
                <p class="ai-panel-note">索引涵盖当前班级所有已上传课件，构建完成后师生均可问答。</p>
              `
              : `<p class="ai-panel-note">${indexStatus.indexed ? "知识库已就绪，直接在右侧提问即可。" : "知识库尚未建立，请联系教师构建索引。"}</p>`
          }
        </article>
      </aside>
      <section class="rag-chat-section surface section-shell">
        <div class="assistant-drawer-head">
          <div>
            <span class="eyebrow">RAG Chat</span>
            <h4>向全班知识库提问</h4>
          </div>
          <div class="button-row">
            <span class="soft-badge ${statusTone}">${indexStatus.indexed ? "索引就绪" : "待建立"}</span>
            <button class="ghost-btn slim-btn" id="rag-clear-btn" type="button">清空记录</button>
          </div>
        </div>
        <div class="ai-assistant-toolbar">
          <div class="suggestion-row">
            ${[
              "请总结这个班级所有课件的核心主题。",
              "知识库中有哪些关于机器学习的内容？",
              "请列举课件中提到的重要算法。",
            ]
              .map(
                (s) => `
                  <button class="suggestion-chip" type="button" data-rag-suggestion="${escapeHtml(s)}">
                    ${escapeHtml(s.replace("请", "").replace("。", "").slice(0, 20))}
                  </button>
                `
              )
              .join("")}
          </div>
        </div>
        <div class="chat-stream" id="rag-chat-stream">
          ${renderRagConversationMarkup()}
        </div>
        <div class="prompt-shell assistant-prompt-shell">
          <form id="rag-form" class="form-grid chat-composer">
            <div class="field prompt-field">
              <label for="rag-question">问题内容</label>
              <textarea id="rag-question" name="question" placeholder="输入你对课件知识库的问题">${escapeHtml(state.ragDraft)}</textarea>
            </div>
            <div class="button-row prompt-actions">
              <button class="primary-btn send-btn" type="submit" ${state.ragLoading || !indexStatus.indexed ? "disabled" : ""}>
                ${state.ragLoading ? "检索中..." : "发送问题"}
              </button>
            </div>
          </form>
        </div>
      </section>
    </section>
  `;

  const stream = document.getElementById("rag-chat-stream");
  if (stream) {
    stream.scrollTop = stream.scrollHeight;
  }

  document.getElementById("rag-build-btn")?.addEventListener("click", async () => {
    try {
      setStatus("正在启动索引构建...");
      await api("/api/rag/index", { method: "POST", body: { class_id: state.currentClassId } });
      setStatus("索引构建任务已启动，请稍后刷新状态。");
      await renderRag();
    } catch (error) {
      setStatus(error.message, "error");
    }
  });

  document.getElementById("rag-refresh-status-btn")?.addEventListener("click", async () => {
    await renderRag();
  });

  document.getElementById("rag-clear-btn")?.addEventListener("click", async () => {
    try {
      await api(buildPath("/api/rag/messages", { class_id: state.currentClassId }), { method: "DELETE" });
      state.ragMessages = [];
      state.ragDraft = "";
      setStatus("问答记录已清空。");
      await renderRag();
    } catch (error) {
      setStatus(error.message, "error");
    }
  });

  document.querySelectorAll("[data-rag-suggestion]").forEach((button) => {
    button.addEventListener("click", () => {
      state.ragDraft = button.dataset.ragSuggestion;
      const textarea = document.getElementById("rag-question");
      if (textarea) {
        textarea.value = state.ragDraft;
        textarea.focus();
      }
    });
  });

  const ragTextarea = document.getElementById("rag-question");
  if (ragTextarea) {
    ragTextarea.addEventListener("input", (event) => {
      state.ragDraft = event.currentTarget.value;
    });
  }

  const ragForm = document.getElementById("rag-form");
  if (ragForm) {
    ragForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const question = (document.getElementById("rag-question")?.value || "").trim();
      if (!question) {
        return;
      }
      state.ragLoading = true;
      state.ragDraft = "";
      await renderRag();
      try {
        const data = await api("/api/rag/ask", {
          method: "POST",
          body: { class_id: state.currentClassId, question },
        });
        state.ragLoading = false;
        state.ragMessages = data.messages || [];
        const s = document.getElementById("rag-chat-stream");
        if (s) {
          s.innerHTML = renderRagConversationMarkup();
          s.scrollTop = s.scrollHeight;
        }
      } catch (error) {
        state.ragLoading = false;
        state.ragDraft = question;
        setStatus(error.message, "error");
        await renderRag();
      }
    });
  }
}

bootstrap();
