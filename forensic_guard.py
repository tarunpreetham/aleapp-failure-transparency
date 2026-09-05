from pathlib import Path
import argparse
import json
import sqlite3
import sys

EXPECTED = {
    "wa_contacts": {"given_name", "family_name", "display_name", "jid", "number"},
    "message": {
        "_id", "timestamp", "received_timestamp", "from_me",
        "message_type", "text_data", "chat_row_id", "recipient_count"
    },
    "chat": {"_id", "jid_row_id"},
    "jid": {"_id", "raw_string"},
    "message_media": {"message_row_id", "file_path", "file_size"},
    "message_location": {
        "message_row_id", "latitude", "longitude",
        "live_location_share_duration",
        "live_location_final_latitude",
        "live_location_final_longitude",
        "live_location_final_timestamp"
    },
}

def connect_ro(path):
    path = Path(path).resolve()
    uri = f"file:{path.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)

def table_names(conn):
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

def column_names(conn, table):
    return {
        row[1]
        for row in conn.execute(f'PRAGMA table_info("{table}")')
    }

def add(results, level, check, detail, **extra):
    item = {
        "level": level,
        "check": check,
        "detail": detail,
    }
    item.update(extra)
    results.append(item)

def check_contacts(wa_path, results):
    wa = connect_ro(wa_path)
    try:
        tables = table_names(wa)

        if "wa_contacts" not in tables:
            add(
                results,
                "FAIL",
                "contacts.table",
                "Required table 'wa_contacts' is missing. "
                "Artifact absence cannot be distinguished safely from parser incompatibility."
            )
            return

        cols = column_names(wa, "wa_contacts")
        missing = EXPECTED["wa_contacts"] - cols

        if missing:
            add(
                results,
                "FAIL",
                "contacts.columns",
                f"Missing required wa_contacts columns: {sorted(missing)}",
                missing_columns=sorted(missing)
            )
            return

        count = wa.execute(
            "SELECT COUNT(*) FROM wa_contacts"
        ).fetchone()[0]

        if count == 0:
            add(
                results,
                "PASS",
                "contacts.schema",
                "wa_contacts schema is compatible and contains 0 rows. "
                "This is a valid empty-artifact condition.",
                row_count=0
            )
        else:
            add(
                results,
                "PASS",
                "contacts.schema",
                f"wa_contacts schema is compatible; row count={count}.",
                row_count=count
            )

    finally:
        wa.close()

def check_message_schema(msg, results):
    tables = table_names(msg)
    required_tables = [
        "message", "chat", "jid", "message_media", "message_location"
    ]

    structural_ok = True

    for table in required_tables:
        if table not in tables:
            structural_ok = False
            add(
                results,
                "FAIL",
                f"messages.table.{table}",
                f"Required table '{table}' is missing."
            )
            continue

        cols = column_names(msg, table)
        missing = EXPECTED[table] - cols

        if missing:
            structural_ok = False
            add(
                results,
                "FAIL",
                f"messages.columns.{table}",
                f"Missing required columns in '{table}': {sorted(missing)}",
                missing_columns=sorted(missing)
            )

    if structural_ok:
        add(
            results,
            "PASS",
            "messages.schema",
            "Required message tables and columns match the expected parser profile."
        )

    return structural_ok

