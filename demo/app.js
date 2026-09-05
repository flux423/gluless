/**
 * GluLess Runtime — app.js
 *
 * AG-UI SSE client, contract-first rendering.
 *
 * Renders state into five semantic zones:
 *   Goal · Limits · Utilities · Pipeline · Decision · Evidence · Result
 *
 * The raw AG-UI event stream is demoted to a collapsible events drawer.
 */

'use strict';

const AGENT_URL = 'http://localhost:8080/agent';

const DEMO_CONTRACT = `id: glu-demo-contract
goals:
  - id: goal-list-services
    expression: "services.listed == true"
    description: "List all services and verify they are reachable"
limits:
  - id: limit-deny-all
    action_pattern: "deny *"
    description: "Deny any action not explicitly permitted"
  - id: limit-allow-list
    action_pattern: "allow Monitoring.services.list"
    description: "Permit listing services — read-only, no side effects"
utilities:
  - Monitoring.services.list
evidence_requirements:
  - id: ev-http-ok
    assertion: "response.status == 200"
    description: "Service API responded with HTTP 200"`.trim();

// ── Pipeline stage → phase mapping ───────────────────────────
const STAGE_PHASES = {
  resolve:   ['resolving'],
  filter:    ['filtering'],
  authorize: ['authorizing'],
  execute:   ['executing'],
  verify:    ['verifying'],
};

const TERMINAL_PHASES = new Set(['proven', 'unresolved']);

// Phase → stage index (for marking prior stages as done)
const PHASE_ORDER = ['resolving', 'filtering', 'authorizing', 'executing', 'verifying'];

// ── State ─────────────────────────────────────────────────────
let isRunning   = false;
let abortCtrl   = null;
let eventCount  = 0;
let currentPhase = null;

// ── DOM refs ──────────────────────────────────────────────────
const $run       = document.getElementById('btn-run');
const $runIcon   = document.getElementById('run-icon');
const $runLabel  = document.getElementById('run-label');
const $statusDot = document.getElementById('status-dot');
const $statusLbl = document.getElementById('status-label');

// Goal
const $goalDesc  = document.getElementById('goal-description');
const $goalPred  = document.getElementById('goal-predicate');
const $verdBadge = document.getElementById('verdict-badge');

// Limits + Utilities
const $limitsList  = document.getElementById('limits-list');
const $fRegistry   = document.getElementById('f-registry');
const $fCompatible = document.getElementById('f-compatible');
const $fPermitted  = document.getElementById('f-permitted');
const $utilCards   = document.getElementById('utility-cards');

// Pipeline stage counts
const $psc = {
  resolve:   document.getElementById('psc-resolve'),
  filter:    document.getElementById('psc-filter'),
  authorize: document.getElementById('psc-authorize'),
  execute:   document.getElementById('psc-execute'),
  verify:    document.getElementById('psc-verify'),
};

// Pipeline stage wrappers
const $ps = {
  resolve:   document.getElementById('ps-resolve'),
  filter:    document.getElementById('ps-filter'),
  authorize: document.getElementById('ps-authorize'),
  execute:   document.getElementById('ps-execute'),
  verify:    document.getElementById('ps-verify'),
};

// Decision + Evidence
const $decPaths = document.getElementById('decision-paths');
const $evEntries = document.getElementById('evidence-entries');

// Result
const $resultBlock   = document.getElementById('zone-result');
const $resultLabel   = document.getElementById('result-label');
const $resultPred    = document.getElementById('result-predicate');
const $resultVerdict = document.getElementById('result-verdict');

// Contract drawer
const $contractDrawer = document.getElementById('contract-drawer');
const $contractPre    = document.getElementById('contract-pre');
const $btnView        = document.getElementById('btn-view-contract');
const $btnCloseContr  = document.getElementById('btn-close-contract');

// Events drawer
const $eventsToggle = document.getElementById('events-toggle');
const $eventsBody   = document.getElementById('events-body');
const $eventsLog    = document.getElementById('events-log');
const $eventsBadge  = document.getElementById('events-badge');
const $toggleCaret  = document.getElementById('toggle-caret');

