const SESSION_KEY = 'text2sql_session_id';
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
const outTables = document.getElementById('out-tables');
const sessionIdEl = document.getElementById('session-id');

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
  outTables.innerHTML = (data.selected_tables && data.selected_tables.length)
    ? data.selected_tables.map(t => `<li><code>${escapeHtml(t)}</code></li>`).join('')
    : '<li>—</li>';

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
    const res = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (!res.ok) {
      showOutput({
        rephrased_question: '',
        keywords: [],
        business_insights: [],
        selected_tables: [],
        error: data.detail || res.statusText,
      });
      return;
    }

    showOutput(data);
  } catch (err) {
    showOutput({
      rephrased_question: '',
      keywords: [],
      business_insights: [],
      selected_tables: [],
      error: err.message || 'Request failed',
    });
  } finally {
    submitBtn.disabled = false;
    outputPlaceholder.textContent = 'Submit a question to see rephrased intent, keywords, business insights, and selected tables.';
  }
});

loadUseCases();
setStoredSessionId(getStoredSessionId());
