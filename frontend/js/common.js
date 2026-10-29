// 导航栏 + 登录注册弹窗 + 鉴权守卫

function requireLogin() {
    if (!getToken()) {
      alert("请先登录");
      location.href = "index.html";
      return false;
    }
    return true;
  }
  
  function renderNavbar(active) {
    const user = getUser();
    const el = document.getElementById("navbar");
    if (!el) return;
    el.innerHTML = `
      <div class="nav-inner">
        <div class="nav-brand">📋 问卷系统</div>
        <div class="nav-links">
        ${user ? `<a href="/home.html" class="${active === 'home' ? 'active' : ''}">个人主页</a>` : ""}
        ${user ? `<a href="/create.html" class="${active === 'create' ? 'active' : ''}">创建问卷</a>` : ""}
        ${user ? `<a href="/question-bank.html" class="${active === 'bank' ? 'active' : ''}">题目库</a>` : ""}
        </div>
        <div class="nav-user">
          ${
            user
              ? `<span class="username">👤 ${user.username}</span>
                 <button class="btn btn-sm" onclick="logout()">退出</button>`
              : `<button class="btn btn-sm btn-primary" onclick="openAuthModal()">登录 / 注册</button>`
          }
        </div>
      </div>`;
  }
  
  function logout() {
    clearAuth();
    location.href = "index.html";
  }
  
  // ---------- 登录注册弹窗 ----------
  function ensureAuthModal() {
    if (document.getElementById("authModal")) return;
    const div = document.createElement("div");
    div.id = "authModal";
    div.className = "modal-mask hidden";
    div.innerHTML = `
      <div class="modal">
        <h3 id="authTitle">登录</h3>
        <div class="form-group">
          <label>用户名</label>
          <input id="authUsername" placeholder="3-30 个字符" />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input id="authPassword" type="password" placeholder="至少 6 位" />
        </div>
        <div class="modal-actions">
          <button class="btn" onclick="closeAuthModal()">取消</button>
          <button class="btn btn-primary" id="authSubmitBtn" onclick="submitAuth()">登录</button>
        </div>
        <p class="auth-switch">
          <a href="javascript:void(0)" onclick="switchAuthMode()" id="authSwitchLink">没有账号？去注册</a>
        </p>
        <p class="error" id="authError"></p>
      </div>`;
    document.body.appendChild(div);
  }
  
  let authMode = "login";
  function openAuthModal() {
    ensureAuthModal();
    authMode = "login";
    updateAuthModal();
    document.getElementById("authModal").classList.remove("hidden");
  }
  function closeAuthModal() {
    document.getElementById("authModal").classList.add("hidden");
    document.getElementById("authError").textContent = "";
  }
  function switchAuthMode() {
    authMode = authMode === "login" ? "register" : "login";
    updateAuthModal();
  }
  function updateAuthModal() {
    document.getElementById("authTitle").textContent = authMode === "login" ? "登录" : "注册";
    document.getElementById("authSubmitBtn").textContent = authMode === "login" ? "登录" : "注册";
    document.getElementById("authSwitchLink").textContent =
      authMode === "login" ? "没有账号？去注册" : "已有账号？去登录";
    document.getElementById("authError").textContent = "";
  }
  async function submitAuth() {
    const u = document.getElementById("authUsername").value.trim();
    const p = document.getElementById("authPassword").value;
    const errEl = document.getElementById("authError");
    errEl.textContent = "";
    try {
      const fn = authMode === "login" ? api.login : api.register;
      const data = await fn(u, p);
      setAuth(data.access_token, data.user);
      closeAuthModal();
      location.reload();
    } catch (e) {
      errEl.textContent = e.detail || "操作失败";
    }
  }