# Puente Telegram → MetaTrader 4 — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Leer señales de trading de un canal de Telegram y abrir automáticamente 3 trades (TP1/TP2/TP3, mismo SL) en una o más cuentas MetaTrader 4 del mismo broker.

**Architecture:** Proceso Python asíncrono. Telethon (cuenta de usuario, solo lectura) recibe mensajes → parser → guardas de riesgo → router que hace fan-out a cada cuenta → puente por archivos (JSON) que un Expert Advisor MQL4 lee dentro de cada terminal MT4 (bajo Wine). Notificaciones a Mensajes Guardados de Telegram. La tolerancia de pips la valida el EA (tiene el precio en vivo); el resto de guardas son lógica pura testeable.

**Tech Stack:** Python 3.11+, Telethon, PyYAML, pytest. Expert Advisor en MQL4.

**Identidad git de este repo (personal):** `MichaelBonilla93 <mdbonillam@gmail.com>`. Nunca usar correo de trabajo. No hacer `push` sin confirmación explícita; solo a GitHub personal `@MichaelBonilla93`.

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---------|-----------------|
| `pyproject.toml` | Deps y config de pytest |
| `.gitignore` | Excluir `.env`, `*.session`, `state/`, etc. |
| `.env.example` | Plantilla de secretos Telethon |
| `config.yaml` | Cuentas + parámetros globales (sin secretos) |
| `src/models.py` | Dataclasses: `Direction`, `Signal`, `Account`, `OrderRequest`, `OrderResult` |
| `src/signal_parser.py` | Texto → `Signal` (o `None`) |
| `src/config.py` | Carga `config.yaml` + `.env` → objetos |
| `src/risk_guard.py` | Kill-switch, máx trades, coherencia SL/TP |
| `src/order_router.py` | `Signal` → 3×N `OrderRequest` (fan-out cuentas) |
| `src/file_bridge.py` | Escribe comando JSON, espera respuesta del EA |
| `src/notifier.py` | Formatea y envía resúmenes a Mensajes Guardados |
| `src/telegram_listener.py` | Telethon + dedup; orquesta el pipeline por mensaje |
| `src/main.py` | Arranque y cableado |
| `mt4/mt4_bridge.mq4` | Expert Advisor: lee comandos, ejecuta OrderSend, responde |
| `tests/*` | Suites pytest por componente |

---

## Task 1: Scaffolding del proyecto

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Crear `pyproject.toml`**

```toml
[project]
name = "telegram-mt4-bridge"
version = "0.1.0"
description = "Puente de señales de Telegram a MetaTrader 4"
requires-python = ">=3.11"
dependencies = [
    "telethon>=1.36",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.pytest.ini_options]
pythonpath = ["."]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Crear `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
venv/
.env
*.session
*.session-journal
state/
.pytest_cache/
.DS_Store
```

- [ ] **Step 3: Crear `.env.example`**

```dotenv
# Credenciales de Telethon (https://my.telegram.org -> API development tools)
TG_API_ID=123456
TG_API_HASH=abcdef0123456789abcdef0123456789
TG_PHONE=+57XXXXXXXXXX
# Identificador del canal: @username, id numérico, o título exacto
TG_CHANNEL=FOREX PIPS PREMIUM
```

- [ ] **Step 4: Crear paquetes vacíos**

Crear `src/__init__.py` y `tests/__init__.py` como archivos vacíos.

- [ ] **Step 5: Instalar dependencias**

Run: `cd /Users/michael.bonilla/dev/telegram-mt4-bridge && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
Expected: instala telethon, pyyaml, pytest sin errores.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: scaffolding del proyecto (deps, gitignore, env.example)"
```

---

## Task 2: Modelos de dominio

**Files:**
- Create: `src/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_models.py
from src.models import Direction, Signal, Account, OrderRequest, OrderResult


def test_direction_from_text():
    assert Direction.from_text("BUY") == Direction.BUY
    assert Direction.from_text("sell") == Direction.SELL


def test_signal_holds_three_take_profits():
    sig = Signal(
        symbol="GBPJPY",
        direction=Direction.BUY,
        entry=214.50,
        stop_loss=213.85,
        take_profits=[214.70, 215.00, 215.50],
    )
    assert sig.symbol == "GBPJPY"
    assert sig.direction is Direction.BUY
    assert len(sig.take_profits) == 3
    assert sig.take_profits[0] == 214.70


def test_account_defaults():
    acc = Account(name="DEMO1", mailbox_path="/tmp/mt4", lot=0.01)
    assert acc.symbol_suffix == ""
    assert acc.active is True
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'src.models'"

- [ ] **Step 3: Escribir la implementación mínima**

```python
# src/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"

    @classmethod
    def from_text(cls, text: str) -> "Direction":
        return cls(text.strip().upper())


@dataclass
class Signal:
    symbol: str
    direction: Direction
    entry: float
    stop_loss: float
    take_profits: list[float]
    raw_text: str = ""
    message_id: int | None = None


@dataclass
class Account:
    name: str
    mailbox_path: str
    lot: float
    symbol_suffix: str = ""
    active: bool = True


@dataclass
class OrderRequest:
    account: str
    symbol: str          # ya incluye el sufijo del broker
    direction: Direction
    lot: float
    stop_loss: float
    take_profit: float
    entry_ref: float
    tolerance_pips: float
    comment: str = ""


@dataclass
class OrderResult:
    success: bool
    ticket: int | None = None
    price: float | None = None
    error: str | None = None
    account: str = ""
    comment: str = ""
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: modelos de dominio (Signal, Account, OrderRequest, OrderResult)"
```

---

## Task 3: Parser de señales (núcleo, TDD exhaustivo)

**Files:**
- Create: `src/signal_parser.py`
- Test: `tests/test_signal_parser.py`

