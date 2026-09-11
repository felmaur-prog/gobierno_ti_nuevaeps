# Diccionario de fuentes y registro de calidad

Todos los archivos crudos van en `data/raw` con los nombres indicados. No se editan a mano.

| Nombre en data/raw | Origen | Contenido | Ventana | Uso |
|---|---|---|---|---|
| F1_pqrd_2022.csv, F1_pqrd_2023_1.csv, F1_pqrd_2023_2.csv, F1_pqrd_2024_1.csv, F1_pqrd_2024_2.csv, F1_pqrd_2025_1.csv, F1_pqrd_2025_2.zip | Supersalud, Datos Abiertos | Una fila por reclamación: EPS, régimen, departamento del afectado, mes, motivo, riesgo | 2022 a 2025 | Variable de resultado (tasa de PQRD) |
| F2_giro_contributivo_ips_2020_2026.xlsx | ADRES vía Así Vamos en Salud | Giro directo contributivo por EPS, IPS (NIT) y mes | 2020-01 a 2026-04 (masivo solo desde 2024: 25 IPS en 2023, 1.614 en 2024) | Flujo de pagos contributivo |
| F2_giro_contributivo_adres_2026_05.xlsx, _06, _07 | ADRES (hoja "Giro a IPS - Proceso", datos desde la fila 11) | Igual que el anterior, un mes por archivo | 2026-05 a 2026-07 | Extiende la serie |
| F2_giro_subsidiado_ips_2020_2024.xlsx | ADRES vía Así Vamos en Salud | Giro directo subsidiado por EPS, IPS y mes | 2020-01 a 2024-10 | Flujo de pagos subsidiado por prestador |
| F2_giro_subsidiado_eps_2019_2026.xlsx | ADRES vía Así Vamos en Salud | LMA por EPS y mes: UPC neta, giro directo a prestadores, giro neto a EPS | 2019 a 2026-05 | Flujo subsidiado a nivel EPS (cubre el vacío 2024-11 en adelante) |
| F2_lma_certificacion_2026_06.xlsx, _07, _08, _09 | ADRES | Certificación mensual de giro a EPS subsidiado | 2026-06 a 2026-09 | Extiende la serie EPS |
| F3_bdua_contributivo.csv, F3_bdua_subsidiado.csv | Datos abiertos (BDUA) | Afiliados activos por EPS, régimen, departamento y municipio; Nueva EPS suma 11.278.956 | corte 7 de septiembre de 2026 | Denominador territorial |
| F3_lma_detalle_2022.xlsx, _2023, _2024, _2025, _2026.xlsb | ADRES, Resumen LMA consolidado | UPC apropiada y neta por municipio, EPS y mes (subsidiado); se usan solo las 11 primeras columnas | 2022 a 2026 | Denominador mensual subsidiado por departamento |
| F4_reps_prestadores.xls | MinSalud, REPS (exportación por prestador; es una tabla HTML con extensión .xls) | NIT, nombre, departamento y municipio de 61.180 prestadores; 50.445 con NIT y departamento válidos | corte 11 de septiembre de 2026 | Asigna departamento a cada IPS del giro directo (87 % de cruce) |

Códigos de Nueva EPS: EPS037 (contributivo), EPSS41 (subsidiado), EPS041 (contributivo por movilidad). Los tres se agrupan como NUEVA EPS.

## Reglas de calidad (src/clean.py)

1. Completitud por variable y por mes; umbral de alerta 90 %.
2. Unicidad de la llave (fuente, EPS, departamento, mes).
3. Códigos DANE de departamento válidos (dos dígitos, con cero a la izquierda).
4. Coherencia temporal: meses faltantes documentados, no imputados en silencio.
5. Contraste externo: PQRD de Nueva EPS por año frente a cifras de la Contraloría (177.479 en 2022, 518.211 en 2025).

Resultados de cada corrida en `data/processed/quality_log.md`.
