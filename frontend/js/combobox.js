/**
 * combobox.js – a small searchable dropdown.
 *
 * Replaces the browser's native <datalist> popup (which dumps ALL options in
 * a giant list that overflows the screen) with a contained, scrollable menu
 * that opens on click/focus and filters as you type.
 *
 *   attachCombobox(inputEl, () => ['label 1', 'label 2', ...])
 *
 * The provider is called each time the menu opens, so it always reflects the
 * latest data. Choosing an item sets input.value to the label and fires an
 * 'input' event, so existing label→id logic keeps working unchanged.
 */
export function attachCombobox(input, getLabels) {
  input.setAttribute('autocomplete', 'off');
  input.removeAttribute('list');            // stop the native datalist popup

  const menu = document.createElement('div');
  menu.className = 'combo-menu';
  menu.style.display = 'none';
  document.body.appendChild(menu);

  let items = [], active = -1, open = false;

  function position() {
    const r = input.getBoundingClientRect();
    menu.style.left = r.left + 'px';
    menu.style.width = r.width + 'px';
    menu.style.top = (r.bottom + 2) + 'px';
    const below = window.innerHeight - r.bottom - 10;
    menu.style.maxHeight = Math.max(120, Math.min(300, below)) + 'px';
  }
  function render() {
    const q = input.value.trim().toLowerCase();
    const all = getLabels() || [];
    items = (q ? all.filter(l => l.toLowerCase().includes(q)) : all).slice(0, 100);
    if (!items.length) { hide(); return; }
    menu.innerHTML = items.map((l, i) =>
      `<div class="combo-opt${i === active ? ' active' : ''}" data-i="${i}">${l.replace(/</g, '&lt;')}</div>`).join('');
    position();
    menu.style.display = 'block';
    open = true;
  }
  function hide() { menu.style.display = 'none'; open = false; active = -1; }
  function choose(i) {
    if (i < 0 || i >= items.length) return;
    input.value = items[i];
    hide();
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }
  function scrollActive() {
    const el = menu.querySelector('.combo-opt.active');
    if (el) el.scrollIntoView({ block: 'nearest' });
  }

  input.addEventListener('focus', () => { active = -1; render(); });
  input.addEventListener('click', () => { active = -1; render(); });
  input.addEventListener('input', () => { active = -1; render(); });
  input.addEventListener('keydown', (e) => {
    if (!open) { if (e.key === 'ArrowDown') render(); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, items.length - 1); render(); scrollActive(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); render(); scrollActive(); }
    else if (e.key === 'Enter') { if (active >= 0) { e.preventDefault(); choose(active); } }
    else if (e.key === 'Escape') { hide(); }
  });
  // mousedown (not click) so it fires before the input's blur
  menu.addEventListener('mousedown', (e) => {
    const o = e.target.closest('.combo-opt');
    if (o) { e.preventDefault(); choose(parseInt(o.dataset.i, 10)); }
  });
  input.addEventListener('blur', () => setTimeout(hide, 150));
  window.addEventListener('resize', () => { if (open) position(); });

  // Clean up the body-level menu once its input is removed from the DOM
  // (e.g. a cart line is deleted or the modal is reset).
  const obs = new MutationObserver(() => {
    if (!document.contains(input)) { menu.remove(); obs.disconnect(); }
  });
  obs.observe(document.body, { childList: true, subtree: true });
}
