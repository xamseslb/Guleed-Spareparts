/**
 * app.js – Hoved-JavaScript for lagerstyringssiden (index.html).
 */

import { api } from './api.js';

const API_BASE = 'http://localhost:8000';

// ─── Auth-sjekk ────────────────────────────────────────────────────
const token = localStorage.getItem('gs_token');
if (!token) window.location.href = 'login.html';

const user = JSON.parse(localStorage.getItem('gs_user') || '{}');
const fullName = user.full_name || 'Employee';
document.getElementById('sidebar-username').textContent = fullName;
document.getElementById('sidebar-role').textContent = user.role || '';
document.getElementById('user-avatar').textContent = fullName.charAt(0).toUpperCase();
document.getElementById('logout-btn').addEventListener('click', () => {
  localStorage.clear();
  window.location.href = 'login.html';
});

// ─── State ─────────────────────────────────────────────────────────
let allParts = [];
let editingPartId = null;
let carCompatList = [];

// ─── Toast ─────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  // SVG icons for each toast type
  const icons = {
    success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    error:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    info:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
  };
  el.innerHTML = `${icons[type] || ''} ${msg}`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ─── Summary Stats ──────────────────────────────────────────────────
async function loadSummary() {
  try {
    const s = await api.getSummary();
    document.getElementById('stat-total').textContent = s.total_parts ?? '–';
    document.getElementById('stat-low').textContent = s.low_stock ?? '–';
    document.getElementById('stat-empty').textContent = s.out_of_stock ?? '–';
    document.getElementById('stat-loan').textContent = s.total_on_loan ?? '–';
    const val = s.total_stock_value_nok;
    document.getElementById('stat-value').textContent = val
      ? val.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
      : '–';
  } catch { /* ignorer */ }
}

// ─── Badge helpers ──────────────────────────────────────────────────
function stockBadge(part) {
  const statusLabel = part.stock_status;
  const cls = { OK: 'ok', Low: 'low', Empty: 'empty' }[part.stock_status] || 'ok';
  return `<span class="badge badge-${cls}">${part.stock_quantity} pcs (${statusLabel})</span>`;
}

// ─── Render tabell ──────────────────────────────────────────────────
function renderTable(parts) {
  const tbody = document.getElementById('parts-table-body');
  const rc = document.getElementById('record-count');
  if (rc) rc.textContent = `${parts.length} part${parts.length === 1 ? '' : 's'} listed`;
  if (!parts.length) {
    tbody.innerHTML = `
      <tr><td colspan="9">
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
          <h3>No parts found</h3>
          <p>Try adjusting your filters or add a new part.</p>
        </div>
      </td></tr>`;
    return;
  }

  tbody.innerHTML = parts.map(p => `
    <tr style="cursor:pointer;" onclick="openPartAction(${p.id})">
      <td data-label="Part No."><span class="cell-part-number">${p.part_number}</span></td>
      <td data-label="Name">
        <div class="cell-name">${p.name}</div>
        ${p.description ? `<div class="cell-desc">${p.description.substring(0, 60)}${p.description.length > 60 ? '…' : ''}</div>` : ''}
      </td>
      <td data-label="Category"><span class="badge badge-category">${p.category}</span></td>
      <td data-label="Location" style="color:var(--text-secondary);font-size:12px;">${p.location || '–'}</td>
      <td data-label="Stock">${stockBadge(p)}</td>
      <td data-label="Ordered" class="stock-secondary">${p.ordered_quantity}</td>
      <td data-label="On Loan" class="stock-secondary">${p.loaned_quantity}</td>
      <td data-label="Price"><span class="stock-num">$${(p.unit_price).toLocaleString('en-US')}</span></td>
      <td class="card-actions" onclick="event.stopPropagation()">
        <div class="cell-actions">
          <button class="btn-icon" onclick="editPart(${p.id})" title="Edit" aria-label="Edit ${p.name}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="btn-icon danger" onclick="deletePart(${p.id}, '${p.name.replace(/'/g, "\\'") }')" title="Delete" aria-label="Delete ${p.name}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
          </button>
        </div>
      </td>
    </tr>
  `).join('');
}

