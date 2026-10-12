// User-initiated maintenance only. No model action can start a firmware job.
export function createFirmwareSetup({api, headers, guarded, t, onChange}) {
  const $ = id => document.getElementById(id);
  let latest = null, pending = false, signature = '', consent = '';
  const terminal = new Set(['idle','completed','failed','stopped']);
  const sizes = bytes => `${bytes / 1048576} MiB (${bytes.toLocaleString()} bytes)`;

  function render() {
    const fw = latest?.firmware, job = fw?.job;
    const busy = pending || fw?.busy;
    const blocked = busy || ![null, undefined, 'adb'].includes(latest?.mode)
      || !terminal.has(latest?.agent?.state || 'idle');
    $('fw-identify').disabled = blocked || !fw?.tool_available || !$('board-port').value;
    $('board-port').disabled = Boolean(busy);
    $('refresh-boards').disabled = Boolean(busy);
    $('fw-availability').textContent = !fw?.tool_available ? t('fwToolMissing')
      : !fw.catalog.available ? t('fwCatalogMissing') : t('fwAvailable');
    const nextConsent = `${job?.id || ''}:${job?.confirmation || ''}`;
    if (nextConsent !== consent) { consent = nextConsent; $('fw-confirm').checked = false; }
    const nextSignature = `${job?.id || ''}:${job?.compatible?.join(',') || ''}`;
    if (nextSignature !== signature) {
      signature = nextSignature;
      $('fw-profile').replaceChildren(new Option(t('fwChooseProfile'), ''),
        ...(job?.compatible || []).map(name => new Option(name, name)));
    } else if ($('fw-profile').options.length) $('fw-profile').options[0].text = t('fwChooseProfile');
    if (job?.profile) $('fw-profile').value = job.profile;
    $('fw-profile').disabled = busy || job?.phase !== 'identified';
    $('fw-backup').disabled = blocked || job?.phase !== 'identified' || !$('fw-profile').value;
    $('fw-confirm').disabled = busy || job?.phase !== 'ready' || job.expired;
    $('fw-write').disabled = blocked || job?.phase !== 'ready' || !job.confirmation || !$('fw-confirm').checked;
    $('fw-cancel').hidden = !job?.cancel_allowed;
    $('fw-cancel').disabled = pending;
    const identity = job?.identity;
    $('fw-identity').textContent = identity
      ? `${job.port} · ${identity.chip} · ${identity.flash_bytes ? sizes(identity.flash_bytes) : t('fwUnknownFlash')}\n${t('fwPcbUnknown')} · MAC …${identity.mac_suffix}`
      : t('fwNoIdentity');
    $('fw-status').textContent = job ? `${t('fw_' + job.phase)} · ${job.elapsed_seconds}s${job.expired ? '\n' + t('fwExpired') : ''}` : t('fwIdle');
    $('fw-error').textContent = job?.error ? `${t('fwError')} ${job.error}` : '';
    $('fw-writing-note').hidden = job?.phase !== 'writing';
    $('fw-success').hidden = job?.phase !== 'written';
    const backup = job?.backup;
    $('fw-backup-info').textContent = backup ? `${backup.profile} · ${sizes(backup.flash_bytes)}\nSHA256 ${backup.sha256}` : t('fwNoBackup');
    $('fw-download').hidden = !backup;
    $('fw-download').disabled = pending;
    const history = (fw?.backups || []).filter(entry => entry.id !== job?.id);
    $('fw-history').replaceChildren(...history.map(entry => {
      const item = document.createElement('li'), button = document.createElement('button');
      button.type = 'button'; button.textContent = `${t('fwDownload')} · ${entry.profile} · ${new Date(entry.created_at * 1000).toLocaleString()}`;
      button.addEventListener('click', () => guarded(() => download(entry.id)));
      const hash = document.createElement('small'); hash.textContent = entry.sha256;
      item.append(button, hash); return item;
    }));
  }

  async function download(id) {
    const response = await fetch(`/api/firmware/backups/${id}`, {headers:headers()});
    if (!response.ok) throw new Error((await response.json()).detail || t('fwError'));
    const url = URL.createObjectURL(await response.blob()), link = document.createElement('a');
    link.href = url; link.download = `esp32-backup-${id}.bin`; document.body.append(link);
    link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000);
  }

  async function start(path, body) {
    if (pending) return;
    pending = true; render();
    try { const value = await api(path, body); latest = {...latest, firmware:value}; }
    finally { pending = false; render(); await onChange(); }
  }
  $('fw-identify').addEventListener('click', () => guarded(() => start('/api/firmware/identify', {port:$('board-port').value})));
  $('fw-profile').addEventListener('change', render);
  $('fw-confirm').addEventListener('change', render);
  $('board-port').addEventListener('change', () => { $('fw-confirm').checked = false; render(); });
  $('fw-backup').addEventListener('click', () => guarded(() => start('/api/firmware/backup', {job_id:latest.firmware.job.id, profile:$('fw-profile').value})));
  $('fw-write').addEventListener('click', () => guarded(() => start('/api/firmware/write', {job_id:latest.firmware.job.id, confirmation:latest.firmware.job.confirmation, confirm_overwrite:$('fw-confirm').checked})));
  $('fw-cancel').addEventListener('click', () => guarded(() => start('/api/firmware/cancel', {job_id:latest.firmware.job.id})));
  $('fw-download').addEventListener('click', () => guarded(() => download(latest.firmware.job.id)));
  return {status(value) { latest = value; render(); }, translated:render};
}
