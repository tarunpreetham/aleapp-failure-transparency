from pathlib import Path
import sqlite3
import csv
import datetime as dt
import hashlib

OUT = Path(__file__).resolve().parent
DB_DIR = OUT / "evidence_root" / "data" / "data" / "com.whatsapp" / "databases"
DB_DIR.mkdir(parents=True, exist_ok=True)
MSG = DB_DIR / "msgstore.db"
WA = DB_DIR / "wa.db"
CSV = OUT / "ground_truth_messages.csv"

for p in (MSG, WA):
    if p.exists():
        p.unlink()

UTC = dt.timezone.utc
base_time = dt.datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC)

def ms_epoch(d):
    return int(d.timestamp() * 1000)

def iso_utc(d):
    return d.strftime("%Y-%m-%d %H:%M:%S+00:00")

records = []
for i in range(1, 21):
    jid = f"120255502{i:02d}@s.whatsapp.net"
    wa_name = f"Participant {i:02d}"
    text = f"Synthetic message {i:02d}"
    t = base_time + dt.timedelta(minutes=i - 1)
    incoming = (i % 2 == 1)
    from_me = 0 if incoming else 1
    received = ms_epoch(t + dt.timedelta(seconds=5)) if incoming else 0
    records.append((i, jid, wa_name, text, ms_epoch(t), received, from_me))

msg_schema = """
CREATE TABLE message (
    _id INTEGER PRIMARY KEY,
    timestamp INTEGER,
    received_timestamp INTEGER,
    from_me INTEGER,
    message_type INTEGER,
    text_data TEXT,
    chat_row_id INTEGER,
    recipient_count INTEGER
);
CREATE TABLE chat (_id INTEGER PRIMARY KEY, jid_row_id INTEGER, subject TEXT);
CREATE TABLE jid (_id INTEGER PRIMARY KEY, raw_string TEXT);
CREATE TABLE message_media (message_row_id INTEGER, file_path TEXT, file_size INTEGER);
CREATE TABLE message_location (
    message_row_id INTEGER,
    latitude REAL,
    longitude REAL,
    live_location_share_duration INTEGER,
    live_location_final_latitude REAL,
    live_location_final_longitude REAL,
    live_location_final_timestamp INTEGER
);
"""

wa_schema = """
CREATE TABLE wa_contacts (
    jid TEXT,
    wa_name TEXT,
    given_name TEXT,
    family_name TEXT,
    display_name TEXT,
    number TEXT
);
"""

conn = sqlite3.connect(MSG)
cur = conn.cursor()
cur.executescript(msg_schema)
cur.executemany("INSERT INTO jid (_id, raw_string) VALUES (?, ?)",
                [(i, jid) for i, jid, _, _, _, _, _ in records])
cur.executemany("INSERT INTO chat (_id, jid_row_id, subject) VALUES (?, ?, ?)",
                [(i, i, None) for i, *_ in records])
cur.executemany("""
INSERT INTO message
(_id, timestamp, received_timestamp, from_me, message_type, text_data, chat_row_id, recipient_count)
VALUES (?, ?, ?, ?, 0, ?, ?, 0)
""", [(i, ts, rts, fm, text, i) for i, _, _, text, ts, rts, fm in records])
conn.commit()
conn.close()

conn = sqlite3.connect(WA)
cur = conn.cursor()
cur.executescript(wa_schema)
cur.executemany("""
INSERT INTO wa_contacts (jid, wa_name, given_name, family_name, display_name, number)
VALUES (?, ?, ?, ?, ?, ?)
""", [(jid, name, "Participant", f"{i:02d}", name, f"+120255502{i:02d}")
      for i, jid, name, *_ in records])
conn.commit()
conn.close()

conn = sqlite3.connect(MSG)
cur = conn.cursor()
cur.execute("ATTACH DATABASE ? AS wadb", (str(WA),))
count = cur.execute("""
SELECT COUNT(*)
FROM message
JOIN chat ON chat._id=message.chat_row_id
JOIN jid ON jid._id=chat.jid_row_id
JOIN wa_contacts ON wa_contacts.jid=jid.raw_string
WHERE message.recipient_count=0
""").fetchone()[0]
conn.close()

assert count == 20, f"Expected 20 joined messages, got {count}"

headers = [
    "record_id","message_id","chat_id","jid_id","jid","wa_name",
    "timestamp_ms","received_timestamp_ms","from_me","recipient_count",
    "message_type","text_data","expected_message_timestamp",
    "expected_received_timestamp","expected_direction",
    "expected_participant_name","expected_message",
    "expected_sending_party_jid","expected_message_type"
]

with CSV.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(headers)
    for i, jid, name, text, ts, rts, fm in records:
        t = dt.datetime.fromtimestamp(ts/1000, tz=UTC)
        rt = "" if rts == 0 else dt.datetime.fromtimestamp(rts/1000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S+00:00")
        w.writerow([
            f"M{i:03d}", i, i, i, jid, name, ts, rts, fm, 0, 0, text,
            t.strftime("%Y-%m-%d %H:%M:%S+00:00"),
            rt,
            "Incoming" if fm == 0 else "Outgoing",
            name,
            text,
            jid if fm == 0 else "",
            "Text"
        ])

print("Created:", MSG)
print("Created:", WA)
print("Created:", CSV)
print("Joined one-to-one message count:", count)
print("msgstore.db SHA-256:", hashlib.sha256(MSG.read_bytes()).hexdigest())
print("wa.db SHA-256:", hashlib.sha256(WA.read_bytes()).hexdigest())
