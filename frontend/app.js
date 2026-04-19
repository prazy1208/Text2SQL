const SESSION_KEY = 'text2sql_session_id';
const LAST_OUTPUT_KEY = 'text2sql_last_output';
const API_BASE = '';

const form = document.getElementById('query-form');
const useCaseSelect = document.getElementById('use-case');
const messageInput = document.getElementById('message');
const submitBtn = document.getElementById('submit-btn');
const outputSection = document.getElementById('output-section');
const outputPlaceholder = document.getElementById('output-placeholder');
const outputContent = document.getElementById('output-content');
const outputError = document.getElementById('output-error');
const outRephrased = document.getElementById('out-rephrased');
const outKeywords = document.getElementById('out-keywords');
const outInsights = document.getElementById('out-insights');
const outFewShot = document.getElementById('out-few-shot');
const outTables = document.getElementById('out-tables');
const outColumns = document.getElementById('out-columns');
const sessionIdEl = document.getElementById('session-id');

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

/** Save last /query response + form context so a hard refresh can restore the panel. */
function persistLastOutput(useCase, message, data) {
  try {
    const pack = {
      session_id: data.session_id || '',
      rephrased_question: data.rephrased_question || '',
      keywords: data.keywords || [],
      business_insights: data.business_insights || [],
      few_shot_examples: data.few_shot_examples || [],
      selected_tables: data.selected_tables || [],
      selected_columns: data.selected_columns || {},
      error: data.error || null,
      _use_case: useCase || '',
      _message: message || '',
    };
    localStorage.setItem(LAST_OUTPUT_KEY, JSON.stringify(pack));
  } catch (e) {
    console.warn('persistLastOutput failed', e);
  }
}

/** Restore output and form after load (e.g. hard refresh). */
function restoreLastOutput() {
  try {
    const raw = localStorage.getItem(LAST_OUTPUT_KEY);
    if (!raw) return;
    const pack = JSON.parse(raw);
    const useCase = pack._use_case;
    const msg = pack._message;
    delete pack._use_case;
    delete pack._message;

    if (useCase && [...useCaseSelect.options].some((o) => o.value === useCase)) {
      useCaseSelect.value = useCase;
    }
    if (msg != null) messageInput.value = msg;

    const hasContent =
      (pack.rephrased_question && String(pack.rephrased_question).trim()) ||
      (pack.keywords && pack.keywords.length) ||
      (pack.business_insights && pack.business_insights.length) ||
      (pack.few_shot_examples && pack.few_shot_examples.length) ||
      (pack.selected_tables && pack.selected_tables.length) ||
      Object.keys(normalizeSelectedColumns(pack.selected_columns)).length ||
      (pack.error && String(pack.error).trim());
    if (hasContent) {
      showOutput(pack);
    }
  } catch (e) {
    console.warn('restoreLastOutput failed', e);
    localStorage.removeItem(LAST_OUTPUT_KEY);
  }
}