// ─── Last varer ─────────────────────────────────────────────────────
async function loadParts() {
  const q = document.getElementById('search-input').value;
  const category = document.getElementById('category-filter').value;
  const car_make = document.getElementById('car-make-input').value;
  const car_model = document.getElementById('car-model-input').value;
  const low_stock_only = document.getElementById('low-stock-toggle').checked;

  try {
    allParts = await api.getParts({ q, category, car_make, car_model, low_stock_only }) || [];
    renderTable(allParts);
    populateCategories();
    loadCategoryPanel();
  } catch (err) {
    toast('Error loading parts: ' + err.message, 'error');
  }
}

function populateCategories() {
  const select = document.getElementById('category-filter');
  const current = select.value;
  const categories = [...new Set((categoryCache || allParts).map(p => p.category))].sort();
  select.innerHTML = '<option value="">All categories</option>' +
    categories.map(c => `<option value="${c}" ${c === current ? 'selected' : ''}>${c}</option>`).join('');
  // Autocomplete suggestions for the Add/Edit Part category field:
  // pick an existing category or type a brand-new one.
  const datalist = document.getElementById('category-options');
  if (datalist) datalist.innerHTML = categories.map(c => `<option value="${c}"></option>`).join('');
}

// ─── Category side panel (Fleet-style tree) ─────────────────────────
let categoryCache = null;
async function loadCategoryPanel(forceRefresh) {
  const list = document.getElementById('cat-panel-list');
  if (!list) return;
  if (!categoryCache || forceRefresh) {
    try { categoryCache = await api.getParts({}) || []; } catch { return; }
  }
  const counts = {};
  categoryCache.forEach(p => { counts[p.category] = (counts[p.category] || 0) + 1; });
  const cats = Object.keys(counts).sort();
  const active = document.getElementById('category-filter').value;

  list.innerHTML =
    `<li class="cat-item ${!active ? 'active' : ''}" data-cat="">
       <span>All categories</span><span class="cat-count">${categoryCache.length}</span></li>` +
    cats.map(c => `
      <li class="cat-item ${c === active ? 'active' : ''}" data-cat="${c}">
        <span>${c}</span><span class="cat-count">${counts[c]}</span></li>`).join('');

  list.querySelectorAll('.cat-item').forEach(li => li.addEventListener('click', () => {
    document.getElementById('category-filter').value = li.dataset.cat;
    loadParts();
  }));
}

// ─── Søk (debounce) ─────────────────────────────────────────────────
let searchTimer;
['search-input', 'car-make-input', 'car-model-input'].forEach(id => {
  document.getElementById(id).addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadParts, 280);
  });
});
document.getElementById('category-filter').addEventListener('change', loadParts);
document.getElementById('low-stock-toggle').addEventListener('change', loadParts);

// ─── Modal ──────────────────────────────────────────────────────────
const modal = document.getElementById('part-modal');
function openModal() { modal.classList.add('open'); }
function closeModal() {
  modal.classList.remove('open');
  document.getElementById('part-form').reset();
  document.getElementById('part-id').value = '';
  document.getElementById('modal-title').textContent = 'Add Spare Part';
  carCompatList = [];
  renderCarList();
  document.getElementById('images-section').style.display = 'none';
  editingPartId = null;
}

document.getElementById('add-part-btn').addEventListener('click', openModal);
document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal-cancel').addEventListener('click', closeModal);
modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

// ─── Bilkompatibilitet ───────────────────────────────────────────────
function renderCarList() {
  const container = document.getElementById('car-compat-list');
  container.innerHTML = carCompatList.map((car, i) => `
    <div style="display:flex;gap:8px;align-items:center;">
      <input class="form-input" value="${car.make}" placeholder="Make" style="flex:1;"
        onchange="carCompatList[${i}].make=this.value">
      <input class="form-input" value="${car.model}" placeholder="Model" style="flex:1;"
        onchange="carCompatList[${i}].model=this.value">
      <input class="form-input" type="number" value="${car.year_from || ''}" placeholder="From" style="width:80px;"
        onchange="carCompatList[${i}].year_from=+this.value||null">
      <input class="form-input" type="number" value="${car.year_to || ''}" placeholder="To" style="width:80px;"
        onchange="carCompatList[${i}].year_to=+this.value||null">
      <button type="button" class="btn-icon danger" onclick="removeCar(${i})" style="flex-shrink:0;">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
  `).join('');
}

