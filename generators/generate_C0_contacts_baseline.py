from pathlib import Path
import sqlite3
import csv
import hashlib

OUT = Path(__file__).resolve().parent
DB_DIR = OUT / "evidence_root" / "data" / "data" / "com.whatsapp" / "databases"
DB_DIR.mkdir(parents=True, exist_ok=True)

DB = DB_DIR / "wa.db"
CSV = OUT / "ground_truth.csv"

records = [
    ("C001","Normal - all fields populated","Alice","Smith","Alice Smith","12025550101@s.whatsapp.net","+12025550101"),
    ("C002","Normal - all fields populated","Brian","Lee","Brian Lee","12025550102@s.whatsapp.net","+12025550102"),
    ("C003","Normal - all fields populated","Carla","Diaz","Carla Diaz","12025550103@s.whatsapp.net","+12025550103"),
    ("C004","Normal - all fields populated","Daniel","Brown","Daniel Brown","12025550104@s.whatsapp.net","+12025550104"),
    ("C005","Normal - all fields populated","Emma","Wilson","Emma Wilson","12025550105@s.whatsapp.net","+12025550105"),
    ("C006","Normal - all fields populated","Farah","Khan","Farah Khan","12025550106@s.whatsapp.net","+12025550106"),
    ("C007","Normal - all fields populated","George","Miller","George Miller","12025550107@s.whatsapp.net","+12025550107"),
    ("C008","Normal - all fields populated","Hannah","Clark","Hannah Clark","12025550108@s.whatsapp.net","+12025550108"),
    ("C009","Normal - all fields populated","Isaac","Moore","Isaac Moore","12025550109@s.whatsapp.net","+12025550109"),
    ("C010","Normal - all fields populated","Julia","Taylor","Julia Taylor","12025550110@s.whatsapp.net","+12025550110"),
    ("C011","family_name NULL","Kevin",None,"Kevin Test","12025550111@s.whatsapp.net","+12025550111"),
    ("C012","family_name NULL","Lina",None,"Lina Test","12025550112@s.whatsapp.net","+12025550112"),
    ("C013","family_name NULL","Marcus",None,"Marcus Test","12025550113@s.whatsapp.net","+12025550113"),
    ("C014","given_name NULL",None,"Nelson","Nora Nelson","12025550114@s.whatsapp.net","+12025550114"),
    ("C015","given_name NULL",None,"Patel","Omar Patel","12025550115@s.whatsapp.net","+12025550115"),
    ("C016","given_name + family_name NULL",None,None,"Project Contact 16","12025550116@s.whatsapp.net","+12025550116"),
    ("C017","given_name + family_name NULL",None,None,"Project Contact 17","12025550117@s.whatsapp.net","+12025550117"),
    ("C018","All name fields NULL",None,None,None,"12025550118@s.whatsapp.net","+12025550118"),
    ("C019","number NULL","Rina","Evans","Rina Evans","12025550119@s.whatsapp.net",None),
    ("C020","number empty string","Sam","Young","Sam Young","12025550120@s.whatsapp.net",""),
]

def expected_name(given, family, display, jid):
    if given is None and family is None and display is None:
        return jid
    if given is None and family is None:
        return display
    if given is None:
        return family
    if family is None:
        return given
    return f"{given} {family}"

def expected_number(number, jid):
    return jid if number is None or number == "" else number

if DB.exists():
    DB.unlink()

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE wa_contacts (
    given_name   TEXT,
    family_name  TEXT,
    display_name TEXT,
    jid          TEXT,
    number       TEXT
)
""")

cur.executemany("""
INSERT INTO wa_contacts (given_name, family_name, display_name, jid, number)
VALUES (?, ?, ?, ?, ?)
""", [(g, f, d, j, n) for _, _, g, f, d, j, n in records])

conn.commit()

# Baseline verification using the same SQL logic as ALEAPP get_whatsapp_contacts().
query = """
SELECT
    CASE
        WHEN WC.given_name IS NULL AND WC.family_name IS NULL AND WC.display_name IS NULL THEN WC.jid
        WHEN WC.given_name IS NULL AND WC.family_name IS NULL THEN WC.display_name
        WHEN WC.given_name IS NULL THEN WC.family_name
        WHEN WC.family_name IS NULL THEN WC.given_name
        ELSE WC.given_name || " " || WC.family_name
    END,
    jid,
    CASE WHEN WC.number IS NULL THEN WC.jid WHEN WC.number == "" THEN WC.jid ELSE WC.number END
FROM wa_contacts AS WC
"""

rows = cur.execute(query).fetchall()
conn.close()

assert len(rows) == 20, f"Baseline failed: expected 20 rows, got {len(rows)}"

headers = [
    "record_id","case_type","given_name","family_name","display_name","jid","number",
    "number_input_state","expected_name","expected_jid","expected_number"
]

with CSV.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    for rid, case, g, fam, disp, jid, num in records:
        state = "NULL" if num is None else ("EMPTY STRING" if num == "" else "VALUE")
        writer.writerow([
            rid, case, g, fam, disp, jid, num, state,
            expected_name(g, fam, disp, jid),
            jid,
            expected_number(num, jid)
        ])

digest = hashlib.sha256(DB.read_bytes()).hexdigest()
print(f"Created: {DB}")
print(f"Created: {CSV}")
print(f"Rows verified: {len(rows)}")
print(f"wa.db SHA-256: {digest}")
