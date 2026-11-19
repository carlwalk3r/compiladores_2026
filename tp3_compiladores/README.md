# TP3 — Análisis de conversaciones sobre reservas y turnos

Proyecto modular en Python para el análisis léxico, sintáctico y semántico de
conversaciones. No utiliza dependencias externas.

## Requisitos

- Python 3.10 o superior.
- Biblioteca estándar de Python.

## Estructura

```text
tp3_compiladores/
├── data/casos.txt
├── src/
│   ├── __init__.py
│   ├── spellchecker.py
│   ├── lexer.py
│   ├── symbol_table.py
│   ├── parser_sdt.py
│   └── reporter.py
├── main.py
├── README.md
└── requirements.txt
```

## Ejecución

Desde esta carpeta:

```bash
python3 main.py data/casos.txt
```

En instalaciones donde el intérprete se publica como `python`, el comando
equivalente es `python main.py data/casos.txt`.

También puede ejecutarse sin argumento; en ese caso se usa `data/casos.txt`:

```bash
python3 main.py
```

El programa muestra el resumen de cada sesión y genera tres archivos:

- `resultado_sesiones.json`, para evaluación automatizada.
- `trazabilidad_completa.txt`, con el paso a paso de S01 a S12.
- `reporte.html`, dashboard visual con indicadores y evidencias desplegables.

## Decisiones de diseño

- El corrector usa la matriz dinámica de Levenshtein y solo corrige cuando hay
  un candidato único a distancia uno.
- `no`, códigos `RS-`, días, horas y números están protegidos.
- La normalización elimina diferencias de mayúsculas y tildes, conservando
  siempre el lexema original.
- El vocabulario pertenece al lexer y permanece separado de la tabla de
  símbolos.
- El parser aplica la gramática predictiva documentada en `parser_sdt.py` y
  separa las cláusulas enlazadas mediante `pero`.
- Los errores de rol o numeración activan recuperación en modo pánico: se
  descarta la línea, se sincroniza con el turno siguiente y la sesión queda
  marcada como `PARCIAL`.
- Una solicitud no sustituye al turno vigente hasta recibir confirmación del
  agente.
- Las evidencias contradictorias se conservan y producen el resumen `MIXTA`.

## Resultados esperados principales

- S01: `PENDIENTE`.
- S02: `REPROGRAMADA`.
- S03: `CONFIRMADA`.
- S04: `CANCELADA`.
- S05: claridad negativa y atención positiva.
- S06: corrección `resrva` → `reserva`.
- S07: `PARCIAL` y `PENDIENTE`.
- S08: abstención para `cambi`.
- S09: atención negativa y claridad positiva.
- S10: atención mixta.
- S11: `PARCIAL` por salto de turno.
- S12: `PENDIENTE`, sin cancelar el turno vigente.
