import subprocess, json, re, sys

def parse_cn_date(text):
    """Returns (year_month_str, day_int_or_None) from Chinese date text."""
    m = re.match(r'(\d{4})年(\d{1,2})月(?:(\d{1,2})日)?', str(text).strip())
    if not m:
        return None, None
    year, month = int(m.group(1)), int(m.group(2))
    day = int(m.group(3)) if m.group(3) else None
    return f"{year}-{month:02d}", day

BASE   = sys.argv[1]   # app token
TABLE  = sys.argv[2]   # table id
SRC    = sys.argv[3]   # source field name, e.g. "补款时间"
YM_DST = sys.argv[4]   # year-month field name, e.g. "补款年月"
D_DST  = sys.argv[5]   # day field name, e.g. "补款日"

# Fetch all records
out = subprocess.check_output([
    "lark-cli", "base", "+record-list",
    "--base-token", BASE, "--table-id", TABLE, "--page-all", "--format", "json"
])
records = json.loads(out)["data"]["items"]

updates, skipped = [], []
for rec in records:
    raw = rec["fields"].get(SRC, "")
    ym, day = parse_cn_date(raw)
    if ym is None:
        skipped.append((rec["record_id"], raw))
        continue
    fields = {YM_DST: ym}
    if day is not None:
        fields[D_DST] = day
    updates.append({"record_id": rec["record_id"], "fields": fields})

# Batch update (max 500 per request)
for i in range(0, len(updates), 500):
    batch = updates[i:i + 500]
    subprocess.run([
        "lark-cli", "base", "+record-batch-update",
        "--base-token", BASE, "--table-id", TABLE,
        "--json", json.dumps({"records": batch})
    ], check=True)
    print(f"Updated {i + 1}–{i + len(batch)}")

print(f"Done. Updated: {len(updates)}, Skipped: {len(skipped)}")
if skipped:
    for rid, raw in skipped:
        print(f"  record {rid}: {repr(raw)}")
