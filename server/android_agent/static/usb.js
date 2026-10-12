export function createUsbSetup({ api, guarded, t, message, onMode }) {
  const $ = id => document.getElementById(id);
  let busy = false, latest = null;
  function render() {
    const usb = latest?.usb;
    $('configure-usb').disabled = busy || !['adb', null, undefined].includes(latest?.mode);
    $('enable-usb').disabled = busy || usb?.listening || !usb?.paired_board;
    $('disable-usb').disabled = busy || !usb?.listening;
    $('use-usb').disabled = busy || !usb?.board?.connected;
    $('usb-listener-status').textContent = !usb ? t('usbListenerOff') : usb.error ? usb.error
      : !usb.listening ? t('usbListenerOff')
      : `${t('usbListening')} TCP ${usb.port} · ${usb.paired_board || ''} · ${usb.board?.connected ? t('usbAuthenticated') : t('usbWaiting')}`;
  }
  $('usb-form').addEventListener('submit', event => {
    event.preventDefault();
    guarded(async () => {
      if (busy) return;
      busy = true; render();
      try {
        await api('/api/usb/configure', { port:$('board-port').value, ssid:$('usb-ssid').value,
          password:$('usb-password').value, host:$('usb-host').value.trim() });
        $('usb-password').value = ''; $('confirm-board-phone').checked = false;
        message(t('usbConfigured'), true);
        latest = await api('/api/status');
      } finally { busy = false; render(); }
    });
  });
  for (const [id, enabled] of [['enable-usb', true], ['disable-usb', false]]) {
    $(id).addEventListener('click', () => guarded(async () => {
      if (busy) return;
      busy = true; render();
      try { await api('/api/usb/listener', { enabled }); latest = await api('/api/status'); }
      finally { busy = false; render(); }
    }));
  }
  $('use-usb').addEventListener('click', () => guarded(async () => {
    if (!$('confirm-board-phone').checked) throw new Error(t('boardConfirmNeeded'));
    await api('/api/control/mode', { mode:'usb', confirm_phone:true });
    await onMode(); message(t('modeSelected'), true);
  }));
  return { status(value) { latest = value; render(); }, translated:render };
}