- [ ] **Step 1: Escribir los tests que fallan (ejemplos reales + basura)**

```python
# tests/test_signal_parser.py
from src.models import Direction
from src.signal_parser import parse_signal

GBPJPY_BUY = """GBPJPY
🔵📊 BUY 214.50

TP: 1️⃣ 214.70
TP: 2️⃣ 215.00
TP: 3️⃣ 215.50
SL: ❌ 213.85"""

GBPJPY_SELL = """GBPJPY
🔴📊 SELL 214.50

TP: 1️⃣ 214.30
TP: 2️⃣ 214.00
TP: 3️⃣ 213.50
SL: ❌ 215.15"""

CHFJPY_BUY = """CHFJPY
🔵📊 BUY 202.95

TP: 1️⃣ 203.15
TP: 2️⃣ 203.45
TP: 3️⃣ 203.95
SL: ❌ 202.30"""


def test_parses_buy_signal():
    sig = parse_signal(GBPJPY_BUY)
    assert sig is not None
    assert sig.symbol == "GBPJPY"
    assert sig.direction is Direction.BUY
    assert sig.entry == 214.50
    assert sig.stop_loss == 213.85
    assert sig.take_profits == [214.70, 215.00, 215.50]


def test_parses_sell_signal():
    sig = parse_signal(GBPJPY_SELL)
    assert sig is not None
    assert sig.direction is Direction.SELL
    assert sig.entry == 214.50
    assert sig.stop_loss == 215.15
    assert sig.take_profits == [214.30, 214.00, 213.50]


def test_parses_different_symbol():
    sig = parse_signal(CHFJPY_BUY)
    assert sig.symbol == "CHFJPY"
    assert sig.take_profits[2] == 203.95


def test_keeps_raw_text():
    sig = parse_signal(GBPJPY_BUY)
    assert sig.raw_text == GBPJPY_BUY


def test_ignores_non_signal_message():
    assert parse_signal("Buenos días traders! Hoy el mercado está volátil 🚀") is None


def test_ignores_message_without_sl():
    text = "GBPJPY\n🔵📊 BUY 214.50\nTP: 1️⃣ 214.70"
    assert parse_signal(text) is None


def test_ignores_empty_message():
    assert parse_signal("") is None
    assert parse_signal(None) is None
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `.venv/bin/pytest tests/test_signal_parser.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'src.signal_parser'"

- [ ] **Step 3: Escribir la implementación**

```python
# src/signal_parser.py
from __future__ import annotations

import re

from src.models import Direction, Signal

_NUM = r"(\d+(?:\.\d+)?)"
_DIRECTION_RE = re.compile(rf"\b(BUY|SELL)\b\D*?{_NUM}", re.IGNORECASE)
_SL_RE = re.compile(rf"SL\b\D*?{_NUM}", re.IGNORECASE)
_TP_RE = re.compile(rf"TP\b\D*?{_NUM}", re.IGNORECASE)
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{3,8}$")


def _find_symbol(lines: list[str]) -> str | None:
    """El símbolo es la primera línea tipo ticker (ej. GBPJPY, XAUUSD, US30)."""
    for line in lines:
        token = line.strip().upper()
        if _SYMBOL_RE.match(token) and not token.startswith(("BUY", "SELL")):
            return token
    return None


def parse_signal(text: str | None) -> Signal | None:
    """Convierte el texto de un mensaje en un Signal, o None si no es señal válida."""
    if not text or not text.strip():
        return None

    lines = [ln for ln in text.splitlines() if ln.strip()]

    dir_match = _DIRECTION_RE.search(text)
    sl_match = _SL_RE.search(text)
    tps = [float(m) for m in _TP_RE.findall(text)]
    symbol = _find_symbol(lines)

    # Una señal válida necesita: símbolo, dirección+entrada, SL y al menos 3 TP.
    if not (symbol and dir_match and sl_match and len(tps) >= 3):
        return None

    direction = Direction.from_text(dir_match.group(1))
    entry = float(dir_match.group(2))
    stop_loss = float(sl_match.group(1))

    return Signal(
        symbol=symbol,
        direction=direction,
        entry=entry,
        stop_loss=stop_loss,
        take_profits=tps[:3],
        raw_text=text,
    )
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `.venv/bin/pytest tests/test_signal_parser.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/signal_parser.py tests/test_signal_parser.py
git commit -m "feat: parser de señales con TDD sobre ejemplos reales"
```

---

## Task 4: Carga de configuración

**Files:**
- Create: `src/config.py`
- Create: `config.yaml`
- Test: `tests/test_config.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_config.py
import textwrap

from src.config import load_config
from src.models import Account


def test_loads_accounts_and_globals(tmp_path):
    yaml_text = textwrap.dedent("""
        trading_enabled: true
        max_open_trades: 9
        tolerance_pips: 20
        accounts:
          - name: DEMO1
            mailbox_path: /tmp/mt4_demo1
            lot: 0.01
            symbol_suffix: ""
            active: true
          - name: DEMO2
            mailbox_path: /tmp/mt4_demo2
            lot: 0.02
            symbol_suffix: ".r"
            active: false
    """)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_text)

    cfg = load_config(str(cfg_file))

    assert cfg.trading_enabled is True
    assert cfg.max_open_trades == 9
    assert cfg.tolerance_pips == 20
    assert len(cfg.accounts) == 2
    assert isinstance(cfg.accounts[0], Account)
    assert cfg.accounts[0].name == "DEMO1"
    assert cfg.accounts[1].symbol_suffix == ".r"


def test_active_accounts_filters_inactive(tmp_path):
    yaml_text = textwrap.dedent("""
        trading_enabled: true
        max_open_trades: 9
        tolerance_pips: 20
        accounts:
          - name: A
            mailbox_path: /tmp/a
            lot: 0.01
            active: true
          - name: B
            mailbox_path: /tmp/b
            lot: 0.01
            active: false
    """)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_text)

    cfg = load_config(str(cfg_file))
    active = cfg.active_accounts()
    assert [a.name for a in active] == ["A"]
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'src.config'"