def check_relationships(msg, wa_path, results):
    msg.execute(
        "ATTACH DATABASE ? AS wadb",
        (str(Path(wa_path).resolve()),)
    )

    candidate = msg.execute("""
        SELECT COUNT(*)
        FROM message
        WHERE recipient_count = 0
    """).fetchone()[0]

    after_chat = msg.execute("""
        SELECT COUNT(*)
        FROM message
        JOIN chat
          ON chat._id = message.chat_row_id
        WHERE message.recipient_count = 0
    """).fetchone()[0]

    after_jid = msg.execute("""
        SELECT COUNT(*)
        FROM message
        JOIN chat
          ON chat._id = message.chat_row_id
        JOIN jid
          ON jid._id = chat.jid_row_id
        WHERE message.recipient_count = 0
    """).fetchone()[0]

    after_contact = msg.execute("""
        SELECT COUNT(*)
        FROM message
        JOIN chat
          ON chat._id = message.chat_row_id
        JOIN jid
          ON jid._id = chat.jid_row_id
        JOIN wadb.wa_contacts
          ON wadb.wa_contacts.jid = jid.raw_string
        WHERE message.recipient_count = 0
    """).fetchone()[0]

    if candidate == after_contact:
        add(
            results,
            "PASS",
            "messages.relationships",
            f"All {candidate} candidate 1:1 messages survive the expected "
            "message→chat→jid→wa_contacts relationship chain.",
            candidate_messages=candidate,
            after_chat=after_chat,
            after_jid=after_jid,
            after_contact=after_contact
        )
    else:
        add(
            results,
            "WARN",
            "messages.relationships",
            f"Potential partial artifact omission: {candidate} candidate 1:1 messages exist, "
            f"but only {after_contact} survive the parser's expected JOIN chain.",
            candidate_messages=candidate,
            after_chat=after_chat,
            after_jid=after_jid,
            after_contact=after_contact,
            potential_missing=candidate - after_contact
        )

    # Detect relationship-like columns that are not part of the expected profile.
    chat_cols = column_names(msg, "chat")
    extra_relationship_cols = sorted(
        c for c in chat_cols
        if c not in EXPECTED["chat"]
        and ("jid" in c.lower() or "participant" in c.lower())
    )

    if extra_relationship_cols:
        add(
            results,
            "WARN",
            "messages.relationship_schema",
            "Unexpected relationship-like columns detected in chat: "
            f"{extra_relationship_cols}. Review whether relationships have migrated.",
            unexpected_columns=extra_relationship_cols
        )

        # Special diagnostic for the controlled M1 experiment.
        if "participant_jid_row_id" in chat_cols:
            migrated = msg.execute("""
                SELECT COUNT(*)
                FROM chat
                WHERE jid_row_id IS NULL
                  AND participant_jid_row_id IS NOT NULL
            """).fetchone()[0]

            if migrated > 0:
                add(
                    results,
                    "WARN",
                    "messages.relationship_migration",
                    f"{migrated} chat rows use participant_jid_row_id while jid_row_id is NULL. "
                    "The fixed parser JOIN on chat.jid_row_id may omit related messages.",
                    migrated_rows=migrated
                )

def classify_timestamp_scale(value):
    value = abs(int(value))

    # Roughly 10-digit Unix seconds versus 13-digit Unix milliseconds.
    if value < 100_000_000_000:
        return "seconds"
    if value < 100_000_000_000_000:
        return "milliseconds"
    return "unknown"

def check_timestamp_scale(msg, results):
    rows = msg.execute("""
        SELECT _id, timestamp
        FROM message
        WHERE recipient_count = 0
          AND timestamp IS NOT NULL
          AND timestamp != 0
        ORDER BY _id
    """).fetchall()

    seconds_ids = []
    milliseconds_ids = []
    unknown_ids = []

    for message_id, timestamp in rows:
        scale = classify_timestamp_scale(timestamp)

        if scale == "seconds":
            seconds_ids.append(message_id)
        elif scale == "milliseconds":
            milliseconds_ids.append(message_id)
        else:
            unknown_ids.append(message_id)

    if seconds_ids and milliseconds_ids:
        add(
            results,
            "WARN",
            "messages.timestamp_scale",
            f"Mixed timestamp representations detected: "
            f"{len(seconds_ids)} seconds-like and "
            f"{len(milliseconds_ids)} milliseconds-like values. "
            "The current ALEAPP query divides all message timestamps by 1000, "
            "so seconds-scale records may be misinterpreted.",
            seconds_like_ids=seconds_ids,
            milliseconds_like_ids=milliseconds_ids,
            unknown_ids=unknown_ids
        )

    elif seconds_ids:
        add(
            results,
            "WARN",
            "messages.timestamp_scale",
            f"All {len(seconds_ids)} non-zero message timestamps appear seconds-scale, "
            "while the current parser expects milliseconds.",
            seconds_like_ids=seconds_ids
        )

    elif unknown_ids:
        add(
            results,
            "WARN",
            "messages.timestamp_scale",
            f"Unexpected timestamp magnitudes detected for message IDs {unknown_ids}.",
            unknown_ids=unknown_ids
        )

    else:
        add(
            results,
            "PASS",
            "messages.timestamp_scale",
            f"All {len(milliseconds_ids)} non-zero message timestamps appear milliseconds-scale."
        )

