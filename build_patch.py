# -*- coding: utf-8 -*-
"""
Genera el .zip liviano de actualización incremental ("parche"): solo
app.py + quotetrip/ + assets/, sin Python/Streamlit/reportlab/pywebview (eso
no cambia entre versiones normales, ver README Actualizaciones.md).

Se zipea directo desde la raíz del repo (no desde dist\\QuoteTrip\\), porque
son exactamente los mismos archivos que PyInstaller empaqueta como `datas`
(QuoteTrip.spec) — no hace falta compilar el .exe para generar el parche.

Uso:   python build_patch.py   (o doble clic en build_patch.bat)
Salida: Output\\QuoteTrip-Patch.zip  +  Output\\QuoteTrip-Patch.sha256.txt
"""

import hashlib
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SALIDA_DIR = RAIZ / "Output"
ZIP_PATH = SALIDA_DIR / "QuoteTrip-Patch.zip"
SHA_PATH = SALIDA_DIR / "QuoteTrip-Patch.sha256.txt"

# Carpetas/archivos que sí van dentro de cada uno de los tres items
EXCLUIR_NOMBRES = {"__pycache__", ".pytest_cache"}
EXCLUIR_SUFIJOS = {".pyc", ".pyo"}


def _incluir(p: Path) -> bool:
    return (
        not any(parte in EXCLUIR_NOMBRES for parte in p.parts) and p.suffix not in EXCLUIR_SUFIJOS
    )


def main():
    SALIDA_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(RAIZ / "app.py", "app.py")
        for carpeta in ("quotetrip", "assets"):
            base = RAIZ / carpeta
            for archivo in base.rglob("*"):
                if archivo.is_file() and _incluir(archivo):
                    z.write(archivo, archivo.relative_to(RAIZ))

    contenido = ZIP_PATH.read_bytes()
    sha256 = hashlib.sha256(contenido).hexdigest()
    SHA_PATH.write_text(sha256, encoding="utf-8")

    print("=" * 60)
    print(f" LISTO: {ZIP_PATH}")
    print(f" Tamaño: {len(contenido) / 1024:.0f} KB")
    print(f" sha256: {sha256}")
    print(" (también guardado en Output\\QuoteTrip-Patch.sha256.txt)")
    print(' Pégalo en version.json bajo la clave "sha256".')
    print("=" * 60)


if __name__ == "__main__":
    main()