- [ ] **Step 3: Escribir la implementación**

```python
# src/config.py
from __future__ import annotations

import os
from dataclasses import dataclass

import yaml

from src.models import Account


@dataclass
class Config:
    trading_enabled: bool
    max_open_trades: int
    tolerance_pips: float
    accounts: list[Account]

    def active_accounts(self) -> list[Account]:
        return [a for a in self.accounts if a.active]


def load_config(path: str = "config.yaml") -> Config:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    accounts = [
        Account(
            name=a["name"],
            mailbox_path=a["mailbox_path"],
            lot=float(a["lot"]),
            symbol_suffix=a.get("symbol_suffix", ""),
            active=a.get("active", True),
        )
        for a in data.get("accounts", [])
    ]

    return Config(
        trading_enabled=bool(data.get("trading_enabled", True)),
        max_open_trades=int(data.get("max_open_trades", 9)),
        tolerance_pips=float(data.get("tolerance_pips", 20)),
        accounts=accounts,
    )


@dataclass
class Secrets:
    api_id: int
    api_hash: str
    phone: str
    channel: str


def load_secrets() -> Secrets:
    """Lee secretos desde variables de entorno (.env cargado por el caller)."""
    return Secrets(
        api_id=int(os.environ["TG_API_ID"]),
        api_hash=os.environ["TG_API_HASH"],
        phone=os.environ["TG_PHONE"],
        channel=os.environ["TG_CHANNEL"],
    )
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Crear `config.yaml` real de ejemplo**

```yaml
# config.yaml — configuración SIN secretos (los secretos van en .env)
trading_enabled: true        # interruptor on/off global del trading
max_open_trades: 9           # máx. posiciones simultáneas (3 TP x 3 cuentas = 9)
tolerance_pips: 20           # descarta si el precio se alejó más de esto de la señal

accounts:
  - name: DEMO1
    # Carpeta buzón DENTRO de MQL4/Files del terminal (ver README)
    mailbox_path: /ruta/al/terminal/MQL4/Files/bridge
    lot: 0.01
    symbol_suffix: ""        # ej. ".r" o "pro" si el broker usa sufijos
    active: true
```

- [ ] **Step 6: Commit**

```bash
git add src/config.py config.yaml tests/test_config.py
git commit -m "feat: carga de configuración (config.yaml + secretos .env)"
```

---

## Task 5: Guardas de riesgo

**Files:**
- Create: `src/risk_guard.py`
- Test: `tests/test_risk_guard.py`

Nota: la tolerancia de pips NO se valida aquí (la valida el EA con precio en vivo). Aquí: kill-switch, máx trades y coherencia SL/TP.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_risk_guard.py
from src.models import Direction, Signal
from src.risk_guard import evaluate

BUY = Signal("GBPJPY", Direction.BUY, 214.50, 213.85, [214.70, 215.00, 215.50])
SELL = Signal("GBPJPY", Direction.SELL, 214.50, 215.15, [214.30, 214.00, 213.50])


def test_rejects_when_trading_disabled():
    ok, reason = evaluate(BUY, trading_enabled=False, max_open_trades=9, current_open=0)
    assert ok is False
    assert "desactivado" in reason.lower()


def test_rejects_when_max_trades_reached():
    # 3 nuevas órdenes no caben si ya hay 7 y el máx es 9
    ok, reason = evaluate(BUY, trading_enabled=True, max_open_trades=9, current_open=7)
    assert ok is False
    assert "máximo" in reason.lower()


def test_rejects_buy_with_sl_above_entry():
    bad = Signal("GBPJPY", Direction.BUY, 214.50, 215.00, [214.70, 215.00, 215.50])
    ok, reason = evaluate(bad, trading_enabled=True, max_open_trades=9, current_open=0)
    assert ok is False
    assert "sl" in reason.lower()


def test_rejects_sell_with_sl_below_entry():
    bad = Signal("GBPJPY", Direction.SELL, 214.50, 213.00, [214.30, 214.00, 213.50])
    ok, reason = evaluate(bad, trading_enabled=True, max_open_trades=9, current_open=0)
    assert ok is False


def test_accepts_valid_buy():
    ok, reason = evaluate(BUY, trading_enabled=True, max_open_trades=9, current_open=0)
    assert ok is True
    assert reason == ""


def test_accepts_valid_sell():
    ok, _ = evaluate(SELL, trading_enabled=True, max_open_trades=9, current_open=0)
    assert ok is True
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/pytest tests/test_risk_guard.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'src.risk_guard'"

- [ ] **Step 3: Escribir la implementación**

```python
# src/risk_guard.py
from __future__ import annotations

from src.models import Direction, Signal

ORDERS_PER_SIGNAL = 3  # una por cada TP


def evaluate(
    signal: Signal,
    *,
    trading_enabled: bool,
    max_open_trades: int,
    current_open: int,
) -> tuple[bool, str]:
    """Devuelve (aprobado, motivo). motivo == '' cuando se aprueba."""
    if not trading_enabled:
        return False, "Trading desactivado (kill-switch off)"

    if current_open + ORDERS_PER_SIGNAL > max_open_trades:
        return False, (
            f"Se alcanzaría el máximo de trades "
            f"({current_open}+{ORDERS_PER_SIGNAL} > {max_open_trades})"
        )

    if signal.direction is Direction.BUY:
        if signal.stop_loss >= signal.entry:
            return False, "BUY incoherente: SL por encima o igual a la entrada"
        if any(tp <= signal.entry for tp in signal.take_profits):
            return False, "BUY incoherente: algún TP por debajo o igual a la entrada"
    else:  # SELL
        if signal.stop_loss <= signal.entry:
            return False, "SELL incoherente: SL por debajo o igual a la entrada"
        if any(tp >= signal.entry for tp in signal.take_profits):
            return False, "SELL incoherente: algún TP por encima o igual a la entrada"

    return True, ""
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.venv/bin/pytest tests/test_risk_guard.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/risk_guard.py tests/test_risk_guard.py
git commit -m "feat: guardas de riesgo (kill-switch, máx trades, coherencia SL/TP)"
```

---

## Task 6: Router de órdenes (fan-out a cuentas)

**Files:**
- Create: `src/order_router.py`
- Test: `tests/test_order_router.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_order_router.py
from src.models import Account, Direction, Signal
from src.order_router import build_orders

