/**
 * GluLess Agent Console — app.js
 * AG-UI SSE streaming client (redesigned)
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
    description: "GasCity responded with HTTP 200"`.trim();

// ── State ─────────────────────────────────────────────
let isRunning   = false;
let eventCount  = 0;
let abortCtrl   = null;
let lineIndex   = 0;

// ── DOM ───────────────────────────────────────────────
const $input     = document.getElementById('contract-input');
const $btnRun    = document.getElementById('btn-run');
const $runIcon   = document.getElementById('run-icon');
const $runLabel  = document.getElementById('run-label');
const $btnClear  = document.getElementById('btn-clear');
const $btnLoad   = document.getElementById('btn-load-demo');
const $body      = document.getElementById('terminal-body');
const $gutter    = document.getElementById('terminal-gutter');
const $agentPill = document.getElementById('agent-pill');
const $pillDot   = $agentPill.querySelector('.pill-dot');
const $pillLabel = document.getElementById('agent-pill-label');

// Inspector refs
const $valId     = document.getElementById('val-id');
const $valGoal   = document.getElementById('val-goal');
const $limitList = document.getElementById('limits-list');
const $utilList  = document.getElementById('utilities-list');
const $evSection = document.getElementById('evidence-section');
const $evList    = document.getElementById('evidence-list');
const $metrics   = document.getElementById('metrics-block');
const $mPlan     = document.getElementById('m-plan');
const $mObs      = document.getElementById('m-obs');
const $mEv       = document.getElementById('m-ev');
const $mEvents   = document.getElementById('m-events');

// Phase strip refs
const $pips = document.querySelectorAll('.phase-pip');

// ── Boot ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  pingAgent();
  $btnRun.addEventListener('click', onRunClick);
  $btnClear.addEventListener('click', onClear);
  $btnLoad.addEventListener('click', loadDemo);
  $input.addEventListener('input', () => {
    $btnRun.disabled = !$input.value.trim();
  });
  $input.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && !$btnRun.disabled) {
      e.preventDefault();
      onRunClick();
    }
  });
  document.getElementById('ctab-contract').addEventListener('click', () => switchTab('contract'));
  document.getElementById('ctab-natural').addEventListener('click', () => switchTab('natural'));
});

function loadDemo() {
  $input.value = DEMO_CONTRACT;
  $input.rows = 8;
  $btnRun.disabled = false;
}

function switchTab(mode) {
  document.querySelectorAll('.ctab').forEach(t => t.classList.remove('active'));
  document.getElementById(`ctab-${mode}`).classList.add('active');
  $input.spellcheck = mode === 'natural';
  $input.placeholder = mode === 'contract'
    ? 'Paste a GLU contract YAML…'
    : 'Describe what you want to achieve…';
}

// ── Agent ping ────────────────────────────────────────
async function pingAgent() {
  try {
    const res = await fetch(AGENT_URL.replace('/agent', '/health'),
      { signal: AbortSignal.timeout(3000) });
    if (res.ok) setAgentStatus('online', 'Ready');
    else setAgentStatus('error', 'Error');
  } catch {
    setAgentStatus('offline', 'Offline');
  }
}

function setAgentStatus(state, label) {
  $pillDot.className = `pill-dot ${state}`;
  $pillLabel.textContent = label;
}

// ── Run ───────────────────────────────────────────────
async function onRunClick() {
  if (isRunning) { abortCtrl?.abort(); return; }

  const msg = $input.value.trim();
  if (!msg) return;

  startRun();

  const threadId = crypto.randomUUID();
  const runId    = crypto.randomUUID();
  abortCtrl = new AbortController();

  try {
    const res = await fetch(AGENT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
      body: JSON.stringify({
        threadId, runId,
        messages: [{ role: 'user', content: msg }],
        context: [], tools: [], state: null,
      }),
      signal: abortCtrl.signal,
    });

    if (!res.ok) {
      logError(`HTTP ${res.status}: ${await res.text()}`);
      endRun(); return;
    }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try { handleEvent(JSON.parse(line.slice(6))); }
          catch { /* skip */ }
        }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      logError(`Connection failed: ${err.message}\n\nStart the agent:\n  cd .agents/agents/glu-agent\n  .venv/bin/uvicorn agent:app --reload --port 8080`);
    }
  } finally {
    endRun();
  }
}

