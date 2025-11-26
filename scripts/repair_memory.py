# scripts/repair_memory.py
import json, os

ROOT = r"C:\Users\HEALTHY MACHINES\OneDrive\Desktop\capstone_project_package"
path = os.path.join(ROOT, "data", "processed", "memory_store.json")
bak = path + ".orig.bak"

print("Input file:", path)
if not os.path.exists(path):
    print("File not found:", path)
    raise SystemExit(1)

# Make a safe backup
if not os.path.exists(bak):
    os.replace(path, bak)
    print("Backed up original to:", bak)
else:
    print("Backup already exists at:", bak)

# Read backup and try to parse as either JSON or JSONL
records = []
with open(bak, "r", encoding="utf-8") as f:
    data = f.read()

# Try plain JSON first
try:
    parsed = json.loads(data)
    # If it's a dict, wrap in list for consistent memory.store format
    if isinstance(parsed, dict):
        records = [parsed]
    elif isinstance(parsed, list):
        records = parsed
    else:
        # unknown top-level but valid JSON — wrap as single element
        records = [parsed]
    print("Parsed as single JSON value with", len(records), "records.")
except json.JSONDecodeError:
    # fallback: parse as JSON lines (one JSON per line)
    records = []
    for i, line in enumerate(data.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            records.append(obj)
        except json.JSONDecodeError as e:
            print(f"Skipping line {i+1} — JSONDecodeError:", e)
    print("Parsed as JSONL with", len(records), "records.")

# Write cleaned JSON array back to memory_store.json
out_path = path  # original path is now freed because we moved to .orig.bak
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print("Wrote cleaned JSON array to:", out_path)
print("Records saved:", len(records))
