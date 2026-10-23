"""
Canonical Database & Cryptographic Audit Store
===============================================
Thread-safe persistence layer for governance audit records, canonical journal events,
and cryptographic SHA-256 state tracking.
"""
import os
import json
import sqlite3
import threading
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class CanonicalDB:
    """Thread-safe SQLite & JSONL persistence engine for canonical governance records."""
    
    def __init__(self, db_path: str = "storage/canonical_db.sqlite", journal_path: str = "storage/canonical_journal.jsonl"):
        self.db_path = db_path
        self.journal_path = journal_path
        self._lock = threading.RLock()
        
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else "storage", exist_ok=True)
        os.makedirs(os.path.dirname(self.journal_path) if os.path.dirname(self.journal_path) else "storage", exist_ok=True)
        self._init_sqlite()

    def _init_sqlite(self) -> None:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS canonical_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    trace_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    parent_event_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS review_records (
                    review_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    decision TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()

    def get_last_event(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT sequence, event_id, trace_id, actor, event_type, payload, parent_event_hash, event_hash, timestamp FROM canonical_events ORDER BY sequence DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if not row:
                return None
            return {
                "sequence": row[0],
                "event_id": row[1],
                "trace_id": row[2],
                "actor": row[3],
                "event_type": row[4],
                "payload": json.loads(row[5]),
                "parent_event_hash": row[6],
                "event_hash": row[7],
                "timestamp": row[8],
            }

    def append_event(self, event_id: str, trace_id: str, actor: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            last = self.get_last_event()
            parent_hash = last["event_hash"] if last else "0" * 64
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            payload_str = json.dumps(payload, sort_keys=True)
            hasher = hashlib.sha256()
            hasher.update(parent_hash.encode("utf-8"))
            hasher.update(event_id.encode("utf-8"))
            hasher.update(trace_id.encode("utf-8"))
            hasher.update(payload_str.encode("utf-8"))
            event_hash = hasher.hexdigest()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO canonical_events (event_id, trace_id, actor, event_type, payload, parent_event_hash, event_hash, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_id, trace_id, actor, event_type, payload_str, parent_hash, event_hash, now_iso))
            conn.commit()
            seq = cursor.lastrowid
            conn.close()

            event_obj = {
                "sequence": seq,
                "event_id": event_id,
                "trace_id": trace_id,
                "actor": actor,
                "event_type": event_type,
                "payload": payload,
                "parent_event_hash": parent_hash,
                "event_hash": event_hash,
                "timestamp": now_iso
            }

            # Append to JSONL journal
            try:
                with open(self.journal_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event_obj) + "\n")
            except Exception:
                pass

            return event_obj

    def store_review(self, review_id: str, candidate_id: str, status: str, score: int, decision: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO review_records (review_id, candidate_id, status, score, decision, created_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (review_id, candidate_id, status, score, decision, now_iso, json.dumps(payload, sort_keys=True)))
            conn.commit()
            conn.close()

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT review_id, candidate_id, status, score, decision, created_at, payload FROM review_records WHERE review_id = ?", (review_id,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                return None
            return {
                "review_id": row[0],
                "candidate_id": row[1],
                "status": row[2],
                "score": row[3],
                "decision": row[4],
                "created_at": row[5],
                "payload": json.loads(row[6])
            }
