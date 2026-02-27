# Explicació del mòdul lifespan MCP

Aquest document explica el funcionament del fitxer `lifespan.py` del contrib MCP de Guillotina.

## Què fa?

El mòdul gestiona el **cicle de vida del session manager MCP**: l'arrenca quan Guillotina s'inicialitza i l'atura de forma ordenada quan l'aplicació es tanca.

## Quan s'executa?

La funció `mcp_lifespan_startup` està registrada com a subscriber de `ApplicationInitializedEvent`. Això vol dir que s'executa automàticament quan Guillotina ha acabat d'inicialitzar-se.

## Flux del codi

### 1. Comprovació de MCP

```python
try:
    mcp_utility = get_utility(IMCPUtility)
except ComponentLookupError:
    return
```

Si MCP no està configurat (no hi ha cap utility `IMCPUtility` registrada), la funció surt sense fer res. Això permet que Guillotina funcioni sense MCP sense errors.

### 2. Variables de coordinació

```python
ready = asyncio.Event()
stop = asyncio.Event()
startup_exc = None
```

- **ready**: S'utilitza per indicar quan el session manager ha arrencat. El codi principal espera aquest senyal abans de continuar.
- **stop**: S'utilitza per indicar al session manager que s'ha d'aturar. El session manager espera aquest senyal dins del seu bucle.
- **startup_exc**: Guarda qualsevol excepció que es produeixi durant l'arrencada, per poder-la propagar després.

### 3. La funció _run_session_manager

Aquesta funció s'executa en una tasca en segon pla (background task). El que fa:

1. Entra al context manager `session_manager.run()` — aquí el session manager arrenca.
2. Crida `ready.set()` — notifica al codi principal que ja ha arrencat.
3. Espera amb `await stop.wait()` — queda bloquejat fins que algú cridi `stop.set()` (quan Guillotina es tanca).
4. Quan es crida `stop.set()`, surt del `await stop.wait()` i el context manager es tanca correctament.

### 4. Gestió d'excepcions

Si hi ha una excepció dins de `session_manager.run()` (per exemple, en entrar al context manager):

```python
except Exception as exc:
    startup_exc = exc
    ready.set()
    raise
```

**Per què `ready.set()` dins de l'except?** Per evitar un deadlock:

- El codi principal fa `await ready.wait()` i queda bloquejat.
- Si l'excepció es produeix abans de `ready.set()`, mai es cridaria `ready.set()`.
- Sense `ready.set()`, el codi principal restaria bloquejat indefinidament.

En cridar `ready.set()` dins de l'except, assegurem que el codi principal sempre es desbloquegi, tant si tot va bé com si hi ha error.

**Per què guardar l'excepció a `startup_exc`?** Perquè el codi principal pugui detectar que ha fallat i propagar l'error a Guillotina. Així l'aplicació pot saber que el MCP no ha pogut arrencar i actuar en conseqüència.

### 5. Esperar l'arrencada

```python
manager_task = asyncio.create_task(_run_session_manager())
await ready.wait()
```

Es crea la tasca en segon pla i el codi principal espera que el session manager arrenqui (o que hi hagi un error, que també faria `ready.set()`).

### 6. Si hi ha hagut error

```python
if startup_exc is not None:
    await asyncio.gather(manager_task, return_exceptions=True)
    raise startup_exc
```

- `asyncio.gather(..., return_exceptions=True)` espera que la tasca acabi i absorbeix l'excepció (no la propaga).
- Després es fa `raise startup_exc` per propagar l'error a qui ha cridat `mcp_lifespan_startup`.

### 7. Registre del cleanup

```python
async def cleanup(_app):
    stop.set()
    await manager_task
    logger.info("MCP session manager stopped (lifespan)")

event.app.on_cleanup.insert(0, cleanup)
```

La funció `cleanup` es registra a `on_cleanup` de l'aplicació. Quan Guillotina es tanca, s'executen totes les funcions de cleanup. El nostre cleanup:

1. Crida `stop.set()` — el session manager que esperava a `stop.wait()` es desbloqueja i pot tancar-se.
2. Espera que `manager_task` acabi amb `await manager_task`.
3. Registra un missatge al log.

Es fa `insert(0, cleanup)` perquè el nostre cleanup s'executi entre els primers (prioritat alta), assegurant que el session manager MCP s'aturi abans que altres recursos.

## Resum

El mòdul connecta el cicle de vida de Guillotina amb el del session manager MCP: l'arrenca en paral·lel quan l'app s'inicialitza i l'atura de forma ordenada quan l'app es tanca. Els events `ready` i `stop` permeten coordinar correctament entre el codi principal i la tasca en segon pla, i la gestió d'excepcions evita deadlocks quan hi ha errors d'arrencada.
