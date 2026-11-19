"""Tabla de símbolos con un ámbito independiente por sesión."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenciaSemantica:
    turno: int
    actor: str
    aspecto: str
    valoracion: str
    regla: str
    texto: str

    def como_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EntradaSesion:
    id_sesion: str
    reserva_id: str | None = None
    turno_vigente: dict[str, str] | None = None
    solicitud_pendiente: dict[str, str] | None = None
    estado_conversacional: str = "SIN_CONFIRMAR"
    analisis_estado: str = "COMPLETO"
    evidencias: list[EvidenciaSemantica] = field(default_factory=list)
    correcciones: list[dict[str, Any]] = field(default_factory=list)
    errores: list[dict[str, Any]] = field(default_factory=list)
    trazas: list[dict[str, Any]] = field(default_factory=list)
    menciones_reserva: int = 0


class TablaSimbolos:
    """Almacena entidades conversacionales; no contiene el vocabulario del lexer."""

    def __init__(self):
        self.sesiones: dict[str, EntradaSesion] = {}
        self.sesion_actual: EntradaSesion | None = None

    def abrir_sesion(self, id_sesion: str) -> EntradaSesion:
        entrada = self.sesiones.setdefault(id_sesion, EntradaSesion(id_sesion))
        self.sesion_actual = entrada
        return entrada

    def cerrar_sesion(self) -> None:
        self.sesion_actual = None

    def registrar_o_enlazar_reserva(self, codigo_rs: str, turno: int, linea: str) -> str:
        if not self.sesion_actual:
            return "Sin sesión activa"
        codigo = codigo_rs.upper()
        if self.sesion_actual.reserva_id is None:
            self.sesion_actual.reserva_id = codigo
            accion = f"Insertar reserva_id={codigo}"
        elif self.sesion_actual.reserva_id == codigo:
            accion = f"Enlazar mención con reserva_id={codigo}"
        else:
            self.registrar_error(
                turno,
                f"Conflicto de reservas: {self.sesion_actual.reserva_id} y {codigo}",
                linea,
            )
            accion = f"Rechazar reserva conflictiva {codigo}"
        self.sesion_actual.menciones_reserva += 1
        return accion

    def establecer_turno_vigente(self, dia: str, hora: str) -> None:
        if self.sesion_actual:
            self.sesion_actual.turno_vigente = {"dia": dia, "hora": hora}

    def establecer_solicitud_pendiente(self, dia: str, hora: str) -> None:
        if self.sesion_actual:
            self.sesion_actual.solicitud_pendiente = {"dia": dia, "hora": hora}

    def confirmar_reprogramacion(self, dia: str | None = None, hora: str | None = None) -> None:
        if not self.sesion_actual:
            return
        if dia is not None and hora is not None:
            self.sesion_actual.turno_vigente = {"dia": dia, "hora": hora}
        elif self.sesion_actual.solicitud_pendiente:
            self.sesion_actual.turno_vigente = dict(self.sesion_actual.solicitud_pendiente)
        self.sesion_actual.solicitud_pendiente = None
        self.sesion_actual.estado_conversacional = "REPROGRAMADA"

    def efectuar_cancelacion(self) -> None:
        if self.sesion_actual:
            self.sesion_actual.turno_vigente = None
            self.sesion_actual.solicitud_pendiente = None
            self.sesion_actual.estado_conversacional = "CANCELADA"

    def registrar_evidencia(
        self,
        turno: int,
        actor: str,
        aspecto: str,
        valoracion: str,
        regla: str,
        texto: str,
    ) -> None:
        if self.sesion_actual:
            self.sesion_actual.evidencias.append(
                EvidenciaSemantica(turno, actor, aspecto, valoracion, regla, texto)
            )

    def registrar_correccion(
        self, turno: int, original: str, corregido: str, motivo: str
    ) -> None:
        if self.sesion_actual:
            tipo = "ABSTENCION" if original == corregido else "CORRECCION"
            self.sesion_actual.correcciones.append(
                {
                    "turno": turno,
                    "tipo": tipo,
                    "original": original,
                    "corregido": corregido,
                    "motivo": motivo,
                }
            )

    def registrar_error(self, turno: int, mensaje: str, linea: str) -> None:
        if self.sesion_actual:
            self.sesion_actual.errores.append(
                {"turno": turno, "mensaje": mensaje, "linea": linea}
            )
            self.sesion_actual.analisis_estado = "PARCIAL"

    def registrar_traza(self, traza: dict[str, Any]) -> None:
        if self.sesion_actual:
            self.sesion_actual.trazas.append(traza)

    def obtener_resumen_aspectos(self, id_sesion: str) -> dict[str, str]:
        sesion = self.sesiones.get(id_sesion)
        resumen = {
            "RESERVA": "SIN_EVIDENCIA",
            "ATENCION": "SIN_EVIDENCIA",
            "CLARIDAD": "SIN_EVIDENCIA",
        }
        if not sesion:
            return resumen

        for aspecto in resumen:
            valores = {
                evidencia.valoracion
                for evidencia in sesion.evidencias
                if evidencia.aspecto == aspecto
            }
            if {"POSITIVA", "NEGATIVA"} <= valores:
                resumen[aspecto] = "MIXTA"
            elif "POSITIVA" in valores:
                resumen[aspecto] = "POSITIVA"
            elif "NEGATIVA" in valores:
                resumen[aspecto] = "NEGATIVA"
            elif "NEUTRA" in valores:
                resumen[aspecto] = "NEUTRA"
        return resumen
