import subprocess, json, sys

LARK = r"C:\Users\Jinting\AppData\Roaming\npm\lark-cli.cmd"
BASE = "Ig3PbAEaSaJa9AsLwiCc77ZinXD"
TABLE = "tblfjivTnDw1eZLJ"

result = subprocess.run(
    [LARK, "api", "GET",
     f"/open-apis/bitable/v1/apps/{BASE}/tables/{TABLE}/records",
     "--params", '{"page_size": 20}'],
    capture_output=True
)
out = result.stdout.decode("utf-8").strip()
with open("debug_out.json", "w", encoding="utf-8") as f:
    f.write(out)

data = json.loads(out)
items = data["data"]["items"]
for r in items:
    date_val = r["fields"].get("补款日期", "(empty)")
    print(repr(date_val))
