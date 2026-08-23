# Actualizaciones automáticas (avisar y descargar nuevas versiones)

**Sí es posible.** El mecanismo incluido funciona así:

1. La app tiene una versión (`APP_VERSION` en `app.py`, hoy `1.1.0`).
2. Al abrirse, consulta un archivo `version.json` publicado en internet.
3. Si ahí hay una versión más nueva, muestra en la barra lateral un aviso
   **“Nueva versión disponible”** con un botón **Descargar actualización**.
4. La persona descarga el nuevo `VoyCotizador-Setup.exe` y lo ejecuta: como el
   instalador usa el mismo identificador, **actualiza sobre lo instalado** y el
   historial se conserva (está en `%LOCALAPPDATA%\VoyTravel\`).

No es una actualización 100% silenciosa (la persona da un clic para instalar),
pero sí es “te llega el aviso y actualizas en dos clics”, que es lo habitual y
lo más seguro.

## Cómo activarlo (una sola vez)

Necesitas un lugar donde publicar dos archivos con URL fija. Lo más simple y
gratis es **GitHub Releases**, pero sirve cualquier hosting o incluso un enlace
directo estable.

1. Crea un repositorio en GitHub (puede ser privado con releases públicos, o
   público).
2. En `app.py`, pon la URL del `version.json` en la constante:

   ```python
   UPDATE_URL = "https://raw.githubusercontent.com/USUARIO/REPO/main/version.json"
   ```

   > Importante: esto debe quedar puesto **antes** de compilar la versión que
   > vas a repartir; si no, las instalaciones existentes no sabrán dónde mirar.

3. Compila e instala esa versión en los equipos (ver `README-instalador.md`).

## Cada vez que quieras sacar una actualización

1. Haz tus cambios en el código.
2. Sube el número de versión en **dos** sitios (deben coincidir):
   - `app.py`  →  `APP_VERSION = "1.2.0"`
   - `installer.iss`  →  `#define MyAppVersion "1.2.0"`
3. Genera el instalador:  `build_installer.bat`  → `Output\VoyCotizador-Setup.exe`
4. Publícalo:
   - Crea un *release* en GitHub y sube `VoyCotizador-Setup.exe`.
   - Actualiza `version.json` con la nueva versión y la URL del instalador, y
     súbelo al repo. Ejemplo:

     ```json
     {
       "version": "1.2.0",
       "url": "https://github.com/USUARIO/REPO/releases/latest/download/VoyCotizador-Setup.exe",
       "notas": "Novedades de esta versión."
     }
     ```

Con eso, la próxima vez que alguien abra la app, verá el aviso y podrá
actualizar. (La comprobación se cachea 1 hora para no consultar en cada acción.)

## Notas

- Si no hay internet o el `version.json` no responde, la app simplemente no
  muestra aviso y sigue funcionando normal.
- Para una experiencia totalmente automática (descargar y ejecutar el instalador
  solo) se puede añadir después; conviene cerrar la app durante la instalación,
  por eso de momento se deja en “avisar + descargar”.
- SmartScreen puede advertir sobre el instalador sin firma (ver
  `README-instalador.md`).