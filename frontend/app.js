const LEGACY_SESSION_KEY = 'text2sql_session_id';
const LEGACY_CHAT_HISTORY_KEY = 'text2sql_chat_history';
const CLIENT_ID_KEY = 'text2sql_client_id';
const ACTIVE_SESSION_KEY = 'text2sql_active_session';
const API_BASE = '';

const form = document.getElementById('query-form');
const useCaseSelect = document.getElementById('use-case');
const messageInput = document.getElementById('message');
const submitBtn = document.getElementById('submit-btn');
const outputPlaceholder = document.getElementById('output-placeholder');
const outputContent = document.getElementById('output-content');
const outputError = document.getElementById('output-error');
const chatScroll = document.getElementById('chat-scroll');
const chatThread = document.getElementById('chat-thread');
const composerStatus = document.getElementById('composer-status');
const intentActions = document.getElementById('intent-actions');
const intentActionsLabel = document.getElementById('intent-actions-label');
const intentYesBtn = document.getElementById('intent-yes-btn');
const intentNoBtn = document.getElementById('intent-no-btn');
const chatListEl = document.getElementById('chat-list');
const newChatBtn = document.getElementById('new-chat-btn');
const deleteConfirmModal = document.getElementById('delete-confirm-modal');
const deleteConfirmCancelBtn = document.getElementById('delete-confirm-cancel');
const deleteConfirmDeleteBtn = document.getElementById('delete-confirm-delete');
const domainSelectorEl = document.getElementById('domain-selector');
const pipelineProgressEl = document.getElementById('pipeline-progress');
const welcomePanel = document.getElementById('welcome-panel');

let activeSessionId = null;
let cachedSessions = [];
let pendingDeleteSessionId = null;
let pendingIntentState = null;
let domainInfo = null;
let pipelineInterval = null;

const PROMPT_CORRECTED_QUESTION = 'Please provide a corrected question.';