BUY = Signal("GBPJPY", Direction.BUY, 214.50, 213.85, [214.70, 215.00, 215.50])


def test_builds_three_orders_per_account():
    accounts = [Account("DEMO1", "/tmp/a", lot=0.01)]
    orders = build_orders(BUY, accounts, tolerance_pips=20)
    assert len(orders) == 3
    assert [o.take_profit for o in orders] == [214.70, 215.00, 215.50]
    assert all(o.stop_loss == 213.85 for o in orders)
    assert all(o.lot == 0.01 for o in orders)
    assert all(o.direction is Direction.BUY for o in orders)
    assert all(o.entry_ref == 214.50 for o in orders)
    assert all(o.tolerance_pips == 20 for o in orders)


def test_applies_symbol_suffix_per_account():
    accounts = [Account("DEMO2", "/tmp/b", lot=0.02, symbol_suffix=".r")]
    orders = build_orders(BUY, accounts, tolerance_pips=20)
    assert all(o.symbol == "GBPJPY.r" for o in orders)
    assert all(o.lot == 0.02 for o in orders)


def test_fans_out_to_multiple_accounts():
    accounts = [
        Account("DEMO1", "/tmp/a", lot=0.01),
        Account("DEMO2", "/tmp/b", lot=0.02, symbol_suffix=".r"),
    ]
    orders = build_orders(BUY, accounts, tolerance_pips=20)
    assert len(orders) == 6  # 3 TP x 2 cuentas
    assert {o.account for o in orders} == {"DEMO1", "DEMO2"}


def test_comment_marks_tp_level():
    accounts = [Account("DEMO1", "/tmp/a", lot=0.01)]
    orders = build_orders(BUY, accounts, tolerance_pips=20)
    assert orders[0].comment == "TG TP1"
    assert orders[2].comment == "TG TP3"
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/pytest tests/test_order_router.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'src.order_router'"

- [ ] **Step 3: Escribir la implementación**

```python
# src/order_router.py
from __future__ import annotations

from src.models import Account, OrderRequest, Signal


def build_orders(
    signal: Signal,
    accounts: list[Account],
    *,
    tolerance_pips: float,
) -> list[OrderRequest]:
    """Genera 3 OrderRequest (TP1/TP2/TP3) por cada cuenta dada."""
    orders: list[OrderRequest] = []
    for account in accounts:
        symbol = f"{signal.symbol}{account.symbol_suffix}"
        for i, tp in enumerate(signal.take_profits, start=1):
            orders.append(
                OrderRequest(
                    account=account.name,
                    symbol=symbol,
                    direction=signal.direction,
                    lot=account.lot,
                    stop_loss=signal.stop_loss,
                    take_profit=tp,
                    entry_ref=signal.entry,
                    tolerance_pips=tolerance_pips,
                    comment=f"TG TP{i}",
                )
            )
    return orders
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.venv/bin/pytest tests/test_order_router.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/order_router.py tests/test_order_router.py
git commit -m "feat: router de órdenes con fan-out a cuentas y sufijo de símbolo"
```

---

## Task 7: Puente por archivos (Python ↔ EA)

**Files:**
- Create: `src/file_bridge.py`
- Test: `tests/test_file_bridge.py`

Contrato de archivos: Python escribe `<mailbox>/commands/<id>.json`. El EA lo procesa, escribe `<mailbox>/responses/<id>.json` y borra el comando. Python hace polling sobre la carpeta `responses`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_file_bridge.py
import json
import threading
import time
from pathlib import Path

from src.file_bridge import FileBridge
from src.models import Direction, OrderRequest

REQ = OrderRequest(
    account="DEMO1", symbol="GBPJPY", direction=Direction.BUY, lot=0.01,
    stop_loss=213.85, take_profit=214.70, entry_ref=214.50,
    tolerance_pips=20, comment="TG TP1",
)


def _fake_ea(mailbox: Path, ticket: int = 5001):
    """Simula al EA: lee el comando, escribe respuesta, borra comando."""
    commands = mailbox / "commands"
    responses = mailbox / "responses"
    for _ in range(50):
        files = list(commands.glob("*.json"))
        if files:
            cmd_file = files[0]
            cmd = json.loads(cmd_file.read_text())
            (responses / cmd_file.name).write_text(json.dumps({
                "id": cmd["id"], "success": True,
                "ticket": ticket, "price": 214.52, "error": None,
            }))
            cmd_file.unlink()
            return
        time.sleep(0.02)


def test_command_roundtrip(tmp_path):
    bridge = FileBridge(str(tmp_path), timeout_s=3)
    t = threading.Thread(target=_fake_ea, args=(tmp_path,))
    t.start()

    result = bridge.send(REQ)
    t.join()

    assert result.success is True
    assert result.ticket == 5001
    assert result.price == 214.52
    assert result.account == "DEMO1"
    assert result.comment == "TG TP1"


