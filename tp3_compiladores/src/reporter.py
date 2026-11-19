"""Vistas de consola, trazabilidad y exportación JSON."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from src.symbol_table import TablaSimbolos


class Reporter:
    def __init__(self, tabla_simbolos: TablaSimbolos):
        self.ts = tabla_simbolos

    @staticmethod
    def _combinar_valores(valores: set[str]) -> str:
        if {"POSITIVA", "NEGATIVA"} <= valores:
            return "MIXTA"
        for valor in ("POSITIVA", "NEGATIVA", "NEUTRA"):
            if valor in valores:
                return valor
        return "SIN_EVIDENCIA"

    def generar_lote_json(self) -> list[dict[str, Any]]:
        lote: list[dict[str, Any]] = []
        for id_sesion, sesion in self.ts.sesiones.items():
            acumulado: dict[int, dict[str, set[str]]] = {}
            for evidencia in sesion.evidencias:
                por_aspecto = acumulado.setdefault(evidencia.turno, {})
                por_aspecto.setdefault(evidencia.aspecto, set()).add(
                    evidencia.valoracion
                )
            valoraciones = {
                str(turno): {
                    aspecto: self._combinar_valores(valores)
                    for aspecto, valores in aspectos.items()
                }
                for turno, aspectos in acumulado.items()
            }

            lote.append(
                {
                    "id_sesion": id_sesion,
                    "analisis": sesion.analisis_estado,
                    "estado_conversacional": sesion.estado_conversacional,
                    "entidades": {
                        "reserva_id": sesion.reserva_id,
                        "turno_vigente": sesion.turno_vigente,
                        "solicitud_pendiente": sesion.solicitud_pendiente,
                    },
                    "resumen_por_aspecto": self.ts.obtener_resumen_aspectos(
                        id_sesion
                    ),
                    "valoraciones_por_turno": valoraciones,
                    "correcciones": sesion.correcciones,
                    "errores": sesion.errores,
                    "evidencias": [e.como_dict() for e in sesion.evidencias],
                    "trazabilidad": sesion.trazas,
                }
            )
        return lote

    def exportar_json(self, ruta_archivo: str | Path) -> Path:
        ruta = Path(ruta_archivo)
        with ruta.open("w", encoding="utf-8") as archivo:
            json.dump(
                self.generar_lote_json(), archivo, indent=2, ensure_ascii=False
            )
        return ruta

    def exportar_trazabilidad_txt(
        self, ruta_archivo: str | Path = "trazabilidad_completa.txt"
    ) -> Path:
        """Exporta la trazabilidad de las 12 sesiones en texto legible."""
        ruta = Path(ruta_archivo)
        lote_json = self.generar_lote_json()

        with ruta.open("w", encoding="utf-8") as archivo:
            archivo.write("=" * 85 + "\n")
            archivo.write(
                "     TRAZABILIDAD PASO A PASO DE TODAS LAS SESIONES (S01 A S12)\n"
            )
            archivo.write("     TP3 - DISEÑO DE COMPILADORES (FPUNA)\n")
            archivo.write("=" * 85 + "\n\n")

            for sesion in lote_json:
                id_sesion = sesion["id_sesion"]
                archivo.write("#" * 85 + "\n")
                archivo.write(
                    f" SESIÓN {id_sesion} | Análisis: {sesion['analisis']} | "
                    f"Estado: {sesion['estado_conversacional']}\n"
                )
                archivo.write("#" * 85 + "\n\n")

                trazabilidad = sesion.get("trazabilidad", [])
                if trazabilidad:
                    for paso in trazabilidad:
                        turno = paso["turno"]
                        actor = paso.get("actor", "DESCONOCIDO")
                        texto = paso.get("texto_original", "")
                        archivo.write(
                            f'--- [Turno {turno}] {actor}: "{texto}" ---\n'
                        )

                        tokens = ", ".join(
                            f"{token['tipo']}('{token['lexema_original']}'"
                            f"->'{token['lexema_normalizado']}', "
                            f"offset={token['offset']})"
                            for token in paso.get("tokens", [])
                        )
                        archivo.write(f"  1. Tokens:                {tokens}\n")
                        archivo.write(
                            "  2. Estructura sintáctica: "
                            f"{paso.get('estructura', 'ORACION')}\n"
                        )

                        cambios_ts = (
                            ", ".join(paso.get("consultas_ts", [])) or "Sin cambios"
                        )
                        archivo.write(
                            f"  3. Tabla de símbolos:     {cambios_ts}\n"
                        )

                        acciones = (
                            ", ".join(paso.get("acciones_semanticas", []))
                            or "Ninguna"
                        )
                        archivo.write(
                            f"  4. Acciones semánticas:   {acciones}\n"
                        )

                        estado = paso.get("estado_despues", {})
                        archivo.write(
                            "  5. Estado tras el turno:  "
                            f"{estado.get('estado')} | "
                            f"Vigente: {estado.get('turno_vigente')} | "
                            f"Pendiente: {estado.get('solicitud_pendiente')}\n\n"
                        )
                else:
                    archivo.write(
                        "  (No se registraron turnos válidos para traza en esta sesión)\n\n"
                    )

                if sesion.get("correcciones"):
                    archivo.write("  EVENTOS DEL CORRECTOR:\n")
                    for evento in sesion["correcciones"]:
                        archivo.write(
                            f"    - T{evento['turno']} [{evento['tipo']}]: "
                            f"{evento['motivo']}\n"
                        )
                    archivo.write("\n")

                if sesion.get("errores"):
                    archivo.write("  RECUPERACIONES / ERRORES:\n")
                    for error in sesion["errores"]:
                        archivo.write(
                            f"    - T{error['turno']}: {error['mensaje']} | "
                            f"Línea: {error['linea']}\n"
                        )
                    archivo.write("\n")

                archivo.write("\n")

        contenido = ruta.read_text(encoding="utf-8").rstrip()
        ruta.write_text(contenido + "\n", encoding="utf-8")
        return ruta

    def imprimir_reporte_consola(self) -> None:
        print("=" * 80)
        print("TP3 - ANÁLISIS DETERMINISTA DE CONVERSACIONES Y TURNOS")
        print("=" * 80)
        for id_sesion, sesion in self.ts.sesiones.items():
            resumen = self.ts.obtener_resumen_aspectos(id_sesion)
            vigente = sesion.turno_vigente or "Ninguno"
            pendiente = sesion.solicitud_pendiente or "Ninguna"
            print(f"\n[{id_sesion}] análisis={sesion.analisis_estado}")
            print(f"  Estado: {sesion.estado_conversacional}")
            print(f"  Reserva: {sesion.reserva_id or 'No citada'}")
            print(f"  Turno vigente: {vigente}")
            print(f"  Solicitud pendiente: {pendiente}")
            print(
                "  Aspectos: "
                + " | ".join(f"{k}={v}" for k, v in resumen.items())
            )
            for correccion in sesion.correcciones:
                print(
                    f"  {correccion['tipo']} T{correccion['turno']}: "
                    f"{correccion['motivo']}"
                )
            for error in sesion.errores:
                print(f"  ERROR T{error['turno']}: {error['mensaje']}")

    def imprimir_trazabilidad_sesion(self, id_sesion: str = "S01") -> None:
        sesion = self.ts.sesiones.get(id_sesion)
        if not sesion:
            return
        print("\n" + "#" * 80)
        print(f"TRAZABILIDAD REAL DE LA SESIÓN {id_sesion}")
        print("#" * 80)
        for traza in sesion.trazas:
            print(f"\nT{traza['turno']} {traza['actor']}: {traza['texto_original']}")
            tokens = ", ".join(
                f"{t['tipo']}({t['lexema_original']}->{t['lexema_normalizado']}, "
                f"coord=({t['sesion']},{t['turno']},{t['offset']}))"
                for t in traza["tokens"]
            )
            print(f"  Tokens: {tokens}")
            print(f"  Estructura: {traza['estructura']}")
            print(f"  Tabla de símbolos: {traza['consultas_ts'] or ['Sin cambios']}")
            print(
                "  Acciones semánticas: "
                f"{traza['acciones_semanticas'] or ['Sin regla aplicable']}"
            )
            print(f"  Resultado: {traza['estado_despues']}")

    def exportar_html(
        self, ruta_archivo: str | Path = "reporte.html"
    ) -> Path:
        """Genera un dashboard HTML autocontenido con las 12 sesiones."""
        ruta = Path(ruta_archivo)
        lote = self.generar_lote_json()

        conteo_estados = {
            "CONFIRMADA": 0,
            "REPROGRAMADA": 0,
            "CANCELADA": 0,
            "PENDIENTE": 0,
            "SIN_CONFIRMAR": 0,
        }
        for sesion in lote:
            estado = sesion["estado_conversacional"]
            conteo_estados[estado] = conteo_estados.get(estado, 0) + 1

        total_parciales = sum(
            1 for sesion in lote if sesion["analisis"] == "PARCIAL"
        )
        total_correcciones = sum(
            len(sesion["correcciones"]) for sesion in lote
        )

        def seguro(valor: Any) -> str:
            return escape(str(valor), quote=True)

        def badge_estado(estado: str) -> str:
            clase = estado.casefold().replace("_", "-")
            return (
                f'<span class="badge badge-estado estado-{seguro(clase)}">'
                f"{seguro(estado)}</span>"
            )

        def badge_valoracion(valoracion: str) -> str:
            clase = valoracion.casefold().replace("_", "-")
            return (
                f'<span class="badge badge-aspecto aspecto-{seguro(clase)}">'
                f"{seguro(valoracion)}</span>"
            )

        filas: list[str] = []
        for sesion in lote:
            id_sesion = seguro(sesion["id_sesion"])
            entidades = sesion["entidades"]
            resumen = sesion["resumen_por_aspecto"]

            reserva = (
                f'<strong>{seguro(entidades["reserva_id"])}</strong>'
                if entidades["reserva_id"]
                else '<span class="sin-dato">No citada</span>'
            )
            if entidades["turno_vigente"]:
                vigente = (
                    f'{seguro(entidades["turno_vigente"]["dia"])} '
                    f'{seguro(entidades["turno_vigente"]["hora"])}'
                )
            else:
                vigente = '<span class="sin-dato">Ninguno</span>'

            if entidades["solicitud_pendiente"]:
                solicitud = (
                    f'{seguro(entidades["solicitud_pendiente"]["dia"])} '
                    f'{seguro(entidades["solicitud_pendiente"]["hora"])}'
                )
            else:
                solicitud = '<span class="sin-dato">Ninguna</span>'

            analisis_clase = (
                "analisis-completo"
                if sesion["analisis"] == "COMPLETO"
                else "analisis-parcial"
            )
            analisis = (
                f'<span class="{analisis_clase}">'
                f'{seguro(sesion["analisis"])}</span>'
            )

            alertas: list[str] = []
            for correccion in sesion["correcciones"]:
                etiqueta = seguro(correccion.get("tipo", "CORRECCION"))
                alertas.append(
                    '<div class="alerta alerta-correccion">'
                    f"[{etiqueta}] {seguro(correccion['motivo'])}</div>"
                )
            for error in sesion["errores"]:
                alertas.append(
                    '<div class="alerta alerta-error">'
                    f"[Error T{seguro(error['turno'])}] "
                    f"{seguro(error['mensaje'])}</div>"
                )
            alertas_html = (
                "".join(alertas)
                if alertas
                else '<span class="sin-dato">Sin eventos</span>'
            )

            evidencias: list[str] = []
            for evidencia in sesion["evidencias"]:
                evidencias.append(
                    '<article class="evidencia">'
                    '<div class="evidencia-meta">'
                    f'<strong>Turno {seguro(evidencia["turno"])}</strong>'
                    f'<span class="actor">{seguro(evidencia["actor"])}</span>'
                    f'<span>Aspecto: <strong>{seguro(evidencia["aspecto"])}</strong></span>'
                    f'{badge_valoracion(evidencia["valoracion"])}'
                    f'<code>{seguro(evidencia["regla"])}</code>'
                    '</div>'
                    f'<p>“{seguro(evidencia["texto"]) }”</p>'
                    '</article>'
                )
            evidencias_html = (
                "".join(evidencias)
                if evidencias
                else '<p class="sin-dato">No se registraron evidencias textuales.</p>'
            )

            aspectos = (
                '<div class="aspectos">'
                f'<div><span>RES</span>{badge_valoracion(resumen["RESERVA"])}</div>'
                f'<div><span>ATC</span>{badge_valoracion(resumen["ATENCION"])}</div>'
                f'<div><span>CLA</span>{badge_valoracion(resumen["CLARIDAD"])}</div>'
                '</div>'
            )

            filas.append(
                f'''<tr class="fila-sesion">
                    <td><strong>{id_sesion}</strong></td>
                    <td>{analisis}</td>
                    <td>{badge_estado(sesion["estado_conversacional"])}</td>
                    <td>{reserva}</td>
                    <td>{vigente}</td>
                    <td>{solicitud}</td>
                    <td>{aspectos}</td>
                    <td class="celda-eventos">{alertas_html}</td>
                    <td class="celda-accion">
                        <button type="button" class="boton-detalle"
                            aria-expanded="false" aria-controls="detalle-{id_sesion}"
                            onclick="toggleDetalle('{id_sesion}', this)">
                            Evidencias
                        </button>
                    </td>
                </tr>
                <tr id="detalle-{id_sesion}" class="fila-detalle" hidden>
                    <td colspan="9">
                        <div class="panel-evidencias">
                            <h3>Evidencias registradas — sesión {id_sesion}</h3>
                            {evidencias_html}
                        </div>
                    </td>
                </tr>'''
            )

        filas_html = "\n".join(filas)
        html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de sesiones — TP3 Compiladores FPUNA</title>
    <style>
        :root {{
            color-scheme: light;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #eef2f7;
            color: #0f172a;
        }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: #eef2f7; color: #0f172a; }}
        .container {{ max-width: 1500px; margin: 0 auto; padding: 24px; }}
        .header {{
            display: flex; justify-content: space-between; gap: 24px;
            align-items: center; padding: 26px 30px; margin-bottom: 24px;
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #dbe4ef; border-radius: 16px;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.07);
        }}
        .header h1 {{ margin: 0; font-size: 1.35rem; line-height: 1.3; }}
        .header p {{ margin: 7px 0 0; color: #475569; font-size: 0.95rem; }}
        .autores {{ text-align: right; color: #334155; line-height: 1.6; font-size: 0.9rem; }}
        .kpi-grid {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 14px; margin-bottom: 24px;
        }}
        .kpi {{
            --acento: #0284c7; background: #ffffff; padding: 17px 18px;
            border: 1px solid #dbe4ef; border-top: 4px solid var(--acento);
            border-radius: 12px; box-shadow: 0 5px 15px rgba(15, 23, 42, 0.04);
        }}
        .kpi span {{ color: #64748b; font-size: 0.76rem; font-weight: 800;
            letter-spacing: 0.05em; text-transform: uppercase; }}
        .kpi strong {{ display: block; margin-top: 5px; font-size: 1.75rem; }}
        .kpi.verde {{ --acento: #16a34a; }} .kpi.azul {{ --acento: #0284c7; }}
        .kpi.amarillo {{ --acento: #d97706; }} .kpi.rojo {{ --acento: #dc2626; }}
        .kpi.gris {{ --acento: #64748b; }} .kpi.violeta {{ --acento: #7c3aed; }}
        .tabla-card {{
            overflow: hidden; background: #ffffff; border: 1px solid #dbe4ef;
            border-radius: 15px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        }}
        .tabla-scroll {{ overflow-x: auto; }}
        table {{ width: 100%; min-width: 1200px; border-collapse: collapse; text-align: left; }}
        th {{
            padding: 14px 12px; background: #0f172a; color: #f8fafc;
            font-size: 0.76rem; letter-spacing: 0.045em; text-transform: uppercase;
        }}
        td {{ padding: 14px 12px; border-bottom: 1px solid #e2e8f0;
            vertical-align: middle; font-size: 0.86rem; }}
        .fila-sesion:hover {{ background: #f8fafc; }}
        .badge {{ display: inline-block; border-radius: 999px; font-weight: 750;
            white-space: nowrap; }}
        .badge-estado {{ padding: 5px 10px; border: 1px solid transparent; font-size: 0.72rem; }}
        .estado-confirmada {{ background:#dcfce7; color:#166534; border-color:#86efac; }}
        .estado-reprogramada {{ background:#e0f2fe; color:#075985; border-color:#7dd3fc; }}
        .estado-cancelada {{ background:#fee2e2; color:#991b1b; border-color:#fca5a5; }}
        .estado-pendiente {{ background:#fef3c7; color:#92400e; border-color:#fcd34d; }}
        .estado-sin-confirmar {{ background:#f1f5f9; color:#475569; border-color:#cbd5e1; }}
        .badge-aspecto {{ padding: 3px 7px; border-radius: 6px; font-size: 0.68rem; }}
        .aspecto-positiva {{ background:#dcfce7; color:#166534; }}
        .aspecto-negativa {{ background:#fee2e2; color:#991b1b; }}
        .aspecto-mixta {{ background:#f3e8ff; color:#6b21a8; }}
        .aspecto-neutra {{ background:#e0e7ff; color:#3730a3; }}
        .aspecto-sin-evidencia {{ background:#f1f5f9; color:#64748b; }}
        .analisis-completo {{ color:#15803d; font-weight:800; }}
        .analisis-parcial {{ display:inline-block; color:#b91c1c; background:#fee2e2;
            padding:4px 7px; border-radius:5px; font-weight:800; }}
        .sin-dato {{ color:#64748b; font-style: italic; }}
        .aspectos {{ display: grid; gap: 5px; }}
        .aspectos div {{ display: flex; align-items: center; justify-content: space-between; gap: 6px; }}
        .aspectos div > span:first-child {{ color:#64748b; font-size:0.7rem; font-weight:800; }}
        .celda-eventos {{ min-width: 235px; max-width: 310px; }}
        .alerta {{ padding: 5px 7px; margin: 3px 0; border-radius: 5px; font-size: 0.75rem; }}
        .alerta-correccion {{ background:#e0f2fe; color:#075985; }}
        .alerta-error {{ background:#fee2e2; color:#b91c1c; }}
        .celda-accion {{ text-align: center; }}
        .boton-detalle {{
            border: 0; border-radius: 7px; padding: 8px 12px; cursor: pointer;
            background:#0369a1; color:#ffffff; font: inherit; font-size:0.78rem; font-weight:750;
            box-shadow: 0 2px 4px rgba(2, 132, 199, 0.18);
        }}
        .boton-detalle:hover {{ background:#075985; }}
        .boton-detalle:focus-visible {{ outline: 3px solid #7dd3fc; outline-offset: 2px; }}
        .fila-detalle td {{ padding: 0; background:#f8fafc; border-bottom:2px solid #cbd5e1; }}
        .panel-evidencias {{ padding: 18px 22px; }}
        .panel-evidencias h3 {{ margin: 0 0 12px; color:#334155; font-size:0.88rem;
            text-transform:uppercase; letter-spacing:0.035em; }}
        .evidencia {{ padding: 11px 13px; margin-bottom: 8px; background:#ffffff;
            border:1px solid #dbe4ef; border-radius:8px; }}
        .evidencia-meta {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; font-size:0.78rem; }}
        .evidencia p {{ margin:8px 0 0; color:#475569; font-size:0.82rem; font-style:italic; }}
        .actor {{ padding:3px 6px; border-radius:5px; background:#e2e8f0; font-weight:800; font-size:0.68rem; }}
        code {{ padding:3px 6px; border-radius:5px; background:#e2e8f0; color:#334155; font-size:0.72rem; }}
        footer {{ padding:18px; color:#64748b; text-align:center; font-size:0.8rem; }}
        @media (max-width: 760px) {{
            .container {{ padding: 12px; }}
            .header {{ align-items:flex-start; flex-direction:column; padding:20px; }}
            .autores {{ text-align:left; }}
        }}
        @media print {{
            body {{ background:#ffffff; }} .container {{ max-width:none; padding:0; }}
            .boton-detalle {{ display:none; }} .tabla-card, .header, .kpi {{ box-shadow:none; }}
        }}
    </style>
</head>
<body>
    <main class="container">
        <header class="header">
            <div>
                <h1>Universidad Nacional de Asunción — Facultad Politécnica</h1>
                <p>Diseño de Compiladores · <strong>Trabajo Práctico 3 (Tema 3)</strong>: Speech Analytics Acotado</p>
            </div>
            <div class="autores">
                <strong>Autores:</strong> Carlos Amarilla &amp; Bethania Chavez<br>
                <strong>Profesor:</strong> Prof. Ing. Sergio A. Aranda
            </div>
        </header>

        <section class="kpi-grid" aria-label="Indicadores principales">
            <div class="kpi azul"><span>Total sesiones</span><strong>{len(lote)}</strong></div>
            <div class="kpi verde"><span>Confirmadas</span><strong>{conteo_estados['CONFIRMADA']}</strong></div>
            <div class="kpi azul"><span>Reprogramadas</span><strong>{conteo_estados['REPROGRAMADA']}</strong></div>
            <div class="kpi amarillo"><span>Pendientes</span><strong>{conteo_estados['PENDIENTE']}</strong></div>
            <div class="kpi rojo"><span>Canceladas</span><strong>{conteo_estados['CANCELADA']}</strong></div>
            <div class="kpi gris"><span>Sin confirmar</span><strong>{conteo_estados['SIN_CONFIRMAR']}</strong></div>
            <div class="kpi rojo"><span>Análisis parciales</span><strong>{total_parciales}</strong></div>
            <div class="kpi violeta"><span>Eventos corrector</span><strong>{total_correcciones}</strong></div>
        </section>

        <section class="tabla-card" aria-label="Resultados por sesión">
            <div class="tabla-scroll">
                <table>
                    <thead>
                        <tr>
                            <th scope="col">Sesión</th><th scope="col">Análisis</th>
                            <th scope="col">Estado</th><th scope="col">Reserva</th>
                            <th scope="col">Turno vigente</th><th scope="col">Solicitud pendiente</th>
                            <th scope="col">Aspectos</th><th scope="col">Eventos / errores</th>
                            <th scope="col">Detalle</th>
                        </tr>
                    </thead>
                    <tbody>{filas_html}</tbody>
                </table>
            </div>
        </section>
        <footer>Generado automáticamente por el compilador determinista de reservas y turnos.</footer>
    </main>
    <script>
        function toggleDetalle(id, boton) {{
            const fila = document.getElementById('detalle-' + id);
            const abrir = fila.hidden;
            fila.hidden = !abrir;
            boton.setAttribute('aria-expanded', String(abrir));
            boton.textContent = abrir ? 'Ocultar evidencias' : 'Evidencias';
        }}
    </script>
</body>
</html>
'''

        ruta.write_text(html, encoding="utf-8")
        return ruta
