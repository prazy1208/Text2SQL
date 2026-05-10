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
const sessionIdEl = document.getElementById('session-id');
const chatListEl = document.getElementById('chat-list');
const newChatBtn = document.getElementById('new-chat-btn');
const deleteConfirmModal = document.getElementById('delete-confirm-modal');
const deleteConfirmCancelBtn = document.getElementById('delete-confirm-cancel');
const deleteConfirmDeleteBtn = document.getElementById('delete-confirm-delete');

/** Current conversation id (also persisted as ACTIVE_SESSION_KEY for reload). */
let activeSessionId = null;

/** Last session list from API (for sidebar titles + use_case when switching). */
let cachedSessions = [];

/** Session id awaiting delete confirmation in the custom modal (null when closed). */
let pendingDeleteSessionId = null;

let pendingIntentState = null;

const PROMPT_CORRECTED_QUESTION = 'Please provide a corrected question.';

function removeLegacyKeys() {
  try {
    localStorage.removeItem(LEGACY_CHAT_HISTORY_KEY);
    localStorage.removeItem(LEGACY_SESSION_KEY);
  } catch (_e) {
    /* ignore */
  }
}

function randomUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function ensureClientId() {
  try {
    let id = localStorage.getItem(CLIENT_ID_KEY);
    if (!id) {
      id = randomUUID();
      localStorage.setItem(CLIENT_ID_KEY, id);
    }
    return id;
  } catch (_e) {
    return randomUUID();
  }
}

function getClientHeaders() {
  const cid = ensureClientId();
  return { 'X-Client-Id': cid };
}

function persistActiveSession(id) {
  try {
    if (id) localStorage.setItem(ACTIVE_SESSION_KEY, id);
    else localStorage.removeItem(ACTIVE_SESSION_KEY);
  } catch (_e) {
    /* ignore */
  }
}

function getRememberedSessionId() {
  try {
    return localStorage.getItem(ACTIVE_SESSION_KEY);
  } catch (_e) {
    return null;
  }
}

function updateSessionHeader(id) {
  sessionIdEl.textContent = id || '—';
}

function getActiveSessionId() {
  return activeSessionId;
}

function setActiveSessionId(id) {
  const sid = id != null && String(id).trim() ? String(id).trim() : null;
  activeSessionId = sid;
  if (sid) {
    persistActiveSession(sid);
    updateSessionHeader(sid);
  } else {
    persistActiveSession(null);
    updateSessionHeader(null);
  }
}

/** Sidebar label for sessions without a DB title (legacy empty rows stay distinguishable). */
function sidebarLabelForSession(s) {
  const t = s.title && String(s.title).trim();
  if (t) return t;
  const raw = String(s.session_id || '').replace(/-/g, '');
  const tail = raw.slice(-6) || raw.slice(0, 6) || '…';
  return `New chat (${tail})`;
}

/**
 * API returns selected_columns as object mapping "schema.table" -> string[].
 * Guard against null, arrays, or bad values (cached HTML / older clients).
 */
function normalizeSelectedColumns(raw) {
  if (raw == null || typeof raw !== 'object' || Array.isArray(raw)) {
    return {};
  }
  const out = {};
  for (const [tableFqn, v] of Object.entries(raw)) {
    if (!tableFqn || !String(tableFqn).trim()) continue;
    if (!Array.isArray(v)) continue;
    const names = v.map((x) => String(x).trim()).filter(Boolean);
    if (names.length) {
      out[String(tableFqn).trim()] = names;
    }
  }
  return out;
}

/** Clear domain dropdown to the placeholder (new chat or no active session). */
function resetDomainSelect() {
  if (!useCaseSelect) return;
  useCaseSelect.value = '';
}

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
  const list = cachedSessions;
  list.forEach((s) => {
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

/** Update active row without refetching the session list (instant when switching chats). */
function setSidebarActiveHighlight(sessionId) {
  if (!chatListEl) return;
  chatListEl.querySelectorAll('.chat-list-row').forEach((row) => {
    const id = row.dataset.sessionId;
    row.classList.toggle('is-active', Boolean(sessionId) && id === sessionId);
  });
}

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
        outputPlaceholder.classList.remove('hidden');
        outputPlaceholder.textContent = 'Submit a question to start the conversation.';
        outputContent.classList.add('hidden');
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
  const opt = [...useCaseSelect.options].find((o) => o.value === uc);
  if (opt) useCaseSelect.value = uc;
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

/**
 * Merge chat_messages with pipeline-turns: rich assistant bubbles for completed pipelines
 * (from agent output tables). Matches each pipeline_completed row to the next intent turn
 * that has SQL or table output (skips greeting-only intent rows).
 */
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
        appendChatBubble('assistant', 'Here is what I found.', turnToAssistantData(t), defer);
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
    appendChatBubble('assistant', 'Here is what I found.', turnToAssistantData(t), defer);
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
  const sid = String(data.session_id);
  setActiveSessionId(sid);
  return sid;
}

/**
 * Load transcript: chat_messages plus structured pipeline-turns (agent DB) for rich replay.
 */
async function loadChatSession(sessionId) {
  if (!sessionId) return;
  setLoadingState(true, 'Loading chat…');
  showError('');
  hideIntentActions();
  pendingIntentState = null;

  try {
    const [msgs, turns] = await Promise.all([
      fetchSessionMessages(sessionId),
      fetchSessionPipelineTurns(sessionId).catch((e) => {
        console.warn('pipeline-turns', e);
        return [];
      }),
    ]);
    setActiveSessionId(sessionId);
    clearChatThread();

    if (!msgs.length) {
      outputPlaceholder.classList.remove('hidden');
      outputPlaceholder.textContent = 'Submit a question to start the conversation.';
      outputContent.classList.add('hidden');
      setSidebarActiveHighlight(sessionId);
      void refreshSidebar().then(() => applyUseCaseFromSession(sessionId));
      return;
    }

    showChatArea();
    renderReloadedThread(msgs, turns);
    setSidebarActiveHighlight(sessionId);
    /** Refetch list in background — do not block showing the thread (was a major cause of slow switches). */
    void refreshSidebar().then(() => applyUseCaseFromSession(sessionId));
  } catch (e) {
    showError(e?.message || 'Failed to load chat');
    updateSessionHeader(getActiveSessionId());
  } finally {
    setLoadingState(false);
  }
}

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

function setLoadingState(loading, text) {
  submitBtn.disabled = loading;
  newChatBtn.disabled = loading;
  const statusText = text || 'Processing...';
  if (loading) {
    outputError.classList.add('hidden');
    outputError.textContent = '';
    const hasThread = chatThread.children.length > 0;
    if (hasThread) {
      outputContent.classList.remove('hidden');
      outputPlaceholder.classList.add('hidden');
      if (composerStatus) {
        composerStatus.textContent = statusText;
        composerStatus.classList.remove('hidden');
      }
    } else {
      outputPlaceholder.classList.remove('hidden');
      outputPlaceholder.textContent = statusText;
      outputContent.classList.add('hidden');
      if (composerStatus) {
        composerStatus.classList.add('hidden');
        composerStatus.textContent = '';
      }
    }
  } else {
    if (composerStatus) {
      composerStatus.classList.add('hidden');
      composerStatus.textContent = '';
    }
    if (!chatThread.children.length) {
      outputPlaceholder.classList.remove('hidden');
      outputPlaceholder.textContent = 'Submit a question to start the conversation.';
      outputContent.classList.add('hidden');
    }
  }
}

function showChatArea() {
  outputPlaceholder.classList.add('hidden');
  outputContent.classList.remove('hidden');
}

function renderColumns(columnsObj) {
  const cols = normalizeSelectedColumns(columnsObj);
  const keys = Object.keys(cols).sort();
  if (!keys.length) return '<p class="out-text-muted">—</p>';
  return keys
    .map((tableFqn) => {
      const items = cols[tableFqn].map((c) => `<li><code>${escapeHtml(String(c))}</code></li>`).join('');
      return `<div class="out-column-group"><h4 class="out-column-table"><code>${escapeHtml(tableFqn)}</code></h4><ul class="out-list out-list-mono">${items}</ul></div>`;
    })
    .join('');
}

function buildAssistantDetails(data) {
  if (!data || typeof data !== 'object') return '';
  const parts = [];
  const state = data.conversation_state;
  if (state === 'waiting_intent_confirmation' || state === 'waiting_user_rephrase') {
    return '';
  }

  if (typeof data.intent_confidence === 'number' && Number.isFinite(data.intent_confidence)) {
    parts.push(`<h4>Intent confidence</h4><p class="out-text">${escapeHtml(String(data.intent_confidence))}%</p>`);
  }

  if (data.rephrased_question) {
    parts.push(`<h4>Rephrased question</h4><p class="out-text">${escapeHtml(data.rephrased_question)}</p>`);
  }

  if (data.keywords && data.keywords.length) {
    parts.push(`<h4>Keywords</h4><ul class="out-list">${data.keywords.map((k) => `<li>${escapeHtml(k)}</li>`).join('')}</ul>`);
  }

  if (data.business_insights && data.business_insights.length) {
    parts.push(
      `<h4>Business insights</h4><ul class="out-list">${data.business_insights.map((b) => `<li>${escapeHtml(b)}</li>`).join('')}</ul>`
    );
  }

  if (data.selected_tables && data.selected_tables.length) {
    parts.push(
      `<h4>Selected tables</h4><ul class="out-list out-list-mono">${data.selected_tables.map((t) => `<li><code>${escapeHtml(t)}</code></li>`).join('')}</ul>`
    );
  }

  if (data.selected_columns && Object.keys(normalizeSelectedColumns(data.selected_columns)).length) {
    parts.push(`<h4>Selected columns</h4><div class="out-columns">${renderColumns(data.selected_columns)}</div>`);
  }

  if (data.generated_sql && String(data.generated_sql).trim()) {
    parts.push(`<h4>Generated SQL</h4><pre class="out-sql"><code>${escapeHtml(String(data.generated_sql).trim())}</code></pre>`);
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

async function callQuery(payload) {
  const body = {
    ...payload,
    client_id: ensureClientId(),
  };
  let res = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  let data = await res.json();

  const invalidSession =
    !res.ok &&
    data?.detail &&
    String(data.detail).toLowerCase().includes('invalid or unknown session_id');
  if (invalidSession) {
    await bootstrapFreshSession();
    const retryPayload = {
      ...body,
      session_id: getActiveSessionId(),
    };
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

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const useCase = useCaseSelect.value?.trim();
  const message = messageInput.value?.trim();
  if (!useCase || !message) return;

  showError('');
  hideIntentActions();
  appendChatBubble('user', message);
  setLoadingState(true, 'Processing... (first request may take 1-2 min to load the model)');

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
      pendingIntentState = {
        useCase,
        pendingIntentId: data.pending_intent_id || null,
      };
      const prompt =
        data.clarification_question ||
        `Did I understand correctly: ${data.resolved_question || data.rephrased_question}?`;
      appendChatBubble('assistant', prompt, data, { intentInline: true });
    } else if (data.conversation_state === 'waiting_user_rephrase') {
      pendingIntentState = {
        useCase,
        pendingIntentId: data.pending_intent_id || null,
      };
      appendChatBubble('assistant', PROMPT_CORRECTED_QUESTION, { conversation_state: 'waiting_user_rephrase' });
      hideIntentActions();
    } else if (data.conversation_state === 'waiting_analytical_query') {
      pendingIntentState = null;
      hideIntentActions();
      appendChatBubble(
        'assistant',
        data.clarification_question || 'Please type your analytical question.',
        data
      );
    } else if (data.conversation_state === 'conversation_ended') {
      pendingIntentState = null;
      hideIntentActions();
      appendChatBubble('assistant', data.clarification_question || 'Ok, thank you!', data);
    } else {
      pendingIntentState = null;
      hideIntentActions();
      appendChatBubble('assistant', 'Here is what I found.', data);
      if (data.error) showError(data.error);
    }
    await refreshSidebar();
    messageInput.value = '';
  } catch (err) {
    const errText = err?.message || 'Request failed';
    showError(errText);
    appendChatBubble('assistant', `Error: ${errText}`);
    await refreshSidebar();
  } finally {
    setLoadingState(false);
  }
});

async function submitIntentConfirmation(answer) {
  if (!pendingIntentState) return;
  hideIntentActions();
  appendChatBubble('user', answer === 'yes' ? 'Yes' : 'No');
  setLoadingState(true, 'Applying confirmation...');
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
      pendingIntentState = {
        useCase: pendingIntentState.useCase,
        pendingIntentId: data.pending_intent_id || null,
      };
      appendChatBubble('assistant', PROMPT_CORRECTED_QUESTION, { conversation_state: 'waiting_user_rephrase' });
    } else if (data.conversation_state === 'waiting_analytical_query') {
      pendingIntentState = null;
      appendChatBubble(
        'assistant',
        data.clarification_question || 'Please type your analytical question.',
        data
      );
    } else if (data.conversation_state === 'conversation_ended') {
      pendingIntentState = null;
      appendChatBubble('assistant', data.clarification_question || 'Ok, thank you!', data);
    } else {
      pendingIntentState = null;
      const done = data.conversation_state === 'completed';
      appendChatBubble(
        'assistant',
        done ? 'Here is what I found.' : 'Thanks — proceeding with SQL generation.',
        data
      );
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

if (deleteConfirmModal) {
  deleteConfirmModal.addEventListener('click', (e) => {
    if (e.target === deleteConfirmModal) closeDeleteConfirmModal();
  });
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

if (chatListEl) {
  chatListEl.addEventListener('click', (e) => {
    const delBtn = e.target.closest('.chat-list-delete');
    if (delBtn && delBtn.dataset.sessionId) {
      e.preventDefault();
      e.stopPropagation();
      void handleDeleteChat(delBtn.dataset.sessionId);
      return;
    }
    const btn = e.target.closest('.chat-list-item');
    if (!btn || !btn.dataset.sessionId) return;
    const id = btn.dataset.sessionId;
    if (id === activeSessionId) return;
    if (btn.dataset.useCase) {
      const uc = btn.dataset.useCase.trim();
      const opt = [...useCaseSelect.options].find((o) => o.value === uc);
      if (opt) useCaseSelect.value = uc;
    }
    loadChatSession(id);
  });
}

if (newChatBtn) {
  newChatBtn.addEventListener('click', async () => {
    showError('');
    setLoadingState(true, 'Starting new chat…');
    try {
      /** No POST /session here — the session row is created on first Send. */
      setActiveSessionId(null);
      resetDomainSelect();
      clearChatThread();
      pendingIntentState = null;
      hideIntentActions();
      outputPlaceholder.classList.remove('hidden');
      outputPlaceholder.textContent = 'Submit a question to start the conversation.';
      outputContent.classList.add('hidden');
      await refreshSidebar();
    } catch (err) {
      showError(err?.message || 'Failed to start chat');
    } finally {
      setLoadingState(false);
    }
  });
}

async function init() {
  submitBtn.disabled = true;
  newChatBtn.disabled = true;
  removeLegacyKeys();
  ensureClientId();
  await loadUseCases();
  showError('');
  hideIntentActions();
  outputPlaceholder.classList.remove('hidden');
  outputPlaceholder.textContent = 'Loading conversations…';
  outputContent.classList.add('hidden');

  try {
    let sessions = [];
    try {
      sessions = await fetchSessionsList();
    } catch (e) {
      console.warn('Could not list sessions', e);
      sessions = [];
    }

    const remembered = getRememberedSessionId();
    let pick = null;
    if (remembered && sessions.some((s) => s.session_id === remembered)) {
      pick = remembered;
    } else if (sessions.length) {
      pick = sessions[0].session_id;
    }

    renderChatList(sessions);

    if (!pick) {
      setActiveSessionId(null);
      resetDomainSelect();
      clearChatThread();
      pendingIntentState = null;
      hideIntentActions();
      outputPlaceholder.classList.remove('hidden');
      outputPlaceholder.textContent = 'Submit a question to start the conversation.';
      outputContent.classList.add('hidden');
      submitBtn.disabled = false;
      newChatBtn.disabled = false;
      return;
    }

    await loadChatSession(pick);

    outputPlaceholder.textContent = 'Submit a question to start the conversation.';
    submitBtn.disabled = false;
    newChatBtn.disabled = false;
  } catch (e) {
    outputPlaceholder.textContent = 'Could not initialize. Refresh to retry.';
    showError(e.message || 'Failed to initialize');
    submitBtn.disabled = false;
    newChatBtn.disabled = false;
  }
}
init();
