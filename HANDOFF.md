# HANDOFF — Estado del proyecto y pasos faltantes

> Documento para que otro agente (o yo en otra sesión) continúe sin contexto previo.
> Última actualización: 2026-05-29.

## TL;DR

MVP **completo, testeado e integrado en `master`** (34 tests verdes). Falta:
1. **Push a GitHub** (bloqueado por autenticación — ver abajo).
2. **Modo dry-run** de solo lectura (diseñado, NO implementado).
3. **Prueba end-to-end en cuenta demo** (requiere intervención del usuario).

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

## PASO PENDIENTE 2 — Modo dry-run de solo lectura (NO implementado)

**Objetivo:** validar el parser contra mensajes REALES del canal y la conexión
Telethon, SIN abrir trades y SIN necesitar MT4. Es el siguiente paso de mayor valor.

**Diseño sugerido:**
- Nuevo entrypoint, p.ej. `src/dry_run.py` (o flag `--dry-run` en main).
- Conecta Telethon con las mismas credenciales (`.env`), usa
  `client.get_messages(channel, limit=N)` para traer los últimos N mensajes.
- Pasa cada texto por `parse_signal()`. Imprime: por cada mensaje, si es señal
  (símbolo/dir/entry/SL/TPs) o por qué se ignoró. NO llama a file_bridge.
- Idealmente reusar `process_message` con bridges "no-op" (un FakeBridge que solo
  registra) y `trading_enabled` efectivo en modo simulación, para ejercitar también
  risk_guard. Alternativa simple: solo parser.
- Seguir TDD donde aplique (el parser ya está cubierto; el dry-run en sí es I/O).

**Riesgo a cubrir:** canales reales mandan promos, mensajes fijados, señales
editadas y otros símbolos (XAUUSD, US30...). Verificar que el parser los maneja
(ignora basura, parsea variantes). Si aparecen formatos nuevos, ampliar tests del
parser con esos ejemplos reales.

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