const COPY_SQL_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>`;

const DOMAIN_ICONS = {
  healthcare: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>`,
  retail: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 002 1.61h9.72a2 2 0 002-1.61L23 6H6"/></svg>`,
  finance: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>`,
};

const PIPELINE_STEPS = ['intent', 'tables', 'columns', 'fewshot', 'sql'];

// ===== Utility =====

function removeLegacyKeys() {
  try {
    localStorage.removeItem(LEGACY_CHAT_HISTORY_KEY);
    localStorage.removeItem(LEGACY_SESSION_KEY);
  } catch (_e) { /* ignore */ }
}

function randomUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function ensureClientId() {
  try {
    let id = localStorage.getItem(CLIENT_ID_KEY);
    if (!id) { id = randomUUID(); localStorage.setItem(CLIENT_ID_KEY, id); }
    return id;
  } catch (_e) { return randomUUID(); }
}

function getClientHeaders() {
  return { 'X-Client-Id': ensureClientId() };
}

function persistActiveSession(id) {
  try { if (id) localStorage.setItem(ACTIVE_SESSION_KEY, id); else localStorage.removeItem(ACTIVE_SESSION_KEY); }
  catch (_e) { /* ignore */ }
}

function getRememberedSessionId() {
  try { return localStorage.getItem(ACTIVE_SESSION_KEY); } catch (_e) { return null; }
}

function updateSessionHeader(id) { /* no-op: session id removed from header */ }

function getActiveSessionId() { return activeSessionId; }

function setActiveSessionId(id) {
  const sid = id != null && String(id).trim() ? String(id).trim() : null;
  activeSessionId = sid;
  persistActiveSession(sid);
}

function sidebarLabelForSession(s) {
  const t = s.title && String(s.title).trim();
  if (t) return t;
  const raw = String(s.session_id || '').replace(/-/g, '');
  const tail = raw.slice(-6) || raw.slice(0, 6) || '…';
  return `New chat (${tail})`;
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

// ===== Domain selector =====

function resetDomainSelect() {
  useCaseSelect.value = '';
  domainSelectorEl.querySelectorAll('.domain-btn').forEach(b => b.classList.remove('is-selected'));
  updatePlaceholderForDomain('');
}

function selectDomain(name, opts = {}) {
  const previousDomain = useCaseSelect.value;
  useCaseSelect.value = name;
  domainSelectorEl.querySelectorAll('.domain-btn').forEach(b => {
    b.classList.toggle('is-selected', b.dataset.domain === name);
  });
  updatePlaceholderForDomain(name);

  if (opts.silent) return;

  if (previousDomain && previousDomain !== name && chatThread.children.length > 0) {
    setActiveSessionId(null);
    clearChatThread();
    pendingIntentState = null;
    hideIntentActions();
    showError('');
    showContextualSuggestions();
    void refreshSidebar();
  } else if (chatThread.children.length === 0) {
    showContextualSuggestions();
  }
}

function renderDomainButtons(domains) {
  if (!domainSelectorEl) return;
  domainSelectorEl.innerHTML = '';
  (domains || []).forEach(d => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'domain-btn';
    btn.dataset.domain = d.name;
    btn.innerHTML = `<span class="domain-btn-icon">${DOMAIN_ICONS[d.name] || ''}</span>${d.display_name}`;
    btn.addEventListener('click', () => selectDomain(d.name));
    domainSelectorEl.appendChild(btn);
  });
}

function updatePlaceholderForDomain(domain) {
  if (!messageInput) return;
  if (domain) {
    const name = domain.charAt(0).toUpperCase() + domain.slice(1);
    messageInput.placeholder = `Ask a question about ${name} data...`;
  } else {
    messageInput.placeholder = 'Select a domain, then ask a question...';
  }
}

// ===== Welcome screen =====

async function loadDomainInfo() {
  try {
    const res = await fetch(`${API_BASE}/domain-info`);
    if (!res.ok) return null;
    const data = await res.json();
    domainInfo = data.domains || [];
    return domainInfo;
  } catch (e) {
    console.warn('domain-info failed', e);
    return null;
  }
}

function renderWelcomePanel(domains) {
  if (!welcomePanel) return;
  if (!domains || !domains.length) {
    welcomePanel.innerHTML = '<p style="color:var(--text-muted)">Loading...</p>';
    return;
  }

  const cardsHtml = domains.map(d => {
    const icon = DOMAIN_ICONS[d.name] || '';
    const tablePills = d.tables.slice(0, 6).map(t =>
      `<span class="table-tag">${escapeHtml(t)}</span>`
    ).join('') + (d.tables.length > 6 ? `<span class="table-tag table-tag--more">+${d.tables.length - 6}</span>` : '');
    const examplesHtml = (d.example_questions || []).map(q =>
      `<li><button type="button" class="example-question-btn" data-domain="${d.name}" data-question="${escapeHtml(q)}">${escapeHtml(q)}</button></li>`
    ).join('');
    return `
      <div class="domain-card">
        <div class="domain-card-header">
          <div class="domain-card-icon domain-card-icon--${d.name}">${icon}</div>
          <h3 class="domain-card-title">${d.display_name}</h3>
        </div>
        <p class="domain-card-desc">${d.description}</p>
        <div class="domain-card-tables">${tablePills}</div>
        <ul class="domain-card-examples">${examplesHtml}</ul>
      </div>
    `;
  }).join('');

  const pipelineHtml = `
    <div class="pipeline-diagram">
      <div class="pipeline-diagram-step"><div class="pipeline-diagram-icon">1</div><span class="pipeline-diagram-label">Intent</span></div>
      <div class="pipeline-diagram-arrow"></div>
      <div class="pipeline-diagram-step"><div class="pipeline-diagram-icon">2</div><span class="pipeline-diagram-label">Tables</span></div>
      <div class="pipeline-diagram-arrow"></div>
      <div class="pipeline-diagram-step"><div class="pipeline-diagram-icon">3</div><span class="pipeline-diagram-label">Columns</span></div>
      <div class="pipeline-diagram-arrow"></div>
      <div class="pipeline-diagram-step"><div class="pipeline-diagram-icon">4</div><span class="pipeline-diagram-label">Few-Shot</span></div>
      <div class="pipeline-diagram-arrow"></div>
      <div class="pipeline-diagram-step"><div class="pipeline-diagram-icon">5</div><span class="pipeline-diagram-label">Gen SQL</span></div>
    </div>
  `;

  welcomePanel.innerHTML = `
    <div class="welcome-hero">
      <h2>Text2SQL</h2>
      <p>Convert natural language into SQL &mdash; powered by a multi-agent AI pipeline.</p>
    </div>
    <div class="welcome-how">
      ${pipelineHtml}
    </div>
    <div class="welcome-domains">${cardsHtml}</div>
  `;

  if (!welcomePanel.dataset.bound) {
    welcomePanel.dataset.bound = '1';
    welcomePanel.addEventListener('click', (e) => {
      const btn = e.target.closest('.example-question-btn');
      if (!btn) return;
      const domain = btn.dataset.domain;
      const question = btn.dataset.question;
      if (domain && question) {
        selectDomain(domain, { silent: true });
        messageInput.value = question;
        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      }
    });
  }
}

function showWelcome() {
  outputPlaceholder.classList.remove('hidden');
  outputContent.classList.add('hidden');
  if (domainInfo) renderWelcomePanel(domainInfo);
}

// ===== Contextual placeholder (in-chat suggestions) =====

function showContextualSuggestions() {
  const domain = useCaseSelect.value;
  if (!domain || !domainInfo) {
    showWelcome();
    return;
  }
  const info = domainInfo.find(d => d.name === domain);
  if (!info) { showWelcome(); return; }

  outputPlaceholder.classList.remove('hidden');
  outputContent.classList.add('hidden');

  const pills = (info.example_questions || []).map(q =>
    `<button type="button" class="suggestion-pill" data-question="${escapeHtml(q)}">${escapeHtml(q)}</button>`
  ).join('');

  welcomePanel.innerHTML = `
    <div class="chat-suggestions">
      <h3>Ask about ${info.display_name}</h3>
      <p>${info.description} &mdash; ${info.table_count} tables available</p>
      <div class="suggestion-pills">${pills}</div>
    </div>
  `;

  welcomePanel.onclick = (e) => {
    const pill = e.target.closest('.suggestion-pill');
    if (!pill) return;
    messageInput.value = pill.dataset.question;
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  };
}

// ===== Pipeline progress =====

function showPipelineProgress() {
  if (!pipelineProgressEl) return;
  pipelineProgressEl.classList.remove('hidden');
  let stepIndex = 0;
  updatePipelineStep(stepIndex);
  pipelineInterval = setInterval(() => {
    stepIndex++;
    if (stepIndex >= PIPELINE_STEPS.length) {
      stepIndex = PIPELINE_STEPS.length - 1;
    }
    updatePipelineStep(stepIndex);
  }, 3000);
}

function updatePipelineStep(activeIdx) {
  const steps = pipelineProgressEl.querySelectorAll('.pipeline-step');
  const connectors = pipelineProgressEl.querySelectorAll('.pipeline-connector');
  steps.forEach((el, i) => {
    el.classList.remove('is-active', 'is-done');
    if (i < activeIdx) el.classList.add('is-done');
    else if (i === activeIdx) el.classList.add('is-active');
  });
  connectors.forEach((el, i) => {
    el.style.background = i < activeIdx ? 'var(--green-500)' : 'var(--border)';
  });
}

function hidePipelineProgress() {
  if (pipelineInterval) { clearInterval(pipelineInterval); pipelineInterval = null; }
  if (!pipelineProgressEl) return;
  const steps = pipelineProgressEl.querySelectorAll('.pipeline-step');
  steps.forEach(el => { el.classList.remove('is-active'); el.classList.add('is-done'); });
  const connectors = pipelineProgressEl.querySelectorAll('.pipeline-connector');
  connectors.forEach(el => { el.style.background = 'var(--green-500)'; });
  setTimeout(() => {
    pipelineProgressEl.classList.add('hidden');
    steps.forEach(el => el.classList.remove('is-done', 'is-active'));
    connectors.forEach(el => { el.style.background = ''; });
  }, 800);
}

// ===== SQL syntax highlighting =====

function highlightSQL(sql) {
  const keywords = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|AND|OR|NOT|IN|IS|NULL|AS|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|UNION|ALL|DISTINCT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TABLE|INDEX|VIEW|SET|VALUES|INTO|BETWEEN|LIKE|ILIKE|EXISTS|CASE|WHEN|THEN|ELSE|END|WITH|RECURSIVE|ASC|DESC|COUNT|SUM|AVG|MIN|MAX|COALESCE|CAST|EXTRACT|DATE_TRUNC|GENERATE_SERIES|OVER|PARTITION|ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD|FILTER|LATERAL|FETCH|NEXT|ROWS|ONLY|NULLS|FIRST|LAST)\b/gi;
  const functions = /\b(COUNT|SUM|AVG|MIN|MAX|COALESCE|CAST|EXTRACT|DATE_TRUNC|GENERATE_SERIES|ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD|NOW|CURRENT_DATE|CURRENT_TIMESTAMP|ROUND|FLOOR|CEIL|ABS|LENGTH|UPPER|LOWER|TRIM|SUBSTRING|CONCAT|TO_CHAR|TO_DATE|TO_NUMBER)\s*(?=\()/gi;
  const strings = /('[^']*')/g;
  const numbers = /\b(\d+\.?\d*)\b/g;
  const comments = /(--[^\n]*)/g;

  let result = escapeHtml(sql);
  result = result.replace(comments, '<span class="sql-comment">$1</span>');
  result = result.replace(strings, '<span class="sql-string">$1</span>');
  result = result.replace(functions, '<span class="sql-function">$1</span>');
  result = result.replace(keywords, '<span class="sql-keyword">$1</span>');
  result = result.replace(numbers, (match, num, offset, str) => {
    const before = str.substring(Math.max(0, offset - 20), offset);
    if (before.includes('sql-')) return match;
    return `<span class="sql-number">${num}</span>`;
  });
  return result;
}

// ===== Use cases / sessions =====

async function loadUseCases() {
  try {
    const res = await fetch(`${API_BASE}/use-cases`);
    if (!res.ok) throw new Error('Failed to load use cases');
    const list = await res.json();
    useCaseSelect.innerHTML =
      '<option value="">Select Domain</option>' +
      list.map((u) => `<option value="${u}">${u.charAt(0).toUpperCase() + u.slice(1)}</option>`).join('');
  } catch (e) {
    useCaseSelect.innerHTML = '<option value="">Failed to load</option>';
    console.error(e);
  }
}

async function fetchSessionsList() {
  const cid = ensureClientId();
  const res = await fetch(`${API_BASE}/sessions?client_id=${encodeURIComponent(cid)}&limit=200`, {
    headers: getClientHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail != null ? err.detail : res.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json();
}

async function refreshSidebar() {
  try {
    const sessions = await fetchSessionsList();
    renderChatList(sessions);
  } catch (e) {
    console.warn('refreshSidebar failed', e);
  }
}

const CHAT_DELETE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`;

