# Crear el instalador (Setup.exe) de QuoteTrip

El objetivo: un **único `QuoteTrip-Setup.exe`** que, en un computador nuevo,
se instala con doble clic y funciona — sin instalar Python ni nada más. Es
el archivo pensado para entregar a un cliente nuevo que compre la app.

Esto es posible porque el build de PyInstaller (`dist\QuoteTrip\`) ya lleva
Python y todas las librerías dentro. El instalador solo lo empaqueta con
accesos directos, icono y desinstalador.

## Requisito (solo en TU equipo, una vez)

Instala **Inno Setup 6** (gratis): https://jrsoftware.org/isdl.php
En los equipos donde se instalará la app **no** se necesita nada de esto.

## Generar el instalador

Desde la carpeta del proyecto, doble clic en:

```
build_installer.bat
```

Ese script:
1. Compila la app con PyInstaller si aún no existe (`dist\QuoteTrip\`).
2. Compila el instalador con Inno Setup.

Resultado: **`Output\QuoteTrip-Setup.exe`**.

## Instalar en un computador nuevo

Copia `QuoteTrip-Setup.exe` al equipo y ábrelo. Instala por usuario (no pide
permisos de administrador), crea acceso directo en el menú de inicio y, si lo
marcas, en el escritorio. Para desinstalar: "Agregar o quitar programas".

- La base de datos del historial y la cuenta de la agencia se guardan en
  `%LOCALAPPDATA%\QuoteTrip\`, así que sobreviven a actualizaciones y
  desinstalaciones.
- La primera vez que se abre, pide registrar la cuenta de la agencia (razón
  social, NIT, logo, colores) y un usuario/contraseña — es el único login
  para todos los que usen ese equipo. Las veces siguientes pide iniciar
  sesión.

## Ventana nativa (WebView2)

La app se muestra en una ventana nativa usando **WebView2**, que ya viene en
Windows 11 y en la mayoría de Windows 10. Si un equipo no lo tiene, la app
**igual funciona**: se abre en el navegador por defecto.

Para garantizar la ventana nativa también en equipos sin WebView2:
1. Descarga el "Evergreen Bootstrapper" desde
   https://developer.microsoft.com/microsoft-edge/webview2/ (archivo
   `MicrosoftEdgeWebview2Setup.exe`).
2. Colócalo **junto a `installer.iss`** antes de compilar.
   El instalador lo detectará y lo instalará en silencio solo si hace falta.

## Nota sobre SmartScreen

Como el instalador no está firmado digitalmente, Windows SmartScreen puede
mostrar "Windows protegió tu PC". Es normal en software sin firma: clic en
"Más información" → "Ejecutar de todas formas". Para eliminar ese aviso se
necesita un certificado de firma de código (de pago).