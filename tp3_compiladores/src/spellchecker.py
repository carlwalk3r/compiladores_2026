"""Corrector ortográfico determinista acotado por Levenshtein <= 1."""

from __future__ import annotations

import re
import unicodedata


def normalizar_texto(texto: str) -> str:
    """Pasa a minúsculas y elimina marcas diacríticas de forma determinista."""
    descompuesto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def distancia_levenshtein(s1: str, s2: str) -> int:
    """Calcula la distancia de Levenshtein mediante una matriz dinámica."""
    m, n = len(s1), len(s2)
    matriz = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        matriz[i][0] = i
    for j in range(n + 1):
        matriz[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            costo = 0 if s1[i - 1] == s2[j - 1] else 1
            matriz[i][j] = min(
                matriz[i - 1][j] + 1,
                matriz[i][j - 1] + 1,
                matriz[i - 1][j - 1] + costo,
            )
    return matriz[m][n]


class CorrectorOrtografico:
    """Aplica candidato único y se abstiene si hay empate a distancia uno."""

    PATRON_RESERVA = re.compile(r"^RS-\d{3,6}$", re.IGNORECASE)
    PATRON_HORA = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    def __init__(self, diccionario_vocabulario: set[str]):
        self.vocabulario = {
            normalizar_texto(palabra) for palabra in diccionario_vocabulario
        }
        self.dias_semana = {
            "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"
        }

    def es_protegida(self, palabra: str) -> bool:
        normalizada = normalizar_texto(palabra)
        return (
            normalizada == "no"
            or normalizada in self.dias_semana
            or bool(self.PATRON_RESERVA.fullmatch(palabra))
            or bool(self.PATRON_HORA.fullmatch(palabra))
            or palabra.isdigit()
        )

    def corregir(self, palabra: str) -> tuple[str, str | None]:
        normalizada = normalizar_texto(palabra)
        if self.es_protegida(palabra) or normalizada in self.vocabulario:
            return palabra, None

        candidatos = sorted(
            voc
            for voc in self.vocabulario
            if distancia_levenshtein(normalizada, voc) == 1
        )

        if len(candidatos) == 1:
            correccion = candidatos[0]
            if palabra[:1].isupper():
                correccion = correccion.capitalize()
            detalle = (
                f"Corregido '{palabra}' -> '{correccion}' "
                "(Levenshtein=1, candidato único)"
            )
            return correccion, detalle

        if len(candidatos) > 1:
            detalle = (
                f"Empate a distancia 1 entre {candidatos}; "
                f"se conserva '{palabra}' por abstención"
            )
            return palabra, detalle

        return palabra, None
