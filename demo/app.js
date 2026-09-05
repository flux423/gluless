/**
 * GluLess Demo — app.js
 * AG-UI streaming client
 *
 * Connects to the GLU Agent via POST + SSE (text/event-stream).
 * Renders AG-UI events into the stream log.
 * Updates sidebar state in real time.
 */

const AGENT_URL = 'http://localhost:8080/agent';

const DEMO_CONTRACT = `id: glu-demo-contract
goals:
  - id: goal-list-cities
    expression: "cities.listed == true"
    description: "Retrieve all registered cities from GasCity"

limits:
  - id: limit-deny-all
    action_pattern: "deny *"
    description: "Deny any action not explicitly permitted"
  - id: limit-allow-list
    action_pattern: "allow GasCity.cities.list"
    description: "Permit listing cities — read only, no side-effects"

utilities:
  - GasCity.cities.list

evidence_requirements:
  - id: ev-http-ok
    assertion: "response.status == 200"
    description: "GasCity responded with HTTP 200"
`.trim();

// ── State ─────────────────────────────────────────
let isRunning = false;
let eventCount = 0;
let currentMessageId = null;
let abortController = null;

// ── DOM refs ──────────────────────────────────────
const $log     = document.getElementById('stream-log');
const $btnRun  = document.getElementById('btn-run');
const $btnClear = document.getElementById('btn-clear');
const $btnLoadDemo = document.getElementById('btn-load-demo');
const $input   = document.getElementById('contract-input');
const $status  = document.getElementById('agent-status');
const $statePanel = document.getElementById('state-panel');
const $phaseBadge = document.getElementById('state-phase-badge');
const $metricPlan  = document.getElementById('metric-plan');
const $metricObs   = document.getElementById('metric-obs');
const $metricEv    = document.getElementById('metric-ev');
const $metricEvts  = document.getElementById('metric-events');
const $evidencePanel = document.getElementById('evidence-panel');
const $tabContract = document.getElementById('tab-contract');
const $tabNatural  = document.getElementById('tab-natural');

// ── Init ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  pingAgent();
  $btnRun.addEventListener('click', onRunClick);
  $btnClear.addEventListener('click', onClear);
  $btnLoadDemo.addEventListener('click', () => {
    $input.value = DEMO_CONTRACT;
    $input.style.rows = 10;
    $btnRun.disabled = false;
  });
  $input.addEventListener('input', () => {
    $btnRun.disabled = $input.value.trim().length === 0;
  });
  $tabContract.addEventListener('click', () => switchTab('contract'));
  $tabNatural.addEventListener('click', () => switchTab('natural'));
  $input.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!$btnRun.disabled) onRunClick();
    }
  });
});

// ── Agent ping ────────────────────────────────────
async function pingAgent() {
  try {
    const res = await fetch(`${AGENT_URL.replace('/agent', '/health')}`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) setStatus('online', 'Agent ready');
    else setStatus('error', 'Agent error');
  } catch {
    setStatus('offline', 'Agent offline');
  }
}

function setStatus(type, label) {
  const dot = $status.querySelector('.status-dot');
  dot.className = `status-dot ${type}`;
  $status.querySelector('span').textContent = label;
}

// ── Tab switching ─────────────────────────────────
function switchTab(mode) {
  [$tabContract, $tabNatural].forEach(t => t.classList.remove('active'));
  if (mode === 'contract') {
    $tabContract.classList.add('active');
    $input.placeholder = 'Paste a GLU contract YAML here…';
    $input.spellcheck = false;
  } else {
    $tabNatural.classList.add('active');
    $input.placeholder = 'Describe your goal in natural language, e.g. "List all cities in GasCity"';
    $input.spellcheck = true;
  }
}

// ── Run ───────────────────────────────────────────
async function onRunClick() {
  if (isRunning) {
    abortController?.abort();
    return;
  }

  const userMessage = $input.value.trim();
  if (!userMessage) return;

  startRun();

  const threadId = crypto.randomUUID();
  const runId    = crypto.randomUUID();

  abortController = new AbortController();

  try {
    const response = await fetch(AGENT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
      body: JSON.stringify({
        threadId,
        runId,
        messages: [{ role: 'user', content: userMessage }],
        context: [],
        tools: [],
        state: null,
      }),
      signal: abortController.signal,
    });

    if (!response.ok) {
      appendError(`HTTP ${response.status}: ${await response.text()}`);
      endRun();
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            handleEvent(event);
          } catch { /* skip malformed */ }
        }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      appendError(`Connection error: ${err.message}\n\nIs the GLU agent running? Start it with:\n  cd .agents/agents/glu-agent && uvicorn agent:app --reload --port 8080`);
    }
  } finally {
    endRun();
  }
}

