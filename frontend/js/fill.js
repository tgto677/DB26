// 依赖 api.js 中的 api / getToken

let fillSurvey = null;         // 当前填写的问卷文档
let fillAnswers = {};          // {qid: value}
let fillPath = [];             // 当前访问路径
let fillIndex = 0;             // 当前在 fillPath 的位置

// 根据已有答案计算访问路径（与后端逻辑一致）
function computePath(questions, answersMap) {
  const idToIndex = {};
  questions.forEach((q, i) => (idToIndex[q.id] = i));
  const visited = [];
  let i = 0, guard = 0;
  const maxSteps = questions.length * 10 + 10;
  while (i >= 0 && i < questions.length) {
    if (++guard > maxSteps) break;
    const q = questions[i];
    visited.push(q.id);
    let hit = false, target = null;
    for (const rule of q.jump_rules || []) {
      if (rule.option_value == null) continue;
      const val = answersMap[q.id];
      if (q.type === "multiple") {
        if (Array.isArray(val) && val.includes(rule.option_value)) { hit = true; target = rule.target_question_id; break; }
      } else {
        if (val != null && String(val) === String(rule.option_value)) { hit = true; target = rule.target_question_id; break; }
      }
    }
    if (hit) {
      if (target == null || target === "__end__") break;
      if (!(target in idToIndex)) break;
      i = idToIndex[target];
    } else i++;
  }
  return visited;
}

async function openFillModal(surveyId) {
  try {
    const survey = await api.getSurvey(surveyId);
    fillSurvey = survey;
    fillAnswers = {};
    fillPath = computePath(survey.questions, fillAnswers);
    fillIndex = 0;
    renderFillStep();
  } catch (e) {
    alert(e.detail || "无法加载问卷");
  }
}

function renderFillStep() {
  const mask = document.getElementById("fillModal");
  mask.classList.remove("hidden");
  const body = document.getElementById("fillBody");
  const progress = document.getElementById("fillProgress");

  // 全部走完
  if (fillIndex >= fillPath.length) {
    body.innerHTML = `<p>已完成所有题目，确认提交？</p>`;
    progress.textContent = "";
    document.getElementById("fillNextBtn").textContent = "提交";
    document.getElementById("fillNextBtn").onclick = submitFill;
    return;
  }

  const qid = fillPath[fillIndex];
  const q = fillSurvey.questions.find((x) => x.id === qid);
  progress.textContent = `第 ${fillIndex + 1} / ${fillPath.length} 题`;
  document.getElementById("fillNextBtn").textContent = fillIndex === fillPath.length - 1 ? "提交" : "下一题";
  document.getElementById("fillNextBtn").onclick = nextFillStep;

  let html = `<div class="q-title">${escapeHtml(q.title)}${q.required ? '<span class="req-star">*</span>' : ""}</div>`;
  const val = fillAnswers[qid];

  if (q.type === "single") {
    for (const o of q.options) {
      html += `<label class="fill-option">
        <input type="radio" name="fill_${qid}" value="${escapeAttr(o.value)}" ${val === o.value ? "checked" : ""}/>
        ${escapeHtml(o.label)}</label>`;
    }
  } else if (q.type === "multiple") {
    const hint = [];
    if (q.min_choices) hint.push(`至少 ${q.min_choices} 项`);
    if (q.max_choices) hint.push(`最多 ${q.max_choices} 项`);
    for (const o of q.options) {
      const checked = Array.isArray(val) && val.includes(o.value) ? "checked" : "";
      html += `<label class="fill-option">
        <input type="checkbox" name="fill_${qid}" value="${escapeAttr(o.value)}" ${checked}/>
        ${escapeHtml(o.label)}</label>`;
    }
    if (hint.length) html += `<div class="fill-hint">${hint.join("，")}</div>`;
  } else if (q.type === "text") {
    const ml = q.max_length ? `maxlength="${q.max_length}"` : "";
    html += `<textarea id="fill_input_${qid}" rows="3" ${ml} placeholder="请输入">${val || ""}</textarea>`;
    if (q.min_length || q.max_length) {
      html += `<div class="fill-hint">${q.min_length ? `至少 ${q.min_length} 字` : ""}${q.max_length ? `，最多 ${q.max_length} 字` : ""}</div>`;
    }
  } else if (q.type === "number") {
    const step = q.integer_only ? "1" : "any";
    html += `<input type="number" id="fill_input_${qid}" step="${step}" value="${val != null ? val : ""}" placeholder="请输入数字"/>`;
    const hint = [];
    if (q.min_value != null) hint.push(`≥ ${q.min_value}`);
    if (q.max_value != null) hint.push(`≤ ${q.max_value}`);
    if (q.integer_only) hint.push("整数");
    if (hint.length) html += `<div class="fill-hint">${hint.join("，")}</div>`;
  }

  body.innerHTML = html;
  document.getElementById("fillError").textContent = "";
}

