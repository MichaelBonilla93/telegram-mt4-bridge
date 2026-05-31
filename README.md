# Telegram → MetaTrader 4 Bridge

Lee señales de trading de un canal de Telegram y abre automáticamente los trades
en una o más cuentas de **MetaTrader 4**, con el Stop Loss y los Take Profit que
trae la señal.

Por cada señal abre **3 posiciones** (una por cada TP: TP1, TP2, TP3) con el mismo
SL. Entrada a mercado con **tolerancia de pips** (si el precio ya se alejó
demasiado, descarta la señal). Replica la misma señal a **todas las cuentas
configuradas**. Notifica a tus **Mensajes Guardados** de Telegram.

> ⚠️ **Aviso:** opera dinero real bajo tu propio riesgo. Pruébalo siempre primero
> en una cuenta **demo**. Este software se entrega sin garantías.

---

## Arquitectura (resumen)

```
Telegram (canal) → TelegramListener → SignalParser → RiskGuard
                                                         ↓
                                          OrderRouter (3 órdenes × N cuentas)
                                                         ↓
                                          FileBridge (escribe JSON por cuenta)
                                                         ↓
                                          MT4 + Expert Advisor (lee JSON, opera)

Notifier → Telegram (Mensajes Guardados)
```

- **Bot (Python):** escucha Telegram, parsea, valida y escribe comandos JSON en una
  carpeta "buzón" por cuenta.
- **Expert Advisor (`mt4/mt4_bridge.mq4`):** corre dentro de cada terminal MT4, lee
  los comandos del buzón, ejecuta `OrderSend` y responde con el resultado.

El puente es **por archivos** (sin DLLs): funciona limpio bajo Wine y es fácil de
depurar.

---

## Requisitos

- **Python 3.11+**
- Una máquina con **MetaTrader 4** instalado. Para correr gratis 24/7 → una VM
  Linux *Always Free* (ej. Oracle Cloud) con MT4 bajo **Wine** (ver más abajo).
- Una cuenta de Telegram que sea **miembro** del canal de señales.

---

## 1. Instalar el bot

```bash
git clone <tu-repo-personal>   # @MichaelBonilla93
cd telegram-mt4-bridge
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Verifica que los tests pasan:

```bash
.venv/bin/pytest -q
```

---

## 2. Credenciales de Telegram (Telethon)

El bot lee el canal con **tu cuenta de usuario** (no un bot), porque el canal es de
un tercero donde solo eres miembro.

1. Entra a <https://my.telegram.org> → **API development tools**.
2. Crea una app (cualquier nombre). Copia el **`api_id`** y el **`api_hash`**.
3. Copia la plantilla de secretos y llénala:

   ```bash
   cp .env.example .env
   ```

   Edita `.env`:

   ```dotenv
   TG_API_ID=123456
   TG_API_HASH=abcdef0123456789abcdef0123456789
   TG_PHONE=+57XXXXXXXXXX
   TG_CHANNEL=FOREX PIPS PREMIUM
   ```

   - `TG_PHONE`: tu número con código de país (el de tu cuenta de Telegram).
   - `TG_CHANNEL`: el **título exacto** del canal, su `@username`, o su id numérico.

> 🔒 `.env` y los archivos `*.session` **nunca** se suben a git (ya están en
> `.gitignore`). Quien tenga el `.session` tiene acceso a tu Telegram: protégelo.

### Identificar el canal

Si el título exacto no funciona, puedes listar tus diálogos para obtener el id:

```bash
.venv/bin/python -c "
import asyncio, os
from telethon import TelegramClient
from src.main import _load_dotenv
_load_dotenv()
async def run():
    c = TelegramClient('state/session', int(os.environ['TG_API_ID']), os.environ['TG_API_HASH'])
    await c.start(phone=os.environ['TG_PHONE'])
    async for d in c.iter_dialogs():
        print(d.id, '|', d.name)
    await c.disconnect()
