import re

file_path = "orders.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix Status Filters
content = content.replace(
    '''<select id="status-filter" class="select-field">
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>''',
    '''<select id="status-filter" class="select-field">
          <option value="">All statuses</option>
          <option value="Ny">Ny</option>
          <option value="Behandles">Behandles</option>
          <option value="Levert">Levert</option>
          <option value="Avbrutt">Avbrutt</option>
        </select>'''
)

# Fix Form
old_form = '''<div class="form-grid">
          <div class="form-group">
            <label class="form-label" for="f-customer">Customer ID *</label>
            <input id="f-customer" type="number" class="form-input" required placeholder="1">
          </div>
          <div class="form-group">
            <label class="form-label" for="f-part">Part ID *</label>
            <input id="f-part" type="number" class="form-input" required placeholder="1">
          </div>
          <div class="form-group">
            <label class="form-label" for="f-quantity">Quantity *</label>
            <input id="f-quantity" type="number" class="form-input" required min="1" value="1">
          </div>
          <div class="form-group">
            <label class="form-label" for="f-status">Status</label>
            <select id="f-status" class="form-select">
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
          <div class="form-group span2">
            <label class="form-label" for="f-notes">Notes</label>
            <textarea id="f-notes" class="form-textarea" placeholder="Optional notes…"></textarea>
          </div>
        </div>'''

new_form = '''<div class="form-grid">
          <div class="form-group">
            <label class="form-label" for="f-customer">Customer *</label>
            <select id="f-customer" class="form-select" required><option value="">Select customer...</option></select>
          </div>
          <div class="form-group">
            <label class="form-label" for="f-part">Part *</label>
            <select id="f-part" class="form-select" required><option value="">Select part...</option></select>
          </div>
          <div class="form-group">
            <label class="form-label" for="f-quantity">Quantity *</label>
            <input id="f-quantity" type="number" class="form-input" required min="1" value="1">
          </div>
          <div class="form-group">
            <label class="form-label" for="f-price">Unit Price at Order (NOK) *</label>
            <input id="f-price" type="number" step="0.01" class="form-input" required min="0">
          </div>
          <div class="form-group">
            <label class="form-label" for="f-status">Status</label>
            <select id="f-status" class="form-select">
              <option value="Ny">Ny</option>
              <option value="Behandles">Behandles</option>
              <option value="Levert">Levert</option>
              <option value="Avbrutt">Avbrutt</option>
            </select>
          </div>
          <div class="form-group span2">
            <label class="form-label" for="f-notes">Notes</label>
            <textarea id="f-notes" class="form-textarea" placeholder="Optional notes…"></textarea>
          </div>
        </div>'''
content = content.replace(old_form, new_form)

# Fix Javascript logic
js_replacements = [
    (
        "function statusBadge(s) {\n  const map = { pending: 'low', completed: 'ok', cancelled: 'empty' };",
        "function statusBadge(s) {\n  const map = { 'Ny': 'low', 'Behandles': 'warn', 'Levert': 'ok', 'Avbrutt': 'empty' };"
    ),
    (
        "document.getElementById('stat-pending').textContent = orders.filter(o => o.status === 'pending').length;",
        "document.getElementById('stat-pending').textContent = orders.filter(o => o.status === 'Ny' || o.status === 'Behandles').length;"
    ),
    (
        "document.getElementById('stat-completed').textContent = orders.filter(o => o.status === 'completed').length;",
        "document.getElementById('stat-completed').textContent = orders.filter(o => o.status === 'Levert').length;"
    ),
    (
        "document.getElementById('stat-cancelled').textContent = orders.filter(o => o.status === 'cancelled').length;",
        "document.getElementById('stat-cancelled').textContent = orders.filter(o => o.status === 'Avbrutt').length;"
    ),
    (
        "<td style=\"color:var(--text-secondary);font-size:12px;\">${o.customer_id}</td>",
        "<td><div style=\"font-weight:500;color:var(--text-primary);\">${o.customer_name || 'Ukjent'}</div><div style=\"font-size:11px;color:var(--text-muted);\">ID: ${o.customer_id}</div></td>"
    ),
    (
        "<td style=\"color:var(--text-secondary);font-size:12px;\">${o.part_id}</td>",
        "<td><div style=\"font-weight:500;color:var(--text-primary);\">${o.part_number || 'N/A'}</div><div style=\"font-size:11px;color:var(--text-muted);\">${o.part_name || ''}</div></td>"
    ),
    (
        "document.getElementById('f-customer').value = o.customer_id;\n    document.getElementById('f-part').value = o.part_id;\n    document.getElementById('f-quantity').value = o.quantity;\n    document.getElementById('f-status').value = o.status;",
        "document.getElementById('f-customer').value = o.customer_id;\n    document.getElementById('f-part').value = o.part_id;\n    document.getElementById('f-quantity').value = o.quantity;\n    document.getElementById('f-price').value = o.unit_price_at_order;\n    document.getElementById('f-status').value = o.status;"
    ),
    (
        "customer_id: parseInt(document.getElementById('f-customer').value),\n    part_id: parseInt(document.getElementById('f-part').value),\n    quantity: parseInt(document.getElementById('f-quantity').value),\n    status: document.getElementById('f-status').value,",
        "customer_id: parseInt(document.getElementById('f-customer').value),\n    part_id: parseInt(document.getElementById('f-part').value),\n    quantity: parseInt(document.getElementById('f-quantity').value),\n    unit_price_at_order: parseFloat(document.getElementById('f-price').value),\n    status: document.getElementById('f-status').value,"
    )
]

for old_s, new_s in js_replacements:
    content = content.replace(old_s, new_s)

# Add loadDropdowns logic
load_dropdowns = """
async function loadDropdowns() {
  try {
    const [customers, parts] = await Promise.all([
      api.getCustomers(),
      api.getParts()
    ]);
    const cSel = document.getElementById('f-customer');
    const pSel = document.getElementById('f-part');
    cSel.innerHTML = '<option value="">Select customer…</option>' + customers.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    pSel.innerHTML = '<option value="">Select part…</option>' + parts.map(p => `<option value="${p.id}" data-price="${p.unit_price}">${p.part_number} - ${p.name} (${p.stock_quantity - (p.loaned_quantity||0)} i lager)</option>`).join('');
    
    pSel.addEventListener('change', (e) => {
      const opt = e.target.options[e.target.selectedIndex];
      if (opt && opt.dataset.price) {
        document.getElementById('f-price').value = opt.dataset.price;
      }
    });
  } catch(e) { console.error('Error loading dropdowns', e); }
}
loadDropdowns();
"""

content = content.replace("loadOrders();", "loadOrders();\n" + load_dropdowns)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("orders.html updated")
