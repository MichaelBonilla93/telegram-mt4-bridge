# Diseño: Puente de señales Telegram → MetaTrader 4

**Fecha:** 2026-05-29
**Estado:** Aprobado

## Objetivo

Conectar las señales de trading publicadas en un canal de Telegram
(FOREX PIPS PREMIUM, donde el usuario es solo miembro) con una o más cuentas
de MetaTrader 4 del mismo broker, abriendo automáticamente los trades con el
Stop Loss y los Take Profit indicados en cada señal.

El sistema debe ser **gratuito**, capaz de correr **24/7**, y quedar **fácil y
escalable** para conectar cuentas adicionales del mismo broker.

## Restricciones y decisiones tomadas

| Tema | Decisión |
|------|----------|
| Despliegue | Gratis y 24/7. VM Linux *Always Free* (ej. Oracle Cloud) con MT4 bajo Wine + bot Python. También funciona en máquina propia. |
| Lectura de Telegram | Telethon con la **cuenta de usuario** del dueño (solo lectura del canal). Un bot oficial no aplica porque el canal es de un tercero. |
| Riesgo Telethon | Aceptado: el bot solo lee, nunca envía al canal. Secretos en `.env`, sesión `.session` protegida y fuera de git. |
| Manejo de los 3 TP | **3 posiciones separadas** por señal: mismo símbolo/dirección/SL, con TP1, TP2 y TP3 respectivamente. |
| Lotaje | **Fijo configurable** por cuenta (ej. 0.01). |
| Tipo de entrada | **A mercado con tolerancia**: entra inmediato salvo que el precio ya se haya alejado más de X pips del precio de la señal (configurable) → descarta. |
| Multi-cuenta | **Misma señal replicada a todas las cuentas activas**, cada una con su propia config (lote, sufijo). |
| Notificaciones | A los **Mensajes Guardados** de Telegram del usuario (misma sesión Telethon). |
| Seguridad | **Máx. trades simultáneos** + **interruptor on/off** global. |
| Puente Python ↔ MT4 | **Puente por archivos**: EA propio en MQL4 que lee comandos JSON de una carpeta buzón y escribe respuestas. Sin DLLs. |

## Formato de la señal (canal FOREX PIPS PREMIUM)

Formato consistente observado:

```
GBPJPY                  ← símbolo
🔵📊 BUY 214.50          ← dirección (BUY/SELL) + precio de entrada
TP: 1️⃣ 214.70           ← take profit 1
TP: 2️⃣ 215.00           ← take profit 2
TP: 3️⃣ 215.50           ← take profit 3
SL: ❌ 213.85            ← stop loss
```

- Dirección BUY → emoji azul; SELL → emoji rojo (no se depende del emoji, sino del
  texto `BUY`/`SELL`).
- Siempre 3 TP y 1 SL.
- Mensajes que no encajen en este patrón se ignoran limpiamente.

## Arquitectura general

```
Telegram (canal) ──lee──▶ TelegramListener ──▶ SignalParser ──▶ RiskGuard
                                                                   │
                                                                   ▼
                                              OrderRouter (fan-out cuentas, 3 órdenes)
                                                   │                │
                                                   ▼                ▼
                                              FileBridge(c1)    FileBridge(c2) ...
                                                   │                │
                                                   ▼ JSON           ▼ JSON
                                              MT4+EA (Wine)     MT4+EA (Wine)
                                              cuenta 1          cuenta 2

Notifier ──▶ Telegram (Mensajes Guardados)
```

Proceso Python asíncrono único. Cada cuenta MT4 corre en su propio terminal bajo
Wine, con un EA que vigila una carpeta buzón. Python escribe órdenes JSON y lee
respuestas.

## Componentes

Cada componente tiene una sola responsabilidad y se prueba de forma aislada.

### `config.py` + `config.yaml`
Configuración versionable (sin secretos):
- Lista de cuentas: `[{nombre, ruta_buzon_mt4, lote, sufijo_simbolo, activa}]`.
- Globales: tolerancia de pips, máx. trades simultáneos, kill-switch on/off,
  identificador del canal.
- Secretos (`api_id`, `api_hash`, teléfono) en `.env`, nunca en git.

### `telegram_listener.py`
Telethon. Se suscribe a mensajes **nuevos** del canal (sin historial). Pasa el
texto crudo al parser. Expone el cliente para que `Notifier` envíe a Mensajes
Guardados por la misma sesión. Reconexión automática.

