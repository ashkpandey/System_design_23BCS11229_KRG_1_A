import xml.etree.ElementTree as ET
import sys
from collections import defaultdict

if len(sys.argv) < 2:
    print("Usage: python fix_drawio_ids.py <file.drawio>")
    sys.exit(2)

path = sys.argv[1]
backup = path + ".bak"

print(f"Reading {path}...")
with open(path, 'r', encoding='utf-8') as f:
    xml = f.read()

# Parse while preserving XML declaration
root = ET.fromstring(xml)

# find the mxGraphModel root <root> element inside diagram -> mxGraphModel -> root
# The file structure: mxfile/diagram/mxGraphModel/root/... so find all mxCell under any root
cells = []
for elem in root.iter():
    if elem.tag.endswith('mxCell') or elem.tag == 'mxCell' or elem.tag.endswith('mxCell'):
        cells.append(elem)

# (No additional fallback needed; operate on parsed elements)
# Build mapping id -> list of elements
id_map = defaultdict(list)
for elem in root.iter():
    if 'id' in elem.attrib:
        id_map[elem.attrib['id']].append(elem)

all_ids = set(id_map.keys())

# Helper to generate a unique id
counter = 1
def gen_unique(prefix='fix'):
    global counter
    while True:
        cand = f"{prefix}{counter}"
        counter += 1
        if cand not in all_ids and cand != '224':
            all_ids.add(cand)
            return cand

# Prepare renames dict old->new
renames = {}

# Handle duplicates: keep first occurrence, rename following
for idval, elems in list(id_map.items()):
    if len(elems) > 1:
        # keep first, rename others
        for dup in elems[1:]:
            new_id = gen_unique(prefix='dup')
            renames[dup.attrib['id']] = renames.get(dup.attrib['id'], []) + [(dup, new_id)]

# Also ensure gap: if any element has id == '224', rename it
if '224' in id_map:
    elems = id_map['224']
    # if single or multiple, rename all to unique ids
    for elem in elems:
        new_id = gen_unique(prefix='gap')
        renames.setdefault('224', []).append((elem, new_id))

# Apply renames and update references
# Build a map from old single instance to new id for replacement purposes
old_to_new = {}
for old, lst in renames.items():
    for (elem, new_id) in lst:
        old_to_new[ elem.attrib['id'] ] = new_id
        elem.attrib['id'] = new_id

# Update references in attributes 'parent', 'source', 'target', maybe 'labelTarget'
refs = ('parent','source','target')
for elem in root.iter():
    for r in refs:
        if r in elem.attrib:
            val = elem.attrib[r]
            if val in old_to_new:
                elem.attrib[r] = old_to_new[val]

# Write backup and new file (pretty printed as string)
print(f"Writing backup to {backup} and updating file {path}...")
with open(backup, 'w', encoding='utf-8') as f:
    f.write(xml)

# Convert ElementTree back to string
new_xml = ET.tostring(root, encoding='utf-8').decode('utf-8')
# Preserve xml header if present
if xml.strip().startswith('<?xml'):
    header = xml.split('?>',1)[0] + '?>\n'
    if not new_xml.startswith(header):
        new_xml = header + new_xml

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_xml)

# Report summary
print('Renamed IDs:')
for old, lst in renames.items():
    for (elem,new) in lst:
        print(f"  {old} -> {new}")

print('Done.')
