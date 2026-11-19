"""Analizador léxico determinista con trazabilidad y normalización."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Callable

from src.spellchecker import CorrectorOrtografico, normalizar_texto


@dataclass(frozen=True)
class Token:
    tipo: str
    lexema_original: str
    lexema_normalizado: str
    sesion: str
    turno: int
    offset: int

    def como_dict(self) -> dict[str, str | int]:
        return asdict(self)


class Lexer:
    """Convierte cada intervención en una secuencia estable de tokens."""

    VOCABULARIO_CANONICO = {
        "a", "al", "atencion", "atendieron", "bien", "buen", "buena", "cambia", "cambio",
        "cambiar", "cancele", "cancelacion", "cancelar", "cliente", "confirmada",
        "confirmado", "confirmaron", "desastre", "dia", "el", "entendi", "excelente",
        "explicacion", "fue", "hola", "la", "mal", "me", "mi", "muy", "no",
        "para", "pasarla", "pero", "pesimo", "quedo", "quiero", "recepcion",
        "reserva", "si", "solicite", "tengo", "un", "una", "voy", "ya",
    }
    DIAS = {"lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"}
    PATRON_RS = re.compile(r"^RS-\d{3,6}$", re.IGNORECASE)
    PATRON_HORA = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    PATRON_TOKEN = re.compile(
        r"RS-\d{3,6}|(?:[01]\d|2[0-3]):[0-5]\d|[^\W\d_]+(?:-[^\W\d_]+)*|\d+|[.,;:!?]",
        re.UNICODE | re.IGNORECASE,
    )

    def __init__(self, corrector: CorrectorOrtografico | None = None):
        self.corrector = corrector or CorrectorOrtografico(self.VOCABULARIO_CANONICO)

    def tokenizar_texto(
        self,
        texto: str,
        id_sesion: str,
        num_turno: int,
        registrar_evento_cb: Callable[[int, str, str, str], None] | None = None,
    ) -> list[Token]:
        tokens: list[Token] = []

        for coincidencia in self.PATRON_TOKEN.finditer(texto):
            original = coincidencia.group(0)
            offset = coincidencia.start()

            if original in {".", ",", ";", ":", "!", "?"}:
                tokens.append(Token("PUNTUACION", original, original, id_sesion, num_turno, offset))
                continue

            if self.PATRON_RS.fullmatch(original):
                tokens.append(Token("COD_RESERVA", original, original.upper(), id_sesion, num_turno, offset))
                continue

            if self.PATRON_HORA.fullmatch(original):
                tokens.append(Token("HORA", original, original, id_sesion, num_turno, offset))
                continue

            if original.isdigit():
                tokens.append(Token("NUMERO", original, original, id_sesion, num_turno, offset))
                continue

            corregido, detalle = self.corrector.corregir(original)
            if detalle and registrar_evento_cb:
                registrar_evento_cb(num_turno, original, corregido, detalle)

            normalizado = normalizar_texto(corregido)
            tipo = self._categorizar(normalizado)
            tokens.append(Token(tipo, original, normalizado, id_sesion, num_turno, offset))

        return tokens

    def _categorizar(self, lexema: str) -> str:
        if lexema in self.DIAS:
            return "DIA"
        if lexema == "pero":
            return "CONJ_PERO"
        if lexema == "no":
            return "ADV_NEG"
        if lexema == "muy":
            return "ADV_INTENS"
        if lexema in {"confirmada", "confirmado", "confirmaron"}:
            return "KW_CONFIRMACION"
        if lexema in {"cancelar", "cancele", "cancelacion"}:
            return "KW_CANCELAR"
        if lexema in {"cambio", "cambiar", "cambia", "pasarla", "solicite"}:
            return "KW_CAMBIO"
        if lexema in {"desastre", "mal", "pesimo"}:
            return "VAL_NEG"
        if lexema in {"bien", "excelente", "buena", "buen"}:
            return "VAL_POS"
        if lexema in {"atencion", "atendieron"}:
            return "ASP_ATENCION"
        if lexema in {"explicacion", "entendi"}:
            return "ASP_CLARIDAD"
        if lexema == "reserva":
            return "ASP_RESERVA"
        return "PALABRA"
