# Actualizaciones automáticas (avisar y descargar nuevas versiones)

**Sí es posible, y ya está activo.** El mecanismo incluido funciona así:

1. La app tiene una versión (`APP_VERSION` en `quotetrip/config.py`, hoy
   `1.1.0`).
2. Al abrirse, consulta un archivo `version.json` publicado en internet
   (`UPDATE_URL` en `quotetrip/config.py`, ya apunta a
   `TheProgramerBone/voy_cotizador` en GitHub).
3. Si ahí hay una versión más nueva, muestra en la barra lateral un aviso
   **“Nueva versión disponible”** con un botón **Descargar actualización**.
4. La persona descarga el nuevo `QuoteTrip-Setup.exe` y lo ejecuta: como el
   instalador usa el mismo identificador (`AppId` en `installer.iss`, no
   cambia con el rebrand), **actualiza sobre lo instalado** y la cuenta +
   historial se conservan (están en `%LOCALAPPDATA%\QuoteTrip\`).

No es una actualización 100% silenciosa (la persona da un clic para instalar),
pero sí es “te llega el aviso y actualizas en dos clics”, que es lo habitual y
lo más seguro.

## Cada vez que quieras sacar una actualización

1. Haz tus cambios en el código.
2. Sube el número de versión en **dos** sitios (deben coincidir):
   - `quotetrip/config.py`  →  `APP_VERSION = "1.2.0"`
   - `installer.iss`  →  `#define MyAppVersion "1.2.0"`
3. Genera el instalador:  `build_installer.bat`  → `Output\QuoteTrip-Setup.exe`
4. Publícalo:
   - Crea un *release* en GitHub (`TheProgramerBone/voy_cotizador`) y sube
     `QuoteTrip-Setup.exe`.
   - Actualiza `version.json` (en la raíz del repo, rama `master`) con la
     nueva versión y sube el cambio. Ejemplo:

     ```json
     {
       "version": "1.2.0",
       "url": "https://github.com/TheProgramerBone/voy_cotizador/releases/latest/download/QuoteTrip-Setup.exe",
       "notas": "Novedades de esta versión."
     }
     ```

Con eso, la próxima vez que alguien abra la app, verá el aviso y podrá
actualizar. (La comprobación se cachea 1 hora para no consultar en cada acción.)

## Si en algún momento quieres apuntar a otro repositorio

Cambia la constante en `quotetrip/config.py`:

```python
UPDATE_URL = "https://raw.githubusercontent.com/USUARIO/REPO/master/version.json"
```

Debe quedar puesto **antes** de compilar la versión que vas a repartir; si no,
las instalaciones existentes no sabrán dónde mirar. Dejar `UPDATE_URL = ""`
desactiva por completo la comprobación.

## Notas

- Si no hay internet o el `version.json` no responde, la app simplemente no
  muestra aviso y sigue funcionando normal.
- Para una experiencia totalmente automática (descargar y ejecutar el instalador
  solo) se puede añadir después; conviene cerrar la app durante la instalación,
  por eso de momento se deja en “avisar + descargar”.
- SmartScreen puede advertir sobre el instalador sin firma (ver
  `README Instalador.md`).
