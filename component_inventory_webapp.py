from __future__ import annotations

import argparse
import os
import sqlite3
from contextlib import closing
from flask import Flask, jsonify, request, g, render_template_string, abort

APP_HTML = r'''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Component Inventory</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --panel: #ffffff;
      --muted: #667085;
      --border: #d0d5dd;
      --accent: #175cd3;
      --accent-soft: #eff4ff;
      --danger: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: #101828;
    }
    .page {
      display: grid;
      grid-template-rows: 56vh 44vh;
      height: 100vh;
      gap: 12px;
      padding: 12px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      overflow: auto;
      box-shadow: 0 1px 3px rgba(16,24,40,0.08);
    }
    .top-grid {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 14px;
      min-height: 100%;
    }
    h1, h2, h3 { margin: 0 0 10px 0; }
    .toolbar {
      display: flex;
      gap: 8px;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }
    input[type=text], input[type=number], textarea, select {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 12px;
      font: inherit;
      background: #fff;
    }
    textarea { min-height: 92px; resize: vertical; }
    .toolbar input[type=text] { max-width: 360px; }
    button {
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      border-radius: 8px;
      padding: 9px 14px;
      cursor: pointer;
      font: inherit;
    }
    button.secondary {
      background: #fff;
      color: var(--accent);
    }
    button.danger {
      background: #fff;
      color: var(--danger);
      border-color: var(--danger);
    }
    .muted { color: var(--muted); }
    .component-title {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      margin-bottom: 10px;
    }
    .field-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .field { margin-bottom: 10px; }
    .field label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 5px;
      text-transform: uppercase;
      letter-spacing: .03em;
    }
    .span-2 { grid-column: span 2; }
    .box-list {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }
    .box-list th, .box-list td {
      border-bottom: 1px solid var(--border);
      text-align: left;
      padding: 8px;
      font-size: 14px;
      vertical-align: top;
    }
    .list-wrap {
      display: grid;
      grid-template-columns: 290px 1fr;
      gap: 14px;
      min-height: 0;
      height: 100%;
    }
    .component-list {
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: auto;
      background: #fff;
    }
    .component-row {
      padding: 10px 12px;
      border-bottom: 1px solid #eaecf0;
      cursor: pointer;
    }
    .component-row:hover, .component-row.active {
      background: var(--accent-soft);
    }
    .small {
      font-size: 12px;
      color: var(--muted);
      margin-top: 3px;
    }
    .status {
      min-height: 20px;
      font-size: 13px;
      margin-top: 8px;
      color: var(--muted);
    }
    .hidden { display: none; }
    .pill {
      display: inline-block;
      background: #f2f4f7;
      border: 1px solid #e4e7ec;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      margin-right: 6px;
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="panel">
      <div class="top-grid">
        <div>
          <div class="toolbar">
            <input id="search" type="text" placeholder="Search by part number, manufacturer, description">
            <button id="newBtn" class="secondary">New part</button>
            <button id="saveBtn">Save</button>
          </div>
          <div class="component-title">
            <div>
              <h2 id="selectedTitle">No component selected</h2>
              <div id="selectedMeta" class="muted"></div>
            </div>
            <div id="componentIdBadge" class="pill hidden"></div>
          </div>
          <div class="field-grid">
            <div class="field">
              <label for="part_number">Part number</label>
              <input id="part_number" type="text">
            </div>
            <div class="field">
              <label for="manufacturer">Manufacturer</label>
              <input id="manufacturer" type="text">
            </div>
            <div class="field span-2">
              <label for="description">Description</label>
              <textarea id="description"></textarea>
            </div>
            <div class="field span-2">
              <label for="datasheet_url">Datasheet URL</label>
              <input id="datasheet_url" type="text">
            </div>
          </div>
          <div class="status" id="status"></div>
        </div>
        <div>
          <h3>Locations</h3>
          <div class="muted">Each row links a component to a box position.</div>
          <table class="box-list" id="locationsTable">
            <thead>
              <tr><th>Box</th><th>X</th><th>Y</th><th>Qty</th><th></th></tr>
            </thead>
            <tbody></tbody>
          </table>
          <h3 style="margin-top:14px;">Add location</h3>
          <div class="field-grid">
            <div class="field">
              <label for="box_id">Box</label>
              <select id="box_id"></select>
            </div>
            <div class="field">
              <label for="quantity">Quantity</label>
              <input id="quantity" type="text" placeholder="Optional">
            </div>
            <div class="field">
              <label for="pos_x">X</label>
              <input id="pos_x" type="number" min="1">
            </div>
            <div class="field">
              <label for="pos_y">Y</label>
              <input id="pos_y" type="number" min="1">
            </div>
          </div>
          <button id="addLocationBtn" class="secondary">Add location</button>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="list-wrap">
        <div>
          <h3>Components</h3>
          <div class="muted">Ordered by part number</div>
          <div id="componentList" class="component-list"></div>
        </div>
        <div>
          <h3>Selected component details</h3>
          <div id="detailPane" class="muted">Select a component from the list or click <b>New part</b>.</div>
        </div>
      </div>
    </div>
  </div>

<script>
let components = [];
let boxes = [];
let selectedId = null;
let newMode = false;

function setStatus(msg, isError=false) {
  const el = document.getElementById('status');
  el.textContent = msg || '';
  el.style.color = isError ? '#b42318' : '#667085';
}

function escapeHtml(value) {
  return (value ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

async function fetchJson(url, options={}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return await res.json();
}

async function loadBoxes() {
  boxes = await fetchJson('/api/boxes');
  const sel = document.getElementById('box_id');
  sel.innerHTML = boxes.map(b => `<option value="${b.id}">${escapeHtml(b.box_name)} (${b.width}x${b.height})</option>`).join('');
}

async function loadComponents(search='') {
  components = await fetchJson('/api/components?search=' + encodeURIComponent(search));
  renderComponentList();
  if (!newMode) {
    if (selectedId && components.some(c => c.id === selectedId)) {
      selectComponent(selectedId);
    } else if (components.length) {
      selectComponent(components[0].id);
    } else {
      clearForm();
      renderDetailPane(null);
    }
  }
}

function renderComponentList() {
  const list = document.getElementById('componentList');
  list.innerHTML = components.map(c => `
    <div class="component-row ${c.id === selectedId ? 'active' : ''}" data-id="${c.id}">
      <div><b>${escapeHtml(c.part_number || '(no part number)')}</b></div>
      <div class="small">${escapeHtml(c.manufacturer || '')}</div>
      <div class="small">${escapeHtml(c.description || '').slice(0, 100)}</div>
    </div>`).join('');

  for (const row of list.querySelectorAll('.component-row')) {
    row.addEventListener('click', () => selectComponent(Number(row.dataset.id)));
  }
}

function clearForm() {
  document.getElementById('part_number').value = '';
  document.getElementById('manufacturer').value = '';
  document.getElementById('description').value = '';
  document.getElementById('datasheet_url').value = '';
  document.getElementById('selectedTitle').textContent = 'New component';
  document.getElementById('selectedMeta').textContent = 'Create a new part, then save it.';
  const badge = document.getElementById('componentIdBadge');
  badge.classList.add('hidden');
  badge.textContent = '';
  document.querySelector('#locationsTable tbody').innerHTML = '';
}

async function selectComponent(id) {
  newMode = false;
  selectedId = id;
  renderComponentList();
  const c = await fetchJson('/api/components/' + id);
  document.getElementById('part_number').value = c.part_number || '';
  document.getElementById('manufacturer').value = c.manufacturer || '';
  document.getElementById('description').value = c.description || '';
  document.getElementById('datasheet_url').value = c.datasheet_url || '';
  document.getElementById('selectedTitle').textContent = c.part_number || '(no part number)';
  document.getElementById('selectedMeta').textContent = c.manufacturer || '';
  const badge = document.getElementById('componentIdBadge');
  badge.textContent = 'ID ' + c.id;
  badge.classList.remove('hidden');
  renderLocations(c.placements || []);
  renderDetailPane(c);
  setStatus('');
}

function renderLocations(placements) {
  const tbody = document.querySelector('#locationsTable tbody');
  tbody.innerHTML = placements.map(p => `
    <tr>
      <td>${escapeHtml(p.box_name)}</td>
      <td>${escapeHtml(p.x)}</td>
      <td>${escapeHtml(p.y)}</td>
      <td>${escapeHtml(p.quantity || '')}</td>
      <td><button class="danger" data-placement-id="${p.placement_id}">Remove</button></td>
    </tr>
  `).join('');
  for (const btn of tbody.querySelectorAll('button[data-placement-id]')) {
    btn.addEventListener('click', async () => {
      try {
        await fetchJson('/api/placements/' + btn.dataset.placementId, { method: 'DELETE' });
        await selectComponent(selectedId);
        setStatus('Location removed.');
      } catch (err) {
        setStatus(err.message, true);
      }
    });
  }
}

function renderDetailPane(c) {
  const pane = document.getElementById('detailPane');
  if (!c) {
    pane.innerHTML = '<div class="muted">No components match the current search.</div>';
    return;
  }
  const locations = (c.placements || []).length
    ? c.placements.map(p => `<tr><td>${escapeHtml(p.box_name)}</td><td>${escapeHtml(p.x)}</td><td>${escapeHtml(p.y)}</td><td>${escapeHtml(p.quantity || '')}</td></tr>`).join('')
    : '<tr><td colspan="4" class="muted">No locations assigned.</td></tr>';
  const ds = c.datasheet_url ? `<a href="${escapeHtml(c.datasheet_url)}" target="_blank" rel="noopener">Open datasheet</a>` : '<span class="muted">No datasheet</span>';
  pane.innerHTML = `
    <div class="field-grid">
      <div class="field"><label>Part number</label><div>${escapeHtml(c.part_number || '')}</div></div>
      <div class="field"><label>Manufacturer</label><div>${escapeHtml(c.manufacturer || '')}</div></div>
      <div class="field span-2"><label>Description</label><div>${escapeHtml(c.description || '')}</div></div>
      <div class="field span-2"><label>Datasheet</label><div>${ds}</div></div>
    </div>
    <h3 style="margin-top: 14px;">Locations</h3>
    <table class="box-list">
      <thead><tr><th>Box</th><th>X</th><th>Y</th><th>Qty</th></tr></thead>
      <tbody>${locations}</tbody>
    </table>`;
}

function collectFormData() {
  return {
    part_number: document.getElementById('part_number').value.trim(),
    manufacturer: document.getElementById('manufacturer').value.trim(),
    description: document.getElementById('description').value.trim(),
    datasheet_url: document.getElementById('datasheet_url').value.trim(),
  };
}

async function saveComponent() {
  const payload = collectFormData();
  if (!payload.part_number) {
    setStatus('Part number is required.', true);
    return;
  }
  try {
    if (newMode || !selectedId) {
      const created = await fetchJson('/api/components', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      selectedId = created.id;
      newMode = false;
      await loadComponents(document.getElementById('search').value);
      await selectComponent(selectedId);
      setStatus('Component created.');
    } else {
      await fetchJson('/api/components/' + selectedId, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      await loadComponents(document.getElementById('search').value);
      await selectComponent(selectedId);
      setStatus('Component updated.');
    }
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function addLocation() {
  if (!selectedId || newMode) {
    setStatus('Save the component before adding locations.', true);
    return;
  }
  const payload = {
    component_id: selectedId,
    box_id: Number(document.getElementById('box_id').value),
    x: Number(document.getElementById('pos_x').value),
    y: Number(document.getElementById('pos_y').value),
    quantity: document.getElementById('quantity').value.trim(),
  };
  if (!payload.box_id || !payload.x || !payload.y) {
    setStatus('Box, X, and Y are required.', true);
    return;
  }
  try {
    await fetchJson('/api/placements', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    await selectComponent(selectedId);
    setStatus('Location added.');
  } catch (err) {
    setStatus(err.message, true);
  }
}

function enterNewMode() {
  newMode = true;
  selectedId = null;
  renderComponentList();
  clearForm();
  renderDetailPane({placements: []});
  setStatus('Ready to create a new component.');
}

window.addEventListener('DOMContentLoaded', async () => {
  await loadBoxes();
  await loadComponents('');
  document.getElementById('search').addEventListener('input', async (e) => {
    await loadComponents(e.target.value);
  });
  document.getElementById('saveBtn').addEventListener('click', saveComponent);
  document.getElementById('newBtn').addEventListener('click', enterNewMode);
  document.getElementById('addLocationBtn').addEventListener('click', addLocation);
});
</script>
</body>
</html>
'''