// ── Bootstrap ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Preload the demo contract
  $contractPre.textContent = DEMO_CONTRACT;

  pingAgent();

  $run.addEventListener('click', onRunClick);

  $btnView.addEventListener('click', () => {
    const hidden = $contractDrawer.hidden;
    $contractDrawer.hidden = !hidden;
    $btnView.textContent = hidden ? 'Hide contract' : 'View contract';
  });

  $btnCloseContr.addEventListener('click', () => {
    $contractDrawer.hidden = true;
    $btnView.textContent = 'View contract';
  });

  $eventsToggle.addEventListener('click', toggleEvents);

  // cmd/ctrl+enter to run
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && !$run.disabled) {
      e.preventDefault();
      onRunClick();
    }
  });
});

// ── Agent health ──────────────────────────────────────────────
async function pingAgent() {
  try {
    const res = await fetch(AGENT_URL.replace('/agent', '/health'),
      { signal: AbortSignal.timeout(3000) });
    const data = res.ok ? await res.json() : null;
    setStatus('online', data ? `Ready · registry ${data.registry ?? '?'}` : 'Ready');
  } catch {
    setStatus('offline', 'Agent offline');
  }
}

function setStatus(state, label) {
  $statusDot.className = `status-dot ${state}`;
  $statusLbl.textContent = label;
}

// ── Run lifecycle ─────────────────────────────────────────────
async function onRunClick() {
  if (isRunning) {
    abortCtrl?.abort();
    return;
  }

  startRun();

  const threadId = crypto.randomUUID();
  const runId    = crypto.randomUUID();
  abortCtrl = new AbortController();

  try {
    const res = await fetch(AGENT_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({
        threadId, runId,
        messages: [{ role: 'user', content: DEMO_CONTRACT }],
        context: [], tools: [], state: null,
      }),
      signal: abortCtrl.signal,
    });

    if (!res.ok) {
      logRuntimeError(`HTTP ${res.status}: ${await res.text()}`);
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
          catch { /* malformed frame — skip */ }
        }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      logRuntimeError(
        `Cannot reach agent at ${AGENT_URL}\n\n` +
        `Start it with:\n  cd .agents/agents/glu-agent\n  .venv/bin/uvicorn agent:app --reload --port 8080`
      );
    }
  } finally {
    endRun();
  }
}

function startRun() {
  isRunning = true;
  eventCount = 0;
  currentPhase = null;

  // Reset UI to initial state
  $run.classList.add('stop');
  $runIcon.textContent = '◼';
  $runLabel.textContent = 'Stop';
  $run.disabled = false;

  setStatus('running', 'Running…');

  // Reset zones
  resetGoalBadge();
  resetPipeline();
  $decPaths.innerHTML  = '<div class="decision-empty">Awaiting authorization evaluation…</div>';
  $evEntries.innerHTML = '<div class="evidence-empty">Awaiting verification…</div>';
  $resultBlock.hidden = true;
  $resultBlock.className = 'zone zone-result';
  $eventsLog.innerHTML = '';
  $eventsBadge.textContent = '0';
}

function endRun() {
  isRunning = false;
  $run.classList.remove('stop');
  $runIcon.textContent = '▶';
  $runLabel.textContent = 'Run contract';
  pingAgent();
}

