# Auditor Remuneracional Ley Médica HPH

Aplicación local en Python y Streamlit para apoyar la auditoría remuneracional mensual del Hospital Padre Alberto Hurtado. Permite comparar dos archivos Excel exportados desde SIRH, APLANO, SAE u otras planillas, detectar diferencias por llave compuesta y código de haber, clasificar una causa probable conservadora y exportar un reporte Excel.

## Instalación

1. Instala Python 3.10 o superior desde [python.org](https://www.python.org/downloads/).
2. Abre una terminal en esta carpeta.
3. Instala las dependencias:

```powershell
python -m pip install -r requirements.txt
```

## Ejecución

```powershell
streamlit run app.py
```

La aplicación funciona localmente. No se conecta a SIRH, no solicita credenciales institucionales y no envía información a servicios externos.

## Archivos a cargar

Carga dos archivos Excel:

- Mes anterior.
- Mes actual.

Cada archivo puede venir desde SIRH, APLANO, SAE u otra planilla remuneracional. La app permite elegir la hoja de cada archivo y mapear columnas manualmente si los nombres no coinciden.

## Columnas sugeridas

La llave de comparación sugerida es:

- RUN
- DV
- Ley
- Jornada
- Cargo/correlativo
- Centro de costo
- Código de haber

Además, para comparar haberes se requiere mapear:

- RUN
- Código de haber
- Nombre de haber
- Monto
- Porcentaje, si existe
- Tipo proceso, si existe

La app reconoce alias habituales como `CODIGO_MOVIMIENTO`, `NOMBRE_MOVIMIENTO`, `JORNADA_HORAS`, `CORRELATIVO_CARGO`, `MONTO_PAGO` y `CENTRO_COSTO`.

Si no se mapea RUN, Monto o Código de haber, la app bloquea la ejecución. Sin Código de haber no es posible auditar por línea remuneracional.

El código de haber se trata como texto y se rellena con ceros a la izquierda. El largo por defecto es de 4 dígitos y puede ajustarse en la configuración de auditoría. La Ley también se trata como texto para evitar valores como `19.664000`.

## Interpretación de resultados

La app separa:

- Diferencia detectada objetivamente.
- Tipo de diferencia.
- Causa probable.
- Observación.
- Nivel de alerta.
- Dato faltante, cuando corresponde.

`TIPO_DIFERENCIA` separa hechos como código nuevo, código eliminado, funcionario nuevo, funcionario ausente, diferencia de monto, registro consolidado o revisión requerida.

`Causa probable` clasifica el haber usando palabras clave presentes principalmente en el código y nombre del haber. Identifica categorías como sueldo base, trienios/antigüedad, experiencia calificada EDF/EPS, reforzamiento profesional diurno, responsabilidad, estímulo/competencias, jornadas prioritarias, proyecto específico, especialidad/permanencia, planilla suplementaria HPH, días trabajados/ausentismo y retroactivos/accesorios.

Si no hay señales suficientes, la causa queda como `Diferencia no clasificada`. `Revisión manual` se reserva para datos mínimos faltantes, montos no numéricos o llaves duplicadas críticas.

Niveles de alerta:

- `Bajo`: diferencia menor o esperable.
- `Medio`: diferencia relevante pero explicable.
- `Alto`: diferencia significativa o potencialmente riesgosa.
- `Revisión manual`: no existen datos suficientes o la llave es ambigua.

## Reporte Excel

El botón de descarga genera un archivo Excel con hojas como:

- `RESUMEN`
- `DIF_DETALLE`
- `CASOS_ALERTA`
- `PRINCIPALES_AUMENTOS`
- `PRINCIPALES_DISMINUCIONES`
- `TOP_CODIGOS`
- `TOP_FUNCIONARIOS`
- `FUNCIONARIOS_NUEVOS`
- `FUNCIONARIOS_AUSENTES`
- `CODIGOS_NUEVOS`
- `CODIGOS_ELIMINADOS`
- `CONFIG_USADA`

La hoja `CASOS_ALERTA` incluye todos los casos con alerta `Medio`, `Alto` o `Revisión manual`.

La hoja `RESUMEN` incluye un resumen ejecutivo automático con principales aumentos, principales disminuciones, funcionarios con mayor diferencia absoluta, códigos de haber con mayor variación total y cantidad de casos que requieren revisión manual.

## Datos ficticios

La carpeta `data_ejemplo` contiene dos archivos Excel ficticios para probar la aplicación:

- `mes_anterior_hph.xlsx`
- `mes_actual_hph.xlsx`

No contienen datos personales reales.

## Advertencias de uso

Esta herramienta no reemplaza la revisión administrativa ni jurídica. Las conclusiones finales deben ser validadas por Gestión de Personas y por los respaldos institucionales correspondientes. Evita cargar o conservar datos sensibles fuera de los procedimientos internos autorizados.
