# Convertir VoyTravel · Cotizaciones en app de escritorio

Streamlit es un **servidor web local**, así que "app de escritorio sin depender
de Python" significa empaquetar Python de forma invisible. Aquí tienes dos
caminos. Los archivos ya están incluidos:

- `desktop.py` — abre la app en una **ventana nativa** (no en el navegador).
- `VoyCotizador.spec`, `build_exe.bat` — para generar un `.exe`.
- `VoyCotizador.bat` — lanzador para la versión con Python portable.
- `requirements-desktop.txt` — dependencias extra (`pywebview`, `pyinstaller`).
- `assets/logo.ico` — icono para el ejecutable / acceso directo.

> La base de datos del historial, cuando la app va empaquetada, se guarda en
> `%LOCALAPPDATA%\VoyTravel\cotizaciones.db` para que **no se borre** al cerrar.

---

## Camino A1 — Python portable (recomendado, sin compilar)

El más fiable: no hay que depurar ningún empaquetado y tu código funciona igual.

1. Descarga **WinPython** (versión "dot", portable) desde winpython.github.io y
   extráelo. Dentro verás una carpeta tipo `WPy64-xxxx\python-3.x.x`.
2. Copia esa carpeta de Python y renómbrala a `python`, dejándola **junto a
   `app.py`**. Debe quedar así:

   ```
   VoyCotizador\
   ├── python\            <- Python portable (incluye python.exe)
   ├── app.py
   ├── desktop.py
   ├── assets\
   └── VoyCotizador.bat
   ```
3. Abre el "WinPython Command Prompt" (o `python\python.exe -m pip`) e instala
   las dependencias en ese Python:

   ```
   python\python.exe -m pip install -r requirements.txt
   python\python.exe -m pip install -r requirements-desktop.txt
   ```
4. Doble clic en **`VoyCotizador.bat`**. Se abre la ventana de la app.
5. Para repartirlo: comprime la carpeta `VoyCotizador\` y pásala a otra máquina
   Windows. Funciona sin instalar nada. (Opcional: crea un acceso directo al
   `.bat`, y en *Propiedades → Cambiar icono* asígnale `assets\logo.ico`.)

Ventaja: cero compilación. Desventaja: la carpeta pesa ~300–500 MB.

---

## Camino A2 — Ejecutable único con PyInstaller (`.exe`)

Genera `dist\VoyCotizador\VoyCotizador.exe`. Más "limpio" para repartir, pero
PyInstaller + Streamlit a veces necesita 1–2 ajustes.

1. En tu entorno (el `.venv` ya te sirve) instala todo:

   ```
   pip install -r requirements.txt
   pip install -r requirements-desktop.txt
   ```
2. Ejecuta:

   ```
   build_exe.bat
   ```

   (equivale a `pyinstaller --noconfirm --clean VoyCotizador.spec`)
3. El resultado queda en `dist\VoyCotizador\`. Reparte **toda** esa carpeta
   (es "one-folder", más estable que un único archivo para Streamlit).

### Si el .exe abre y se cierra o da error de Streamlit
Casi siempre es metadata o archivos estáticos que faltan. Prueba, en orden:

- Reconstruye añadiendo el paquete que reclame el error al bloque
  `collect_all` o `copy_metadata` dentro de `VoyCotizador.spec`.
- Ejecuta el `.exe` desde una consola (`cmd`) para ver el mensaje real.
- Como diagnóstico, pon `console=True` en el `.spec` y reconstruye: verás los
  logs de arranque.

---

## Camino B — Sin Python en absoluto (stlite / Electron)

`stlite` compila Streamlit a WebAssembly y se empaqueta con Electron
(`@stlite/desktop`): el resultado es un `.exe` que **no lleva Python**.
ReportLab y Pillow funcionan en ese entorno, pero hay que **portar** la app y
revisar la persistencia de SQLite (se haría con el almacenamiento del navegador
o IndexedDB) y la lectura del logo. Es más trabajo y no es un cambio directo.
Si te interesa esta vía, puedo ayudarte a adaptar el código.

---

## ¿Cuál elegir?

- Uso interno en una o pocas máquinas → **A1 (Python portable)**. Rápido y a
  prueba de fallos.
- Quieres un instalador/`.exe` para repartir → **A2 (PyInstaller)**, y si
  quieres un instalador con acceso directo y desinstalador, añade **Inno Setup**
  apuntando a la carpeta `dist\VoyCotizador\`.
- Quieres cero Python y aceptas reescribir → **B (stlite)**.