function renderChatList(sessions) {
  if (!chatListEl) return;
  cachedSessions = Array.isArray(sessions) ? sessions.slice() : [];
  chatListEl.innerHTML = '';
  cachedSessions.forEach((s) => {
    const row = document.createElement('div');
    row.className = 'chat-list-row' + (s.session_id === activeSessionId ? ' is-active' : '');
    row.dataset.sessionId = s.session_id;
    row.setAttribute('role', 'listitem');

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'chat-list-item';
    btn.dataset.sessionId = s.session_id;
    btn.textContent = sidebarLabelForSession(s);
    if (s.use_case) btn.dataset.useCase = s.use_case;

    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'chat-list-delete';
    del.dataset.sessionId = s.session_id;
    del.setAttribute('aria-label', 'Delete chat');
    del.title = 'Delete chat';
    del.innerHTML = CHAT_DELETE_SVG;

    row.appendChild(btn);
    row.appendChild(del);
    chatListEl.appendChild(row);
  });
}

function setSidebarActiveHighlight(sessionId) {
  if (!chatListEl) return;
  chatListEl.querySelectorAll('.chat-list-row').forEach((row) => {
    row.classList.toggle('is-active', Boolean(sessionId) && row.dataset.sessionId === sessionId);
  });
}

// ===== Session management =====

