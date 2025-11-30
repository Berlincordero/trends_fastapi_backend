# run_dev.py
import os
import sys
import importlib
import asyncio
import socket


# 1) Forzar Proactor TAMBIÉN aquí (por si corres este script directo)
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass


# 2) Carga .env si existe
if os.path.exists(".env"):
    try:
        from dotenv import load_dotenv
        load_dotenv(".env")
    except Exception:
        pass


# 3) posibles módulos donde puede estar tu FastAPI
CANDIDATES = [
    os.getenv("APP_MODULE"),   # p.ej. "app.main:app"
    "app.main:app",
    "main:app",
    "server:app",
    "backend.main:app",
]


def resolve_import_string() -> str:
    """
    Devuelve 'paquete.modulo:objeto' válido para uvicorn.
    Loguea por qué falló cada intento.
    """
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    errors: list[str] = []

    for spec in filter(None, CANDIDATES):
        try:
            mod_name, obj_name = spec.split(":")
            m = importlib.import_module(mod_name)
            getattr(m, obj_name)
            print(f"✅ Encontrado: {spec}")
            return spec
        except Exception as e:
            err = f"⚠️ Falló import '{spec}': {e!r}"
            print(err)
            errors.append(err)

    print("❌ Ninguna ruta de APP_MODULE funcionó. Errores:")
    for e in errors:
        print("   ", e)
    raise RuntimeError("No se pudo localizar FastAPI. Define APP_MODULE (p.ej. 'app.main:app').")


def _lan_ip() -> str:
    """Obtiene IP LAN real sin depender de hostname/DNS."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    import uvicorn

    spec = resolve_import_string()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    # 👇 Controlar reload desde env
    # - En Linux/Mac puedes dejarlo en 1
    # - En Windows es mejor dejarlo en 0 mientras sirves video
    reload_env = os.getenv("RELOAD")

    if reload_env is not None:
        # si lo ponen a mano en el entorno, respetamos eso
        reload_flag = reload_env.strip() in ("1", "true", "True", "yes", "on")
    else:
        # valor por defecto: en Windows -> False, en otros -> True
        reload_flag = not sys.platform.startswith("win")

    print(f"🔗 API local: http://127.0.0.1:{port}")
    print(f"📱 API LAN:   http://{_lan_ip()}:{port}")
    print(f"🌀 reload={'ON' if reload_flag else 'OFF'}")

    uvicorn.run(
        spec,
        host=host,
        port=port,
        loop="asyncio",          # usamos el loop que ya forzamos arriba
        http="h11",
        ws="websockets",
        reload=reload_flag,
        reload_dirs=["app"],
        reload_excludes=[".venv", ".git", "node_modules", "__pycache__", "media"],
        timeout_keep_alive=30,
        timeout_graceful_shutdown=15,
        log_level=os.getenv("LOG_LEVEL", "info"),
        lifespan="on",
    )


if __name__ == "__main__":
    main()