def check_messages(msg_path, wa_path, results):
    msg = connect_ro(msg_path)

    try:
        structural_ok = check_message_schema(msg, results)

        if not structural_ok:
            return

        # wa_contacts must exist before relationship checking.
        wa = connect_ro(wa_path)
        try:
            wa_tables = table_names(wa)
            if "wa_contacts" not in wa_tables:
                add(
                    results,
                    "FAIL",
                    "messages.wa_contacts",
                    "Cannot evaluate message relationships because wa_contacts is missing."
                )
                return

            wa_cols = column_names(wa, "wa_contacts")
            message_contact_required = {"jid", "wa_name"}
            missing_contact_cols = message_contact_required - wa_cols
            if missing_contact_cols:
                add(
                    results,
                    "FAIL",
                    "messages.wa_contacts_columns",
                    f"Missing wa_contacts columns required by the message parser: "
                    f"{sorted(missing_contact_cols)}",
                    missing_columns=sorted(missing_contact_cols)
                )
                return
        finally:
            wa.close()

        check_relationships(msg, wa_path, results)
        check_timestamp_scale(msg, results)

    finally:
        msg.close()

def summarize(results):
    levels = [r["level"] for r in results]

    if "FAIL" in levels:
        overall = "FAIL"
    elif "WARN" in levels:
        overall = "WARN"
    else:
        overall = "PASS"

    return overall

def main():
    parser = argparse.ArgumentParser(
        description="Preflight schema, relationship, and timestamp guard for the "
                    "ALEAPP WhatsApp Contacts and One-to-One Messages artifacts."
    )
    parser.add_argument(
        "--wa",
        required=True,
        help="Path to wa.db"
    )
    parser.add_argument(
        "--msg",
        help="Path to msgstore.db. Omit for Contacts-only checking."
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default="guard_report.json",
        help="Output JSON report path (default: guard_report.json)"
    )

    args = parser.parse_args()

    results = []

    check_contacts(args.wa, results)

    if args.msg:
        check_messages(args.msg, args.wa, results)

    overall = summarize(results)

    report = {
        "overall": overall,
        "wa_db": str(Path(args.wa).resolve()),
        "msgstore_db": str(Path(args.msg).resolve()) if args.msg else None,
        "checks": results
    }

    print("\n=== WhatsApp Forensic Parser Guard ===")
    print(f"Overall: {overall}\n")

    for result in results:
        print(f"[{result['level']}] {result['check']}")
        print(f"    {result['detail']}")

    json_path = Path(args.json_path)
    json_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print(f"\nJSON report written to: {json_path.resolve()}")

    if overall == "FAIL":
        print("\nRecommendation: Do not interpret an empty ALEAPP result as evidence absence.")
        print("Required parser assumptions are not satisfied.")
        sys.exit(2)

    if overall == "WARN":
        print("\nRecommendation: Parser output may be incomplete or semantically unreliable.")
        print("Manual validation is required.")
        sys.exit(1)

    print("\nRecommendation: Expected parser assumptions passed preflight checks.")
    sys.exit(0)

if __name__ == "__main__":
    main()
