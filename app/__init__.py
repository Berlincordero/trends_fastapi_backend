# app/__init__.py
"""
Inicialización del paquete `app`.

Aquí forzamos el event loop correcto para Windows para evitar el error:

    Fatal write error on socket transport
    IndexError: pop from an empty deque

El problema viene de que en Windows, cuando uvicorn lanza un proceso hijo
(que es lo que pasa con --reload), ese proceso a veces usa el
WindowsSelectorEventLoopPolicy por defecto, que es el que muestra
el traceback en selector_events.py.

Al ponerlo aquí, nos aseguramos de que **cada** vez que alguien haga
`import app...` (uvicorn, alembic, tests, etc.), se aplique la policy.
"""

import sys
import asyncio

if sys.platform.startswith("win"):
    try:
        # El Proactor es el que mejor se lleva con sockets/file en Windows.
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        # Si por alguna razón no está disponible, no rompemos el import.
        pass