function showOutput(data) {
  outputError.classList.add('hidden');
  outputError.textContent = '';
  outputPlaceholder.classList.add('hidden');
  outputContent.classList.remove('hidden');

  outRephrased.textContent = data.rephrased_question || '—';
  outKeywords.innerHTML = (data.keywords && data.keywords.length)
    ? data.keywords.map(k => `<li>${escapeHtml(k)}</li>`).join('')
    : '<li>—</li>';
  outInsights.innerHTML = (data.business_insights && data.business_insights.length)
    ? data.business_insights.map(b => `<li>${escapeHtml(b)}</li>`).join('')
    : '<li>—</li>';

  if (outFewShot) {
    const fs = data.few_shot_examples;
    if (fs && fs.length) {
      outFewShot.innerHTML = fs.map((ex) => {
        const id = ex.id != null ? ex.id : '—';
        const qt = escapeHtml(String(ex.query_type || ''));
        const qn = escapeHtml(String(ex.question_text || ''));
        const sql = escapeHtml(String(ex.sql_query || ''));
        return `<div class="out-few-shot-item"><div class="out-few-shot-head"><span class="out-few-shot-id">#${id}</span> <code>${qt}</code></div><p class="out-few-shot-q">${qn}</p><pre class="out-sql"><code>${sql}</code></pre></div>`;
      }).join('');
    } else {
      outFewShot.innerHTML = '<p class="out-text-muted">—</p>';
    }
  }

  outTables.innerHTML = (data.selected_tables && data.selected_tables.length)
    ? data.selected_tables.map(t => `<li><code>${escapeHtml(t)}</code></li>`).join('')
    : '<li>—</li>';

  const cols = normalizeSelectedColumns(data.selected_columns);
  const colKeys = Object.keys(cols);
  if (outColumns) {
    if (!colKeys.length) {
      const hint =
        (data.selected_tables && data.selected_tables.length)
          ? 'No columns in this response.'
          : '—';
      outColumns.innerHTML = `<p class="out-text-muted">${escapeHtml(hint)}</p>`;
    } else {
      colKeys.sort();
      outColumns.innerHTML = colKeys.map((tableFqn) => {
        const list = cols[tableFqn];
        const items = list.map((c) => `<li><code>${escapeHtml(String(c))}</code></li>`).join('');
        return `<div class="out-column-group"><h4 class="out-column-table"><code>${escapeHtml(tableFqn)}</code></h4><ul class="out-list out-list-mono">${items}</ul></div>`;
      }).join('');
    }
  } else {
    console.error('text2sql UI: missing #out-columns in index.html — hard refresh (Ctrl+Shift+R) or clear cache.');
  }

  if (data.session_id) setStoredSessionId(data.session_id);
  if (data.error) {
    outputError.textContent = data.error;
    outputError.classList.remove('hidden');
  }
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

  submitBtn.disabled = true;
  outputPlaceholder.classList.remove('hidden');
  outputPlaceholder.textContent = 'Processing… (first request may take 1–2 min to load the model)';
  outputContent.classList.add('hidden');
  outputError.classList.add('hidden');

  try {
    const body = {
      message,
      use_case: useCase,
      session_id: getStoredSessionId(),
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
      const retryBody = {
        ...body,
        session_id: getStoredSessionId(),
      };
      res = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(retryBody),
      });
      data = await res.json();
    }

    if (!res.ok) {
      const detail = data.detail != null ? data.detail : res.statusText;
      const errText = typeof detail === 'string' ? detail : JSON.stringify(detail);
      const errPayload = {
        rephrased_question: '',
        keywords: [],
        business_insights: [],
        few_shot_examples: [],
        selected_tables: [],
        selected_columns: {},
        error: errText,
      };
      showOutput(errPayload);
      persistLastOutput(useCase, message, errPayload);
      return;
    }

    showOutput(data);
    persistLastOutput(useCase, message, data);
  } catch (err) {
    const errPayload = {
      rephrased_question: '',
      keywords: [],
      business_insights: [],
      few_shot_examples: [],
      selected_tables: [],
      selected_columns: {},
      error: err.message || 'Request failed',
    };
    showOutput(errPayload);
    persistLastOutput(useCase, message, errPayload);
  } finally {
    submitBtn.disabled = false;
    outputPlaceholder.textContent = 'Submit a question to see rephrased intent, keywords, business insights, few-shot patterns, selected tables, and selected columns.';
  }
});

async function init() {
  submitBtn.disabled = true;
  await loadUseCases();
  localStorage.removeItem(LAST_OUTPUT_KEY);
  clearStoredSessionId();
  outputError.classList.add('hidden');
  outputError.textContent = '';
  outputPlaceholder.classList.remove('hidden');
  outputPlaceholder.textContent = 'Starting a fresh session...';
  outputContent.classList.add('hidden');

  try {
    await bootstrapFreshSession();
    outputPlaceholder.textContent = 'Submit a question to see rephrased intent, keywords, business insights, few-shot patterns, selected tables, and selected columns.';
    submitBtn.disabled = false;
  } catch (e) {
    outputPlaceholder.textContent = 'Could not create a session. Refresh to retry.';
    outputError.textContent = e.message || 'Failed to initialize session';
    outputError.classList.remove('hidden');
  }
}
init();