document.getElementById('add-car-btn').addEventListener('click', () => {
  carCompatList.push({ make: '', model: '', year_from: null, year_to: null });
  renderCarList();
});

window.removeCar = (i) => {
  carCompatList.splice(i, 1);
  renderCarList();
};

// ─── Bildegalleri ───────────────────────────────────────────────────
function renderImageGallery(images) {
  const gallery = document.getElementById('image-gallery');
  const count = document.getElementById('image-count');
  const canAdd = images.length < 10;

  gallery.innerHTML = images.map((src, i) => `
    <div class="image-thumb">
      <img src="${API_BASE}${src}" alt="Part image ${i + 1}" loading="lazy">
      <div class="img-delete" onclick="deleteImage(${i})" title="Remove" role="button" tabindex="0">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="10" height="10"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </div>
    </div>
  `).join('') + (canAdd ? `
    <div class="image-add-btn" onclick="document.getElementById('image-upload').click()" title="Upload image" role="button" tabindex="0">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      <span>Upload</span>
    </div>
  ` : '');

  count.textContent = `${images.length} / 10 images`;
}

window.deleteImage = async (index) => {
  if (!editingPartId) return;
  try {
    const updated = await api.deleteImage(editingPartId, index);
    renderImageGallery(updated.images || []);
    toast('Image deleted', 'success');
  } catch (err) {
    toast(err.message, 'error');
  }
};

document.getElementById('image-upload').addEventListener('change', async (e) => {
  if (!editingPartId || !e.target.files.length) return;
  const file = e.target.files[0];
  try {
    const updated = await api.uploadImage(editingPartId, file);
    renderImageGallery(updated.images || []);
    toast('Image uploaded!', 'success');
  } catch (err) {
    toast(err.message, 'error');
  }
  e.target.value = '';
});

// ─── Rediger vare ───────────────────────────────────────────────────
window.editPart = async (id) => {
  try {
    const p = await api.getPart(id);
    editingPartId = id;
    document.getElementById('part-id').value = id;
    document.getElementById('modal-title').textContent = 'Edit Spare Part';
    document.getElementById('f-part-number').value = p.part_number;
    document.getElementById('f-name').value = p.name;
    document.getElementById('f-description').value = p.description || '';
    document.getElementById('f-category').value = p.category;
    document.getElementById('f-location').value = p.location || '';
    document.getElementById('f-price').value = p.unit_price;
    document.getElementById('f-stock').value = p.stock_quantity;
    document.getElementById('f-ordered').value = p.ordered_quantity;
    document.getElementById('f-loaned').value = p.loaned_quantity;
    document.getElementById('f-threshold').value = p.low_stock_threshold;

    carCompatList = JSON.parse(JSON.stringify(p.compatible_cars || []));
    renderCarList();

    document.getElementById('images-section').style.display = 'block';
    renderImageGallery(p.images || []);

    openModal();
  } catch (err) {
    toast(err.message, 'error');
  }
};

// ─── Slett vare ─────────────────────────────────────────────────────
window.deletePart = async (id, name) => {
  if (!confirm(`Are you sure you want to delete "${name}"?`)) return;
  try {
    await api.deletePart(id);
    toast(`"${name}" deleted`, 'success');
    loadParts();
    loadSummary();
    loadCategoryPanel(true);
  } catch (err) {
    toast(err.message, 'error');
  }
};

