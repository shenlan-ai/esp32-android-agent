export function boardStatusKey(status) {
  const board = status.board;
  if (!board) return 'boardInactive';
  if (!board.connected) return 'boardDisconnected';
  if (!board.hid_ready) {
    if (status.mode === 'usb') return 'usbHostNeeded';
    const state = board.ble_state;
    if (!state?.link) return 'boardPairNeeded';
    if (!state.authenticated) return 'boardAuthNeeded';
    if (!state.keyboard_subscribed || !state.mouse_subscribed) return 'boardReportsNeeded';
    return 'boardNotReady';
  }
  return status.calibrated ? 'boardReady' : 'boardCalibrateNeeded';
}