async function deleteSessionRemote(sessionId) {
  const cid = ensureClientId();
  const res = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}?client_id=${encodeURIComponent(cid)}`,
    { method: 'DELETE', headers: getClientHeaders() }
  );
  if (res.status === 204) return;
  const err = await res.json().catch(() => ({}));
  const detail = err.detail != null ? err.detail : res.statusText;
  throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
}

function openDeleteConfirmModal(sessionId) {
  if (!deleteConfirmModal || !sessionId) return;
  pendingDeleteSessionId = sessionId;
  deleteConfirmModal.classList.remove('hidden');
  deleteConfirmModal.setAttribute('aria-hidden', 'false');
  if (deleteConfirmCancelBtn) deleteConfirmCancelBtn.focus();
}

function closeDeleteConfirmModal() {
  if (!deleteConfirmModal) return;
  pendingDeleteSessionId = null;
  deleteConfirmModal.classList.add('hidden');
  deleteConfirmModal.setAttribute('aria-hidden', 'true');
}

function handleDeleteChat(sessionId) {
  if (!sessionId) return;
  openDeleteConfirmModal(sessionId);
}

async function executeConfirmedDeleteChat() {
  const sessionId = pendingDeleteSessionId;
  if (!sessionId) return;
  closeDeleteConfirmModal();
  showError('');
  try {
    await deleteSessionRemote(sessionId);
    const wasActive = sessionId === activeSessionId;
    await refreshSidebar();
    if (wasActive) {
      if (cachedSessions.length > 0 && cachedSessions[0].session_id) {
        await loadChatSession(cachedSessions[0].session_id);
      } else {
        setActiveSessionId(null);
        resetDomainSelect();
        clearChatThread();
        pendingIntentState = null;
        hideIntentActions();
        showWelcome();
        setSidebarActiveHighlight(null);
      }
    }
  } catch (e) {
    showError(e?.message || 'Failed to delete chat');
  }
}

function applyUseCaseFromSession(sessionId) {
  const row = cachedSessions.find((x) => x.session_id === sessionId);
  const uc = row?.use_case && String(row.use_case).trim();
  if (!uc) return;
  selectDomain(uc, { silent: true });
}

async function fetchSessionMessages(sessionId) {
  const res = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/messages`,
    { headers: getClientHeaders() }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail != null ? err.detail : res.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json();
}

