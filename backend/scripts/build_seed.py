#!/usr/bin/env python
"""
One-time conversion of the legacy Postgres seed dump into the fixture that
``migrations/versions/0002_seed_data.py`` loads.

The source is the ``0001_init.sql`` file from the original version of this
app: a flat list of ``INSERT`` statements against the *legacy* schema, which
predates the patient/physician split.

    users    (id, name, is_physician)
    threads  (id, title, users /* JSON array of user ids */, date_created)
    messages (id, "userId", "threadId", message, timestamp, "msgIndex")

This script reshapes that onto the current schema:

* ``users`` fans out into ``patients`` and ``physicians``, preserving ids.
* each thread's JSON ``users`` array becomes one ``patient_id`` plus a set of
  ``threads_physicians`` rows.
* each message's ``userId`` resolves to either ``author_patient_id`` or
  ``author_physician_id`` depending on the author's role.

Output is a gzipped JSONL file — one JSON object per line, each tagged with a
``kind`` — which the migration streams through ``bulk_create``.

Usage::

    uv run build-seed path/to/0001_init.sql

The generated fixture is committed, so this only needs re-running if the
upstream seed changes.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "fixtures" / "seed.jsonl.gz"

INSERT_RE = re.compile(r"^INSERT INTO (\w+) \((.*?)\) VALUES \((.*)\);$")


def parse_values(raw: str) -> list[Any]:
    """
    Split a Postgres ``VALUES`` tuple body into Python values.

    Handles single-quoted strings with doubled-quote escaping, integers, and
    the TRUE/FALSE/NULL keywords — which is the entire vocabulary the dump
    uses.
    """
    values: list[Any] = []
    i = 0
    n = len(raw)
    while i < n:
        while i < n and raw[i] in " ,":
            i += 1
        if i >= n:
            break
        if raw[i] == "'":
            i += 1
            chars: list[str] = []
            while i < n:
                if raw[i] == "'":
                    if i + 1 < n and raw[i + 1] == "'":
                        chars.append("'")
                        i += 2
                        continue
                    i += 1
                    break
                chars.append(raw[i])
                i += 1
            values.append("".join(chars))
        else:
            start = i
            while i < n and raw[i] != ",":
                i += 1
            token = raw[start:i].strip()
            if token == "TRUE":
                values.append(True)
            elif token == "FALSE":
                values.append(False)
            elif token == "NULL":
                values.append(None)
            else:
                values.append(int(token))
    return values


def iter_inserts(sql_path: Path) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(table, {column: value})`` for every INSERT in the dump."""
    with sql_path.open(encoding="utf-8") as handle:
        for line in handle:
            match = INSERT_RE.match(line.strip())
            if not match:
                continue
            table, columns_src, values_src = match.groups()
            columns = [c.strip().strip('"') for c in columns_src.split(",")]
            values = parse_values(values_src)
            if len(columns) != len(values):
                raise ValueError(f"column/value mismatch on: {line[:120]}")
            yield table, dict(zip(columns, values))


def build(sql_path: Path, output_path: Path) -> None:
    users: dict[str, dict[str, Any]] = {}
    threads: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []

    for table, row in iter_inserts(sql_path):
        if table == "users":
            users[str(row["id"])] = row
        elif table == "threads":
            threads.append(row)
        elif table == "messages":
            messages.append(row)
        else:
            raise ValueError(f"unexpected table in seed: {table}")

    is_physician = {uid: bool(u["is_physician"]) for uid, u in users.items()}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = {"patient": 0, "physician": 0, "thread": 0, "thread_physician": 0, "message": 0}

    with gzip.open(output_path, "wt", encoding="utf-8", compresslevel=9) as out:

        def emit(record: dict[str, Any]) -> None:
            counts[record["kind"]] += 1
            out.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")

        for uid, user in users.items():
            emit(
                {
                    "kind": "physician" if is_physician[uid] else "patient",
                    "id": uid,
                    "name": user["name"],
                }
            )

        for thread in threads:
            participants = json.loads(str(thread["users"]))
            patient_ids = [u for u in participants if not is_physician[u]]
            physician_ids = [u for u in participants if is_physician[u]]
            if len(patient_ids) != 1:
                raise ValueError(
                    f"thread {thread['id']} has {len(patient_ids)} patients; expected exactly 1"
                )
            emit(
                {
                    "kind": "thread",
                    "id": thread["id"],
                    "title": thread["title"],
                    "date_created": thread["date_created"],
                    "patient_id": patient_ids[0],
                }
            )
            # dict.fromkeys dedupes while preserving the dump's ordering.
            for physician_id in dict.fromkeys(physician_ids):
                emit(
                    {
                        "kind": "thread_physician",
                        "thread_id": thread["id"],
                        "physician_id": physician_id,
                    }
                )

        thread_ids = {t["id"] for t in threads}
        for message in messages:
            if message["threadId"] not in thread_ids:
                # The legacy SQLite source had no FK enforcement; the dump was
                # already filtered, but stay defensive.
                continue
            author = str(message["userId"])
            emit(
                {
                    "kind": "message",
                    "id": message["id"],
                    "thread_id": message["threadId"],
                    "author_patient_id": None if is_physician[author] else author,
                    "author_physician_id": author if is_physician[author] else None,
                    "message": message["message"],
                    "timestamp": message["timestamp"],
                    "msg_index": message["msgIndex"],
                }
            )

    size_kb = output_path.stat().st_size / 1024
    print(f"wrote {output_path} ({size_kb:.0f} KiB)")
    for kind, count in counts.items():
        print(f"  {kind}: {count}")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(f"usage: {sys.argv[0]} <0001_init.sql> [output.jsonl.gz]")
    sql_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    build(sql_path, output_path)


if __name__ == "__main__":
    main()
