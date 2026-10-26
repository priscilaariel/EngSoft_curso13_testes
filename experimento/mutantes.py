"""Teste de mutação manual: injeta um defeito por vez no código da API e roda cada suíte.

Um mutante é "morto" quando pelo menos um teste da suíte falha. Mutantes sobreviventes
mostram o que a suíte não verifica. Uso:

    python experimento/mutantes.py                  # roda todas as suítes existentes
    python experimento/mutantes.py "P1 v1" "P2"     # roda só as suítes citadas
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SUITES = {
    "P1 v1": ["tests/p1_contrato"],
    "P1 v2": ["tests/p1_contrato", "tests/p1_contrato_v2"],
    "P2": ["tests/p2_codigo"],
    "P1 v2 + P2": ["tests/p1_contrato", "tests/p1_contrato_v2", "tests/p2_codigo"],
}

# (id, regra, arquivo, trecho original, trecho mutado, descrição do defeito)
MUTANTS = [
    ("M01", "R10", "app/provider.py", "return min(int(value), MAX_RETRY_AFTER_SECONDS)", "return int(value)",
     "Retry-After sem limite de 10 s"),
    ("M02", "R10", "app/provider.py", "wait = self.backoff_seconds * (2 ** (attempt - 1))", "wait = self.backoff_seconds",
     "backoff não dobra"),
    ("M03", "R10", "app/provider.py", "            if attempt < self.max_attempts:\n                self.sleep(wait)",
     "            self.sleep(wait)", "espera também depois da última tentativa"),
    ("M04", "R10", "app/provider.py", "            wait = self.backoff_seconds * (2 ** (attempt - 1))\n",
     "            wait = self.backoff_seconds * (2 ** (attempt - 1))\n            if attempt > 1:\n                headers[\"Idempotency-Key\"] = f\"{job_id}-{attempt}\"\n",
     "Idempotency-Key muda nas retentativas"),
    ("M05", "R10", "app/provider.py", "RETRYABLE_STATUSES = {429, 500, 502, 503, 504}", "RETRYABLE_STATUSES = {500, 502, 503, 504}",
     "429 não é tentado de novo"),
    ("M06", "R11", "app/provider.py", "RETRYABLE_STATUSES = {429, 500, 502, 503, 504}", "RETRYABLE_STATUSES = {400, 429, 500, 502, 503, 504}",
     "400 é tentado de novo"),
    ("M07", "R12", "app/provider.py", "            except httpx.TimeoutException:\n                last_error = ProviderTimeout()",
     "            except httpx.TimeoutException:\n                last_error = ProviderUnavailable()", "timeout vira provider_unavailable"),
    ("M08", "R10", "app/provider.py", "for attempt in range(1, self.max_attempts + 1):", "for attempt in range(1, self.max_attempts):",
     "uma tentativa a menos"),
    ("M09", "R13", "app/provider.py", "if not isinstance(provider_id, str) or not provider_id:", "if not isinstance(provider_id, str):",
     "id vazio é aceito"),
    ("M10", "R10", "app/provider.py", "if value.isascii() and value.isdigit():", "if True:", "Retry-After não numérico derruba a requisição"),
    ("M11", "R13", "app/provider.py", 'body.get("id") if isinstance(body, dict) else None', 'body.get("id")',
     "corpo JSON que não é objeto causa erro 500"),
    ("M12", "R13", "app/service.py", "        except sqlite3.IntegrityError:", "        except ZeroDivisionError:",
     "id repetido do Provedor deixa job preso e crédito debitado"),
    ("M13", "R22", "app/repository.py",
     "                conn.execute(\n                    \"UPDATE users SET credits = credits + ? WHERE user_id = ?\",\n                    (row[\"cost\"], row[\"user_id\"]),\n                )\n            return \"applied\"",
     "            return \"applied\"", "webhook failed não devolve o crédito"),
    ("M14", "R23", "app/repository.py", "            if row[\"status\"] in FINAL_STATUSES:\n                return \"ignored\"",
     "            if False:\n                return \"ignored\"", "webhook repetido é reaplicado"),
    ("M15", "R07", "app/repository.py", "if row[\"credits\"] < cost:", "if row[\"credits\"] <= cost:",
     "saldo igual ao custo é recusado"),
    ("M16", "R17", "app/repository.py", "ORDER BY created_at DESC, rowid DESC", "ORDER BY created_at ASC, rowid ASC",
     "listagem do mais antigo para o mais novo"),
    ("M17", "R17", "app/repository.py", "total = self.db.query(f\"SELECT COUNT(*) AS n FROM jobs {where}\", tuple(params))[0][\"n\"]",
     "total = self.db.query(\"SELECT COUNT(*) AS n FROM jobs\")[0][\"n\"]", "total ignora os filtros"),
    ("M18", "R14", "app/repository.py", "\"UPDATE users SET credits = credits + ? WHERE user_id = ?\", (row[\"cost\"], row[\"user_id\"])",
     "\"UPDATE users SET credits = credits + ? WHERE user_id = ?\", (1, row[\"user_id\"])", "reembolso parcial na falha de criação"),
    ("M19", "R14", "app/repository.py", "if row is None or row[\"status\"] in FINAL_STATUSES:", "if row is None:",
     "fail_and_refund repete reembolso em job já finalizado"),
    ("M20", "R18", "app/main.py", "if not hmac.compare_digest(expected.encode(), received.encode()):",
     "if received and not hmac.compare_digest(expected.encode(), received.encode()):", "assinatura ausente é aceita"),
    ("M21", "R19", "app/schemas.py", "not self.image_url.startswith(\"https://\")", "not self.image_url.startswith(\"http\")",
     "image_url http é aceita"),
    ("M22", "R05", "app/schemas.py", "strip_whitespace=True", "strip_whitespace=False", "prompt não é aparado"),
    ("M23", "R05", "app/schemas.py", "model_config = ConfigDict(extra=\"forbid\")\n    user_id: UserId",
     "model_config = ConfigDict(extra=\"ignore\")\n    user_id: UserId", "campos extras no job são aceitos"),
    ("M24", "R19", "app/schemas.py", "error: Optional[str] = Field(default=None, max_length=200)",
     "error: Optional[str] = Field(default=None, max_length=2000)", "limite de 200 caracteres de error vira 2000"),
    ("M25", "R02", "app/schemas.py", "credits: int = Field(ge=0, le=10000, strict=True)", "credits: int = Field(ge=0, le=10000)",
     "credits aceita texto numérico como \"10\""),
    ("M26", "R17", "app/main.py", "limit: int = Query(20, ge=1, le=100)", "limit: int = Query(20, ge=1, le=1000)",
     "limit máximo vira 1000"),
    ("M27", "R04", "app/service.py", "COSTS = {512: 1, 1024: 2, 2048: 4}", "COSTS = {512: 1, 1024: 2, 2048: 3}",
     "custo de 2048 errado"),
    ("M28", "R13", "app/provider.py", "if response.status_code == 202:", "if response.status_code in (200, 202):",
     "200 do Provedor é aceito como sucesso"),
    ("M29", "R19", "app/main.py", "return JSONResponse(status_code=422, content={\"detail\": \"invalid_payload\"})",
     "return JSONResponse(status_code=400, content={\"detail\": \"invalid_payload\"})", "payload inválido devolve 400"),
    ("M30", "R04", "app/schemas.py", "resolution: Literal[512, 1024, 2048] = 1024", "resolution: Literal[512, 1024, 2048] = 512",
     "resolução padrão errada"),
    ("M31", "R10", "app/provider.py", "MAX_RETRY_AFTER_SECONDS = 10", "MAX_RETRY_AFTER_SECONDS = 60",
     "limite do Retry-After vira 60 s"),
    ("M32", "R22", "app/repository.py", "error or \"provider_failed\"", "error or \"failed\"", "failure_reason padrão errado"),
    ("M33", "R10", "app/provider.py", "if value.isascii() and value.isdigit():", "if value.isdigit():",
     "Retry-After com dígito não ASCII derruba a requisição (defeito real achado pelo P2)"),
    ("M34", "R25", "app/service.py", "        except sqlite3.Error:", "        except ZeroDivisionError:",
     "falha do banco depois do aceite do Provedor deixa crédito preso (defeito real achado pelo P2)"),
]


def run_suite(workdir: Path, paths: list[str]) -> bool:
    """Devolve True se a suíte falhou (mutante morto)."""
    existing = [p for p in paths if (workdir / p).exists() and any((workdir / p).glob("test_*.py"))]
    if not existing:
        return False
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", *existing],
        cwd=workdir, capture_output=True, text=True, timeout=180,
    )
    return result.returncode != 0


def main() -> None:
    wanted = sys.argv[1:] or list(SUITES)
    work = Path(tempfile.mkdtemp(prefix="mutantes_"))
    copy = work / "projeto"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git", ".venv", "*.db"))

    for suite in wanted:
        if run_suite(copy, SUITES[suite]):
            raise SystemExit(f"A suíte {suite} falha no código original; corrija antes de rodar mutantes.")

    results = []
    for mid, rule, rel, old, new, desc in MUTANTS:
        target = copy / rel
        original = target.read_text(encoding="utf-8")
        if original.count(old) != 1:
            raise SystemExit(f"{mid}: trecho original encontrado {original.count(old)} vezes em {rel}")
        target.write_text(original.replace(old, new), encoding="utf-8")
        try:
            killed = {suite: run_suite(copy, SUITES[suite]) for suite in wanted}
        finally:
            target.write_text(original, encoding="utf-8")
        results.append({"id": mid, "rule": rule, "file": rel, "desc": desc, "killed": killed})
        print(mid, rule, desc, {s: ("morto" if k else "SOBREVIVEU") for s, k in killed.items()}, flush=True)

    summary = {s: sum(r["killed"][s] for r in results) for s in wanted}
    print("\nMutantes mortos por suíte (de %d):" % len(results), summary)
    out = ROOT / "experimento" / "resultados_mutacao.json"
    out.write_text(json.dumps({"total": len(results), "summary": summary, "mutants": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