// ── Event handlers ────────────────────────────────
function handleEvent(event) {
  eventCount++;
  $metricEvts.textContent = eventCount;

  const { type } = event;

  switch (type) {
    case 'RUN_STARTED':
      appendEventRow(type, `thread=${event.threadId?.slice(0,8)}…  run=${event.runId?.slice(0,8)}…`);
      setPhase('compiling');
      setStatus('running', 'Running…');
      break;

    case 'TEXT_MESSAGE_START':
      currentMessageId = event.messageId;
      currentChunkEl = null;
      appendEventRow(type, `messageId=${event.messageId?.slice(0,8)}…`);
      break;

    case 'TEXT_MESSAGE_CHUNK': {
      // Each chunk is its own log row — reads like a live terminal
      const delta = event.delta || '';
      if (delta.trim()) {
        appendChunkLine(delta);
      }
      break;
    }

    case 'TEXT_MESSAGE_END':
      currentMessageId = null;
      break;

    case 'STATE_SNAPSHOT': {
      const s = event.snapshot || {};
      setPhase(s.phase || 'idle');
      $metricPlan.textContent = s.plan?.length || 0;
      $metricObs.textContent  = s.observations?.length || 0;
      $metricEv.textContent   = s.evidence?.length || 0;
      $statePanel.style.display = 'block';
      updateSidebarFromState(s);
      appendEventRow(type, `phase=${s.phase}  goals=${s.goals?.length}  utilities=${s.utilities?.length}`);
      renderEvidence(s.evidence || []);
      break;
    }

    case 'STATE_DELTA': {
      appendEventRow(type, `ops=${event.delta?.length || 0}`);
      break;
    }

    case 'RUN_FINISHED':
      appendEventRow(type, event.warning ? `⚠️ ${event.warning}` : '✅ success');
      setPhase('complete');
      setStatus('online', 'Agent ready');
      break;

    case 'RUN_ERROR':
      appendEventRow(type, `${event.code}: ${event.message}`);
      setPhase('error');
      setStatus('error', 'Error');
      break;

    default:
      appendEventRow(type, JSON.stringify(event).slice(0, 120));
  }
}

// ── DOM helpers ───────────────────────────────────
function startRun() {
  isRunning = true;
  eventCount = 0;
  $btnRun.innerHTML = '<span class="btn-icon">◼</span> Stop';
  $btnRun.classList.add('running');
  $btnRun.disabled = false;
  clearWelcome();
  setStatus('running', 'Connecting…');
}

function endRun() {
  isRunning = false;
  $btnRun.innerHTML = '<span class="btn-icon">▶</span> Run Contract';
  $btnRun.classList.remove('running');
  if (isRunning === false) setStatus('online', 'Agent ready');
  pingAgent();
}

function clearWelcome() {
  const w = $log.querySelector('.stream-welcome');
  if (w) w.remove();
}

function onClear() {
  $log.innerHTML = '<div class="stream-welcome"><div class="welcome-icon">⬡</div><h2>Ready to execute</h2><p>Enter a GLU contract below or use the pre-loaded demo contract.</p><div class="welcome-pills"><span class="pill">AG-UI Protocol</span><span class="pill">SSE Streaming</span><span class="pill">GLU Contracts</span><span class="pill">A2UI Ready</span></div></div>';
  $statePanel.style.display = 'none';
  $evidencePanel.innerHTML = '<div class="evidence-empty">No evidence yet</div>';
  eventCount = 0;
  $metricEvts.textContent = '0';
  $metricPlan.textContent = '0';
  $metricObs.textContent  = '0';
  $metricEv.textContent   = '0';
  resetPhases();
}

