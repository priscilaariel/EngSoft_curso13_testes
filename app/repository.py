import uuid
from datetime import datetime, timezone
from typing import Optional

from app.db import Database

FINAL_STATUSES = ("succeeded", "failed")


class UserNotFound(Exception):
    pass


class InsufficientCredits(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------ usuários
    def put_user(self, user_id: str, credits: int) -> dict:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO users(user_id, credits) VALUES(?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET credits = excluded.credits",
                (user_id, credits),
            )
        return {"user_id": user_id, "credits": credits}

    def get_user(self, user_id: str) -> Optional[dict]:
        rows = self.db.query("SELECT user_id, credits FROM users WHERE user_id = ?", (user_id,))
        return dict(rows[0]) if rows else None

    # ---------------------------------------------------------------- jobs
    def create_job_debiting(self, user_id: str, prompt: str, resolution: int, cost: int) -> dict:
        job_id = str(uuid.uuid4())
        with self.db.transaction() as conn:
            row = conn.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row is None:
                raise UserNotFound(user_id)
            if row["credits"] < cost:
                raise InsufficientCredits(user_id)
            conn.execute("UPDATE users SET credits = credits - ? WHERE user_id = ?", (cost, user_id))
            now = _now()
            conn.execute(
                "INSERT INTO jobs(id, user_id, prompt, resolution, cost, status, created_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?, 'queued', ?, ?)",
                (job_id, user_id, prompt, resolution, cost, now, now),
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> Optional[dict]:
        rows = self.db.query("SELECT * FROM jobs WHERE id = ?", (job_id,))
        return dict(rows[0]) if rows else None

    def list_jobs(self, user_id: Optional[str], status: Optional[str], limit: int, offset: int) -> dict:
        conditions, params = [], []
        if user_id is not None:
            conditions.append("user_id = ?")
            params.append(user_id)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        total = self.db.query(f"SELECT COUNT(*) AS n FROM jobs {where}", tuple(params))[0]["n"]
        rows = self.db.query(
            f"SELECT * FROM jobs {where} ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?",
            tuple(params) + (limit, offset),
        )
        return {"items": [dict(r) for r in rows], "total": total}

    def mark_processing(self, job_id: str, provider_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'processing', provider_id = ?, updated_at = ? "
                "WHERE id = ? AND status = 'queued'",
                (provider_id, _now(), job_id),
            )

    def fail_and_refund(self, job_id: str, reason: str) -> bool:
        """Marca o job como failed e devolve o crédito, tudo na mesma transação.

        Devolve False (sem alterar nada) se o job não existe ou já terminou.
        """
        with self.db.transaction() as conn:
            row = conn.execute("SELECT user_id, cost, status FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None or row["status"] in FINAL_STATUSES:
                return False
            conn.execute(
                "UPDATE jobs SET status = 'failed', failure_reason = ?, updated_at = ? WHERE id = ?",
                (reason, _now(), job_id),
            )
            conn.execute(
                "UPDATE users SET credits = credits + ? WHERE user_id = ?", (row["cost"], row["user_id"])
            )
            return True

    def apply_provider_result(
        self, provider_id: str, status: str, image_url: Optional[str], error: Optional[str]
    ) -> Optional[str]:
        """Aplica o resultado do webhook. Devolve 'applied', 'ignored' ou None (id desconhecido)."""
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT id, user_id, cost, status FROM jobs WHERE provider_id = ?", (provider_id,)
            ).fetchone()
            if row is None:
                return None
            if row["status"] in FINAL_STATUSES:
                return "ignored"
            now = _now()
            if status == "succeeded":
                conn.execute(
                    "UPDATE jobs SET status = 'succeeded', image_url = ?, updated_at = ? WHERE id = ?",
                    (image_url, now, row["id"]),
                )
            else:
                conn.execute(
                    "UPDATE jobs SET status = 'failed', failure_reason = ?, updated_at = ? WHERE id = ?",
                    (error or "provider_failed", now, row["id"]),
                )
                conn.execute(
                    "UPDATE users SET credits = credits + ? WHERE user_id = ?",
                    (row["cost"], row["user_id"]),
                )
            return "applied"