// 读取当前题答案并校验（前端同步校验，后端仍会复核）
function readCurrentAnswer() {
  const qid = fillPath[fillIndex];
  const q = fillSurvey.questions.find((x) => x.id === qid);
  let value = null;
  if (q.type === "single") {
    const el = document.querySelector(`input[name="fill_${qid}"]:checked`);
    value = el ? el.value : null;
  } else if (q.type === "multiple") {
    value = Array.from(document.querySelectorAll(`input[name="fill_${qid}"]:checked`)).map((e) => e.value);
    if (value.length === 0) value = null;
  } else if (q.type === "text") {
    const v = document.getElementById(`fill_input_${qid}`).value.trim();
    value = v === "" ? null : v;
  } else if (q.type === "number") {
    const raw = document.getElementById(`fill_input_${qid}`).value;
    value = raw === "" ? null : Number(raw);
  }
  return { q, value };
}

function validateAnswer(q, value) {
  const empty = value == null || value === "" || (Array.isArray(value) && value.length === 0);
  if (empty) {
    if (q.required) return `「${q.title}」为必填`;
    return null;
  }
  if (q.type === "multiple") {
    if (q.min_choices && value.length < q.min_choices) return `「${q.title}」至少选 ${q.min_choices} 项`;
    if (q.max_choices && value.length > q.max_choices) return `「${q.title}」最多选 ${q.max_choices} 项`;
  }
  if (q.type === "text") {
    if (q.min_length && value.length < q.min_length) return `「${q.title}」至少 ${q.min_length} 字`;
    if (q.max_length && value.length > q.max_length) return `「${q.title}」最多 ${q.max_length} 字`;
  }
  if (q.type === "number") {
    if (isNaN(value)) return `「${q.title}」必须是数字`;
    if (q.integer_only && !Number.isInteger(value)) return `「${q.title}」必须为整数`;
    if (q.min_value != null && value < q.min_value) return `「${q.title}」不能小于 ${q.min_value}`;
    if (q.max_value != null && value > q.max_value) return `「${q.title}」不能大于 ${q.max_value}`;
  }
  return null;
}

function nextFillStep() {
  const { q, value } = readCurrentAnswer();
  const err = validateAnswer(q, value);
  if (err) {
    document.getElementById("fillError").textContent = err;
    return;
  }
  if (value == null) delete fillAnswers[q.id];
  else fillAnswers[q.id] = value;

  // 重算路径（跳转规则可能改变后续）
  const newPath = computePath(fillSurvey.questions, fillAnswers);
  fillPath = newPath;
  fillIndex = fillPath.indexOf(q.id) + 1;

  renderFillStep();
}

async function submitFill() {
  const errEl = document.getElementById("fillError");
  errEl.textContent = "";
  // 最终提交前再全部校验一遍（只校验路径上的题）
  for (const qid of fillPath) {
    const q = fillSurvey.questions.find((x) => x.id === qid);
    const err = validateAnswer(q, fillAnswers[qid]);
    if (err) { errEl.textContent = err; return; }
  }
  const answers = Object.entries(fillAnswers).map(([question_id, value]) => ({ question_id, value }));
  try {
    await api.submit(fillSurvey.id, answers);
    closeFillModal();
    alert("提交成功！");
  } catch (e) {
    errEl.textContent = e.detail || "提交失败";
  }
}

function closeFillModal() {
  document.getElementById("fillModal").classList.add("hidden");
}

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }