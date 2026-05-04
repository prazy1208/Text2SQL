const SESSION_KEY = 'text2sql_session_id';
const CHAT_HISTORY_KEY = 'text2sql_chat_history';
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

let pendingIntentState = null;

const PROMPT_CORRECTED_QUESTION = 'Please provide a corrected question.';

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

async function loadUseCases() {
  try {
    const res = await fetch(`${API_BASE}/use-cases`);
    if (!res.ok) throw new Error('Failed to load use cases');
    const list = await res.json();
    useCaseSelect.innerHTML = '<option value="">Select domain…</option>' +
      list.map(u => `<option value="${u}">${u.charAt(0).toUpperCase() + u.slice(1)}</option>`).join('');
  } catch (e) {
    useCaseSelect.innerHTML = '<option value="">Failed to load</option>';
    console.error(e);
  }
}

function getStoredSessionId() {
  return localStorage.getItem(SESSION_KEY) || null;
}

function setStoredSessionId(id) {
  if (id) localStorage.setItem(SESSION_KEY, id);
  sessionIdEl.textContent = id || '—';
}

function clearStoredSessionId() {
  localStorage.removeItem(SESSION_KEY);
  sessionIdEl.textContent = '—';
}

function getStoredChatHistory() {
  try {
    const raw = localStorage.getItem(CHAT_HISTORY_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch (_e) {
    return [];
  }
}

function setStoredChatHistory(history) {
  try {
    localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(history || []));
  } catch (e) {
    console.warn('setStoredChatHistory failed', e);
  }
}

function clearStoredChatHistory() {
  localStorage.removeItem(CHAT_HISTORY_KEY);
}

async function bootstrapFreshSession() {
  const res = await fetch(`${API_BASE}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  const data = await res.json();
  if (!res.ok || !data?.session_id) {
    const detail = data?.detail != null ? data.detail : res.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  setStoredSessionId(String(data.session_id));
  return data.session_id;
}

function scrollChatToBottom() {
  if (!chatScroll) return;
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function setLoadingState(loading, text) {
  submitBtn.disabled = loading;
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
  return keys.map((tableFqn) => {
    const items = cols[tableFqn].map((c) => `<li><code>${escapeHtml(String(c))}</code></li>`).join('');
    return `<div class="out-column-group"><h4 class="out-column-table"><code>${escapeHtml(tableFqn)}</code></h4><ul class="out-list out-list-mono">${items}</ul></div>`;
  }).join('');
}

function buildAssistantDetails(data) {
  if (!data || typeof data !== 'object') return '';
  const parts = [];
  const state = data.conversation_state;
  // Confirmation / rephrase: the main bubble text is enough — no duplicate rephrase or metadata blocks.
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
    parts.push(`<h4>Business insights</h4><ul class="out-list">${data.business_insights.map((b) => `<li>${escapeHtml(b)}</li>`).join('')}</ul>`);
  }

  if (data.selected_tables && data.selected_tables.length) {
    parts.push(`<h4>Selected tables</h4><ul class="out-list out-list-mono">${data.selected_tables.map((t) => `<li><code>${escapeHtml(t)}</code></li>`).join('')}</ul>`);
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
  scrollChatToBottom();
}

function persistCurrentChat() {
  const history = [];
  chatThread.querySelectorAll('.chat-bubble').forEach((node) => {
    const isUser = node.classList.contains('chat-bubble-user');
    const textNode = node.querySelector('.chat-bubble-text');
    history.push({
      role: isUser ? 'user' : 'assistant',
      text: textNode ? textNode.textContent : '',
      html: node.innerHTML,
    });
  });
  setStoredChatHistory(history);
}

function restoreChat() {
  const history = getStoredChatHistory();
  if (!history.length) return;
  showChatArea();
  history.forEach((item) => {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${item.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'}`;
    bubble.innerHTML = item.html || '';
    chatThread.appendChild(bubble);
  });
  scrollChatToBottom();
}

function showError(errorText) {
  outputError.textContent = errorText || '';
  outputError.classList.toggle('hidden', !errorText);
}

function hideIntentActions() {
  dockIntentActionsDefault();
}

async function callQuery(payload) {
  let res = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  let data = await res.json();

  const invalidSession =
    !res.ok &&
    data?.detail &&
    String(data.detail).toLowerCase().includes('invalid or unknown session_id');
  if (invalidSession) {
    await bootstrapFreshSession();
    const retryPayload = {
      ...payload,
      session_id: getStoredSessionId(),
    };
    res = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(retryPayload),
    });
    data = await res.json();
  }

  if (data.session_id) setStoredSessionId(data.session_id);
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
      session_id: getStoredSessionId(),
      message_type: pendingIntentState ? 'intent_correction' : 'new_query',
    };
    const { res, data } = await callQuery(body);

    if (!res.ok) {
      const detail = data.detail != null ? data.detail : res.statusText;
      const errText = typeof detail === 'string' ? detail : JSON.stringify(detail);
      showError(errText);
      appendChatBubble('assistant', `Error: ${errText}`);
      persistCurrentChat();
      return;
    }

    if (data.conversation_state === 'waiting_intent_confirmation') {
      pendingIntentState = {
        useCase,
        pendingIntentId: data.pending_intent_id || null,
      };
      const prompt = data.clarification_question || `Did I understand correctly: ${data.resolved_question || data.rephrased_question}?`;
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
      appendChatBubble(
        'assistant',
        data.clarification_question || 'Ok, thank you!',
        data
      );
    } else {
      pendingIntentState = null;
      hideIntentActions();
      appendChatBubble('assistant', 'Here is what I found.', data);
      if (data.error) showError(data.error);
    }
    persistCurrentChat();
    messageInput.value = '';
  } catch (err) {
    const errText = err?.message || 'Request failed';
    showError(errText);
    appendChatBubble('assistant', `Error: ${errText}`);
    persistCurrentChat();
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
      session_id: getStoredSessionId(),
      message_type: 'intent_confirmation',
      confirmation: answer,
    };
    const { res, data } = await callQuery(payload);
    if (!res.ok) {
      const detail = data.detail != null ? data.detail : res.statusText;
      const errText = typeof detail === 'string' ? detail : JSON.stringify(detail);
      showError(errText);
      appendChatBubble('assistant', `Error: ${errText}`);
      persistCurrentChat();
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
      appendChatBubble(
        'assistant',
        data.clarification_question || 'Ok, thank you!',
        data
      );
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
    persistCurrentChat();
  } catch (err) {
    const errText = err?.message || 'Request failed';
    showError(errText);
    appendChatBubble('assistant', `Error: ${errText}`);
    persistCurrentChat();
  } finally {
    setLoadingState(false);
    hideIntentActions();
  }
}

intentYesBtn.addEventListener('click', () => submitIntentConfirmation('yes'));
intentNoBtn.addEventListener('click', () => submitIntentConfirmation('no'));

async function init() {
  submitBtn.disabled = true;
  await loadUseCases();
  clearStoredSessionId();
  showError('');
  hideIntentActions();
  outputPlaceholder.classList.remove('hidden');
  outputPlaceholder.textContent = 'Starting a fresh session...';
  outputContent.classList.add('hidden');

  try {
    await bootstrapFreshSession();
    restoreChat();
    outputPlaceholder.textContent = 'Submit a question to start the conversation.';
    submitBtn.disabled = false;
  } catch (e) {
    outputPlaceholder.textContent = 'Could not create a session. Refresh to retry.';
    showError(e.message || 'Failed to initialize session');
  }
}
init();
