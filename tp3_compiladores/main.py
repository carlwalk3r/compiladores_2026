"""Punto de entrada: python main.py [ruta_al_archivo_de_casos]."""

from __future__ import annotations

import sys
from pathlib import Path

from src.lexer import Lexer
from src.parser_sdt import ParserSDT
from src.reporter import Reporter
from src.symbol_table import TablaSimbolos


def main() -> int:
    raiz = Path(__file__).resolve().parent
    ruta_entrada = Path(sys.argv[1]) if len(sys.argv) > 1 else raiz / "data" / "casos.txt"
    if not ruta_entrada.exists():
        print(f"[ERROR] No se encontró el archivo de entrada: {ruta_entrada}")
        print("Uso: python main.py [data/casos.txt]")
        return 1

    with ruta_entrada.open("r", encoding="utf-8") as archivo:
        lineas = archivo.readlines()

    tabla = TablaSimbolos()
    parser = ParserSDT(tabla, Lexer())
    parser.procesar_archivo(lineas)

    reporter = Reporter(tabla)
    reporter.imprimir_reporte_consola()
    ruta_salida = reporter.exportar_json(raiz / "resultado_sesiones.json")
    print(f"\n[OK] JSON generado en: {ruta_salida}")
    ruta_trazabilidad = reporter.exportar_trazabilidad_txt(
        raiz / "trazabilidad_completa.txt"
    )
    print(f"[OK] Trazabilidad completa generada en: {ruta_trazabilidad}")
    ruta_html = reporter.exportar_html(raiz / "reporte.html")
    print(f"[OK] Reporte visual HTML generado en: {ruta_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