async function fetchSessionPipelineTurns(sessionId) {
  const res = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/pipeline-turns`,
    { headers: getClientHeaders() }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail != null ? err.detail : res.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json();
}

function turnToAssistantData(turn) {
  return {
    conversation_state: turn.conversation_state || 'completed',
    rephrased_question: turn.rephrased_question || '',
    resolved_question: turn.resolved_question || turn.rephrased_question || '',
    keywords: Array.isArray(turn.keywords) ? turn.keywords : [],
    business_insights: Array.isArray(turn.business_insights) ? turn.business_insights : [],
    intent_confidence: typeof turn.intent_confidence === 'number' ? turn.intent_confidence : 0,
    selected_tables: Array.isArray(turn.selected_tables) ? turn.selected_tables : [],
    selected_columns:
      turn.selected_columns && typeof turn.selected_columns === 'object' && !Array.isArray(turn.selected_columns)
        ? turn.selected_columns
        : {},
    few_shot_examples: Array.isArray(turn.few_shot_examples) ? turn.few_shot_examples : [],
    generated_sql: turn.generated_sql || '',
    error: turn.error != null ? turn.error : null,
  };
}

function turnHasPipelineArtifacts(turn) {
  const sql = (turn.generated_sql || '').trim();
  const tables = Array.isArray(turn.selected_tables) && turn.selected_tables.length > 0;
  return Boolean(sql || tables);
}

function renderReloadedThread(msgs, turns) {
  const list = Array.isArray(msgs) ? msgs : [];
  const pipelineTurns = Array.isArray(turns) ? turns : [];
  const consumedTurnIds = new Set();

  function consumeNextRichTurn() {
    for (const t of pipelineTurns) {
      const id = t.intent_output_id;
      if (id == null || consumedTurnIds.has(id)) continue;
      if (!turnHasPipelineArtifacts(t)) continue;
      consumedTurnIds.add(id);
      return t;
    }
    return null;
  }

  const defer = { deferScroll: true };
  for (const m of list) {
    const role = (m.role || '').toLowerCase() === 'user' ? 'user' : 'assistant';
    const mt = (m.message_type || '').toLowerCase();
    if (role === 'assistant' && mt === 'pipeline_completed') {
      const t = consumeNextRichTurn();
      if (t) {
        appendChatBubble('assistant', 'SQL generated successfully.', turnToAssistantData(t), defer);
      } else {
        appendPlainBubble(role, m.content || '', defer);
      }
    } else {
      appendPlainBubble(role, m.content || '', defer);
    }
  }

  for (const t of pipelineTurns) {
    const id = t.intent_output_id;
    if (id == null || consumedTurnIds.has(id) || !turnHasPipelineArtifacts(t)) continue;
    consumedTurnIds.add(id);
    appendChatBubble('user', t.user_input || '', null, defer);
    appendChatBubble('assistant', 'SQL generated successfully.', turnToAssistantData(t), defer);
  }
  scrollChatToBottom();
}

function clearChatThread() {
  chatThread.innerHTML = '';
  dockIntentActionsDefault();
}

async function bootstrapFreshSession() {
  const cid = ensureClientId();
  const res = await fetch(`${API_BASE}/session?client_id=${encodeURIComponent(cid)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  const data = await res.json();
  if (!res.ok || !data?.session_id) {
    const detail = data?.detail != null ? data.detail : res.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  setActiveSessionId(String(data.session_id));
  return String(data.session_id);
}

async function loadChatSession(sessionId) {
  if (!sessionId) return;
  setLoadingState(true, 'Loading chat…');
  showError('');
  hideIntentActions();
  pendingIntentState = null;

  try {
    const [msgs, turns] = await Promise.all([
      fetchSessionMessages(sessionId),
      fetchSessionPipelineTurns(sessionId).catch((e) => { console.warn('pipeline-turns', e); return []; }),
    ]);
    setActiveSessionId(sessionId);
    clearChatThread();

    if (!msgs.length) {
      showContextualSuggestions();
      setSidebarActiveHighlight(sessionId);
      void refreshSidebar().then(() => applyUseCaseFromSession(sessionId));
      return;
    }

    showChatArea();
    renderReloadedThread(msgs, turns);
    setSidebarActiveHighlight(sessionId);
    void refreshSidebar().then(() => applyUseCaseFromSession(sessionId));
  } catch (e) {
    showError(e?.message || 'Failed to load chat');
  } finally {
    setLoadingState(false);
  }
}

// ===== Chat rendering =====

function appendPlainBubble(role, text, options = {}) {
  showChatArea();
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'}`;
  const title = role === 'user' ? 'You' : 'Assistant';
  bubble.innerHTML = `
    <p class="chat-bubble-meta">${title}</p>
    <p class="chat-bubble-text">${escapeHtml(text || '')}</p>
  `;
  chatThread.appendChild(bubble);
  if (!options.deferScroll) scrollChatToBottom();
}

function scrollChatToBottom() {
  if (!chatScroll) return;
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function bindSqlCopyDelegation() {
  if (!chatThread || chatThread.dataset.sqlCopyBound === '1') return;
  chatThread.dataset.sqlCopyBound = '1';
  chatThread.addEventListener('click', async (e) => {
    const btn = e.target.closest('.copy-sql-btn');
    if (!btn || !chatThread.contains(btn)) return;
    e.preventDefault();
    const wrap = btn.closest('.out-sql-wrap');
    const codeEl = wrap && wrap.querySelector('.out-sql code');
    const text = codeEl ? codeEl.textContent : '';
    if (!text || !String(text).trim()) return;

    const revert = () => {
      btn.classList.remove('copy-sql-btn--done');
      btn.setAttribute('aria-label', 'Copy SQL');
      btn.title = 'Copy SQL';
      window.clearTimeout(btn._copyResetTid);
    };

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement('textarea');
        ta.value = text; ta.setAttribute('readonly', '');
        ta.style.position = 'fixed'; ta.style.left = '-9999px';
        document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); document.body.removeChild(ta);
      }
      btn.classList.add('copy-sql-btn--done');
      btn.setAttribute('aria-label', 'Copied'); btn.title = 'Copied';
      window.clearTimeout(btn._copyResetTid);
      btn._copyResetTid = window.setTimeout(revert, 1600);
    } catch (_err) { revert(); }
  });
}