function startRun() {
  isRunning = true;
  eventCount = 0;
  lineIndex = 0;
  clearEmpty();
  $btnRun.classList.add('stop');
  $runIcon.textContent = '◼';
  $runLabel.textContent = 'Stop';
  $btnRun.disabled = false;
  setAgentStatus('running', 'Running');
}

function endRun() {
  isRunning = false;
  $btnRun.classList.remove('stop');
  $runIcon.textContent = '▶';
  $runLabel.textContent = 'Run';
  pingAgent();
}

// ── Event dispatch ────────────────────────────────────
function handleEvent(event) {
  eventCount++;
  bump($mEvents, eventCount);

  const { type } = event;

  switch (type) {

    case 'RUN_STARTED':
      logRow('RUN_STARTED', 'b-RUN_STARTED',
        `thread=${event.threadId?.slice(0,8)}…  run=${event.runId?.slice(0,8)}…`);
      setPhase('compiling');
      break;

    // Protocol signals — silent
    case 'TEXT_MESSAGE_START':
    case 'TEXT_MESSAGE_END':
      break;

    case 'TEXT_MESSAGE_CHUNK': {
      const delta = (event.delta || '').replace(/\n$/, '');
      if (!delta.trim()) break;
      // Split on embedded newlines — each line is its own row
      for (const line of delta.split('\n')) {
        if (!line.trim()) continue;
        const bodyClass = line.startsWith('✅') ? 'ok'
          : line.startsWith('⚠') ? 'warn'
          : line.startsWith('❌') ? 'err'
          : '';
        logChunk(line, bodyClass);
      }
      break;
    }

    case 'STATE_SNAPSHOT': {
      const s = event.snapshot || {};
      setPhase(s.phase || 'idle');
      bump($mPlan, s.plan?.length || 0);
      bump($mObs,  s.observations?.length || 0);
      bump($mEv,   s.evidence?.length || 0);
      $metrics.style.display = 'grid';
      syncInspector(s);
      logRow('SNAPSHOT', 'b-STATE_SNAPSHOT',
        `phase=${s.phase}  goals=${s.goals?.length}  utilities=${s.utilities?.length}`);
      renderEvidence(s.evidence || []);
      break;
    }

    case 'STATE_DELTA': {
      const ops = event.delta || [];
      const summary = ops.map(op => {
        const field = op.path?.replace('/', '') || '?';
        const val   = typeof op.value === 'object'
          ? `[${Array.isArray(op.value) ? op.value.length + ' item(s)' : 'object'}]`
          : String(op.value);
        return `${field} → ${val}`;
      }).join('  ·  ');
      logRow('DELTA', 'b-STATE_DELTA', summary || `${ops.length} op(s)`);
      const phaseOp = ops.find(o => o.path === '/phase');
      if (phaseOp?.value) setPhase(phaseOp.value);
      break;
    }

    case 'RUN_FINISHED':
      if (event.warning) {
        logRow('FINISHED', 'b-RUN_FINISHED_W', event.warning);
        setPhase('warning');
      } else {
        logRow('FINISHED', 'b-RUN_FINISHED', 'success');
        setPhase('complete');
      }
      setAgentStatus('online', 'Ready');
      break;

    case 'RUN_ERROR':
      logError(`${event.code || 'ERROR'}: ${event.message}`);
      setPhase('error');
      setAgentStatus('error', 'Error');
      break;

    default:
      logRow(type, 'b-STATE_SNAPSHOT', JSON.stringify(event).slice(0, 100));
  }
}

// ── DOM helpers ───────────────────────────────────────
function clearEmpty() {
  document.getElementById('term-empty')?.remove();
}

function onClear() {
  $body.innerHTML = '<div class="term-empty" id="term-empty"><div class="term-empty-sigil">⬡</div><div class="term-empty-head">Ready to execute</div><div class="term-empty-sub">Load a contract below and press <kbd>⌘↵</kbd> to run</div></div>';
  $gutter.innerHTML = '';
  lineIndex = 0;
  eventCount = 0;
  $mEvents.textContent = '0';
  $mPlan.textContent = '0';
  $mObs.textContent = '0';
  $mEv.textContent = '0';
  $metrics.style.display = 'none';
  $evSection.style.display = 'none';
  resetPhase();
}

function logRow(label, badgeClass, body) {
  lineIndex++;
  const ts = now();

  const row = document.createElement('div');
  row.className = 'log-row';
  row.innerHTML = `
    <span class="log-ts">${ts}</span>
    <span class="log-badge ${badgeClass}">${escHtml(label)}</span>
    <span class="log-body">${escHtml(body)}</span>
  `;
  $body.appendChild(row);
  addGutterLine(lineIndex);
  scroll();
}

