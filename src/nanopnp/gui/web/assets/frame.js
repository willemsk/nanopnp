// The frame's key listener: a browser page can stop a chord's default only here, so the shortcuts
// are matched in the page and the command they name runs on the server (commands.py).
window.frame = {
  // The chord the server's table uses: modifiers in the order Ctrl, Alt, Shift, Meta, then the key.
  chordOf(e) {
    let key = null;
    if (/^Key[A-Z]$/.test(e.code)) key = e.code.slice(3);
    else if (/^Digit[0-9]$/.test(e.code)) key = e.code.slice(5);
    else if (e.code === 'Comma') key = ',';
    else if (e.code === 'Tab') key = 'Tab';
    else if (/^F\d+$/.test(e.code)) key = e.code;
    if (key === null) return null;
    const modifiers = [e.ctrlKey && 'Ctrl', e.altKey && 'Alt', e.shiftKey && 'Shift', e.metaKey && 'Meta'];
    const held = modifiers.filter(Boolean);
    // A key typed into a field is not a shortcut: only an F key may stand alone.
    if (held.length === 0 && !/^F\d+$/.test(key)) return null;
    return [...held, key].join('+');
  },
  // While capturing, the next chord goes to the settings instead of running its command.
  capturing: false,
};
document.addEventListener('keydown', (e) => {
  const chord = window.frame.chordOf(e);
  if (chord === null) return;
  if (window.frame.capturing) {
    e.preventDefault();
    window.frame.capturing = false;
    emitEvent('chord', { chord });
    return;
  }
  const id = (window.frameChords || {})[chord];
  if (!id) return;
  e.preventDefault();
  emitEvent('command', { id });
}, true);