function showTypingIndicator() {
  removeTypingIndicator();
  const typing = document.createElement('div');
  typing.className = 'chat-bubble chat-bubble-assistant typing-indicator';
  typing.id = 'typing-indicator';
  typing.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div>`;
  chatThread.appendChild(typing);
  scrollChatToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function setLoadingState(loading, text, showPipeline = false) {
  submitBtn.disabled = loading;
  newChatBtn.disabled = loading;
  if (loading) {
    outputError.classList.add('hidden');
    outputError.textContent = '';
    if (showPipeline) {
      showPipelineProgress();
      showTypingIndicator();
    }
    const hasThread = chatThread.children.length > 0;
    if (hasThread) {
      outputContent.classList.remove('hidden');
      outputPlaceholder.classList.add('hidden');
    }
    if (composerStatus) {
      composerStatus.textContent = text || 'Processing...';
      composerStatus.classList.remove('hidden');
    }
  } else {
    hidePipelineProgress();
    removeTypingIndicator();
    if (composerStatus) { composerStatus.classList.add('hidden'); composerStatus.textContent = ''; }
    if (!chatThread.children.length) {
      showContextualSuggestions();
    }
  }
}

function showChatArea() {
  outputPlaceholder.classList.add('hidden');
  outputContent.classList.remove('hidden');
}

function buildAssistantDetails(data) {
  if (!data || typeof data !== 'object') return '';
  const state = data.conversation_state || '';
  if (state !== 'completed') return '';

  const parts = [];
  const interpreted = (data.resolved_question || data.rephrased_question || '').trim();
  if (interpreted) {
    parts.push(`<div class="detail-interpreted"><span class="detail-label">Interpreted as:</span> <span class="detail-value">${escapeHtml(interpreted)}</span></div>`);
  }

  const sql = (data.generated_sql && String(data.generated_sql).trim()) || '';
  if (sql) {
    parts.push(`<div class="out-sql-wrap">
<pre class="out-sql"><code>${highlightSQL(sql)}</code></pre>
<button type="button" class="copy-sql-btn" aria-label="Copy SQL" title="Copy SQL">${COPY_SQL_ICON}</button>
</div>`);
  } else if (data.error != null && String(data.error).trim()) {
    parts.push(`<p class="out-text out-error">${escapeHtml(String(data.error).trim())}</p>`);
  }

  if (parts.length === 0) return '';
  return `<div class="chat-details">${parts.join('')}</div>`;
}

function dockIntentActionsDefault() {
  intentActions.classList.add('hidden');
  intentActions.setAttribute('hidden', '');
  intentActionsLabel.classList.remove('sr-only');
  intentActionsLabel.textContent = 'Is this understanding correct?';
  outputContent.append(chatThread, intentActions);
}

function appendChatBubble(role, text, data = null, options = {}) {
  showChatArea();
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'}`;

  const title = role === 'user' ? 'You' : 'Assistant';
  let html = `
    <p class="chat-bubble-meta">${title}</p>
    <p class="chat-bubble-text">${escapeHtml(text || '')}</p>
  `;

  if (role === 'assistant' && data) {
    html += buildAssistantDetails(data);
  }

  bubble.innerHTML = html;

  if (options.intentInline && role === 'assistant') {
    const wrap = document.createElement('div');
    wrap.className = 'chat-item chat-item--intent-prompt';
    wrap.appendChild(bubble);
    intentActionsLabel.classList.add('sr-only');
    intentActionsLabel.textContent = 'Confirm with Yes or No';
    wrap.appendChild(intentActions);
    intentActions.classList.remove('hidden');
    intentActions.removeAttribute('hidden');
    chatThread.appendChild(wrap);
  } else {
    chatThread.appendChild(bubble);
  }
  if (!options.deferScroll) scrollChatToBottom();
}