// ── Event dispatcher ──────────────────────────────────────────
function handleEvent(event) {
  const { type } = event;

  // Count every event for the drawer badge
  eventCount++;
  $eventsBadge.textContent = eventCount;

  switch (type) {

    case 'RUN_STARTED':
      logEvent('RUN_STARTED', `thread=${short(event.threadId)}  run=${short(event.runId)}`);
      break;

    // Suppress — protocol noise
    case 'TEXT_MESSAGE_START':
    case 'TEXT_MESSAGE_END':
      break;

    case 'TEXT_MESSAGE_CHUNK': {
      const text = (event.delta || '').replace(/\n$/, '');
      if (!text.trim()) break;
      for (const line of text.split('\n')) {
        if (!line.trim()) continue;
        const cls = line.startsWith('✅') ? 'ok'
          : (line.startsWith('⚠') || line.startsWith('🎯'))  ? 'warn'
          : line.startsWith('❌') ? 'err'
          : '';
        logEvent('', line, 'chunk ' + cls);
      }
      break;
    }

    case 'STATE_SNAPSHOT':
      applyState(event.snapshot || {});
      logEvent('STATE_SNAPSHOT', `phase=${event.snapshot?.phase}  goals=${event.snapshot?.goals?.length}  utilities=${event.snapshot?.utilities?.length}`);
      break;

    case 'STATE_DELTA': {
      const ops = event.delta || [];
      // Apply partial updates
      const phaseOp = ops.find(o => o.path === '/phase');
      if (phaseOp?.value) applyPhase(phaseOp.value);

      const cpOps = ops.filter(o => o.path?.startsWith('/context_projection'));
      if (cpOps.length) {
        // Partial projection update
        for (const op of cpOps) {
          if (op.path === '/context_projection/goal_compatible') {
            $fCompatible.textContent = op.value ?? '—';
          } else if (op.path === '/context_projection/limit_permitted') {
            $fPermitted.textContent = op.value ?? '—';
          }
        }
      }

      const dpOp = ops.find(o => o.path === '/decision_paths');
      if (dpOp?.value) renderDecisionPaths(dpOp.value);

      const obsOp = ops.find(o => o.path === '/observations');
      if (obsOp?.value) {
        $psc.execute.textContent = obsOp.value.length;
      }

      const planOp = ops.find(o => o.path === '/plan');
      if (planOp?.value) {
        // count authorized/pending
        const authorized = (planOp.value || []).length;
        $psc.authorize.textContent = authorized;
      }

      const summary = ops.map(o => {
        const field = (o.path || '').replace(/^\//, '');
        const val = Array.isArray(o.value)
          ? `[${o.value.length} item(s)]`
          : (typeof o.value === 'object' && o.value !== null)
            ? '[object]'
            : String(o.value);
        return `${field} → ${val}`;
      }).join('  ·  ');

      logEvent('STATE_DELTA', summary || `${ops.length} op(s)`);
      break;
    }

    case 'RUN_FINISHED':
      logEvent('RUN_FINISHED', event.warning ? `⚠ ${event.warning}` : '✓ success');
      break;

    case 'RUN_ERROR':
      logRuntimeError(`${event.code || 'ERROR'}: ${event.message}`);
      applyPhase('error');
      break;

    default:
      logEvent(type, JSON.stringify(event).slice(0, 120));
  }
}

// ── Full state apply (from STATE_SNAPSHOT) ────────────────────
function applyState(s) {
  // Goal
  if (s.goals?.length) {
    const g = s.goals[0];
    $goalDesc.textContent = g.description || 'List all services and verify they are reachable';
    $goalPred.textContent = g.expression  || 'services.listed == true';
  }

  // Limits
  if (s.limits?.length) renderLimits(s.limits);

  // Utilities + context projection
  if (s.utilities?.length) renderUtilities(s.utilities);

  if (s.context_projection) {
    const cp = s.context_projection;
    if (cp.registry_total  != null) $fRegistry.textContent   = cp.registry_total;
    if (cp.goal_compatible != null) $fCompatible.textContent = cp.goal_compatible;
    if (cp.limit_permitted != null) $fPermitted.textContent  = cp.limit_permitted;
  }

  // Decision paths
  if (s.decision_paths?.length) renderDecisionPaths(s.decision_paths);

  // Evidence
  if (s.evidence?.length) renderEvidence(s.evidence);

  // Phase (do this last so pipeline reflects full state)
  if (s.phase) applyPhase(s.phase);

  // Pipeline counts from state
  if (s.context_projection?.registry_total != null) {
    $psc.resolve.textContent = s.context_projection.registry_total;
  }
  if (s.context_projection?.goal_compatible != null) {
    $psc.filter.textContent = s.context_projection.goal_compatible;
  }
  if (s.context_projection?.limit_permitted != null) {
    $psc.authorize.textContent = s.context_projection.limit_permitted;
  }
  if (s.plan?.length != null) {
    $psc.execute.textContent = s.observations?.length ?? 0;
  }
  if (s.evidence?.length != null) {
    $psc.verify.textContent = s.evidence.length;
  }
}

// ── Phase → pipeline ──────────────────────────────────────────
function applyPhase(phase) {
  if (phase === currentPhase) return;
  currentPhase = phase;

  const STAGE_NAMES = ['resolve', 'filter', 'authorize', 'execute', 'verify'];

  // Find the currently active stage index for this phase
  let activeIdx = -1;
  for (const [stage, phases] of Object.entries(STAGE_PHASES)) {
    if (phases.includes(phase)) {
      activeIdx = STAGE_NAMES.indexOf(stage);
      break;
    }
  }

  const isTerminal = TERMINAL_PHASES.has(phase);
  const isError = phase === 'error';

  STAGE_NAMES.forEach((stage, idx) => {
    const el = $ps[stage];
    el.className = 'p-stage';

    if (isTerminal || isError) {
      // All stages done (proven/unresolved/error)
      el.classList.add(isError ? 'error' : 'done');
    } else if (idx < activeIdx) {
      el.classList.add('done');
    } else if (idx === activeIdx) {
      el.classList.add('active');
    } else {
      el.classList.add('pending');
    }
  });

  // Goal verdict badge
  if (phase === 'proven') {
    $verdBadge.className = 'verdict-badge satisfied';
    $verdBadge.textContent = 'SATISFIED';
    showResult('proven');
  } else if (phase === 'unresolved') {
    $verdBadge.className = 'verdict-badge unresolved';
    $verdBadge.textContent = 'UNRESOLVED';
    showResult('unresolved');
  }
}

// ── Result block ───────────────────────────────────────────────
function showResult(verdict) {
  $resultBlock.hidden = false;
  $resultBlock.className = `zone zone-result ${verdict}`;

  if (verdict === 'proven') {
    $resultLabel.textContent   = 'GOAL SATISFIED';
    $resultPred.textContent    = $goalPred.textContent;
    $resultVerdict.textContent = 'PROVEN';
  } else {
    $resultLabel.textContent   = 'GOAL UNRESOLVED';
    $resultPred.textContent    = $goalPred.textContent;
    $resultVerdict.textContent = 'UNRESOLVED';
  }

  $resultBlock.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Limits render ─────────────────────────────────────────────
function renderLimits(limits) {
  $limitsList.innerHTML = limits.map(l => {
    const pattern = l.pattern || '';
    const isDeny  = pattern.startsWith('deny');
    const verb    = isDeny ? 'deny' : 'allow';
    const rest    = pattern.replace(/^(deny|allow)\s*/, '');
    const annot   = l.description || (isDeny ? 'all actions denied by default' : '');
    return `<div class="limit-row ${isDeny ? 'deny' : 'allow'}">
      <span class="limit-verb">${verb}</span>
      <span class="limit-pattern">${esc(rest || '*')}</span>
      <span class="limit-annotation">${esc(annot)}</span>
    </div>`;
  }).join('');
}

// ── Utilities render ──────────────────────────────────────────
function renderUtilities(utilities) {
  $utilCards.innerHTML = utilities.map(u => {
    const isMutation = (u.type || '').includes('mutation');
    const transport  = u.transport
      ? `${u.transport.method} ${u.transport.path}`
      : '';
    return `<div class="utility-card" id="uc-${css(u.id)}">
      <div class="uc-name">${esc(u.id)}</div>
      <div class="uc-meta-row">
        <span class="uc-badge ${isMutation ? 'mutation' : 'read'}">${isMutation ? 'MUTATION' : 'READ'}</span>
        <span class="uc-meta">${esc(u.sideEffects || 'no side effects')}</span>
      </div>
      ${transport ? `<div class="uc-binding">OpenAPI · ${esc(transport)}</div>` : ''}
    </div>`;
  }).join('');
}

// ── Decision paths render ─────────────────────────────────────
function renderDecisionPaths(paths) {
  if (!paths?.length) return;

  $decPaths.innerHTML = paths.map(d => {
    const isAuth = d.decision === 'authorized';
    const glyph  = isAuth ? '✅' : '✕';
    const verdict = isAuth ? 'AUTHORIZED' : 'DENIED';
    const effect  = d.sideEffects
      ? (d.sideEffects === 'none' ? 'read · no side effects' : d.sideEffects.replace(/-/g, ' '))
      : d.type || '';

    return `<div class="dp-row ${d.decision}">
      <span class="dp-glyph">${glyph}</span>
      <div class="dp-content">
        <div class="dp-id">${esc(d.utilityId)}</div>
        <div class="dp-attrs">
          <span class="dp-attr">${esc(effect)}</span>
        </div>
        <div class="dp-reason">${esc(d.reason || '')}</div>
      </div>
      <span class="dp-verdict">${verdict}</span>
    </div>`;
  }).join('');
}

// ── Evidence render ───────────────────────────────────────────
function renderEvidence(items) {
  if (!items?.length) return;

  $evEntries.innerHTML = items.map(ev => {
    const pass = ev.passed;
    const glyph = pass ? '✅' : '❌';
    const detail = ev.httpStatus != null
      ? `HTTP ${ev.httpStatus}`
      : (pass ? 'passed' : 'failed');

    return `<div class="ev-row ${pass ? 'pass' : 'fail'}">
      <span class="ev-glyph">${glyph}</span>
      <div class="ev-content">
        <div class="ev-req">${esc(ev.requirementId)}</div>
        <div class="ev-assert">${esc(ev.assertion)}</div>
        <div class="ev-detail">${esc(detail)}</div>
      </div>
    </div>`;
  }).join('');

  // Update verify stage count
  $psc.verify.textContent = items.length;
}

// ── Events drawer ─────────────────────────────────────────────
function toggleEvents() {
  const isOpen = !$eventsBody.hidden;
  $eventsBody.hidden = isOpen;
  $eventsToggle.setAttribute('aria-expanded', String(!isOpen));
  $toggleCaret.className = `toggle-caret${isOpen ? '' : ' open'}`;
}

function logEvent(type, body, extraClass = '') {
  const ts  = now();
  const row = document.createElement('div');
  row.className = `ev-log-row${extraClass ? ' ' + extraClass : ''}`;
  row.innerHTML = `<span class="ev-log-ts">${ts}</span>`
    + `<span class="ev-log-type">${esc(type)}</span>`
    + `<span class="ev-log-body">${esc(body)}</span>`;
  $eventsLog.appendChild(row);
  $eventsLog.scrollTop = $eventsLog.scrollHeight;
}

function logRuntimeError(msg) {
  logEvent('ERROR', msg, 'err');
  // Also open the drawer so it's visible
  if ($eventsBody.hidden) toggleEvents();
}

// ── Resets ────────────────────────────────────────────────────
function resetGoalBadge() {
  $verdBadge.className = 'verdict-badge unsatisfied';
  $verdBadge.textContent = 'UNSATISFIED';
}

function resetPipeline() {
  Object.values($ps).forEach(el => {
    el.className = 'p-stage pending';
  });
  Object.values($psc).forEach(el => {
    el.textContent = '—';
  });
}

// ── Utilities ─────────────────────────────────────────────────
function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function css(s) {
  return String(s).replace(/[^a-zA-Z0-9-]/g, '-');
}

function short(uuid) {
  return uuid ? `${uuid.slice(0, 8)}…` : '?';
}

function now() {
  return new Date().toLocaleTimeString('en-US', {
    hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}
