import os
import re

files = ["parts.html", "index.html", "orders.html", "customers.html", "loans.html"]
os.chdir(r"C:\Users\47940\OneDrive - OsloMet\Skrivebord\mineProsjekter\Guleed spareparts\frontend")

base_nav = """    <nav class="sidebar-nav">
      <div class="nav-section-label">Inventory</div>
      <a href="parts.html" class="nav-item{P}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="7" height="9"/><rect x="15" y="3" width="7" height="5"/><rect x="15" y="12" width="7" height="9"/><rect x="2" y="16" width="7" height="5"/></svg>
        Parts
      </a>
      <a href="orders.html" class="nav-item{O}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        Orders
      </a>
      <a href="customers.html" class="nav-item{C}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        Customers
      </a>
      <a href="loans.html" class="nav-item{L}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/></svg>
        Loans
      </a>
      <div class="nav-section-label" style="margin-top:8px;">Analytics</div>
      <a href="index.html" class="nav-item{D}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        Dashboard
      </a>
    </nav>"""

for file in files:
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()

    # Determine active classes
    P = " active" if file == "parts.html" else ""
    O = " active" if file == "orders.html" else ""
    C = " active" if file == "customers.html" else ""
    L = " active" if file == "loans.html" else ""
    D = " active" if file == "index.html" else ""

    nav = base_nav.format(P=P, O=O, C=C, L=L, D=D)
    
    # Replace the old nav block using regex
    content = re.sub(r'    <nav class="sidebar-nav">.*?</nav>', nav, content, flags=re.DOTALL)
    
    with open(file, "w", encoding="utf-8") as f:
        f.write(content)
        
print("Nav sections updated")