function appendEventRow(type, body) {
  const el = document.createElement('div');
  el.className = 'stream-event';

  const ts = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  el.innerHTML = `
    <span class="event-ts">${ts}</span>
    <span class="event-type-badge badge-${type}">${type}</span>
    <span class="event-body">${escHtml(body)}</span>
  `;
  $log.appendChild(el);
  scrollLog();
}

function appendChunkLine(text) {
  // Trim trailing newline for display, keep internal newlines
  const display = text.replace(/\n$/, '');
  if (!display) return;
  const lines = display.split('\n');
  for (const line of lines) {
    if (!line) continue;
    const el = document.createElement('div');
    el.className = 'stream-event chunk-line';
    el.innerHTML = `
      <span class="event-ts">${new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
      <span class="event-type-badge badge-TEXT_MESSAGE_CHUNK">CHUNK</span>
      <span class="event-body chunk-text">${escHtml(line)}</span>
    `;
    $log.appendChild(el);
  }
  scrollLog();
}

function appendError(msg) {
  const el = document.createElement('div');
  el.className = 'stream-event';
  el.style.borderLeft = '2px solid var(--accent-red)';
  el.style.marginLeft = '4px';
  el.innerHTML = `
    <span class="event-ts">${new Date().toLocaleTimeString('en-US', { hour12: false })}</span>
    <span class="event-type-badge badge-RUN_ERROR">RUN_ERROR</span>
    <span class="event-body" style="color:var(--accent-red);white-space:pre-wrap">${escHtml(msg)}</span>
  `;
  $log.appendChild(el);
  scrollLog();
}

function scrollLog() {
  $log.scrollTop = $log.scrollHeight;
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Phase tracker ─────────────────────────────────
const PHASE_ORDER = ['idle', 'compiling', 'planning', 'executing', 'complete', 'error'];

function setPhase(phase) {
  const steps = document.querySelectorAll('.phase-step');
  const idx = PHASE_ORDER.indexOf(phase);

  steps.forEach(el => {
    const p = el.dataset.phase;
    const pIdx = PHASE_ORDER.indexOf(p);
    el.classList.remove('active', 'done');
    if (p === phase) el.classList.add('active');
    else if (pIdx < idx && phase !== 'error') el.classList.add('done');
  });

  $phaseBadge.textContent = phase;
  $phaseBadge.className = `state-phase-badge phase-${phase}`;
}

function resetPhases() {
  document.querySelectorAll('.phase-step').forEach(el => el.classList.remove('active','done'));
  $phaseBadge.textContent = '—';
  $phaseBadge.className = 'state-phase-badge';
}

// ── Sidebar state sync ────────────────────────────
function updateSidebarFromState(state) {
  // Goals
  if (state.goals?.length) {
    document.getElementById('goal-text').textContent = state.goals[0].expression;
    document.getElementById('block-goal').classList.add('active-goal');
  }

  // Limits
  if (state.limits?.length) {
    const el = document.getElementById('limits-list');
    el.innerHTML = state.limits.map(l => {
      const isAllow = l.pattern?.startsWith('allow');
      return `<div class="limit-item${isAllow ? ' allow' : ''}">${escHtml(l.pattern || l.id)}</div>`;
    }).join('');
    document.getElementById('block-limits').classList.add('active-limit');
  }

  // Utilities
  if (state.utilities?.length) {
    const el = document.getElementById('utilities-list');
    el.innerHTML = state.utilities.map(u => `
      <div class="utility-pill${state.phase === 'executing' ? ' active' : ''}" id="util-${u.id}">
        <span class="util-dot"></span>
        ${escHtml(u.id)}
      </div>
    `).join('');
    document.getElementById('block-utilities').classList.add('active-util');
  }
}

// ── Evidence ──────────────────────────────────────
function renderEvidence(evidence) {
  if (!evidence.length) return;
  $evidencePanel.innerHTML = '';
  evidence.forEach(ev => {
    const el = document.createElement('div');
    el.className = `evidence-item ${ev.passed ? 'pass' : 'fail'}`;
    el.innerHTML = `
      <span class="ev-badge">${ev.passed ? '✅' : '❌'}</span>
      <div class="ev-content">
        <span class="ev-id">${escHtml(ev.requirementId)}</span>
        <span class="ev-assertion">${escHtml(ev.assertion)}</span>
      </div>
    `;
    $evidencePanel.appendChild(el);
  });
}