def test_command_file_has_expected_fields(tmp_path):
    bridge = FileBridge(str(tmp_path), timeout_s=1)
    # No arrancamos EA: el comando queda escrito y luego da timeout
    bridge.send(REQ)  # devolverá error por timeout
    written = list((tmp_path / "commands").glob("*.json"))
    assert len(written) == 1
    cmd = json.loads(written[0].read_text())
    assert cmd["action"] == "OPEN"
    assert cmd["symbol"] == "GBPJPY"
    assert cmd["direction"] == "BUY"
    assert cmd["lot"] == 0.01
    assert cmd["stop_loss"] == 213.85
    assert cmd["take_profit"] == 214.70
    assert cmd["tolerance_pips"] == 20


def test_timeout_returns_error(tmp_path):
    bridge = FileBridge(str(tmp_path), timeout_s=0.3)
    result = bridge.send(REQ)
    assert result.success is False
    assert "timeout" in result.error.lower()
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/pytest tests/test_file_bridge.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'src.file_bridge'"

- [ ] **Step 3: Escribir la implementación**

```python
# src/file_bridge.py
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from src.models import OrderRequest, OrderResult


class FileBridge:
    """Puente por archivos hacia un terminal MT4 (un buzón por cuenta)."""

    def __init__(self, mailbox_path: str, timeout_s: float = 10.0, poll_s: float = 0.1):
        self.mailbox = Path(mailbox_path)
        self.commands = self.mailbox / "commands"
        self.responses = self.mailbox / "responses"
        self.timeout_s = timeout_s
        self.poll_s = poll_s
        self.commands.mkdir(parents=True, exist_ok=True)
        self.responses.mkdir(parents=True, exist_ok=True)

    def send(self, req: OrderRequest) -> OrderResult:
        cmd_id = uuid.uuid4().hex
        payload = {
            "id": cmd_id,
            "action": "OPEN",
            "symbol": req.symbol,
            "direction": req.direction.value,
            "lot": req.lot,
            "stop_loss": req.stop_loss,
            "take_profit": req.take_profit,
            "entry_ref": req.entry_ref,
            "tolerance_pips": req.tolerance_pips,
            "comment": req.comment,
        }
        # Escritura atómica: escribir a .tmp y renombrar.
        tmp = self.commands / f"{cmd_id}.json.tmp"
        final = self.commands / f"{cmd_id}.json"
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.rename(final)

        response_file = self.responses / f"{cmd_id}.json"
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            if response_file.exists():
                data = json.loads(response_file.read_text(encoding="utf-8"))
                response_file.unlink(missing_ok=True)
                return OrderResult(
                    success=bool(data.get("success")),
                    ticket=data.get("ticket"),
                    price=data.get("price"),
                    error=data.get("error"),
                    account=req.account,
                    comment=req.comment,
                )
            time.sleep(self.poll_s)

        return OrderResult(
            success=False,
            error=f"Timeout: el EA no respondió en {self.timeout_s}s",
            account=req.account,
            comment=req.comment,
        )
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.venv/bin/pytest tests/test_file_bridge.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/file_bridge.py tests/test_file_bridge.py
git commit -m "feat: puente por archivos JSON con timeout y escritura atómica"
```

---

## Task 8: Notificador (formato puro + envío)

**Files:**
- Create: `src/notifier.py`
- Test: `tests/test_notifier.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_notifier.py
from src.models import Direction, OrderResult, Signal
from src.notifier import format_executed, format_discarded

BUY = Signal("GBPJPY", Direction.BUY, 214.50, 213.85, [214.70, 215.00, 215.50])


def test_format_discarded_includes_reason():
    msg = format_discarded(BUY, "Trading desactivado (kill-switch off)")
    assert "GBPJPY" in msg
    assert "descart" in msg.lower()
    assert "kill-switch" in msg.lower()


def test_format_executed_lists_tickets_and_failures():
    results = [
        OrderResult(success=True, ticket=1, price=214.52, account="DEMO1", comment="TG TP1"),
        OrderResult(success=True, ticket=2, price=214.52, account="DEMO1", comment="TG TP2"),
        OrderResult(success=False, error="price moved", account="DEMO1", comment="TG TP3"),
    ]
    msg = format_executed(BUY, results)
    assert "GBPJPY" in msg
    assert "BUY" in msg
    assert "#1" in msg and "#2" in msg
    assert "TP3" in msg
    assert "price moved" in msg
    assert "2/3" in msg  # 2 de 3 exitosas
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/pytest tests/test_notifier.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'src.notifier'"

- [ ] **Step 3: Escribir la implementación**

```python
# src/notifier.py
from __future__ import annotations

from src.models import OrderResult, Signal


def format_discarded(signal: Signal, reason: str) -> str:
    return (
        f"⚠️ Señal descartada — {signal.symbol} {signal.direction.value} "
        f"@ {signal.entry}\nMotivo: {reason}"
    )


def format_executed(signal: Signal, results: list[OrderResult]) -> str:
    ok = [r for r in results if r.success]
    lines = [
        f"✅ {signal.symbol} {signal.direction.value} @ {signal.entry} "
        f"| SL {signal.stop_loss}",
        f"Ejecutadas {len(ok)}/{len(results)}:",
    ]
    for r in results:
        if r.success:
            lines.append(f"  • {r.account} {r.comment}: #{r.ticket} @ {r.price}")
        else:
            lines.append(f"  • {r.account} {r.comment}: ❌ {r.error}")
    return "\n".join(lines)


class Notifier:
    """Envía mensajes a Mensajes Guardados usando un cliente Telethon."""

    def __init__(self, client):
        self._client = client

    async def send(self, text: str) -> None:
        # 'me' = chat de Mensajes Guardados del propio usuario
        await self._client.send_message("me", text)
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.venv/bin/pytest tests/test_notifier.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/notifier.py tests/test_notifier.py
git commit -m "feat: notificador con formato de ejecución y descarte"
```

---

## Task 9: Dedup de mensajes procesados

**Files:**
- Create: `src/dedup.py`
- Test: `tests/test_dedup.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_dedup.py
from src.dedup import SeenStore


