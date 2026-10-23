"""Demostración local del DSS usando el motor y el CSV oficial del piloto.

Desde la raíz del repositorio: python -m scripts.demo_local
Solo escucha en 127.0.0.1; no consulta servicios externos ni requiere tokens.
"""

from __future__ import annotations

from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from src.dss.config import IRRIGATION_EFFICIENCY, RecommendationRequest
from src.dss.engine import recommend

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "demo" / "index.html"


def calculate(params: dict[str, list[str]]) -> dict:
    """Validate browser inputs and call the same DSS engine as Streamlit/CLI."""
    def one(name: str, default: str) -> str:
        return params.get(name, [default])[0]

    issue = date.fromisoformat(one("fecha", "2025-06-28"))
    if not date(2025, 5, 1) <= issue <= date(2025, 9, 30):
        raise ValueError("La fecha debe estar entre el 01/05/2025 y el 30/09/2025.")
    system = one("sistema", "goteo")
    if system not in IRRIGATION_EFFICIENCY:
        raise ValueError("Sistema de riego no admitido.")
    area = float(one("superficie", "1.5"))
    allocation = one("dotacion", "")
    request = RecommendationRequest(
        issue_date=issue,
        horizon_days=int(one("horizonte", "7")),
        irrigation_system=system,
        efficiency=float(one("eficiencia", str(IRRIGATION_EFFICIENCY[system]))),
        area_ha=area,
        weekly_allocation_mm=float(allocation) if allocation else None,
        mode="planificacion",
    )
    return recommend(request).to_json_dict()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        url = urlsplit(self.path)
        if url.path in {"/", "/index.html"}:
            self._send(PAGE.read_bytes(), "text/html; charset=utf-8")
        elif url.path == "/api/recommend":
            try:
                result = calculate(parse_qs(url.query))
                self._send(json.dumps(result, ensure_ascii=False).encode("utf-8"),
                           "application/json; charset=utf-8")
            except (ValueError, TypeError, OverflowError) as exc:
                self._send(json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"),
                           "application/json; charset=utf-8", status=400)
        else:
            self._send(b"Not found", "text/plain; charset=utf-8", status=404)

    def _send(self, body: bytes, mime: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    address = ("127.0.0.1", 8765)
    server = ThreadingHTTPServer(address, Handler)
    print(f"Demostración lista: http://{address[0]}:{address[1]}")
    print("Pulsa Ctrl+C para detenerla.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
