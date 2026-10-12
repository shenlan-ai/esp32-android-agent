// Task views and authenticated fetch SSE. No credentials are placed in URLs.
export function createTaskView({ element: $, translate: t, api, headers, guarded, message }) {
  const running = new Set(['planning','observing','executing','verifying','pausing','stopping']);
  const terminal = new Set(['idle','completed','failed','stopped']);
  let current = null, configured = false, deviceStatus = null, loading = null, streamController = null;
  let signature = '', imageGeneration = 0, testing = false;
  const imageUrls = new Set();

  function controls(status) {
    deviceStatus = status;
    const task = status.agent, maintenance = status.firmware?.busy, active = running.has(task.state), held = active || task.state === 'paused';
    $('task-state').textContent = t(`state_${task.state}`);
    $('run-task').disabled = !status.serial || !configured || !terminal.has(task.state) || !status.capabilities.length;
    $('pause-task').disabled = !['planning','observing','executing','verifying'].includes(task.state);
    $('resume-task').disabled = maintenance || task.state !== 'paused';
    $('clear-task').disabled = !task.id || !terminal.has(task.state);
    $('goal').disabled = held;
    $('test-model').disabled = !configured || active || testing;
    if (testing) $('run-task').disabled = true;
    $('export-task').hidden = !task.id;
    for (const id of ['select-device','use-ble','use-adb','save-calibration','probe-x','probe-y']) {
      if (active || maintenance) $(id).disabled = true;
      else if (['select-device','use-ble','use-adb'].includes(id)) $(id).disabled = false;
    }
    for (const form of ['text-form','key-form']) {
      $(form).querySelectorAll('input,select,button').forEach(el => {
        el.disabled = active || !status.serial || !status.capabilities.includes(form === 'text-form' ? 'type' : 'key');
      });
    }
    document.querySelectorAll('[data-action]').forEach(el => { el.disabled = active || !status.capabilities.includes(el.dataset.action); });
    $('task-usage').textContent = task.id ? `${t('actionsCount')}: ${task.actions}/${task.limits.max_steps} · ${t('activeTime')}: ${Math.round(task.active_seconds)}s/${task.limits.max_seconds}s · Token: ${task.tokens}/${task.limits.max_total_tokens}${task.estimated_calls ? ` · ${t('estimatedUsage')}` : ''}` : '';
  }

  function resetImages() {
    imageGeneration++;
    for (const url of imageUrls) URL.revokeObjectURL(url);
    imageUrls.clear();
  }

  async function preview(step, phase, container, taskId, generation) {
    const response = await fetch(`/api/task/steps/${step.index}/${phase}.jpg`, {headers:headers(),cache:'no-store'});
    if (!response.ok) return;
    const url = URL.createObjectURL(await response.blob());
    if (generation !== imageGeneration || current?.id !== taskId) { URL.revokeObjectURL(url); return; }
    imageUrls.add(url);
    const figure = document.createElement('figure'), image = document.createElement('img'), caption = document.createElement('figcaption');
    image.src = url; image.alt = `${t(phase)} · ${step.index}`; image.className = 'step-image';
    caption.textContent = t(phase);
    figure.append(caption, image); container.append(figure);
  }

  function stepNode(step) {
    const li = document.createElement('li'), title = document.createElement('strong');
    li.value = step.index;
    title.textContent = `${t('action_'+step.action)} · ${t('step_'+step.status)}`;
    li.append(title);
    for (const [label, text] of [['reason',step.reason],['expected',step.expected],['evidence',step.evidence]]) {
      if (!text) continue;
      const p = document.createElement('p'); p.textContent = `${t(label)}: ${text}`; li.append(p);
    }
    if (step.model_seconds !== undefined || step.action_seconds !== undefined) {
      const p = document.createElement('p'); p.textContent = `${t('modelTime')}: ${step.model_seconds ?? '—'}s · ${t('inputTime')}: ${step.action_seconds ?? '—'}s`; li.append(p);
    }
    return li;
  }

  function render(snapshot) {
    current = snapshot;
    if (snapshot.id && (running.has(snapshot.state) || snapshot.state === 'paused' || !$('goal').value)) {
      $('goal').value = snapshot.goal;
    }
    $('task-reason').textContent = snapshot.reason || '';
    $('plan-section').hidden = !snapshot.plan;
    $('plan-text').textContent = snapshot.plan || '';
    const next = JSON.stringify([snapshot.id,snapshot.steps]);
    if (next !== signature) {
      signature = next; resetImages();
      const generation = imageGeneration;
      $('steps').replaceChildren(...(snapshot.steps || []).map(step => {
        const li = stepNode(step), images = document.createElement('div'); images.className = 'step-images'; li.append(images);
        for (const phase of ['before','after']) if (step[phase+'_available']) {
          preview(step, phase, images, snapshot.id, generation).catch(() => {});
        }
        return li;
      }));
    }
    if (deviceStatus) controls({...deviceStatus,agent:snapshot});
  }

  async function refresh() {
    if (loading) return loading;
    loading = api('/api/task').then(render).finally(() => { loading = null; });
    return loading;
  }

  async function download(taskId) {
    const response = await fetch(`/api/history/${taskId}/export.zip`, {headers:headers()});
    if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Export failed'); }
    const url = URL.createObjectURL(await response.blob()), link = document.createElement('a');
    link.href = url; link.download = `task-${taskId}.zip`; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url),1000);
  }

  async function history() {
    const data = await api('/api/history');
    $('history-list').replaceChildren(...data.tasks.map(item => {
      const li = document.createElement('li'), view = document.createElement('button'), exportButton = document.createElement('button');
      view.textContent = `${item.goal} · ${t('state_'+item.state)}`;
      exportButton.textContent = t('exportTask');
      view.addEventListener('click',() => guarded(async () => {
        const snapshot = await api(`/api/history/${item.id}`), title = document.createElement('p'), list = document.createElement('ol');
        title.textContent = `${snapshot.goal} · ${snapshot.reason || t('state_'+snapshot.state)}`;
        list.className = 'steps'; list.append(...(snapshot.steps || []).map(stepNode));
        $('history-detail').replaceChildren(title,list);
      }));
      exportButton.addEventListener('click',() => guarded(() => download(item.id)));
      li.append(view,exportButton); return li;
    }));
    if (!data.tasks.length) $('history-list').textContent = t('historyEmpty');
  }

  async function events() {
    streamController?.abort();
    const controller = new AbortController(); streamController = controller;
    while (!controller.signal.aborted) {
      try {
        const response = await fetch('/api/events',{headers:headers(),signal:controller.signal});
        if (!response.ok || !response.body) throw new Error('Events unavailable');
        const reader = response.body.getReader(), decoder = new TextDecoder(); let buffer = '';
        try {
          while (!controller.signal.aborted) {
            const {value,done} = await reader.read(); if (done) break;
            buffer += decoder.decode(value,{stream:true});
            let end;
            while ((end = buffer.indexOf('\n\n')) >= 0) {
              const event = buffer.slice(0,end); buffer = buffer.slice(end+2);
              if (event.includes('event: changed') || event.includes('event: reset')) guarded(refresh);
            }
            if (buffer.length > 65536) throw new Error('Invalid event stream');
          }
        } finally { reader.releaseLock(); }
      } catch { /* Status polling also restores snapshots when streaming is unavailable. */ }
      if (!controller.signal.aborted) await new Promise(resolve => setTimeout(resolve,2000));
    }
  }

  $('run-task').addEventListener('click',() => guarded(async () => { render(await api('/api/task/start',{goal:$('goal').value})); }));
  $('pause-task').addEventListener('click',() => guarded(async () => { render(await api('/api/task/pause',{})); }));
  $('resume-task').addEventListener('click',() => guarded(async () => { render(await api('/api/task/resume',{})); }));
  $('clear-task').addEventListener('click',() => guarded(async () => { render(await api('/api/task/clear',{})); }));
  $('export-task').addEventListener('click',() => guarded(() => download(current.id)));
  $('refresh-history').addEventListener('click',() => guarded(history));
  $('test-model').addEventListener('click',() => guarded(async () => {
    testing = true;
    $('test-model').disabled = true;
    $('run-task').disabled = true;
    message('');
    try { const result = await api('/api/models/test',{}); message(`${t('modelTestPassed')} · ${result.seconds}s · Token: ${result.tokens}${result.estimated ? ' ('+t('estimatedUsage')+')' : ''}`,true); }
    finally { testing = false; if (deviceStatus) controls(deviceStatus); }
  }));
  return {
    controls, refresh, events,
    settings(prefs) { configured = Boolean(prefs.actor.model?.trim()); if (deviceStatus) controls(deviceStatus); },
    status(status) { controls(status); if (current?.revision !== status.agent.revision) guarded(refresh); },
    translated() { signature=''; if (current) render(current); },
    manualAllowed() { return !deviceStatus?.firmware?.busy && !running.has(deviceStatus?.agent.state); },
  };
}
