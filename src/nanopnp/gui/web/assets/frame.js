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
    else if (e.code === 'Escape') key = 'Escape';
    else if (/^F\d+$/.test(e.code)) key = e.code;
    if (key === null) return null;
    const modifiers = [e.ctrlKey && 'Ctrl', e.altKey && 'Alt', e.shiftKey && 'Shift', e.metaKey && 'Meta'];
    const held = modifiers.filter(Boolean);
    // A key typed into a field is not a shortcut, and Shift only capitalises it: a chord needs Ctrl,
    // Alt or Meta, except an F key, which may stand alone.
    const strong = e.ctrlKey || e.altKey || e.metaKey;
    if (!strong && !/^F\d+$/.test(key) && !(key === 'Escape' && window.frame.capturing)) return null;
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
    e.stopPropagation();
    window.frame.capturing = false;
    emitEvent('chord', { chord });
    return;
  }
  const id = (window.frameChords || {})[chord];
  if (!id) return;
  e.preventDefault();
  emitEvent('command', { id });
}, true);

// The frame's separators: a drawer's edge and the bottom panel's top, moved by pointer or keys.
// Each emits `separator` with its new size at most every 50 ms, and once more with `done` when
// released, which saves the layout. A separator carries role=separator and its limits (frame.py).
window.frameSeparators = {
  STEP: 16,
  THROTTLE_MS: 50,
  install(root) {
    root.querySelectorAll('[role=separator][data-separator]').forEach((handle) => {
      if (handle.dataset.installed) return;
      handle.dataset.installed = '1';
      this.bind(handle);
    });
  },
  bind(handle) {
    const name = handle.dataset.separator;
    const vertical = handle.getAttribute('aria-orientation') === 'vertical';
    const min = Number(handle.getAttribute('aria-valuemin'));
    const max = Number(handle.getAttribute('aria-valuemax'));
    let last = 0;
    let pending = null;
    const clamp = (value) => Math.round(Math.min(max, Math.max(min, value)));
    const current = () => Number(handle.getAttribute('aria-valuenow'));
    const send = (value, done) => {
      handle.setAttribute('aria-valuenow', String(value));
      if (done) {
        clearTimeout(pending);
        pending = null;
        emitEvent('separator', { name, value, done: true });
        return;
      }
      const now = Date.now();
      if (now - last >= this.THROTTLE_MS) {
        last = now;
        emitEvent('separator', { name, value, done: false });
      } else if (pending === null) {
        pending = setTimeout(() => {
          pending = null;
          last = Date.now();
          emitEvent('separator', { name, value: current(), done: false });
        }, this.THROTTLE_MS);
      }
    };
    handle.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      handle.setPointerCapture(e.pointerId);
      const start = vertical ? e.clientX : e.clientY;
      const from = current();
      // The drawer grows rightwards; the panel grows upwards, against the pointer's y.
      const sign = vertical ? 1 : -1;
      const at = (p) => clamp(from + sign * ((vertical ? p.clientX : p.clientY) - start));
      const move = (m) => send(at(m), false);
      const up = (u) => {
        handle.removeEventListener('pointermove', move);
        handle.removeEventListener('pointerup', up);
        handle.releasePointerCapture(u.pointerId);
        send(at(u), true);
      };
      handle.addEventListener('pointermove', move);
      handle.addEventListener('pointerup', up);
    });
    handle.addEventListener('keydown', (e) => {
      const grow = vertical ? 'ArrowRight' : 'ArrowUp';
      const shrink = vertical ? 'ArrowLeft' : 'ArrowDown';
      let next = null;
      if (e.key === grow) next = current() + this.STEP;
      else if (e.key === shrink) next = current() - this.STEP;
      else if (e.key === 'Home') next = min;
      else if (e.key === 'End') next = max;
      if (next === null) return;
      e.preventDefault();
      send(clamp(next), true);
    });
  },
};
new MutationObserver(() => window.frameSeparators.install(document)).observe(
  document.documentElement, { childList: true, subtree: true },
);
