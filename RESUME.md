# RESUME — Cómo retomar este proyecto (para el próximo agente)

Este documento te permite continuar el trabajo sin contexto previo y sin errores.
Léelo completo antes de actuar. El detalle técnico está en `HANDOFF.md`.

---

## 0. PROMPT PARA PEGARLE AL AGENTE

Copia y pega esto al iniciar la sesión:

> Vas a retomar un proyecto personal ya avanzado: un puente que lee señales de
> trading de un canal de Telegram y abre trades en MetaTrader 4. El proyecto está
> en `/Users/michael.bonilla/dev/telegram-mt4-bridge` (repo git, rama `master`).
>
> ANTES DE HACER NADA, lee en este orden: `RESUME.md`, `HANDOFF.md`, `README.md`,
> y el spec/plan en `docs/superpowers/`. NO repitas trabajo ya hecho.
>
> Reglas que NO puedes romper:
> - Este proyecto es PERSONAL. NUNCA uses el correo de trabajo
>   `michael.bonilla@rappi.com` en commits. La identidad git local ya está bien
>   (`MichaelBonilla93 <mdbonillam@gmail.com>`).
> - El `gh` CLI está autenticado con la cuenta de TRABAJO; NO lo uses para este
>   repo. El push funciona vía SSH (`git push origin master`) con la llave personal.
> - Es un bot que (eventualmente) mueve dinero: filosofía fail-safe. Ante cualquier
>   duda, NO operar. Pide confirmación antes de acciones de riesgo.
> - Usa el entorno virtual: `.venv/bin/python` y `.venv/bin/pytest`.
>
> Estado actual: MVP completo, 42 tests verdes, parser validado contra 200 mensajes
> reales vía dry-run. Falta SOLO la prueba end-to-end con MetaTrader 4 real
> (instalar MT4 + el Expert Advisor bajo Wine, llenar `config.yaml`, correr el bot
> en demo). Los pasos están en `RESUME.md` sección 3 y en `README.md`.
>
> Mi objetivo en esta sesión es: [EL USUARIO COMPLETA AQUÍ — p.ej. "instalar MT4
> bajo Wine en mi Mac y probar el loop completo en demo", o "desplegar en una VM
> gratis 24/7", o "afinar el parser con un formato de señal nuevo"].

---

## 1. ARCHIVOS A LEER (en orden)

| Orden | Archivo | Por qué |
|-------|---------|---------|
| 1 | `RESUME.md` (este) | Punto de partida y pasos definidos |
| 2 | `HANDOFF.md` | Estado técnico detallado, reglas, limitaciones |
| 3 | `README.md` | Setup de usuario (Telethon, EA, Wine, 24/7) |
| 4 | `docs/superpowers/specs/2026-05-29-telegram-mt4-bridge-design.md` | Diseño y decisiones |
| 5 | `docs/superpowers/plans/2026-05-29-telegram-mt4-bridge.md` | Plan de implementación |
| 6 | `src/*.py` | Código (módulos pequeños, una responsabilidad c/u) |
| 7 | `mt4/mt4_bridge.mq4` | El Expert Advisor (lado MetaTrader) |

No hace falta leer todo `src/` de entrada; entra a un módulo cuando vayas a tocarlo.

---

## 2. CÓMO VERIFICAR QUE TODO SIGUE SANO (primeros comandos)

```bash
cd /Users/michael.bonilla/dev/telegram-mt4-bridge
.venv/bin/pytest -q                              # debe dar 42 passed
.venv/bin/python -c "import src.main; print('wiring OK')"
git status -sb                                   # debe estar limpio, en master
git log --oneline -5
```

Si `.venv` no existe (otro equipo): `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`

---

## 3. EL PASO PENDIENTE: prueba end-to-end en MetaTrader 4 (demo)

Es lo único que falta. Valida que el Expert Advisor reciba los comandos y abra los
trades. Requiere intervención del usuario (su broker, su entorno). El usuario está
en **macOS**, así que MT4 corre bajo **Wine** o en una VM/PC Windows.

### 3.1 Pre-requisitos ya resueltos
- Telethon ya autenticado: existe `state/session` (no pedirá código de nuevo).
- El canal se resuelve por su título "FOREX PIPS PREMIUM" vía `resolve_channel`.
- El parser está validado. El dry-run funciona: `.venv/bin/python -m src.dry_run 50`.

### 3.2 Pasos (guiar al usuario, ver README secciones 3–5 para detalle)
1. **Instalar MT4 bajo Wine** (o en VM/PC Windows). Abrir una cuenta DEMO del broker.
2. **Compilar el EA:** copiar `mt4/mt4_bridge.mq4` a `<terminal>/MQL4/Experts/`,
   abrir MetaEditor, compilar (F7).
3. **Crear el buzón:** `<terminal>/MQL4/Files/bridge/` con subcarpetas
   `commands/` y `responses/`.
4. **Cargar el EA** en un gráfico, habilitar AutoTrading, `BridgeFolder=bridge`.
5. **Configurar `config.yaml`:**
   - `mailbox_path` = ruta ABSOLUTA real a `.../MQL4/Files/bridge` (bajo Wine suele
     ser `~/.wine/drive_c/.../MQL4/Files/bridge`).
   - `symbol_suffix` = verificar el nombre EXACTO del símbolo en el Market Watch del
     broker (puede ser `GBPJPY`, `GBPJPY.r`, `XAUUSD.m`, etc.). CRÍTICO: si no
     coincide, el EA no encontrará el símbolo.
   - `lot`, `tolerance_pips`, `max_open_trades` según preferencia.
6. **Correr el bot:** `.venv/bin/python -m src.main`
7. **Probar:** esperar (o reenviar al canal) una señal y verificar en MT4 que se
   abren 3 trades con SL/TP correctos, y que llega la notificación a Mensajes
   Guardados de Telegram.

### 3.3 Prueba aislada del EA (recomendada antes del loop completo)
Para validar solo el puente EA↔archivos sin depender de Telegram: escribir a mano un
JSON en `MQL4/Files/bridge/commands/test.json` con el formato de comando (ver
`src/file_bridge.py`, claves: id, action=OPEN, symbol, direction, lot, stop_loss,
take_profit, entry_ref, tolerance_pips, comment) y verificar que el EA lo procesa y
escribe la respuesta en `responses/test.json`.

---

## 4. DESPLIEGUE 24/7 GRATIS (opcional, cuando demo funcione)
Oracle Cloud *Always Free* (Linux) + Wine + MT4 + bot bajo systemd/tmux. Detalle en
`README.md` sección 6. El primer login de Telethon y el setup del EA conviene
hacerlos con VNC; luego corre desatendido.

---

## 5. THINGS TO KNOW (evita tropiezos)

- **Identidad/seguridad git:** ver sección 0. `gh` = cuenta de trabajo, NO usar.
  Push solo por SSH a `git@github.com:MichaelBonilla93/telegram-mt4-bridge.git`.
- **`current_open=0` fijo** en `src/main.py` (hay `# TODO`): el guard de
  `max_open_trades` aún no consulta posiciones reales en MT4. Mejora futura: comando
  `COUNT` en el EA. No es bloqueante para la prueba demo.
- **Señales contradictorias** (texto "BUY" pero emoji 🔴 + geometría SELL): el bot
  las DESCARTA por decisión del usuario (2026-05-31). NO auto-corregir dirección.
  Caso real cubierto en `tests/test_real_signals.py`. Si el usuario cambia de
  opinión, las alternativas (deducir por geometría / por emoji) están discutidas en
  el historial; implementarlas en `signal_parser.py` + `risk_guard.py` con tests.
- **Tolerancia de pips:** la valida el EA con precio en vivo (no Python). Python solo
  manda `entry_ref` + `tolerance_pips`.
- **Resolución del canal:** `main.py` usa `events.NewMessage(chats=<título>)`. Si en
  vivo falla con "Cannot find entity", aplicar el mismo `resolve_channel` de
  `src/dry_run.py` dentro de `main.py`/`telegram_listener.py` (resolver la entidad
  antes de registrar el handler). Anotado como posible ajuste.
- **Rutas relativas** en `main.py` (`config.yaml`, `state/`, `bridge.log`): correr
  siempre desde la raíz del proyecto. Para systemd, endurecer con rutas relativas a
  `__file__`.
- **Script de depuración:** `.venv/bin/python scripts/dump_messages.py <id> <id> ...`
  imprime el texto crudo (`repr`) de mensajes por id — útil para diagnosticar
  parseos.

---

## 6. FLUJO DE TRABAJO ESPERADO
- TDD para cualquier cambio de lógica (hay 42 tests; mantenerlos verdes).
- Commits pequeños y frecuentes, en español, identidad personal.
- Push por SSH tras cada avance significativo.
- Mantener `HANDOFF.md` y este `RESUME.md` actualizados al terminar.