// ─── Lagre (opprett/oppdater) ────────────────────────────────────────
document.getElementById('modal-save').addEventListener('click', async () => {
  const id = document.getElementById('part-id').value;
  const payload = {
    part_number: document.getElementById('f-part-number').value.trim(),
    name: document.getElementById('f-name').value.trim(),
    description: document.getElementById('f-description').value.trim() || null,
    category: document.getElementById('f-category').value.trim(),
    location: document.getElementById('f-location').value.trim() || null,
    unit_price: parseFloat(document.getElementById('f-price').value),
    stock_quantity: parseInt(document.getElementById('f-stock').value) || 0,
    ordered_quantity: parseInt(document.getElementById('f-ordered').value) || 0,
    loaned_quantity: parseInt(document.getElementById('f-loaned').value) || 0,
    low_stock_threshold: parseInt(document.getElementById('f-threshold').value) || 5,
    compatible_cars: carCompatList.filter(c => c.make || c.model),
  };

  if (!payload.part_number || !payload.name || !payload.category || isNaN(payload.unit_price)) {
    toast('Please fill in required fields (part number, name, category, price)', 'error');
    return;
  }

  try {
    if (id) {
      await api.updatePart(id, payload);
      toast('Part updated!', 'success');
    } else {
      const created = await api.createPart(payload);
      editingPartId = created.id;
      document.getElementById('part-id').value = created.id;
      document.getElementById('images-section').style.display = 'block';
      renderImageGallery([]);
      toast('Part created! You can now upload images.', 'success');
    }
    loadParts();
    loadSummary();
    loadCategoryPanel(true);
    if (id) closeModal();
  } catch (err) {
    toast(err.message, 'error');
  }
});

// ─── Category combobox: reliable dropdown of existing categories ─────
// Shows existing categories on focus (filtered as you type); you can also
// type a brand-new one. Replaces the unreliable native <datalist>.
function setupCategoryCombo() {
  const input = document.getElementById('f-category');
  const menu = document.getElementById('category-menu');
  if (!input || !menu) return;

  const categories = () =>
    [...new Set((categoryCache || allParts || []).map(p => p.category))].filter(Boolean).sort();

  function render() {
    const q = input.value.trim().toLowerCase();
    const matches = categories().filter(c => c.toLowerCase().includes(q));
    if (!matches.length) { menu.hidden = true; return; }
    menu.innerHTML = matches.map(c => `<div class="combo-option" data-val="${c}">${c}</div>`).join('');
    menu.hidden = false;
  }

  input.addEventListener('focus', render);
  input.addEventListener('input', render);
  // Use mousedown so the choice registers before the input's blur fires
  menu.addEventListener('mousedown', (e) => {
    const opt = e.target.closest('.combo-option');
    if (!opt) return;
    e.preventDefault();
    input.value = opt.dataset.val;
    menu.hidden = true;
  });
  input.addEventListener('blur', () => setTimeout(() => { menu.hidden = true; }, 150));
}

// ─── Excel / CSV import ───────────────────────────────────────────────
const importModal = document.getElementById('import-modal');
function closeImport() { importModal && importModal.classList.remove('open'); }
document.getElementById('import-parts-btn')?.addEventListener('click', () => {
  document.getElementById('import-result').innerHTML = '';
  document.getElementById('import-file').value = '';
  importModal.classList.add('open');
});
document.getElementById('import-close')?.addEventListener('click', closeImport);
document.getElementById('import-cancel')?.addEventListener('click', closeImport);
importModal?.addEventListener('click', e => { if (e.target === importModal) closeImport(); });