def test_marks_and_detects_seen(tmp_path):
    store = SeenStore(str(tmp_path / "seen.json"))
    assert store.seen(101) is False
    store.mark(101)
    assert store.seen(101) is True


def test_persists_across_instances(tmp_path):
    path = str(tmp_path / "seen.json")
    s1 = SeenStore(path)
    s1.mark(202)
    s2 = SeenStore(path)
    assert s2.seen(202) is True
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/pytest tests/test_dedup.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'src.dedup'"

- [ ] **Step 3: Escribir la implementación**

```python
# src/dedup.py
from __future__ import annotations

import json
from pathlib import Path


class SeenStore:
    """Persiste los IDs de mensajes ya procesados para evitar duplicados."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ids: set[int] = set()
        if self._path.exists():
            self._ids = set(json.loads(self._path.read_text(encoding="utf-8")))

    def seen(self, message_id: int) -> bool:
        return message_id in self._ids

    def mark(self, message_id: int) -> None:
        self._ids.add(message_id)
        self._path.write_text(json.dumps(sorted(self._ids)), encoding="utf-8")
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.venv/bin/pytest tests/test_dedup.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/dedup.py tests/test_dedup.py
git commit -m "feat: dedup persistente de mensajes procesados"
```

---

## Task 10: Pipeline de procesamiento de una señal

**Files:**
- Create: `src/pipeline.py`
- Test: `tests/test_pipeline.py`

Junta parser + risk_guard + router + bridges + notifier en una función testeable, sin Telethon.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_pipeline.py
from src.config import Config
from src.models import Account, OrderRequest, OrderResult
from src.pipeline import process_message


class FakeBridge:
    def __init__(self):
        self.sent: list[OrderRequest] = []

    def send(self, req: OrderRequest) -> OrderResult:
        self.sent.append(req)
        return OrderResult(success=True, ticket=len(self.sent), price=214.52,
                           account=req.account, comment=req.comment)


GBPJPY_BUY = """GBPJPY
🔵📊 BUY 214.50

TP: 1️⃣ 214.70
TP: 2️⃣ 215.00
TP: 3️⃣ 215.50
SL: ❌ 213.85"""


def _cfg(enabled=True):
    return Config(trading_enabled=enabled, max_open_trades=9, tolerance_pips=20,
                  accounts=[Account("DEMO1", "/tmp/a", lot=0.01)])


def test_valid_signal_sends_three_orders():
    bridge = FakeBridge()
    notes = []
    outcome = process_message(
        GBPJPY_BUY, message_id=1, config=_cfg(),
        bridges={"DEMO1": bridge}, current_open=0, notify=notes.append,
    )
    assert outcome == "executed"
    assert len(bridge.sent) == 3
    assert len(notes) == 1 and "GBPJPY" in notes[0]


def test_non_signal_is_ignored_silently():
    bridge = FakeBridge()
    notes = []
    outcome = process_message(
        "hola traders", message_id=2, config=_cfg(),
        bridges={"DEMO1": bridge}, current_open=0, notify=notes.append,
    )
    assert outcome == "ignored"
    assert bridge.sent == []
    assert notes == []


def test_disabled_trading_discards_and_notifies():
    bridge = FakeBridge()
    notes = []
    outcome = process_message(
        GBPJPY_BUY, message_id=3, config=_cfg(enabled=False),
        bridges={"DEMO1": bridge}, current_open=0, notify=notes.append,
    )
    assert outcome == "discarded"
    assert bridge.sent == []
    assert len(notes) == 1 and "descart" in notes[0].lower()
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/pytest tests/test_pipeline.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'src.pipeline'"

- [ ] **Step 3: Escribir la implementación**

```python
# src/pipeline.py
from __future__ import annotations

from typing import Callable

from src.config import Config
from src.file_bridge import FileBridge
from src.notifier import format_discarded, format_executed
from src.order_router import build_orders
from src.risk_guard import evaluate
from src.signal_parser import parse_signal


def process_message(
    text: str,
    *,
    message_id: int,
    config: Config,
    bridges: dict[str, FileBridge],
    current_open: int,
    notify: Callable[[str], None],
) -> str:
    """Procesa un mensaje. Devuelve 'ignored' | 'discarded' | 'executed'."""
    signal = parse_signal(text)
    if signal is None:
        return "ignored"
    signal.message_id = message_id

    ok, reason = evaluate(
        signal,
        trading_enabled=config.trading_enabled,
        max_open_trades=config.max_open_trades,
        current_open=current_open,
    )
    if not ok:
        notify(format_discarded(signal, reason))
        return "discarded"

    accounts = config.active_accounts()
    orders = build_orders(signal, accounts, tolerance_pips=config.tolerance_pips)

    results = []
    for order in orders:
        bridge = bridges[order.account]
        results.append(bridge.send(order))

    notify(format_executed(signal, results))
    return "executed"
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.venv/bin/pytest tests/test_pipeline.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat: pipeline de procesamiento de señal (parser→riesgo→router→bridge→notify)"
```

---

## Task 11: Listener de Telegram + main (cableado)

**Files:**
- Create: `src/telegram_listener.py`
- Create: `src/main.py`

No tiene unit tests automáticos (depende de Telethon en vivo); se valida manualmente en Task 13.

- [ ] **Step 1: Escribir `src/telegram_listener.py`**

```python
# src/telegram_listener.py
from __future__ import annotations

import logging
from typing import Callable

from telethon import TelegramClient, events

log = logging.getLogger(__name__)


class TelegramListener:
    def __init__(self, client: TelegramClient, channel: str,
                 on_message: Callable[[str, int], None]):
        self._client = client
        self._channel = channel
        self._on_message = on_message

    def register(self) -> None:
        @self._client.on(events.NewMessage(chats=self._channel))
        async def _handler(event):
            text = event.message.message or ""
            mid = event.message.id
            log.info("Mensaje nuevo id=%s", mid)
            try:
                self._on_message(text, mid)
            except Exception:  # nunca dejar caer el listener por un mensaje
                log.exception("Error procesando mensaje id=%s", mid)
```