asyncio.run(run())
"
```

Usa el id (ej. `-1001234567890`) o el nombre en `TG_CHANNEL`.

---

## 2.5. Dry-run: validar el parser con mensajes reales (recomendado antes de MT4)

Antes de instalar nada en MT4, corre el **modo dry-run de solo lectura**. Trae los
últimos N mensajes del canal, los pasa por el pipeline completo (parser + guardas +
ruteo) con un **bridge simulado** y muestra **qué órdenes se enviarían**, sin abrir
ningún trade y sin necesitar MT4.

```bash
.venv/bin/python -m src.dry_run 50      # analiza los últimos 50 mensajes
```

Verás, por cada mensaje, si se detecta como señal (✅ EXECUTED con las órdenes que
se simularían), si se descarta (⚠️ con el motivo) o si se ignora. Úsalo para
confirmar que el parser entiende bien las señales reales del canal. Si aparece un
formato nuevo que no parsea, hay que ampliar el parser y sus tests.

> La tolerancia de pips NO se evalúa en dry-run (en producción la valida el EA con
> el precio en vivo). El dry-run valida parseo, guardas de riesgo y ruteo.

---

## 3. Instalar el Expert Advisor en MT4

Por **cada** terminal MT4 (uno por cuenta):

1. En MT4: **Archivo → Abrir carpeta de datos**. Ahí está la carpeta `MQL4/`.
2. Copia `mt4/mt4_bridge.mq4` a `MQL4/Experts/`.
3. Abre **MetaEditor** (botón en MT4), abre `mt4_bridge.mq4` y **compila** (F7).
   No debe haber errores.
4. Crea la carpeta buzón y sus subcarpetas dentro de `MQL4/Files/`:

   ```
   MQL4/Files/bridge/
   MQL4/Files/bridge/commands/
   MQL4/Files/bridge/responses/
   ```

5. En MT4, arrastra el EA **mt4_bridge** a cualquier gráfico.
   - En la pestaña **Common**, marca *Allow live trading*.
   - Parámetro `BridgeFolder` = `bridge` (debe coincidir con la subcarpeta de
     `MQL4/Files`).
6. Habilita el botón **AutoTrading** (arriba en MT4). Debe verse una carita
   sonriente en la esquina del gráfico.

> El EA solo usa I/O de archivos dentro de su sandbox `MQL4/Files/`. No necesita
> DLLs ni permisos especiales.

---

## 4. Configurar cuentas y parámetros (`config.yaml`)

```yaml
trading_enabled: true        # interruptor on/off global del trading
max_open_trades: 9           # máx. posiciones simultáneas (3 TP × 3 cuentas = 9)
tolerance_pips: 20           # descarta si el precio se alejó más de esto de la señal

accounts:
  - name: DEMO1
    # Ruta ABSOLUTA a la carpeta 'bridge' dentro de MQL4/Files de ESE terminal
    mailbox_path: /ruta/al/terminal/MQL4/Files/bridge
    lot: 0.01
    symbol_suffix: ""        # ej. ".r", "pro", "m" si el broker usa sufijos
    active: true