function logChunk(text, bodyClass = '') {
  lineIndex++;
  const ts = now();

  const row = document.createElement('div');
  row.className = 'log-row chunk-row';
  row.innerHTML = `
    <span class="log-ts">${ts}</span>
    <span class="log-badge b-CHUNK"></span>
    <span class="log-body${bodyClass ? ' ' + bodyClass : ''}">${escHtml(text)}</span>
  `;
  $body.appendChild(row);
  addGutterLine(lineIndex);
  scroll();
}

function logError(msg) {
  lineIndex++;
  const row = document.createElement('div');
  row.className = 'log-row';
  row.style.borderLeft = '2px solid var(--red)';
  row.style.paddingLeft = '8px';
  row.innerHTML = `
    <span class="log-ts">${now()}</span>
    <span class="log-badge b-RUN_ERROR">ERROR</span>
    <span class="log-body err" style="white-space:pre-wrap">${escHtml(msg)}</span>
  `;
  $body.appendChild(row);
  addGutterLine(lineIndex);
  scroll();
}

function addGutterLine(n) {
  const el = document.createElement('div');
  el.className = 'gutter-line';
  el.textContent = n;
  $gutter.appendChild(el);
}

function scroll() {
  $body.scrollTop = $body.scrollHeight;
}

function now() {
  return new Date().toLocaleTimeString('en-US', {
    hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function bump(el, val) {
  el.textContent = val;
  el.classList.add('bump');
  setTimeout(() => el.classList.remove('bump'), 300);
}

// ── Inspector sync ────────────────────────────────────
function syncInspector(s) {
  if (s.contractId) $valId.textContent = s.contractId;

  if (s.goals?.length) {
    $valGoal.textContent = s.goals[0].expression;
  }

  if (s.limits?.length) {
    $limitList.innerHTML = s.limits.map(l => {
      const isAllow = l.pattern?.startsWith('allow');
      const verb = isAllow ? 'allow' : 'deny';
      const rest = (l.pattern || l.id).replace(/^(allow|deny)\s*/, '');
      return `<div class="limit-row ${isAllow ? 'allow' : 'deny'}">
        <span class="limit-verb">${verb}</span>${escHtml(rest)}
      </div>`;
    }).join('');
  }

  if (s.utilities?.length) {
    $utilList.innerHTML = s.utilities.map(u => `
      <div class="utility-row${s.phase === 'executing' ? ' active' : s.phase === 'complete' || s.phase === 'warning' ? ' done' : ''}" id="u-${u.id}">
        <span class="u-status-dot"></span>
        <span class="u-id">${escHtml(u.id)}</span>
      </div>
    `).join('');
  }
}

// ── Evidence ──────────────────────────────────────────
function renderEvidence(items) {
  if (!items.length) return;
  $evSection.style.display = 'block';
  $evList.innerHTML = items.map(ev => `
    <div class="ev-row ${ev.passed ? 'pass' : 'fail'}">
      <span class="ev-glyph">${ev.passed ? '✅' : '❌'}</span>
      <div class="ev-content">
        <span class="ev-req">${escHtml(ev.requirementId)}</span>
        <span class="ev-assert">${escHtml(ev.assertion)}</span>
      </div>
    </div>
  `).join('');
}

// ── Phase strip ───────────────────────────────────────
const PHASE_PROG     = ['compiling', 'planning', 'executing', 'complete'];
const PHASE_TERMINAL = new Set(['complete', 'warning', 'error']);

function setPhase(phase) {
  const progIdx    = PHASE_PROG.indexOf(phase);
  const isTerminal = PHASE_TERMINAL.has(phase);

  $pips.forEach(pip => {
    const p = pip.dataset.phase;
    pip.classList.remove('active', 'done', 'warning', 'error');

    if (p === phase) {
      pip.classList.add(isTerminal && phase !== 'complete' ? phase : 'active');
    } else if (PHASE_PROG.includes(p)) {
      const pIdx = PHASE_PROG.indexOf(p);
      const cutoff = isTerminal ? PHASE_PROG.length : progIdx;
      if (pIdx < cutoff) pip.classList.add('done');
    }
  });
}

function resetPhase() {
  $pips.forEach(p => p.classList.remove('active', 'done', 'warning', 'error'));
}