- [ ] **Step 2: Escribir `src/main.py`**

```python
# src/main.py
from __future__ import annotations

import asyncio
import logging
import os

from telethon import TelegramClient

from src.config import load_config, load_secrets
from src.dedup import SeenStore
from src.file_bridge import FileBridge
from src.notifier import Notifier
from src.pipeline import process_message
from src.telegram_listener import TelegramListener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bridge.log")],
)
log = logging.getLogger("main")


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


async def amain() -> None:
    _load_dotenv()
    config = load_config()
    secrets = load_secrets()

    bridges = {a.name: FileBridge(a.mailbox_path) for a in config.active_accounts()}
    seen = SeenStore("state/seen.json")

    client = TelegramClient("state/session", secrets.api_id, secrets.api_hash)
    await client.start(phone=secrets.phone)
    log.info("Conectado a Telegram. Escuchando canal: %s", secrets.channel)

    notifier = Notifier(client)
    pending_notes: list[str] = []

    def on_message(text: str, mid: int) -> None:
        if seen.seen(mid):
            return
        seen.mark(mid)
        # current_open=0: MVP no consulta posiciones abiertas reales todavía.
        outcome = process_message(
            text, message_id=mid, config=config, bridges=bridges,
            current_open=0, notify=pending_notes.append,
        )
        log.info("Mensaje id=%s -> %s", mid, outcome)

    listener = TelegramListener(client, secrets.channel, on_message)
    listener.register()

    await notifier.send("🤖 Puente Telegram→MT4 iniciado y escuchando.")

    # Bucle: drena las notas pendientes generadas por el handler síncrono.
    async def flush_notes():
        while True:
            while pending_notes:
                await notifier.send(pending_notes.pop(0))
            await asyncio.sleep(1)

    await asyncio.gather(client.run_until_disconnected(), flush_notes())


if __name__ == "__main__":
    asyncio.run(amain())
```

- [ ] **Step 3: Verificar que todo importa y los tests siguen verdes**

Run: `.venv/bin/python -c "import src.main" && .venv/bin/pytest -q`
Expected: importa sin error y todos los tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/telegram_listener.py src/main.py
git commit -m "feat: listener de Telegram y main (cableado del bot)"
```

---

## Task 12: Expert Advisor MQL4 (puente del lado MT4)

**Files:**
- Create: `mt4/mt4_bridge.mq4`

No hay unit tests para MQL4; se valida manualmente en Task 13.

- [ ] **Step 1: Escribir el Expert Advisor**

El EA usa la librería estándar de MT4 para JSON simple por parsing manual (los comandos son planos). Vigila `MQL4/Files/<bridge>/commands`, ejecuta y escribe en `responses`.

```mql4
//+------------------------------------------------------------------+
//|                                              mt4_bridge.mq4       |
//|  Puente por archivos: lee comandos JSON y ejecuta OrderSend.     |
//+------------------------------------------------------------------+
#property strict

input string BridgeFolder = "bridge"; // subcarpeta dentro de MQL4/Files
input int    Slippage     = 30;       // slippage en puntos
input int    MagicNumber  = 770077;

string CmdDir() { return BridgeFolder + "\\commands\\"; }
string RspDir() { return BridgeFolder + "\\responses\\"; }

int OnInit()
{
   EventSetMillisecondTimer(500); // revisar cada 500ms
   Print("mt4_bridge iniciado. Carpeta: ", BridgeFolder);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) { EventKillTimer(); }

// Extrae el valor (string) de una clave en un JSON plano.
string JsonStr(string json, string key)
{
   string pat = "\"" + key + "\"";
   int k = StringFind(json, pat);
   if(k < 0) return "";
   int colon = StringFind(json, ":", k);
   if(colon < 0) return "";
   int i = colon + 1;
   // saltar espacios y comillas de apertura
   while(i < StringLen(json) && (StringGetChar(json,i)==' ' )) i++;
   bool quoted = (StringGetChar(json,i)=='"');
   if(quoted) i++;
   string out = "";
   while(i < StringLen(json))
   {
      int c = StringGetChar(json,i);
      if(quoted && c=='"') break;
      if(!quoted && (c==',' || c=='}')) break;
      out += CharToString((uchar)c);
      i++;
   }
   return out;
}

double JsonNum(string json, string key) { return StringToDouble(JsonStr(json,key)); }

double PipSize(string symbol)
{
   int digits = (int)MarketInfo(symbol, MODE_DIGITS);
   double point = MarketInfo(symbol, MODE_POINT);
   // 5 o 3 dígitos => pip = 10 * point; 4 o 2 => pip = point
   if(digits==5 || digits==3) return 10*point;
   return point;
}

void WriteResponse(string fname, string id, bool ok, int ticket, double price, string err)
{
   int h = FileOpen(RspDir()+fname, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) { Print("No pude escribir respuesta ", fname); return; }
   string oks = ok ? "true" : "false";
   string es  = (err=="") ? "null" : "\""+err+"\"";
   string json = StringFormat(
      "{\"id\":\"%s\",\"success\":%s,\"ticket\":%d,\"price\":%.5f,\"error\":%s}",
      id, oks, ticket, price, es);
   FileWriteString(h, json);
   FileClose(h);
}

