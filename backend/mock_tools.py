from __future__ import annotations

import sqlite3
from typing import Any

import sqlglot
from sqlglot import exp

from models.schemas import ToolCall


class MockTools:
    """Local-only tool implementations; these never contact external systems."""

    def __init__(self) -> None:
        self.database = sqlite3.connect(":memory:", check_same_thread=False)
        self.database.row_factory = sqlite3.Row
        self.database.executescript(
            """
            CREATE TABLE customers (id TEXT PRIMARY KEY, name TEXT, tier TEXT);
            CREATE TABLE payroll (employee_id TEXT PRIMARY KEY, salary INTEGER);
            INSERT INTO customers VALUES
                ('C-102', 'Demo Customer', 'standard'),
                ('C-204', 'Sample Account', 'enterprise');
            INSERT INTO payroll VALUES ('E-001', 0);
            """
        )
        self.outbox: list[dict[str, str]] = []
        self.crm_notes: list[dict[str, str | None]] = []

    def execute(self, call: ToolCall) -> dict[str, Any]:
        args = call.arguments
        if call.tool_name == "send_email":
            self.outbox.append(
                {
                    "recipient": str(args["recipient"]),
                    "subject": str(args.get("subject", "")),
                    "body": str(args.get("body", "")),
                }
            )
            return {"mocked": True, "outbox_count": len(self.outbox)}
        if call.tool_name == "query_db":
            statements = sqlglot.parse(str(args["sql"]), read="sqlite")
            if (
                len(statements) != 1
                or statements[0] is None
                or statements[0].key.upper()
                not in {"SELECT", "INSERT", "UPDATE", "DELETE"}
            ):
                raise ValueError("Mock database accepts one data statement only")
            statement = statements[0]
            if (
                statement is not None
                and statement.key.upper() in {"UPDATE", "DELETE"}
                and statement.find(exp.Where) is None
            ):
                raise ValueError("Mock database requires WHERE for updates and deletes")
            cursor = self.database.execute(str(args["sql"]))
            return {
                "mocked": True,
                "rows": [dict(row) for row in cursor.fetchmany(50)],
            }
        if call.tool_name == "update_crm":
            self.crm_notes.extend(args["updates"])
            return {"mocked": True, "updated_records": len(args["updates"])}
        if call.tool_name == "read_file":
            return {
                "mocked": True,
                "path": str(args["path"]),
                "content": "Synthetic demo file content.",
            }
        if call.tool_name == "http_request":
            return {
                "mocked": True,
                "url": str(args["url"]),
                "note": "No network request was made.",
            }
        raise ValueError(f"Unsupported mock tool: {call.tool_name}")
