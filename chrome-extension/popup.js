/**
 * PFA 雪球助手 — Popup UI Logic
 */

let config = { userIds: [], symbols: [], monitorUrls: [] };

// ===================================================================
// Tag rendering helpers
// ===================================================================

function renderTags(containerId, items, configKey) {
  const el = document.getElementById(containerId);
  el.innerHTML = "";
  items.forEach((item) => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.innerHTML = `${item} <span class="remove" data-key="${configKey}" data-val="${item}">×</span>`;
    el.appendChild(tag);
  });
  el.querySelectorAll(".remove").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const key = e.target.dataset.key;
      const val = e.target.dataset.val;
      config[key] = config[key].filter((v) => v !== val);
      renderAll();
    });
  });
}

function renderAll() {
  renderTags("user-tags", config.userIds, "userIds");
  renderTags("symbol-tags", config.symbols, "symbols");
  renderTags("url-tags", config.monitorUrls, "monitorUrls");
}

// ===================================================================
// Input handlers: Enter to add
// ===================================================================

function setupInput(inputId, configKey) {
  document.getElementById(inputId).addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const val = e.target.value.trim();
      if (val && !config[configKey].includes(val)) {
        config[configKey].push(val);
        e.target.value = "";
        renderAll();
      }
    }
  });
}

// ===================================================================
// Status checks
// ===================================================================

async function checkStatus() {
  // Check PFA server
  const dotServer = document.getElementById("dot-server");
  const serverStatus = document.getElementById("server-status");
  try {
    const resp = await fetch("http://localhost:8765", { method: "OPTIONS" });
    dotServer.className = "status-dot dot-green";
    serverStatus.textContent = "在线";
  } catch {
    dotServer.className = "status-dot dot-gray";
    serverStatus.textContent = "离线";
  }

  // Check Xueqiu login
  const dotXq = document.getElementById("dot-xueqiu");
  const xqStatus = document.getElementById("xueqiu-status");
  try {
    const cookies = await chrome.cookies.getAll({ domain: ".xueqiu.com" });
    const hasToken = cookies.some((c) => c.name === "xq_a_token" && c.value);
    const isLogin = cookies.some((c) => c.name === "xq_is_login" && c.value === "1");
    if (isLogin) {
      dotXq.className = "status-dot dot-green";
      xqStatus.textContent = "已登录";
    } else if (hasToken) {
      dotXq.className = "status-dot dot-green";
      xqStatus.textContent = "有 Token";
    } else {
      dotXq.className = "status-dot dot-red";
      xqStatus.textContent = "未登录";
    }
  } catch {
    dotXq.className = "status-dot dot-gray";
    xqStatus.textContent = "未知";
  }

  // Last fetch info
  chrome.runtime.sendMessage({ action: "getStatus" }, (data) => {
    if (data) {
      if (data.lastFetch) {
        const d = new Date(data.lastFetch);
        document.getElementById("last-fetch").textContent = d.toLocaleTimeString();
      }
      if (data.lastCount !== undefined) {
        document.getElementById("last-count").textContent = `${data.lastCount} 条`;
      }
      // Load config
      config.userIds = data.userIds || config.userIds;
      config.symbols = data.symbols || config.symbols;
      config.monitorUrls = data.monitorUrls || config.monitorUrls;
      renderAll();
    }
  });
}

// ===================================================================
// Button handlers
// ===================================================================

document.getElementById("btn-fetch").addEventListener("click", () => {
  const statusText = document.getElementById("status-text");
  statusText.textContent = "抓取中...";
  chrome.runtime.sendMessage({ action: "fetchNow" }, (resp) => {
    if (resp && resp.success) {
      statusText.textContent = `抓取完成: ${resp.count} 条`;
      checkStatus();
    } else {
      statusText.textContent = "抓取失败";
    }
  });
});

document.getElementById("btn-save").addEventListener("click", () => {
  chrome.runtime.sendMessage(
    { action: "saveConfig", config },
    (resp) => {
      document.getElementById("status-text").textContent = "配置已保存";
    }
  );
});

// ===================================================================
// Init
// ===================================================================

setupInput("new-user", "userIds");
setupInput("new-symbol", "symbols");
setupInput("new-url", "monitorUrls");
checkStatus();
