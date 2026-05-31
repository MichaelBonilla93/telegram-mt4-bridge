# HANDOFF — Estado del proyecto y pasos faltantes

> Documento para que otro agente (o yo en otra sesión) continúe sin contexto previo.
> Última actualización: 2026-05-29.

## TL;DR

MVP **completo, testeado e integrado en `master`** (40 tests verdes). Estado:
1. ✅ **Push a GitHub** hecho (SSH personal, `origin` sincronizado).
2. ✅ **Modo dry-run** de solo lectura implementado (`src/dry_run.py`,
   `python -m src.dry_run [N]`). En rama `feature/dry-run` (pendiente merge a master).
3. ⏳ **Prueba end-to-end en cuenta demo** (requiere intervención del usuario).

---

## ⚠️ Reglas NO NEGOCIABLES de este proyecto

- Es **personal y privado**. NUNCA usar el correo de trabajo `michael.bonilla@rappi.com`.
- Identidad git de este repo (config `--local`, ya configurada):
  `MichaelBonilla93 <mdbonillam@gmail.com>`. GitHub personal: **@MichaelBonilla93**.
- `gh` CLI está autenticado con la cuenta de **TRABAJO** (`michael-bonilla_rappinc`).
  **NO crear/pushear nada con esa cuenta.** Ver sección Push.
- Nunca commitear `.env`, `*.session`, `state/`, logs (ya están en `.gitignore`).

---

## Qué hace el proyecto

Puente **Telegram → MetaTrader 4**. Lee señales del canal "FOREX PIPS PREMIUM"
(donde el usuario es solo miembro) y abre trades automáticamente.

Formato de señal real:
```
GBPJPY
🔵📊 BUY 214.50
TP: 1️⃣ 214.70
TP: 2️⃣ 215.00
TP: 3️⃣ 215.50
SL: ❌ 213.85
```

Decisiones de diseño (todas implementadas):
- Por señal: **3 posiciones** (TP1/TP2/TP3, mismo SL).
- Lote **fijo configurable** por cuenta.
- Entrada **a mercado con tolerancia de pips** (la valida el EA con precio en vivo).
- **Multi-cuenta**: misma señal a todas las cuentas `active`, con sufijo de símbolo.
- Notificaciones a **Mensajes Guardados** de Telegram.
- Seguridad: **kill-switch** (`trading_enabled`) + **máx. trades**.
- Lectura de Telegram con **Telethon (cuenta de usuario, solo lectura)**.
- Puente **por archivos JSON** (sin DLLs) + **Expert Advisor MQL4**.

Documentos clave en el repo:
- Spec: `docs/superpowers/specs/2026-05-29-telegram-mt4-bridge-design.md`
- Plan: `docs/superpowers/plans/2026-05-29-telegram-mt4-bridge.md`
- Setup de usuario: `README.md`

---

## Estado del código (HECHO)

Todo en `master`. Arquitectura:
`telegram_listener → pipeline → signal_parser → risk_guard → order_router → file_bridge → mt4_bridge.mq4`, con `notifier` y `dedup`.

| Módulo | Estado |
|--------|--------|
| `src/models.py` | ✅ Direction, Signal, Account, OrderRequest, OrderResult |
| `src/signal_parser.py` | ✅ parse_signal() — TDD con señales reales (maneja emojis keycap) |
| `src/config.py` | ✅ load_config(), load_secrets(), Config |
| `src/risk_guard.py` | ✅ evaluate() — kill-switch, máx trades, coherencia SL/TP |
| `src/order_router.py` | ✅ build_orders() — fan-out 3×N + sufijo |
| `src/file_bridge.py` | ✅ FileBridge — JSON atómico, timeout, manejo de errores |
| `src/notifier.py` | ✅ format_executed/format_discarded + Notifier |
| `src/dedup.py` | ✅ SeenStore — persistente, escritura atómica |
| `src/pipeline.py` | ✅ process_message() |
| `src/telegram_listener.py` | ✅ TelegramListener (callback async) |
| `src/main.py` | ✅ cableado; offload de trabajo bloqueante a hilo |
| `mt4/mt4_bridge.mq4` | ✅ EA: lee comandos, valida tolerancia, OrderSend, respuesta atómica |

**Tests:** `.venv/bin/pytest -q` → 34 passed. Se ejecutó modo subagent-driven con
revisión de spec + calidad por bloque; issues encontrados ya corregidos
(escritura atómica dedup, errores file_bridge, notificación engañosa, match falso
de claves JSON en EA, race en respuesta del EA, strip de comillas en .env).

Cómo correr tests:
```bash
cd /Users/michael.bonilla/dev/telegram-mt4-bridge
.venv/bin/pytest -q
.venv/bin/python -c "import src.main; print('wiring OK')"
```

---

## PASO PENDIENTE 1 — Push a GitHub (BLOQUEADO por auth)