function showError(errorText) {
  outputError.textContent = errorText || '';
  outputError.classList.toggle('hidden', !errorText);
}

function hideIntentActions() {
  dockIntentActionsDefault();
}

// ===== Query submission =====

async function callQuery(payload) {
  const body = { ...payload, client_id: ensureClientId() };
  let res = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  let data = await res.json();

  const invalidSession =
    !res.ok && data?.detail && String(data.detail).toLowerCase().includes('invalid or unknown session_id');
  if (invalidSession) {
    await bootstrapFreshSession();
    const retryPayload = { ...body, session_id: getActiveSessionId() };
    res = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(retryPayload),
    });
    data = await res.json();
  }

  if (data.session_id) setActiveSessionId(String(data.session_id));
  return { res, data };
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const useCase = useCaseSelect.value?.trim();
  const message = messageInput.value?.trim();
  if (!useCase) {
    showError('Please select a domain first (Healthcare, Retail, or Finance)');
    return;
  }
  if (!message) return;

  showError('');
  hideIntentActions();
  appendChatBubble('user', message);
  messageInput.value = '';
  setLoadingState(true, 'Running multi-agent pipeline...', true);

  try {
    const body = {
      message,
      use_case: useCase,
      session_id: getActiveSessionId(),
      message_type: pendingIntentState ? 'intent_correction' : 'new_query',
    };
    const { res, data } = await callQuery(body);

    if (!res.ok) {
      const detail = data.detail != null ? data.detail : res.statusText;
      const errText = typeof detail === 'string' ? detail : JSON.stringify(detail);
      showError(errText);
      appendChatBubble('assistant', `Error: ${errText}`);
      await refreshSidebar();
      return;
    }

    if (data.conversation_state === 'waiting_intent_confirmation') {
      pendingIntentState = { useCase, pendingIntentId: data.pending_intent_id || null };
      const prompt = data.clarification_question ||
        `Did I understand correctly: ${data.resolved_question || data.rephrased_question}?`;
      appendChatBubble('assistant', prompt, data, { intentInline: true });
    } else if (data.conversation_state === 'waiting_user_rephrase') {
      pendingIntentState = { useCase, pendingIntentId: data.pending_intent_id || null };
      appendChatBubble('assistant', PROMPT_CORRECTED_QUESTION, { conversation_state: 'waiting_user_rephrase' });
      hideIntentActions();
    } else if (data.conversation_state === 'waiting_analytical_query') {
      pendingIntentState = null;
      hideIntentActions();
      appendChatBubble('assistant', data.clarification_question || 'Please type your analytical question.', data);
    } else if (data.conversation_state === 'conversation_ended') {
      pendingIntentState = null;
      hideIntentActions();
      appendChatBubble('assistant', data.clarification_question || 'Ok, thank you!', data);
    } else {
      pendingIntentState = null;
      hideIntentActions();
      appendChatBubble('assistant', 'SQL generated successfully.', data);
      if (data.error) showError(data.error);
    }
    await refreshSidebar();
  } catch (err) {
    const errText = err?.message || 'Request failed';
    showError(errText);
    appendChatBubble('assistant', `Error: ${errText}`);
    await refreshSidebar();
  } finally {
    setLoadingState(false);
  }
});

// ===== Intent confirmation =====

