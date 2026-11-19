"""Parser predictivo LL(1) y traducción dirigida por sintaxis (SDT).

Gramática de las intervenciones, después de validar el encabezado del turno:

    ORACION  -> CLAUSULA RESTO
    RESTO    -> CONJ_PERO CLAUSULA RESTO | epsilon
    CLAUSULA -> ELEMENTO COLA
    COLA     -> ELEMENTO COLA | epsilon
    ELEMENTO -> cualquier terminal léxico excepto CONJ_PERO

FIRST(RESTO)={CONJ_PERO, epsilon}; FOLLOW(RESTO)={EOF}. La elección de cada
producción se realiza con un único token de anticipación.
"""

from __future__ import annotations

import re
from typing import Any

from src.lexer import Lexer, Token
from src.symbol_table import TablaSimbolos


class ParserSDT:
    PATRON_SESION = re.compile(r"^SESION\s+(S\d+)$", re.IGNORECASE)
    PATRON_TURNO = re.compile(
        r"^(\d+)\s+([A-ZÁÉÍÓÚÜÑ]+)\s*:\s*(.+)$", re.IGNORECASE
    )

    def __init__(self, tabla_simbolos: TablaSimbolos, lexer: Lexer | None = None):
        self.ts = tabla_simbolos
        self.lexer = lexer or Lexer()
        self._tokens: list[Token] = []
        self._posicion = 0

    def procesar_archivo(self, lineas: list[str]) -> None:
        indice = 0
        while indice < len(lineas):
            linea = lineas[indice].strip()
            if not linea:
                indice += 1
                continue

            sesion_match = self.PATRON_SESION.fullmatch(linea)
            if not sesion_match:
                indice += 1
                continue

            id_sesion = sesion_match.group(1).upper()
            self.ts.abrir_sesion(id_sesion)
            indice += 1
            turno_esperado = 1
            encontro_fin = False

            while indice < len(lineas):
                linea_turno = lineas[indice].strip()
                if not linea_turno:
                    indice += 1
                    continue
                if linea_turno == "FIN":
                    encontro_fin = True
                    break
                if self.PATRON_SESION.fullmatch(linea_turno):
                    self.ts.registrar_error(
                        turno_esperado, "Falta FIN antes de la siguiente sesión", linea_turno
                    )
                    break
                turno_esperado = self._analizar_turno(
                    linea_turno, id_sesion, turno_esperado
                )
                indice += 1

            if not encontro_fin:
                self.ts.registrar_error(turno_esperado, "Sesión sin FIN", linea)
                self.ts.cerrar_sesion()
                continue

            self.ts.cerrar_sesion()
            indice += 1

    def _analizar_turno(
        self, linea: str, id_sesion: str, turno_esperado: int
    ) -> int:
        coincidencia = self.PATRON_TURNO.fullmatch(linea)
        if not coincidencia:
            self.ts.registrar_error(
                turno_esperado, "Encabezado de turno mal formado", linea
            )
            return turno_esperado + 1

        numero = int(coincidencia.group(1))
        rol = coincidencia.group(2).upper()
        texto = coincidencia.group(3).strip()
        siguiente_esperado = numero + 1

        if numero != turno_esperado:
            self.ts.registrar_error(
                turno_esperado,
                f"Número fuera de secuencia: esperado {turno_esperado}, recibido {numero}",
                linea,
            )
            return siguiente_esperado

        if rol not in {"CLIENTE", "AGENTE"}:
            self.ts.registrar_error(
                numero,
                f"Rol no admitido '{rol}'; se esperaba CLIENTE o AGENTE",
                linea,
            )
            return siguiente_esperado

        callback = lambda t, o, c, m: self.ts.registrar_correccion(t, o, c, m)
        tokens = self.lexer.tokenizar_texto(texto, id_sesion, numero, callback)

        antes = self._instantanea_estado()
        acciones_ts: list[str] = []
        for token in tokens:
            if token.tipo == "COD_RESERVA":
                acciones_ts.append(
                    self.ts.registrar_o_enlazar_reserva(
                        token.lexema_normalizado, numero, linea
                    )
                )

        clausulas = self._parsear_oracion(tokens, numero, linea)
        reglas: list[str] = []
        for clausula in clausulas:
            reglas.extend(self._evaluar_clausula_sdt(clausula, rol, numero))

        self.ts.registrar_traza(
            {
                "turno": numero,
                "actor": rol,
                "texto_original": texto,
                "tokens": [token.como_dict() for token in tokens],
                "estructura": f"ORACION -> {len(clausulas)} CLAUSULA(S)",
                "consultas_ts": acciones_ts,
                "acciones_semanticas": reglas,
                "estado_antes": antes,
                "estado_despues": self._instantanea_estado(),
            }
        )
        return siguiente_esperado

    def _parsear_oracion(
        self, tokens: list[Token], turno: int, linea: str
    ) -> list[list[Token]]:
        self._tokens = tokens
        self._posicion = 0
        clausulas: list[list[Token]] = []

        primera = self._clausula()
        if not primera:
            self.ts.registrar_error(turno, "Oración sin cláusula inicial", linea)
            return clausulas
        clausulas.append(primera)
        self._resto(clausulas, turno, linea)
        return clausulas

    def _resto(
        self, clausulas: list[list[Token]], turno: int, linea: str
    ) -> None:
        if self._actual() and self._actual().tipo == "CONJ_PERO":
            self._avanzar()
            clausula = self._clausula()
            if not clausula:
                self.ts.registrar_error(
                    turno, "Se esperaba una cláusula después de 'pero'", linea
                )
                return
            clausulas.append(clausula)
            self._resto(clausulas, turno, linea)
        # epsilon cuando el token de anticipación es EOF

    def _clausula(self) -> list[Token]:
        elementos: list[Token] = []
        while self._actual() and self._actual().tipo != "CONJ_PERO":
            elementos.append(self._avanzar())
        if not any(token.tipo != "PUNTUACION" for token in elementos):
            return []
        return elementos

    def _actual(self) -> Token | None:
        if self._posicion >= len(self._tokens):
            return None
        return self._tokens[self._posicion]

    def _avanzar(self) -> Token:
        token = self._tokens[self._posicion]
        self._posicion += 1
        return token

    def _evaluar_clausula_sdt(
        self, tokens: list[Token], rol: str, turno: int
    ) -> list[str]:
        palabras = [
            token.lexema_normalizado
            for token in tokens
            if token.tipo != "PUNTUACION"
        ]
        texto = " ".join(token.lexema_original for token in tokens)
        conjunto = set(palabras)
        reglas: list[str] = []
        sesion = self.ts.sesion_actual
        if not sesion:
            return reglas

        def contiene(*secuencia: str) -> bool:
            longitud = len(secuencia)
            return any(
                palabras[i : i + longitud] == list(secuencia)
                for i in range(len(palabras) - longitud + 1)
            )

        def evidencia(aspecto: str, valor: str, regla: str) -> None:
            self.ts.registrar_evidencia(turno, rol, aspecto, valor, regla, texto)
            reglas.append(regla)

        # Valoraciones: cada cláusula tiene alcance propio, incluida la negación.
        if contiene("atendieron", "muy", "bien"):
            evidencia("ATENCION", "POSITIVA", "Regla_Val_Atencion_Pos")
        elif "atencion" in conjunto and (
            contiene("no", "fue", "muy", "buena")
            or "desastre" in conjunto
            or "pesimo" in conjunto
            or "mal" in conjunto
        ):
            evidencia("ATENCION", "NEGATIVA", "Regla_Val_Atencion_Neg")
        elif "atencion" in conjunto and ({"excelente", "buena", "bien"} & conjunto):
            evidencia("ATENCION", "POSITIVA", "Regla_Val_Atencion_Pos")

        if contiene("no", "entendi", "la", "explicacion"):
            evidencia("CLARIDAD", "NEGATIVA", "Regla_Val_Claridad_Neg")
        elif "explicacion" in conjunto and "excelente" in conjunto:
            evidencia("CLARIDAD", "POSITIVA", "Regla_Val_Claridad_Pos")

        if "reserva" in conjunto and "desastre" in conjunto:
            evidencia("RESERVA", "NEGATIVA", "Regla_Val_Reserva_Neg")
        elif "reserva" in conjunto and "excelente" in conjunto:
            evidencia("RESERVA", "POSITIVA", "Regla_Val_Reserva_Pos")

        dia = next(
            (token.lexema_normalizado for token in tokens if token.tipo == "DIA"), None
        )
        hora = next(
            (token.lexema_normalizado for token in tokens if token.tipo == "HORA"), None
        )

        # Precedencia semántica: negación > confirmación/cancelación > solicitud.
        if contiene("no", "quiero", "cancelar") or contiene("no", "voy", "a", "cancelar"):
            evidencia("RESERVA", "NEUTRA", "Regla_Neg_Cancelacion")
            return reglas

        if "cambio" in conjunto and "confirmado" in conjunto and rol == "AGENTE":
            self.ts.confirmar_reprogramacion(dia, hora)
            evidencia("RESERVA", "POSITIVA", "Regla_Confirmacion_Reprogramacion")
            return reglas

        if contiene("ya", "cancele") or contiene("cancelacion", "realizada"):
            self.ts.efectuar_cancelacion()
            evidencia("RESERVA", "NEGATIVA", "Regla_Cancelacion_Efectiva")
            return reglas

        es_solicitud_cambio = (
            contiene("quiero", "pasarla")
            or contiene("quiero", "cambiar")
            or contiene("solicite", "el", "cambio")
        )
        if es_solicitud_cambio:
            sesion.estado_conversacional = "PENDIENTE"
            if dia and hora:
                self.ts.establecer_solicitud_pendiente(dia, hora)
            evidencia("RESERVA", "NEUTRA", "Regla_Solicitud_Cambio")
            return reglas

        if "reserva" in conjunto and "confirmada" in conjunto:
            sesion.estado_conversacional = "CONFIRMADA"
            if dia and hora:
                self.ts.establecer_turno_vigente(dia, hora)
            evidencia("RESERVA", "POSITIVA", "Regla_Confirmacion_Inicial")
            return reglas

        if contiene("voy", "a", "cancelar") or contiene("quiero", "cancelar"):
            sesion.estado_conversacional = "PENDIENTE"
            evidencia("RESERVA", "NEUTRA", "Regla_Intencion_Cancelacion")
        return reglas

    def _instantanea_estado(self) -> dict[str, Any]:
        sesion = self.ts.sesion_actual
        if not sesion:
            return {}
        return {
            "estado": sesion.estado_conversacional,
            "reserva_id": sesion.reserva_id,
            "turno_vigente": dict(sesion.turno_vigente) if sesion.turno_vigente else None,
            "solicitud_pendiente": (
                dict(sesion.solicitud_pendiente)
                if sesion.solicitud_pendiente
                else None
            ),
        }
