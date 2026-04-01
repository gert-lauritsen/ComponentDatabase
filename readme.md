# Component database


```markdown
# Component Inventory System

This project provides a workflow to manage electronic components using:

- JSON database (frontend-friendly)
- HTML editor (no backend required)
- Python enrichment script (Mouser API)
- Optional Flask backend (for full DB integration)

---

# 📁 Project Structure

```

project/
│
├── components_editor_standalone.html   # HTML UI (editor + viewer)
├── components_editor_import.json       # JSON database (input/output)
├── enrich_components_json_safe.py      # JSON enrichment script
├── config_keys.py                      # API keys (private)
└── README.md

```

---

# ⚠️ Security

Your API key is stored in:

:contentReference[oaicite:0]{index=0}

👉 **IMPORTANT**
- Do NOT commit this file to Git
- Regenerate your API key if it was exposed
- Add to `.gitignore`:

```

config_keys.py

````

---

# 🧠 JSON Database Format

The system uses this structure:

```json
{
  "components": [
    {
      "id": 1,
      "part_number": "LM1117-3.3",
      "manufacturer": "",
      "description": "",
      "datasheet_url": "",
      "locations": [
        { "box": "1", "x": "2", "y": "3", "qty": "1" }
      ]
    }
  ]
}
````

---

# 🌐 HTML Editor

File:

*

## Features

* Search components
* Add / edit parts
* Add locations (box, x, y)
* Export JSON
* Import JSON
* Works offline (no server)

## Usage

Open in browser:

```
components_editor_standalone.html
```

---

# 🔧 JSON Enrichment Script

File:

*

## What it does

1. Reads JSON file
2. Finds components missing:

   * manufacturer
   * description
   * datasheet_url
3. Queries Mouser API
4. Updates ONLY missing fields (safe mode)
5. Writes:

   * enriched JSON
   * unresolved parts list

---

## ▶️ Run

```bash
pip install requests

python enrich_components_json_safe.py components_editor_import.json
```

---

## Output

```
components_editor_import_safe_enriched.json
components_editor_import_safe_enriched_unresolved.json
```

---

# 🧠 Matching Logic

The script uses:

* exact part-number match
* normalized comparison (removes symbols)
* score-based filtering

Only accepts **high-confidence matches**

---

## 🚫 Skipped Components

The script will skip:

* resistors (R, 10k, etc.)
* capacitors (C, 100nF)
* connectors
* headers
* power symbols

This is intentional to avoid incorrect datasheets.

---

# 🔌 Mouser API

Uses:

* Mouser Part Search API

From documentation:



## Setup

1. Create Mouser account
2. Request API key
3. Add to `config_keys.py`:

```python
MOUSER_API_KEY = "your_key_here"
```

---

# 🧪 Example Flow

1. Edit components in HTML
2. Export JSON
3. Run enrichment script
4. Import enriched JSON back into HTML

---

# 🧩 Optional: Flask Backend

File:

*

## Features

* SQLite database backend
* REST API
* Full CRUD operations
* Multi-user ready

## Run

```bash
pip install flask

python component_inventory_webapp.py components.db
```

Open:

```
http://127.0.0.1:5000
```

---

# 🚀 Recommended Workflow

### Simple (no backend)

✔ HTML + JSON
✔ Easy
✔ Portable

### Advanced

✔ Flask + SQLite
✔ Multi-user
✔ Persistent storage

---

# 🔧 Future Improvements

Possible upgrades:

* Octopart/Nexar fallback
* fuzzy part matching
* barcode scanning
* grid visualization of boxes
* automatic part categorization
* BOM import/export

---

# ✅ Summary

This system provides:

✔ Offline editing
✔ Safe enrichment from Mouser
✔ Structured component storage
✔ Expandable architecture

---

# 🧑‍💻 Author Notes

* Safe mode prevents incorrect datasheets
* JSON format is optimized for frontend use
* Database version available for scaling

---