### `signal_parser.py`
Convierte texto → objeto `Signal` con regex robusto. Extrae símbolo, dirección,
precio de entrada, SL y [TP1, TP2, TP3]. Si el mensaje no es una señal válida,
retorna `None`. **Pieza con mayor cobertura de TDD.**

### `models.py`
Dataclasses: `Signal`, `OrderRequest`, `OrderResult`, `Account`.

### `risk_guard.py`
Reglas previas a operar:
- Kill-switch global.
- Máx. trades abiertos simultáneos.
- Tolerancia de pips (precio actual vs. precio de la señal).
- Coherencia: SL/TP del lado correcto según BUY/SELL.
Decide aprobar o descartar **con motivo**.

### `order_router.py`
Por cada cuenta activa genera 3 `OrderRequest` (mismo símbolo/dirección/SL, con
TP1/TP2/TP3), aplicando el sufijo de símbolo de esa cuenta. Hace fan-out a cada
`FileBridge`.

### `file_bridge.py`
Una instancia por cuenta. Escribe el comando JSON en el buzón, espera la
respuesta del EA con timeout, parsea el `OrderResult`.

### `notifier.py`
Formatea y envía resúmenes a los Mensajes Guardados: trades abiertos, señales
descartadas (con motivo) y errores.

### `mt4_bridge.mq4`
Expert Advisor en MQL4. Vigila la carpeta buzón (~500ms); al ver un comando
ejecuta `OrderSend` con su SL/TP y escribe un archivo de respuesta con
ticket/precio/error.

### `main.py`
Orquesta: carga config, arranca Telethon, conecta el pipeline.

## Flujo de datos

1. Mensaje nuevo → `TelegramListener` lo captura.
2. `SignalParser` parsea; si no es señal válida → se ignora (log debug).
3. `RiskGuard` valida (kill-switch, máx trades, tolerancia, coherencia). Si falla
   → descarta y **notifica el motivo**.
4. `OrderRouter` arma 3 órdenes por cada cuenta activa y hace fan-out.
5. Cada `FileBridge` escribe el JSON; el EA ejecuta y responde.
6. `Notifier` envía resumen a Mensajes Guardados.

## Manejo de errores

- **Fail-safe por defecto:** ante cualquier duda, no opera y notifica.
- **Deduplicación:** se guarda el ID de cada mensaje procesado (archivo de estado)
  para no repetir tras reenvíos o reinicios.
- **Timeout del EA:** si no responde en X seg, se marca error y se notifica (no se
  asume éxito).
- **Reconexión Telethon:** reintentos automáticos.
- **Símbolo no mapeado:** si el broker usa sufijo no configurado → descarta y avisa.
- **Fallo parcial:** si una de las 3 órdenes falla, se reportan las que entraron y
  cuál falló.

## Testing

- `signal_parser`: suite exhaustiva con ejemplos reales (BUY/SELL, varios pares) +
  casos basura que debe ignorar. Grueso del TDD.
- `risk_guard`: tolerancia, kill-switch, máx trades, coherencia SL/TP.
- `order_router`: genera 3 órdenes correctas por cuenta y aplica sufijos.
- `file_bridge`: buzón simulado (carpeta temp + respuesta mock).
- EA MQL4: prueba manual en MT4 demo con comandos de ejemplo.

## Estructura del proyecto

```
telegram-mt4-bridge/
├── config.yaml              # config sin secretos (versionable)
├── .env.example             # plantilla de secretos
├── README.md                # setup paso a paso (Telethon, Wine, EA)
├── pyproject.toml
├── src/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── telegram_listener.py
│   ├── signal_parser.py
│   ├── risk_guard.py
│   ├── order_router.py
│   ├── file_bridge.py
│   └── notifier.py
├── mt4/
│   └── mt4_bridge.mq4       # Expert Advisor
└── tests/
    ├── test_signal_parser.py
    ├── test_risk_guard.py
    ├── test_order_router.py
    └── test_file_bridge.py
```

## Fuera de alcance (YAGNI por ahora)

- Cierres parciales / trailing stop / break-even automático.
- Lotaje por riesgo % (se puede agregar luego sobre `risk_guard`/`order_router`).
- Reglas distintas por cuenta (filtros de pares, saltarse TPs).
- Dashboard web. La observabilidad es vía Telegram + logs.