def create_app(db_path: str) -> Flask:
    app = Flask(__name__)
    app.config['DB_PATH'] = os.path.abspath(db_path)

    def get_db() -> sqlite3.Connection:
        if 'db' not in g:
            conn = sqlite3.connect(app.config['DB_PATH'])
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')
            g.db = conn
        return g.db

    @app.teardown_appcontext
    def close_db(exception: Exception | None) -> None:
        db = g.pop('db', None)
        if db is not None:
            db.close()

    def dicts(rows):
        return [dict(r) for r in rows]

    def ensure_schema() -> None:
        db = get_db()
        db.executescript(
            '''
            CREATE TABLE IF NOT EXISTS boxes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_number INTEGER,
                box_name TEXT NOT NULL UNIQUE,
                width INTEGER,
                height INTEGER
            );
            CREATE TABLE IF NOT EXISTS components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_number TEXT NOT NULL UNIQUE,
                manufacturer TEXT,
                description TEXT,
                datasheet_url TEXT
            );
            CREATE TABLE IF NOT EXISTS placements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_id INTEGER NOT NULL,
                component_id INTEGER NOT NULL,
                x INTEGER,
                y INTEGER,
                quantity TEXT,
                source_sheet TEXT,
                FOREIGN KEY(box_id) REFERENCES boxes(id) ON DELETE CASCADE,
                FOREIGN KEY(component_id) REFERENCES components(id) ON DELETE CASCADE,
                UNIQUE(box_id, x, y)
            );
            '''
        )
        db.commit()

    @app.before_request
    def _before_request() -> None:
        ensure_schema()

    @app.get('/')
    def index():
        return render_template_string(APP_HTML)

    @app.get('/api/boxes')
    def api_boxes():
        db = get_db()
        rows = db.execute('SELECT id, box_number, box_name, width, height FROM boxes ORDER BY COALESCE(box_number, 999999), box_name').fetchall()
        return jsonify(dicts(rows))

    @app.get('/api/components')
    def api_components():
        search = (request.args.get('search') or '').strip()
        db = get_db()
        if search:
            like = f'%{search}%'
            rows = db.execute(
                '''
                SELECT id, part_number, manufacturer, description, datasheet_url
                FROM components
                WHERE part_number LIKE ? OR manufacturer LIKE ? OR description LIKE ?
                ORDER BY part_number COLLATE NOCASE
                ''',
                (like, like, like),
            ).fetchall()
        else:
            rows = db.execute(
                'SELECT id, part_number, manufacturer, description, datasheet_url FROM components ORDER BY part_number COLLATE NOCASE'
            ).fetchall()
        return jsonify(dicts(rows))

    @app.get('/api/components/<int:component_id>')
    def api_component(component_id: int):
        db = get_db()
        row = db.execute(
            'SELECT id, part_number, manufacturer, description, datasheet_url FROM components WHERE id = ?',
            (component_id,),
        ).fetchone()
        if row is None:
            abort(404, f'Component {component_id} not found')
        placements = db.execute(
            '''
            SELECT p.id AS placement_id, p.box_id, b.box_name, b.width, b.height, p.x, p.y, p.quantity
            FROM placements p
            JOIN boxes b ON b.id = p.box_id
            WHERE p.component_id = ?
            ORDER BY b.box_name, p.y, p.x
            ''',
            (component_id,),
        ).fetchall()
        result = dict(row)
        result['placements'] = dicts(placements)
        return jsonify(result)

    @app.post('/api/components')
    def api_create_component():
        db = get_db()
        data = request.get_json(force=True, silent=False) or {}
        part_number = (data.get('part_number') or '').strip()
        if not part_number:
            abort(400, 'part_number is required')
        try:
            cur = db.execute(
                'INSERT INTO components (part_number, manufacturer, description, datasheet_url) VALUES (?, ?, ?, ?)',
                (
                    part_number,
                    (data.get('manufacturer') or '').strip() or None,
                    (data.get('description') or '').strip() or None,
                    (data.get('datasheet_url') or '').strip() or None,
                ),
            )
            db.commit()
        except sqlite3.IntegrityError as exc:
            abort(400, f'Could not create component: {exc}')
        return jsonify({'id': cur.lastrowid, 'status': 'created'})

    @app.put('/api/components/<int:component_id>')
    def api_update_component(component_id: int):
        db = get_db()
        data = request.get_json(force=True, silent=False) or {}
        part_number = (data.get('part_number') or '').strip()
        if not part_number:
            abort(400, 'part_number is required')
        try:
            cur = db.execute(
                '''
                UPDATE components
                SET part_number = ?, manufacturer = ?, description = ?, datasheet_url = ?
                WHERE id = ?
                ''',
                (
                    part_number,
                    (data.get('manufacturer') or '').strip() or None,
                    (data.get('description') or '').strip() or None,
                    (data.get('datasheet_url') or '').strip() or None,
                    component_id,
                ),
            )
            db.commit()
        except sqlite3.IntegrityError as exc:
            abort(400, f'Could not update component: {exc}')
        if cur.rowcount == 0:
            abort(404, f'Component {component_id} not found')
        return jsonify({'status': 'updated'})

    @app.post('/api/placements')
    def api_create_placement():
        db = get_db()
        data = request.get_json(force=True, silent=False) or {}
        required = ['component_id', 'box_id', 'x', 'y']
        missing = [k for k in required if data.get(k) in (None, '')]
        if missing:
            abort(400, f'Missing required fields: {", ".join(missing)}')
        try:
            cur = db.execute(
                '''
                INSERT INTO placements (box_id, component_id, x, y, quantity)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    int(data['box_id']),
                    int(data['component_id']),
                    int(data['x']),
                    int(data['y']),
                    (data.get('quantity') or '').strip() or None,
                ),
            )
            db.commit()
        except sqlite3.IntegrityError as exc:
            abort(400, f'Could not add location: {exc}')
        return jsonify({'id': cur.lastrowid, 'status': 'created'})

    @app.delete('/api/placements/<int:placement_id>')
    def api_delete_placement(placement_id: int):
        db = get_db()
        cur = db.execute('DELETE FROM placements WHERE id = ?', (placement_id,))
        db.commit()
        if cur.rowcount == 0:
            abort(404, f'Placement {placement_id} not found')
        return jsonify({'status': 'deleted'})

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description='Web app for browsing, creating, and editing component inventory records.')
    parser.add_argument('db', help='Path to the SQLite database file')
    parser.add_argument('--host', default='127.0.0.1', help='Host interface to bind')
    parser.add_argument('--port', type=int, default=5000, help='Port number')
    parser.add_argument('--debug', action='store_true', help='Enable Flask debug mode')
    args = parser.parse_args()

    app = create_app(args.db)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