async function submitIntentConfirmation(answer) {
  if (!pendingIntentState) return;
  hideIntentActions();
  appendChatBubble('user', answer === 'yes' ? 'Yes' : 'No');
  setLoadingState(true, 'Confirming intent and generating SQL...', true);
  try {
    const payload = {
      message: answer,
      use_case: pendingIntentState.useCase,
      session_id: getActiveSessionId(),
      message_type: 'intent_confirmation',
      confirmation: answer,
    };
    const { res, data } = await callQuery(payload);
    if (!res.ok) {
      const detail = data.detail != null ? data.detail : res.statusText;
      const errText = typeof detail === 'string' ? detail : JSON.stringify(detail);
      showError(errText);
      appendChatBubble('assistant', `Error: ${errText}`);
      await refreshSidebar();
      return;
    }

    if (data.conversation_state === 'waiting_user_rephrase') {
      pendingIntentState = { useCase: pendingIntentState.useCase, pendingIntentId: data.pending_intent_id || null };
      appendChatBubble('assistant', PROMPT_CORRECTED_QUESTION, { conversation_state: 'waiting_user_rephrase' });
    } else if (data.conversation_state === 'waiting_analytical_query') {
      pendingIntentState = null;
      appendChatBubble('assistant', data.clarification_question || 'Please type your analytical question.', data);
    } else if (data.conversation_state === 'conversation_ended') {
      pendingIntentState = null;
      appendChatBubble('assistant', data.clarification_question || 'Ok, thank you!', data);
    } else {
      pendingIntentState = null;
      const done = data.conversation_state === 'completed';
      appendChatBubble('assistant', done ? 'SQL generated successfully.' : 'Thanks — generating SQL now.', data);
      if (data.error) showError(data.error);
    }
    await refreshSidebar();
  } catch (err) {
    const errText = err?.message || 'Request failed';
    showError(errText);
    appendChatBubble('assistant', `Error: ${errText}`);
    await refreshSidebar();
  } finally {
    setLoadingState(false);
    hideIntentActions();
  }
}

intentYesBtn.addEventListener('click', () => submitIntentConfirmation('yes'));
intentNoBtn.addEventListener('click', () => submitIntentConfirmation('no'));

// ===== Modal =====

if (deleteConfirmModal) {
  deleteConfirmModal.addEventListener('click', (e) => { if (e.target === deleteConfirmModal) closeDeleteConfirmModal(); });
}
if (deleteConfirmCancelBtn) {
  deleteConfirmCancelBtn.addEventListener('click', () => closeDeleteConfirmModal());
}
if (deleteConfirmDeleteBtn) {
  deleteConfirmDeleteBtn.addEventListener('click', () => void executeConfirmedDeleteChat());
}

document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  if (!deleteConfirmModal || deleteConfirmModal.classList.contains('hidden')) return;
  closeDeleteConfirmModal();
});

// ===== Sidebar events =====

if (chatListEl) {
  chatListEl.addEventListener('click', (e) => {
    const delBtn = e.target.closest('.chat-list-delete');
    if (delBtn && delBtn.dataset.sessionId) {
      e.preventDefault(); e.stopPropagation();
      void handleDeleteChat(delBtn.dataset.sessionId);
      return;
    }
    const btn = e.target.closest('.chat-list-item');
    if (!btn || !btn.dataset.sessionId) return;
    const id = btn.dataset.sessionId;
    if (id === activeSessionId) return;
    if (btn.dataset.useCase) selectDomain(btn.dataset.useCase.trim(), { silent: true });
    loadChatSession(id);
  });
}

if (newChatBtn) {
  newChatBtn.addEventListener('click', async () => {
    showError('');
    setActiveSessionId(null);
    resetDomainSelect();
    clearChatThread();
    pendingIntentState = null;
    hideIntentActions();
    showWelcome();
    setSidebarActiveHighlight(null);
    await refreshSidebar();
  });
}

// ===== Init =====

async function init() {
  bindSqlCopyDelegation();
  submitBtn.disabled = true;
  newChatBtn.disabled = true;
  removeLegacyKeys();
  ensureClientId();

  const [, domains] = await Promise.all([loadUseCases(), loadDomainInfo()]);
  if (domains) renderDomainButtons(domains);

  showError('');
  hideIntentActions();
  showWelcome();

  try {
    let sessions = [];
    try { sessions = await fetchSessionsList(); } catch (e) { console.warn('Could not list sessions', e); }
    renderChatList(sessions);
    setActiveSessionId(null);
    resetDomainSelect();
    showWelcome();
    submitBtn.disabled = false;
    newChatBtn.disabled = false;
  } catch (e) {
    showError(e.message || 'Failed to initialize');
    submitBtn.disabled = false;
    newChatBtn.disabled = false;
  }
}

init();