document.getElementById('download-template')?.addEventListener('click', async () => {
  // A real .xlsx (built on the server) so Excel keeps the columns separate –
  // a comma CSV collapses into one column on machines that use ';' as the list separator.
  try {
    const blob = await api.importTemplate();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'parts_template.xlsx';
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (err) {
    toast(err.message, 'error');
  }
});

document.getElementById('import-run')?.addEventListener('click', async () => {
  const file = document.getElementById('import-file').files[0];
  if (!file) { toast('Choose a file first', 'error'); return; }
  const btn = document.getElementById('import-run');
  btn.disabled = true; btn.textContent = 'Importing…';
  try {
    const res = await api.importParts(file);
    let html = `<div style="color:var(--green);font-weight:600;">✓ ${res.created} part(s) imported</div>`;
    if (res.skipped_duplicates) html += `<div style="color:var(--text-muted);">${res.skipped_duplicates} skipped (already existed)</div>`;
    if (res.error_count) {
      html += `<div style="color:var(--red);margin-top:4px;">${res.error_count} row(s) had errors:</div>`;
      html += '<ul style="margin:4px 0 0 16px;color:var(--text-secondary);">' +
        res.errors.map(e => `<li>Row ${e.row}: ${e.reason}</li>`).join('') + '</ul>';
    }
    document.getElementById('import-result').innerHTML = html;
    if (res.created) { toast(`${res.created} parts imported`, 'success'); loadParts(); loadCategoryPanel(true); }
  } catch (err) {
    document.getElementById('import-result').innerHTML = `<div style="color:var(--red);">${err.message}</div>`;
    toast(err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Import';
  }
});

// ─── Init ────────────────────────────────────────────────────────────
loadParts();
loadSummary();
loadCategoryPanel(true);
setupCategoryCombo();

// ════════════════════════════════════════════════════════════════════════
// PART ACTION MODAL – opens when a user clicks on a table row
// Lets staff register a purchase (order) or loan for the selected part
// ════════════════════════════════════════════════════════════════════════

const actionModal  = document.getElementById('action-modal');
const stepChoose   = document.getElementById('action-step-choose');
const stepPurchase = document.getElementById('action-step-purchase');
const stepLoan     = document.getElementById('action-step-loan');

let selectedPart = null;  // the part object the user clicked on

// ── Show/hide steps ─────────────────────────────────────────────────
function showStep(step) {
  stepChoose.style.display   = step === 'choose'   ? 'block' : 'none';
  stepPurchase.style.display = step === 'purchase' ? 'block' : 'none';
  stepLoan.style.display     = step === 'loan'     ? 'block' : 'none';
}

// ── Open the action modal for a part ───────────────────────────────
window.openPartAction = async (partId) => {
  const part = allParts.find(p => p.id === partId);
  if (!part) return;
  selectedPart = part;

  const available = part.stock_quantity - part.loaned_quantity;

  // Fill in the header
  document.getElementById('action-part-name').textContent = part.name;
  document.getElementById('action-part-meta').textContent =
    `${part.part_number} · ${part.category} · ${available} pcs available · $${part.unit_price.toLocaleString('en-US')}`;

  // Reset to choose step
  showStep('choose');
  actionModal.classList.add('open');

  // Pre-fill purchase price fields
  document.getElementById('pu-price').value = part.unit_price;
  document.getElementById('pu-quantity').value = 1;
  updatePurchaseTotal();

  // Set default loan date to now
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  document.getElementById('lo-loan-date').value = now.toISOString().slice(0, 16);

  // Load customers and employees into dropdowns (if not already loaded)
  await loadActionDropdowns();
};

// ── Populate customer + employee dropdowns ──────────────────────────
let dropdownsLoaded = false;
async function loadActionDropdowns() {
  if (dropdownsLoaded) return;
  try {
    const [customers, employees] = await Promise.all([
      api.getCustomers(),
      api.getEmployees(),
    ]);

    // Purchase customer dropdown
    const puCust = document.getElementById('pu-customer');
    const loCust = document.getElementById('lo-customer');
    puCust.innerHTML = '<option value="">Select customer…</option>';
    loCust.innerHTML = '<option value="">Select customer…</option>';
    customers.forEach(c => {
      const opt = `<option value="${c.id}">${c.name}${c.phone ? ' – ' + c.phone : ''}</option>`;
      puCust.insertAdjacentHTML('beforeend', opt);
      loCust.insertAdjacentHTML('beforeend', opt);
    });

    // Employee dropdown (loans only)
    const loEmp = document.getElementById('lo-employee');
    loEmp.innerHTML = '<option value="">Select employee…</option>';
    employees.forEach(e => {
      loEmp.insertAdjacentHTML('beforeend',
        `<option value="${e.full_name}">${e.full_name} (${e.role})</option>`);
    });

    dropdownsLoaded = true;
  } catch (err) {
    console.error('Error loading dropdowns:', err);
  }
}

// ── Auto-calculate total for purchase ───────────────────────────────
function updatePurchaseTotal() {
  const price = parseFloat(document.getElementById('pu-price').value) || 0;
  const qty   = parseInt(document.getElementById('pu-quantity').value) || 1;
  document.getElementById('pu-total').value = (price * qty).toFixed(2);
}
document.getElementById('pu-quantity').addEventListener('input', updatePurchaseTotal);

// ── Close modal ──────────────────────────────────────────────────────
function closeActionModal() {
  actionModal.classList.remove('open');
  selectedPart = null;
  document.getElementById('purchase-form').reset();
  document.getElementById('loan-quick-form').reset();
}
document.getElementById('action-close').addEventListener('click', closeActionModal);
document.getElementById('action-close-2').addEventListener('click', closeActionModal);
document.getElementById('action-close-3').addEventListener('click', closeActionModal);
actionModal.addEventListener('click', e => { if (e.target === actionModal) closeActionModal(); });

// ── Back buttons ─────────────────────────────────────────────────────
document.getElementById('back-from-purchase').addEventListener('click', () => showStep('choose'));
document.getElementById('back-from-loan').addEventListener('click',     () => showStep('choose'));

// ── Step 1: choose Purchase or Loan ─────────────────────────────────
document.getElementById('choose-purchase').addEventListener('click', () => {
  if (!selectedPart) return;
  const available = selectedPart.stock_quantity - selectedPart.loaned_quantity;
  if (available <= 0) { toast('No stock available for purchase', 'error'); return; }
  showStep('purchase');
});

document.getElementById('choose-loan').addEventListener('click', () => {
  if (!selectedPart) return;
  const available = selectedPart.stock_quantity - selectedPart.loaned_quantity;
  if (available <= 0) { toast('No stock available to loan out', 'error'); return; }
  showStep('loan');
});

// ── Confirm Purchase → create order ─────────────────────────────────
document.getElementById('save-purchase').addEventListener('click', async () => {
  const customer_id = parseInt(document.getElementById('pu-customer').value);
  const quantity    = parseInt(document.getElementById('pu-quantity').value);
  const notes       = document.getElementById('pu-notes').value.trim();

  if (!customer_id || !quantity) {
    toast('Please select a customer and quantity', 'error'); return;
  }
  const available = selectedPart.stock_quantity - selectedPart.loaned_quantity;
  if (quantity > available) {
    toast(`Only ${available} pcs available`, 'error'); return;
  }

  try {
    await api.createOrder({
      customer_id,
      part_id: selectedPart.id,
      quantity,
      status: 'Delivered',   // a direct purchase is completed immediately
      notes: notes || null,
    });
    toast(`Purchase registered: ${quantity}× ${selectedPart.name}`, 'success');
    closeActionModal();
    loadParts();
    loadSummary();
  } catch (err) {
    toast(err.message, 'error');
  }
});

// ── Confirm Loan → create loan ────────────────────────────────────────
document.getElementById('save-loan').addEventListener('click', async () => {
  const customer_id   = parseInt(document.getElementById('lo-customer').value);
  const quantity      = parseInt(document.getElementById('lo-quantity').value);
  const loan_price    = parseFloat(document.getElementById('lo-price').value) || 0;
  const employee_name = document.getElementById('lo-employee').value;
  const loanDateVal   = document.getElementById('lo-loan-date').value;
  const retDateVal    = document.getElementById('lo-return-date').value;
  const notes         = document.getElementById('lo-notes').value.trim();

  if (!customer_id || !quantity || !employee_name) {
    toast('Please fill in customer, quantity and employee', 'error'); return;
  }
  const available = selectedPart.stock_quantity - selectedPart.loaned_quantity;
  if (quantity > available) {
    toast(`Only ${available} pcs available to loan`, 'error'); return;
  }

  try {
    await api.createLoan({
      customer_id,
      part_id: selectedPart.id,
      quantity,
      loan_price,
      employee_name,
      loan_date: loanDateVal ? new Date(loanDateVal).toISOString() : null,
      expected_return_date: retDateVal ? new Date(retDateVal).toISOString() : null,
      notes: notes || null,
    });
    toast(`Loan registered: ${quantity}× ${selectedPart.name}`, 'success');
    closeActionModal();
    loadParts();
    loadSummary();
  } catch (err) {
    toast(err.message, 'error');
  }
});
