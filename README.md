# Convertir QuoteTrip en app de escritorio

Streamlit es un **servidor web local**, así que "app de escritorio sin depender
de Python" significa empaquetar Python de forma invisible. Aquí tienes dos
caminos. Los archivos ya están incluidos:

- `desktop.py` — abre la app en una **ventana nativa** (no en el navegador).
- `VoyCotizador.spec`, `build_exe.bat` — para generar un `.exe` (el nombre del
  archivo `.spec` quedó igual por costumbre; lo que genera ya se llama
  `QuoteTrip.exe`).
- `QuoteTrip.bat` — lanzador para la versión con Python portable.
- `requirements-desktop.txt` — dependencias extra (`pywebview`, `pyinstaller`).
- `assets/logo.ico` — icono para el ejecutable / acceso directo (todavía es el
  logo de la instalación original; reemplázalo por el del producto cuando
  tengas uno).

> La base de datos del historial y la cuenta de la agencia (NIT, logo,
> colores, login), cuando la app va empaquetada, se guardan en
> `%LOCALAPPDATA%\QuoteTrip\cotizaciones.db` para que **no se borren** al
> cerrar. Si el equipo tenía una instalación anterior con el nombre viejo
> (`%LOCALAPPDATA%\VoyTravel\`), esos datos se copian ahí automáticamente la
> primera vez que se abre esta versión — no hace falta hacer nada manual.

> La primera vez que se abre la app (sin ninguna cuenta creada todavía) pide
> registrar los datos de la agencia (razón social, NIT, logo, colores) y un
> usuario/contraseña. Las veces siguientes pide iniciar sesión. Ver el
> asistente guiado dentro de la app ("❓ Ayuda") para el resto del flujo.

---

## Camino A1 — Python portable (recomendado, sin compilar)

El más fiable: no hay que depurar ningún empaquetado y tu código funciona igual.

1. Descarga **WinPython** (versión "dot", portable) desde winpython.github.io y
   extráelo. Dentro verás una carpeta tipo `WPy64-xxxx\python-3.x.x`.
2. Copia esa carpeta de Python y renómbrala a `python`, dejándola **junto a
   `app.py`**. Debe quedar así:

   ```
   QuoteTrip\
   ├── python\            <- Python portable (incluye python.exe)
   ├── app.py
   ├── quotetrip\         <- paquete con la lógica de la app
   ├── desktop.py
   ├── assets\
   └── QuoteTrip.bat
   ```
3. Abre el "WinPython Command Prompt" (o `python\python.exe -m pip`) e instala
   las dependencias en ese Python:

   ```
   python\python.exe -m pip install -r requirements.txt
   python\python.exe -m pip install -r requirements-desktop.txt
   ```
4. Doble clic en **`QuoteTrip.bat`**. Se abre la ventana de la app.
5. Para repartirlo: comprime la carpeta `QuoteTrip\` y pásala a otra máquina
   Windows. Funciona sin instalar nada. (Opcional: crea un acceso directo al
   `.bat`, y en *Propiedades → Cambiar icono* asígnale `assets\logo.ico`.)

Ventaja: cero compilación. Desventaja: la carpeta pesa ~300–500 MB.

---

## Camino A2 — Ejecutable único con PyInstaller (`.exe`)

Genera `dist\QuoteTrip\QuoteTrip.exe`. Más "limpio" para repartir, pero
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
3. El resultado queda en `dist\QuoteTrip\`. Reparte **toda** esa carpeta
   (es "one-folder", más estable que un único archivo para Streamlit).

### Si el .exe abre y se cierra o da error de Streamlit
Casi siempre es metadata o archivos estáticos que faltan. Prueba, en orden:

- Reconstruye añadiendo el paquete que reclame el error al bloque
  `collect_all` o `copy_metadata` dentro de `VoyCotizador.spec`.
- Ejecuta el `.exe` desde una consola (`cmd`) para ver el mensaje real.
- Como diagnóstico, pon `console=True` en el `.spec` y reconstruye: verás los
  logs de arranque.
- Si el error menciona el paquete `quotetrip` (no encontrado / import error),
  confirma que `("quotetrip", "quotetrip")` sigue en la lista `datas` del
  `.spec` — ese paquete viaja como datos sueltos junto a `app.py`, no se
  compila.

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
- Quieres un instalador/`.exe` para repartir (venderlo a otras agencias) →
  **A2 (PyInstaller)** + **Inno Setup** (`build_installer.bat`, ver
  `README Instalador.md`) apuntando a la carpeta `dist\QuoteTrip\`. Este es el
  camino pensado para distribuir a clientes.
- Quieres cero Python y aceptas reescribir → **B (stlite)**.
