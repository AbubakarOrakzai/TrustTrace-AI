from __future__ import annotations

import base64
import binascii
import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from models.schemas import AuditEvent, ToolCall, Verdict


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class AuditLedger:
    def __init__(self, database_path: Path, key_path: Path) -> None:
        self.database_path = database_path
        self.key_path = key_path
        self._lock = threading.Lock()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._private_key = self._load_or_create_key()
        self._public_key = self._private_key.public_key()
        public_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.fingerprint = hashlib.sha256(public_bytes).hexdigest()
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS audit_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    fingerprint TEXT NOT NULL
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _load_or_create_key(self) -> Ed25519PrivateKey:
        if self.key_path.exists():
            key = serialization.load_pem_private_key(
                self.key_path.read_bytes(), password=None
            )
            if not isinstance(key, Ed25519PrivateKey):
                raise ValueError("Audit signing key must be Ed25519")
            return key
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        key = Ed25519PrivateKey.generate()
        encoded = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        self.key_path.write_bytes(encoded)
        self.key_path.chmod(0o600)
        return key

    def append(
        self,
        call: ToolCall,
        verdict: Verdict,
        policy_version: str,
        model_id: str = "deterministic-only",
    ) -> AuditEvent:
        with self._lock, self._connect() as connection:
            previous = connection.execute(
                "SELECT seq, event_hash FROM audit_events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            seq = 1 if previous is None else int(previous["seq"]) + 1
            prev_hash = "0" * 64 if previous is None else str(previous["event_hash"])
            event_id = str(uuid4())
            timestamp = datetime.now(timezone.utc)
            payload = {
                "seq": seq,
                "event_id": event_id,
                "timestamp": timestamp.isoformat(),
                "tool_call": call.model_dump(mode="json"),
                "verdict": verdict.model_dump(mode="json"),
                "policy_version": policy_version,
                "model_id": model_id,
                "public_key_fingerprint": self.fingerprint,
            }
            event_hash = hashlib.sha256(
                (canonical_json(payload) + prev_hash).encode("utf-8")
            ).hexdigest()
            signature = base64.b64encode(
                self._private_key.sign(event_hash.encode("ascii"))
            ).decode("ascii")
            connection.execute(
                """INSERT INTO audit_events
                (seq, event_id, payload, prev_hash, event_hash, signature, fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    seq,
                    event_id,
                    canonical_json(payload),
                    prev_hash,
                    event_hash,
                    signature,
                    self.fingerprint,
                ),
            )
        return AuditEvent(
            **{
                **payload,
                "timestamp": timestamp,
                "prev_hash": prev_hash,
                "hash": event_hash,
                "signature": signature,
            }
        )

    def list_events(self, limit: int = 100) -> list[AuditEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY seq DESC LIMIT ?", (limit,)
            ).fetchall()
        events = []
        for row in reversed(rows):
            payload = json.loads(row["payload"])
            events.append(
                AuditEvent(
                    **{
                        **payload,
                        "timestamp": datetime.fromisoformat(payload["timestamp"]),
                        "prev_hash": row["prev_hash"],
                        "hash": row["event_hash"],
                        "signature": row["signature"],
                    }
                )
            )
        return events

    def get_event(self, event_id: str) -> AuditEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM audit_events WHERE event_id = ?", (event_id,)
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload"])
        return AuditEvent(
            **{
                **payload,
                "timestamp": datetime.fromisoformat(payload["timestamp"]),
                "prev_hash": row["prev_hash"],
                "hash": row["event_hash"],
                "signature": row["signature"],
            }
        )

    def verify(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY seq ASC"
            ).fetchall()
        previous_hash = "0" * 64
        for expected_seq, row in enumerate(rows, start=1):
            try:
                payload = json.loads(row["payload"])
            except json.JSONDecodeError:
                return {"valid": False, "broken_at_seq": expected_seq}
            expected_hash = hashlib.sha256(
                (canonical_json(payload) + previous_hash).encode("utf-8")
            ).hexdigest()
            try:
                Ed25519PublicKey.from_public_bytes(
                    self._public_key.public_bytes(
                        encoding=serialization.Encoding.Raw,
                        format=serialization.PublicFormat.Raw,
                    )
                ).verify(
                    base64.b64decode(row["signature"], validate=True),
                    row["event_hash"].encode("ascii"),
                )
            except (InvalidSignature, ValueError, TypeError, binascii.Error):
                return {"valid": False, "broken_at_seq": expected_seq}
            if (
                int(row["seq"]) != expected_seq
                or row["prev_hash"] != previous_hash
                or row["event_hash"] != expected_hash
                or row["fingerprint"] != self.fingerprint
                or payload.get("public_key_fingerprint") != self.fingerprint
            ):
                return {"valid": False, "broken_at_seq": expected_seq}
            previous_hash = row["event_hash"]
        return {
            "valid": True,
            "broken_at_seq": None,
            "events_verified": len(rows),
            "public_key_fingerprint": self.fingerprint,
        }

    def report(self) -> dict[str, Any]:
        events = self.list_events(limit=10000)
        counts = {"ALLOW": 0, "REVIEW": 0, "BLOCK": 0}
        for event in events:
            counts[event.verdict.decision] += 1
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "event_count": len(events),
            "decisions": counts,
            "chain_verification": self.verify(),
            "events": [event.model_dump(mode="json") for event in events],
            "disclaimer": (
                "Evidence aligned with SOC 2 / AIUC-1 control concepts only. "
                "This report does not establish certification or compliance."
            ),
        }
