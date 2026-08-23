# -*- coding: utf-8 -*-
"""
Lanzador de escritorio para QuoteTrip.

Arranca Streamlit como PROCESO APARTE (no en un hilo: Streamlit instala un
manejador de señales que solo funciona en el hilo principal) y muestra la app
dentro de una ventana nativa con pywebview. Si pywebview no está disponible,
abre la app en el navegador por defecto.

Funciona ejecutándose con Python normal/portable y dentro de un .exe de
PyInstaller.

Uso en desarrollo:   python desktop.py
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

TITULO = "QuoteTrip"


def _dir_recursos() -> Path:
    """Carpeta donde están app.py y assets (soporta PyInstaller)."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else Path(__file__).resolve().parent


def _puerto_libre() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    return puerto


def _esperar_servidor(puerto: int, timeout: int = 90) -> bool:
    fin = time.time() + timeout
    while time.time() < fin:
        try:
            with socket.create_connection(("127.0.0.1", puerto), 0.5):
                return True
        except OSError:
            time.sleep(0.4)
    return False


def _args_streamlit(app_path: str, puerto: int):
    return [
        "run",
        app_path,
        f"--server.port={puerto}",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--global.developmentMode=false",
        "--server.fileWatcherType=none",
        "--server.runOnSave=false",
        "--browser.gatherUsageStats=false",
    ]


def _run_server_inproc(puerto: int):
    """Corre Streamlit en ESTE proceso (hilo principal del proceso hijo)."""
    app_path = str(_dir_recursos() / "app.py")
    sys.argv = ["streamlit"] + _args_streamlit(app_path, puerto)
    from streamlit.web import cli as stcli

    sys.exit(stcli.main())


def _lanzar_servidor(puerto: int) -> subprocess.Popen:
    """Lanza Streamlit como proceso hijo."""
    creationflags = 0
    if os.name == "nt":  # ocultar consola del hijo en Windows
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    if getattr(sys, "frozen", False):
        # Dentro del .exe: nos re-invocamos en modo servidor.
        cmd = [sys.executable, "--run-server", str(puerto)]
    else:
        # Python normal/portable: usamos el mismo intérprete con -m streamlit.
        app_path = str(_dir_recursos() / "app.py")
        cmd = [sys.executable, "-m", "streamlit"] + _args_streamlit(app_path, puerto)

    return subprocess.Popen(cmd, creationflags=creationflags)


def main():
    # Modo servidor (proceso hijo del ejecutable empaquetado)
    if "--run-server" in sys.argv:
        idx = sys.argv.index("--run-server")
        _run_server_inproc(int(sys.argv[idx + 1]))
        return

    puerto = _puerto_libre()
    proc = _lanzar_servidor(puerto)
    url = f"http://127.0.0.1:{puerto}"

    if not _esperar_servidor(puerto):
        try:
            proc.terminate()
        except Exception:
            pass
        print("No se pudo iniciar el servidor de la aplicación.")
        sys.exit(1)

    try:
        import webview

        webview.create_window(TITULO, url, width=1250, height=880)
        webview.start()  # bloquea hasta que se cierra la ventana
    except Exception:
        import webbrowser

        webbrowser.open(url)
        try:
            proc.wait()
        except KeyboardInterrupt:
            pass
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