```

**Notas importantes:**

- `mailbox_path` debe apuntar a la carpeta `bridge` que creaste en el paso 3, con
  ruta absoluta (en Linux/Wine, la ruta real en disco de `MQL4/Files/bridge`).
- `symbol_suffix`: muchos brokers nombran los símbolos con sufijo (ej. `GBPJPY.r`).
  Abre el **Observación de Mercado** (Market Watch) en MT4 y mira el nombre exacto
  de un par. Si es `GBPJPY` deja `""`; si es `GBPJPY.r` pon `.r`.
- **Agregar otra cuenta** = otro terminal MT4 con su EA + otra entrada en
  `accounts:` con su propio `mailbox_path` y `lot`. El bot replica la señal a todas
  las cuentas `active: true` automáticamente.

---

## 5. Primer arranque

```bash
.venv/bin/python -m src.main
```

- La **primera vez**, Telethon te pedirá el **código** que llega a tu app de
  Telegram (y tu contraseña 2FA si la tienes). Solo ocurre una vez; luego la sesión
  queda guardada en `state/session`.
- Verás en el log "Conectado a Telegram. Escuchando canal: ..." y te llegará a
  Mensajes Guardados: *"🤖 Puente Telegram→MT4 iniciado y escuchando."*
- Cuando llegue una señal nueva al canal, el bot abrirá los trades y te notificará
  con los tickets, o te dirá por qué la descartó.

Los logs quedan en consola y en `bridge.log`.

---

## 6. Correr 24/7 gratis (Oracle Cloud + Wine)

Resumen de la ruta gratuita más común:

1. **VM gratis:** crea una instancia *Always Free* en Oracle Cloud (Linux x86).
2. **Wine + MT4:** instala Wine, descarga el instalador de MT4 de tu broker y
   ejecútalo con Wine. Como la VM no tiene pantalla, corre MT4 con un display
   virtual (`xvfb-run`) o instala un servidor **VNC** ligero para verlo la primera
   vez (login de la cuenta + arrastrar el EA + AutoTrading).
3. **Bot:** clona el repo, crea el venv e instala como en el paso 1. Llena `.env` y
   `config.yaml` (con la ruta real de `MQL4/Files/bridge` dentro del prefijo de
   Wine, normalmente algo como `~/.wine/drive_c/.../MQL4/Files/bridge`).
4. **Persistencia:** corre el bot con `systemd` (un service que reinicie solo) o
   dentro de `tmux`. Igual para que MT4 quede siempre abierto.

> El primer login de Telethon y el setup del EA conviene hacerlos con VNC. Después
> todo corre desatendido.

---

## 7. Operación y seguridad

- **Pausar el trading sin apagar el bot:** pon `trading_enabled: false` en
  `config.yaml` y reinicia el bot. Seguirá escuchando pero descartará toda señal
  (te avisa el motivo). Vuelve a `true` para reanudar.
- **Límite de posiciones:** `max_open_trades` evita abrir de más si el canal manda
  muchas señales seguidas.
- **Fail-safe:** ante cualquier duda (señal no parseable, símbolo raro, EA sin
  responder, precio fuera de tolerancia) el bot **no opera** y notifica.
- **Deduplicación:** los mensajes ya procesados se guardan en `state/seen.json`
  para no repetir si el bot reinicia.

### Nunca subas a git

`.env`, `*.session` y `state/` ya están ignorados. Este proyecto es **personal**:
usa tu GitHub personal (**@MichaelBonilla93**), nunca correos/credenciales de
trabajo.

---

## Estructura del proyecto

```
telegram-mt4-bridge/
├── config.yaml              # config sin secretos
├── .env / .env.example      # secretos Telethon (.env nunca a git)
├── src/
│   ├── main.py              # arranque y cableado
│   ├── config.py            # carga config + secretos
│   ├── models.py            # Signal, Account, OrderRequest, OrderResult
│   ├── signal_parser.py     # texto → Signal
│   ├── risk_guard.py        # kill-switch, máx trades, coherencia SL/TP
│   ├── order_router.py      # 3 órdenes × N cuentas
│   ├── file_bridge.py       # escribe comando JSON / lee respuesta
│   ├── notifier.py          # avisos a Mensajes Guardados
│   ├── telegram_listener.py # Telethon (solo lectura)
│   ├── dedup.py             # mensajes ya procesados
│   └── pipeline.py          # orquesta el procesamiento de una señal
├── mt4/
│   └── mt4_bridge.mq4       # Expert Advisor (lado MT4)
├── tests/                   # suite pytest
└── docs/superpowers/        # spec y plan de implementación
```

---

## Tests

```bash
.venv/bin/pytest -v
```

---

## Limitaciones conocidas / mejoras futuras

- `max_open_trades` usa un contador interno (MVP); aún no consulta las posiciones
  abiertas reales en MT4. Mejora: comando `COUNT` en el EA.
- Fuera de alcance por ahora: cierres parciales, trailing/break-even, lotaje por
  riesgo %, reglas distintas por cuenta.
