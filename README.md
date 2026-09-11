# Gobierno de TI en Nueva EPS: diagnóstico y modelo de gobierno de datos y sistemas

Proyecto del curso **Gerencia y Gobierno de TI** (Maestría en Analítica Aplicada, Universidad de La Sabana), 2026-2.

**Caso:** Nueva EPS S.A. (Colombia), bajo intervención forzosa administrativa de la Superintendencia Nacional de Salud desde abril de 2024.

**Reto de gobierno:** la entidad no logra procesar, auditar ni reportar de forma oportuna y confiable la información de su proceso de cuentas médicas (rezago de 14,2 millones de facturas por 14,9 billones de pesos e incumplimiento del reporte regulatorio desde febrero de 2024). El proyecto diagnostica las brechas de gobierno de TI que explican esa situación y propone un modelo de gobierno basado en COBIT 2019, ITIL 4 y NIST AI RMF, soportado en evidencia analítica reproducible construida con datos abiertos.

## Pregunta central de gobierno

¿Qué mecanismos de gobierno de TI (estructuras de decisión, políticas de gobierno de datos y control de los recursos tecnológicos) debe implementar Nueva EPS para que su capacidad de procesar, auditar y reportar la información de cuentas médicas sea oportuna, trazable y conforme con las exigencias de la Supersalud, sin comprometer la continuidad de la atención a sus afiliados?

## Pregunta analítica (SMART)

¿En qué magnitud y con qué heterogeneidad territorial se asocian las fallas del proceso de cuentas médicas de Nueva EPS (aproximadas por el flujo de giro directo a prestadores) con el deterioro del acceso de sus afiliados (tasa mensual de PQRD por cada 1.000 afiliados), en los 32 departamentos y Bogotá, entre enero de 2022 y diciembre de 2025, y qué departamentos y prestadores deberían priorizarse en el plan de saneamiento?

## Fuentes de datos

| Código | Fuente | Contenido | Acceso |
|---|---|---|---|
| F1 | Superintendencia Nacional de Salud, Datos Abiertos | PQRD por EPS, departamento, motivo y mes (2018 en adelante) | https://www.supersalud.gov.co (sección Datos abiertos) |
| F2 | ADRES, Analítica, tablero Giro Directo | Valor girado por régimen, EPS ordenadora, IPS, municipio y mes (2020 en adelante) | https://www.adres.gov.co/analitica |
| F3 | Ministerio de Salud, SISPRO / BDUA | Afiliados por EPS, régimen y municipio (denominador) | https://www.sispro.gov.co |

La evaluación de calidad, completitud y trazabilidad de cada fuente está en `data/README.md` y en la Sección 7 del Entregable 1.

## Estructura del repositorio

```
gobierno_ti_nuevaeps/
  README.md                 este archivo
  data/
    README.md               diccionario de fuentes y registro de calidad
    raw/                    descargas originales, inmutables (no se editan)
    processed/              panel integrado y tablas derivadas
  src/
    ingest.py               descarga y registro (hash, fecha) de las fuentes
    clean.py                estandarización, validación y reglas de calidad
    build_panel.py          integración del panel departamento x mes
    model.py                series interrumpidas, panel e índice de priorización
  notebooks/                exploración y figuras
  docs/
    entregables/            Canvas, Bitácora #1, Entregable 1 (PDF)
    figuras/                mapa de brechas, pipeline, cronograma
```

## Pipeline

Ingesta -> limpieza y validación -> integración (panel por EPS y mes, 2019 a 2026, y panel departamental mensual, 2022 a 2025) -> modelado (series interrumpidas y diferencias en diferencias a nivel EPS; regresión de panel e índice de priorización a nivel departamental) -> validación (placebos, sensibilidad, auditoría de sesgo).

Estado de la evaluación de fuentes (12 de septiembre de 2026): 6.574.638 PQRD procesadas (Nueva EPS 2025: 518.191 frente a 518.211 de la Contraloría); 909.129 registros de giro directo de Nueva EPS, 87 % georreferenciados por NIT con el REPS; 11.278.956 afiliados de Nueva EPS en el BDUA. El giro contributivo por prestador solo es masivo desde 2024 y el subsidiado por prestador termina en octubre de 2024; la serie subsidiada por EPS (2019 a 2026) es la única continua a través de la intervención.

Ver `docs/figuras/pipeline.png`.

## Cómo reproducir

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/ingest.py        # descarga a data/raw y registra hash y fecha
python src/clean.py         # genera data/processed/*_clean.csv y quality_log.md
python src/build_panel.py   # genera data/processed/panel_depto_mes.csv
python src/model.py         # estimaciones y figuras en docs/figuras
```

## Consideraciones éticas

Se utilizan exclusivamente datos agregados publicados por autoridades públicas. No se procesan microdatos ni identificadores de pacientes (Ley 1581 de 2012, datos sensibles de salud). El modelo de priorización se documenta bajo NIST AI RMF (Govern, Map, Measure, Manage) e incluye auditoría de sesgo por régimen y ruralidad y supervisión humana obligatoria.

## Marcos de referencia

COBIT 2019 (marco principal), ITIL 4 (gestión del servicio y de proveedores), NIST AI RMF 1.0 y Ley de IA de la UE (gobierno del componente analítico), Marco de Referencia de Arquitectura Empresarial y MGGTI de MinTIC (conformidad nacional), normativa sectorial colombiana (Ley 1581 de 2012, Ley 2015 de 2020, Resoluciones 2275 de 2023 y 948 de 2026, Circular Única de Supersalud).

## Cronograma

Siete semanas, del 31 de agosto al 18 de octubre de 2026: Unidad 1 (31 de agosto al 11 de septiembre, cierre de entregas el 13), Unidad 2 (12 al 20 de septiembre), Unidad 3 (21 de septiembre al 4 de octubre) y Unidad 4 (5 al 18 de octubre). Hitos: Entregable 1 (13 de septiembre), Entregable 2, PETI y modelo de gobierno (4 de octubre), Informe final y presentación ejecutiva (18 de octubre). Ver `docs/figuras/gantt.png`.

## Equipo

* Felix Mauricio Campo Ariza (@felmaur-prog) y Pablo Andrés Toledo Lugo: diagnóstico organizacional, ciencia de datos y repositorio, marcos de referencia (COBIT 2019, ITIL 4, MGGTI), cumplimiento normativo, reflexión ética (NIST AI RMF, ODS 9.b), diseño del modelo de gobierno y presentación ejecutiva.

## Licencia

Contenido académico. Código bajo licencia MIT; los datos pertenecen a sus entidades publicadoras y se citan en cada uso.
