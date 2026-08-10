import json
from pathlib import Path
p = Path('Academic_Truth_Engine_v3.ipynb')
text = p.read_text(encoding='utf-8-sig')
nb = json.loads(text)
new_cells = []
removed = 0
for cell in nb['cells']:
    if cell.get('cell_type') == 'code' and any('if "run_academic_query" not in globals()' in line for line in cell.get('source', [])):
        removed += 1
        continue
    new_cells.append(cell)
nb['cells'] = new_cells
p.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')
print('removed', removed, 'cell(s)')
