"""Smoke-test waitlist signup, launch mail, and founder promotion."""

from __future__ import annotations

from pathlib import Path
import json
import os
import sqlite3
import tempfile
import unittest

import mailer


class FounderMailerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "rated.db"
        self.outbox = Path(self.temp.name) / "outbox.jsonl"
        mailer.OUTBOX = self.outbox
        self.connection = sqlite3.connect(self.db)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                profile_picture TEXT,
                is_founder INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        mailer.init_founder_schema(self.connection)
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        self.temp.cleanup()

    def test_promote_sets_gold_star_founder(self):
        self.connection.execute(
            """
            INSERT INTO waitlist (username, email, password_hash, updates_opt_in)
            VALUES (?, ?, ?, 1)
            """,
            ("earlyfan", "fan@rated.test", "hash"),
        )
        self.connection.commit()
        row = self.connection.execute("SELECT * FROM waitlist").fetchone()
        user_id = mailer.promote_waitlist_row(self.connection, row)
        self.connection.commit()
        user = self.connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        self.assertEqual(user["username"], "earlyfan")
        self.assertEqual(user["is_founder"], 1)
        self.assertTrue(mailer.public_user(user)["is_founder"])

    def test_welcome_email_writes_outbox(self):
        sent = mailer.send_waitlist_email("fan@rated.test", "earlyfan", "welcome")
        self.assertFalse(sent)
        lines = self.outbox.read_text(encoding="utf-8").strip().splitlines()
        payload = json.loads(lines[-1])
        self.assertEqual(payload["kind"], "welcome")
        self.assertIn("gold star", payload["text"].lower())

    def test_seat_display_starts_at_4781_then_recalibrates_at_5000(self):
        shown = mailer.displayed_seat_count(self.connection)
        self.assertEqual(shown["count"], 4781)
        self.assertFalse(shown["recalibrated"])

        self.connection.execute(
            """
            INSERT INTO waitlist (username, email, password_hash)
            VALUES ('one', 'one@rated.test', 'hash')
            """
        )
        bumped = mailer.bump_seat_display(self.connection)
        self.assertEqual(bumped["count"], 4782)
        self.assertEqual(bumped["real"], 1)

        self.connection.execute("DELETE FROM waitlist")
        for index in range(5000):
            self.connection.execute(
                """
                INSERT INTO waitlist (username, email, password_hash)
                VALUES (?, ?, 'hash')
                """,
                (f"user{index}", f"user{index}@rated.test"),
            )
        snapped = mailer.displayed_seat_count(self.connection)
        self.assertEqual(snapped["real"], 5000)
        self.assertEqual(snapped["count"], 5000)
        self.assertTrue(snapped["recalibrated"])

    def test_launch_sets_flag_and_mails(self):
        mailer.set_launched(self.connection)
        self.connection.commit()
        self.assertTrue(mailer.is_launched(self.connection))
        mailer.send_waitlist_email("fan@rated.test", "earlyfan", "launch")
        payload = json.loads(self.outbox.read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertEqual(payload["subject"], "RATED is live. Your seat is waiting.")


if __name__ == "__main__":
    unittest.main()