void ProcessFile(string fname)
{
   int h = FileOpen(CmdDir()+fname, FILE_READ|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) return;
   string json = "";
   while(!FileIsEnding(h)) json += FileReadString(h);
   FileClose(h);

   string id        = JsonStr(json, "id");
   string symbol    = JsonStr(json, "symbol");
   string direction = JsonStr(json, "direction");
   double lot       = JsonNum(json, "lot");
   double sl        = JsonNum(json, "stop_loss");
   double tp        = JsonNum(json, "take_profit");
   double entryRef  = JsonNum(json, "entry_ref");
   double tolPips   = JsonNum(json, "tolerance_pips");
   string comment   = JsonStr(json, "comment");

   int cmd = (direction=="BUY") ? OP_BUY : OP_SELL;
   double price = (cmd==OP_BUY) ? MarketInfo(symbol, MODE_ASK)
                                : MarketInfo(symbol, MODE_BID);

   // Tolerancia: validar con precio en vivo
   double pip = PipSize(symbol);
   double deviation = MathAbs(price - entryRef) / pip;
   if(deviation > tolPips)
   {
      WriteResponse(fname, id, false, 0, price,
         StringFormat("Precio fuera de tolerancia (%.1f pips > %.1f)", deviation, tolPips));
      FileDelete(CmdDir()+fname);
      return;
   }

   int ticket = OrderSend(symbol, cmd, lot, price, Slippage, sl, tp,
                          comment, MagicNumber, 0, clrNONE);
   if(ticket < 0)
      WriteResponse(fname, id, false, 0, price, "OrderSend error " + IntegerToString(GetLastError()));
   else
      WriteResponse(fname, id, true, ticket, price, "");

   FileDelete(CmdDir()+fname);
}

void OnTimer()
{
   string fname;
   long h = FileFindFirst(CmdDir()+"*.json", fname);
   if(h==INVALID_HANDLE) return;
   do {
      if(StringFind(fname, ".tmp") < 0)  // ignorar archivos a medio escribir
         ProcessFile(fname);
   } while(FileFindNext(h, fname));
   FileFindClose(h);
}
//+------------------------------------------------------------------+
```

- [ ] **Step 2: Commit**

```bash
git add mt4/mt4_bridge.mq4
git commit -m "feat: Expert Advisor MQL4 (puente por archivos con tolerancia)"
```

---

## Task 13: README con setup completo

**Files:**
- Create: `README.md`

- [ ] **Step 1: Escribir el README**

Debe documentar, paso a paso:

1. **Requisitos:** Python 3.11+, una VM/PC con MT4 (Wine en Linux para opción gratis 24/7).
2. **Credenciales Telethon:** crear app en `https://my.telegram.org` → API development tools → copiar `api_id` y `api_hash`. Copiar `.env.example` a `.env` y llenar `TG_API_ID`, `TG_API_HASH`, `TG_PHONE`, `TG_CHANNEL`.
3. **Identificar el canal:** cómo obtener el nombre/handle exacto del canal (título "FOREX PIPS PREMIUM" o id).
4. **Instalar el EA en MT4:**
   - Copiar `mt4/mt4_bridge.mq4` a `<terminal>/MQL4/Experts/`.
   - Compilar en MetaEditor (F7).
   - Crear la carpeta buzón `<terminal>/MQL4/Files/bridge/` con subcarpetas `commands/` y `responses/`.
   - Arrastrar el EA al gráfico de cualquier símbolo; habilitar **AutoTrading**.
   - Poner `mailbox_path` en `config.yaml` apuntando a esa carpeta `bridge`.
5. **Configurar cuentas y parámetros** en `config.yaml` (lote, tolerancia, máx trades, sufijo de símbolo — verificar el sufijo real abriendo el "Market Watch" del broker).
6. **Primer arranque:** `python -m src.main`. La primera vez Telethon pedirá el código que llega a tu Telegram. Luego queda la sesión guardada en `state/session`.
7. **Correr 24/7 gratis:** notas para Oracle Cloud Always Free + Wine + MT4 (headless con `xvfb` o VNC), y arrancar el bot con `systemd` o `tmux`.
8. **Seguridad:** nunca subir `.env` ni `*.session`; el repo ya los ignora. Recordatorio: este proyecto es personal — git/GitHub personal, no correo de trabajo.
9. **Kill-switch:** poner `trading_enabled: false` en `config.yaml` y reiniciar para pausar el trading sin apagar el listener.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README con setup completo (Telethon, EA, Wine, 24/7)"
```

---

## Task 14: Verificación final

- [ ] **Step 1: Correr toda la suite**

Run: `.venv/bin/pytest -v`
Expected: TODOS los tests PASS (models, parser, config, risk_guard, order_router, file_bridge, notifier, dedup, pipeline).

- [ ] **Step 2: Verificar que el bot importa y arranca el wiring (sin credenciales reales fallará en login, lo cual es esperado)**

Run: `.venv/bin/python -c "import src.main; print('wiring OK')"`
Expected: imprime "wiring OK".

- [ ] **Step 3: Prueba manual end-to-end (requiere MT4 demo)**

Documentada en README: con MT4 demo + EA cargado, ejecutar el bot, copiar manualmente una señal real al canal de prueba (o usar una cuenta secundaria), y verificar que se abren 3 trades con SL/TP correctos y que llega la notificación a Mensajes Guardados.

- [ ] **Step 4: Commit final si hubo ajustes**

```bash
git add -A
git commit -m "chore: verificación final de la suite" || echo "nada que commitear"
```

---

## Notas de cierre

- **MVP:** `current_open` se pasa como 0 (el máx-trades aún no consulta posiciones reales de MT4). Mejora futura: comando `COUNT` en el EA que devuelva posiciones abiertas para alimentar `risk_guard` con el valor real.
- **Escalabilidad:** agregar una cuenta = añadir una entrada en `config.yaml` con su `mailbox_path` y su EA en ese terminal. El fan-out es automático.
- **Mejoras futuras (fuera de alcance):** cierres parciales, trailing/break-even, lotaje por riesgo %, reglas por cuenta.