- Repo remoto YA creado por el usuario (privado): 
  `https://github.com/MichaelBonilla93/telegram-mt4-bridge.git`
- Remote `origin` YA configurado apuntando ahí.
- **Bloqueo:** `gh`/credential helper usan la cuenta de TRABAJO. Un `git push`
  normal usaría el token de trabajo, que NO tiene acceso al repo personal privado
  (fallaría 403) y además es indeseable.

### Cómo desbloquear (elegir UNA, requiere acción del usuario)
**A. Personal Access Token (PAT) personal:**
   1. Usuario crea un PAT en github.com (cuenta @MichaelBonilla93) con scope `repo`.
   2. Push: `git push https://MichaelBonilla93:<PAT>@github.com/MichaelBonilla93/telegram-mt4-bridge.git master`
      (o configurar credential helper para esta cuenta). NO dejar el PAT en archivos versionados.

**B. SSH con llave personal:**
   1. Cambiar remote a SSH: `git remote set-url origin git@github.com:MichaelBonilla93/telegram-mt4-bridge.git`
   2. Asegurar que la llave SSH cargada corresponde a @MichaelBonilla93.
   3. `git push -u origin master`

**C. `gh auth login` con la cuenta personal** (ojo: cambia la cuenta activa de gh,
   afectaría operaciones de trabajo hasta `gh auth switch`).

**Verificar SIEMPRE antes de pushear** que la identidad efectiva es la personal.
Tras el push exitoso: `git push -u origin master` deja el upstream configurado.

---

## PASO 2 — Modo dry-run de solo lectura (✅ IMPLEMENTADO)

Hecho en `src/dry_run.py` (+ `tests/test_dry_run.py`, 6 tests). En rama
`feature/dry-run`. Reusa `process_message` con un `DryRunBridge` simulado que
registra órdenes y devuelve éxito ficticio (no toca MT4). Función pura testeable
`analyze(text, *, message_id, config) -> DryRunResult(outcome, orders, notes)`.

Uso: `python -m src.dry_run [N]` (N=50 por defecto). Trae los últimos N mensajes y
muestra qué señales detecta / descarta / ignora y qué órdenes simularía.

**VALIDADO (2026-05-31):** corrido contra 200 mensajes reales → 114 señales
detectadas (símbolos: GBPJPY, XAUUSD, EURJPY, CHFJPY, NZDJPY, USDJPY, CADJPY),
83 ignoradas correctamente (saludos, "X PIPS", cierres manuales), 3 descartadas.
El parser generaliza bien más allá del ejemplo original.

Las 3 descartadas eran **errores de tipeo del canal**: texto "BUY" pero emoji 🔴 +
TPs descendentes + SL por encima de la entrada = un SELL mal etiquetado. El
`risk_guard` las descartó por incoherencia (comportamiento correcto). **Decisión
del usuario: seguir descartándolas** (no auto-corregir dirección). Caso real
blindado en `tests/test_real_signals.py`.

**Pendiente git:** mergeado a master y pusheado.

---

## PASO PENDIENTE 3 — Prueba end-to-end en demo (requiere al usuario)

Seguir `README.md`. Resumen:
1. Credenciales Telethon en `.env` (my.telegram.org). Primer login pide código SMS.
2. Instalar MT4 (Windows o Wine), copiar `mt4/mt4_bridge.mq4` a `MQL4/Experts/`,
   compilar (F7), crear `MQL4/Files/bridge/{commands,responses}/`, arrastrar el EA
   al gráfico, habilitar AutoTrading.
3. Llenar `config.yaml`: `mailbox_path` (ruta absoluta a `.../MQL4/Files/bridge`),
   `lot`, `symbol_suffix` (verificar nombre real del símbolo en Market Watch del
   broker — puede ser `GBPJPY.r`, etc.).
4. Correr: `.venv/bin/python -m src.main`. Verificar que abre 3 trades con SL/TP
   correctos en demo y que llega la notificación.

---

## Limitaciones conocidas / mejoras futuras (fuera de alcance del MVP)

- `current_open` está fijo en 0 en `main.py` (hay `# TODO`): `max_open_trades` aún
  no consulta posiciones reales de MT4. Mejora: comando `COUNT` en el EA que
  devuelva posiciones abiertas, alimentar `risk_guard`.
- Rutas relativas en `main.py` (`config.yaml`, `state/`, `bridge.log`): correr desde
  la raíz del proyecto. Endurecer con rutas relativas a `__file__` para systemd.
- Fuera de alcance: cierres parciales, trailing/break-even, lotaje por riesgo %,
  reglas distintas por cuenta.

---

## Despliegue 24/7 gratis (cuando aplique)
Oracle Cloud *Always Free* (Linux) + Wine + MT4 + el bot bajo systemd/tmux.
Detalles en `README.md` sección 6.
