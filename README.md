# Auditor Remuneracional Ley Médica HPH

Aplicación local en Python y Streamlit para apoyar la auditoría remuneracional mensual del Hospital Padre Alberto Hurtado. Permite comparar dos archivos Excel exportados desde SIRH, APLANO, SAE u otras planillas, detectar diferencias por llave compuesta y código de haber, clasificar una causa probable conservadora y exportar un reporte Excel.

## Instalación

1. Instala Python 3.10 o superior desde [python.org](https://www.python.org/downloads/).
2. Abre una terminal en esta carpeta.
3. Instala las dependencias:

```powershell
python -m pip install -r requirements.txt
```

## Ejecución rápida

En Windows, puedes abrir la app ejecutando:

```powershell
.\iniciar_app.bat
```

## Ejecución manual

```powershell
python -m streamlit run app.py
```

La aplicación funciona localmente. No se conecta a SIRH, no solicita credenciales institucionales y no envía información a servicios externos.

## Archivos a cargar

Carga dos archivos Excel:

- Mes anterior.
- Mes actual.

Cada archivo puede venir desde SIRH, APLANO, SAE u otra planilla remuneracional. La app permite elegir la hoja de cada archivo y mapear columnas manualmente si los nombres no coinciden.

La app incluye una capa de normalización interna. Aunque los archivos planos de Ley 15.076, Ley 19.664, Ley 18.834, APLANO o SAE usen nombres de columnas distintos, el mapeo convierte la base a un esquema común antes de comparar. La auditoría trabaja con campos internos como `RUN`, `LEY`, `CARGO_CORRELATIVO`, `CODIGO_HABER`, `MONTO`, `TIPO_PROCESO` y campos opcionales de contexto.

En el mapeo se puede elegir un perfil de base:

- `Autodetectar`
- `APLANO Ley 15.076`
- `APLANO Ley 19.664`
- `APLANO Ley 18.834`
- `SAE Ley 19.664`
- `Base personalizada`

El perfil solo sugiere mapeos iniciales. El usuario siempre puede corregir manualmente cada columna.

## Columnas sugeridas

La llave de comparación sugerida es:

- RUN
- DV
- Ley
- Jornada
- Correlativo real cargo
- Centro de costo
- Código de haber
- Tipo proceso, si existe
- Corr pago, si existe

Además, para comparar haberes se requiere mapear:

- RUN
- Código de haber
- Nombre de haber
- Monto
- Porcentaje, si existe
- Tipo proceso, si existe

`Mes pago`, `Mes devengo` y `Periodo devengo` no forman parte de la llave base mensual. Se mantienen como datos informativos y para construir una llave analítica de devengo en pagos accesorios, retroactivos, pendientes o planillas suplementarias. Esto evita que un pago ordinario normal aparezca artificialmente como código eliminado en un mes y código nuevo en el siguiente solo porque cambió el mes de pago.

También se pueden mapear campos opcionales para enriquecer la causa probable y la observación, sin cambiar la llave principal ni reemplazar la comparación por código de haber:

- Días trabajados o días a pago.
- Calidad jurídica, grado/nivel, fechas de ingreso o término.
- Tipo de ausentismo, observación, tipo de movimiento o contrato.
- Planilla suplementaria, periodo de devengo, mes de pago.
- Liberado de guardia.

La app reconoce alias habituales como `CODIGO_MOVIMIENTO`, `NOMBRE_MOVIMIENTO`, `JORNADA_HORAS`, `CORRELATIVO_CARGO`, `MONTO_PAGO` y `CENTRO_COSTO`.

Si no se mapea RUN, Monto o Código de haber, la app bloquea la ejecución. Sin Código de haber no es posible auditar por línea remuneracional.

Campos recomendados para mejorar trazabilidad e interpretación: DV, Nombre, Ley, Jornada, Cargo/correlativo, Corr pago, Centro de costo, Nombre de haber y Tipo proceso. Si las bases parecen tener estructuras o leyes distintas y no hay una columna Ley clara, la app advierte que la interpretación de causas probables dependerá de ese dato.

Para bases con múltiples cargos, se recomienda distinguir:

- `Nro correlativo cargo`: número interno simple del archivo, por ejemplo 1, 2 o 3.
- `Correlativo real cargo`: identificador más estable del vínculo o cargo. Si existe, debe preferirse para la llave.
- `ID cargo`: identificador auxiliar cuando la base lo trae.

Si no se mapea el correlativo real y sí existe un número correlativo, la app puede usarlo como respaldo junto con Ley, Jornada y Centro de costo, pero mostrará una advertencia porque hay riesgo de consolidar cargos que no corresponden.

El código de haber se trata como texto y se rellena con ceros a la izquierda. El largo por defecto es de 4 dígitos y puede ajustarse en la configuración de auditoría. La Ley también se trata como texto para evitar valores como `19.664000`.

## Interpretación de resultados

La app separa:

- Diferencia detectada objetivamente.
- Tipo de diferencia.
- Causa probable.
- Observación.
- Nivel de alerta.
- Dato faltante, cuando corresponde.

`DIF_DETALLE` muestra una fila por código de haber con diferencia. Es la base trazable de todo el análisis: montos anterior/actual, diferencia, tipo de diferencia, causa probable, alerta y observación.

`TIPO_DIFERENCIA` separa hechos como código nuevo, código eliminado, funcionario nuevo, funcionario ausente, diferencia de monto, registro consolidado o revisión requerida.

`Causa probable` clasifica el haber usando palabras clave presentes en el código, nombre del haber y campos opcionales cuando existen. Identifica categorías de Ley 15.076, Ley 19.664 y transversales, como sueldo base, trienios/antigüedad, Art. 39 DL 3551, Art. 65 Ley 18.482, falencia por especialidad, HNDyF/Sistema 1, liberado de guardia Art. 44, experiencia calificada EDF/EPS, reforzamiento profesional diurno, responsabilidad, estímulo/competencias, jornadas prioritarias, proyecto específico, especialidad/permanencia, desempeño individual/colectivo, planilla suplementaria HPH Ley 21.095, días trabajados/ausentismo, permiso sin goce, licencia médica, comisión de servicio y retroactivos/accesorios.

Para permisos sin goce, comisiones, licencias y días trabajados se requiere que la base traiga esos campos o que se cargue información complementaria. Si esos campos no están presentes, la app no infiere automáticamente ausentismo solo por una baja de monto.

`RESUMEN_FUNCIONARIOS` corresponde al resumen base por funcionario/cargo. Se construye desde `DIF_DETALLE` y agrupa diferencias por RUN, ley, jornada, cargo, corr pago, unidad y centro de costo. Muestra diferencia positiva, negativa, neta y absoluta, códigos involucrados, causa principal, nivel máximo de alerta y una explicación breve en lenguaje administrativo.

`CONTROL_ESTIMULOS_19664` es un control conceptual orientativo para Ley 19.664. Agrupa por RUN, cargo/correlativo y jornada, suma por separado los porcentajes del mes anterior y del mes actual asociados a estímulo/competencias, jornadas prioritarias, proyecto específico, condiciones/lugares de trabajo u hospitalista, y alerta si el mes actual supera 180%. No suma ambos meses en un solo total y no incluye asignación de responsabilidad dentro de ese tope. Este control depende de que los porcentajes estén correctamente informados.

`REVISION_SUGERIDA` consolida recomendaciones administrativas desde `DIF_DETALLE`, `RESUMEN_FUNCIONARIOS` y el control de estímulos. Propone documentos o sistemas a validar y prioridad de revisión, sin concluir pago indebido, deuda ni error.

Para liberados de guardia Ley 15.076, la app solo alerta por glosa o código. No reemplaza la revisión de relación de servicio, resolución o respaldo administrativo.

`MULTICARGOS_DETECTADOS` identifica RUN con más de un vínculo remuneracional probable, considerando combinaciones de Ley, Jornada, Cargo/correlativo, Centro de costo y Corr pago cuando corresponde. Si hay múltiples vínculos y no se mapeó Cargo/correlativo, la app recomienda mapear un identificador único del cargo para evitar consolidaciones incorrectas.

`TIPO_PAGO_ANALITICO` separa los movimientos en `Ordinario del mes`, `Accesorio`, `Retroactivo`, `Pago pendiente`, `Planilla suplementaria HPH`, `Cobranza / reintegro / descuento especial` o `Requiere revisión`.

`Mes pago` indica el mes en que el movimiento fue pagado. `Mes devengo` o `Periodo devengo` indica el periodo al que corresponde el derecho, ajuste o diferencia. Si el devengo es distinto del mes de pago, la app no excluye el movimiento: lo conserva porque fue pagado en el mes, pero lo marca como posible retroactivo, accesorio o pendiente para revisión.

Los pagos accesorios, retroactivos y pendientes se muestran en una sección específica y en la hoja `ACCESORIOS_RETROACTIVOS`. Esto permite revisar variaciones que no corresponden al pago ordinario puro del mes.

Las cobranzas, reintegros, restituciones, descuentos especiales y referencias a Contraloría/CGR se agrupan como `Cobranza / reintegro / descuento especial` y se exportan en `COBRANZAS_REINTEGROS`. La app no concluye que el cobro sea correcto o incorrecto; solo sugiere validar resolución, oficio, acto administrativo o respaldo correspondiente.

En la configuración de auditoría se puede elegir si el resumen general incluye accesorios:

- Sí, incluir todo lo pagado en el mes.
- No, mostrar solo pago ordinario.
- Mostrar ambos resúmenes.

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
- `RESUMEN_FUNCIONARIOS`
- `TOP_FUNCIONARIOS_RESUMEN`
- `TOP_CODIGOS_RESUMEN`
- `REVISION_SUGERIDA`
- `CONTROL_ESTIMULOS_19664`
- `MULTICARGOS_DETECTADOS`
- `ACCESORIOS_RETROACTIVOS`
- `COBRANZAS_REINTEGROS`
- `FUNCIONARIOS_NUEVOS`
- `FUNCIONARIOS_AUSENTES`
- `CODIGOS_NUEVOS`
- `CODIGOS_ELIMINADOS`
- `CONFIG_MAPEO`
- `CONFIG_USADA`

La hoja `CASOS_ALERTA` incluye todos los casos con alerta `Medio`, `Alto` o `Revisión manual`.

La hoja `RESUMEN` incluye un resumen ejecutivo automático con principales aumentos, principales disminuciones, funcionarios con mayor diferencia absoluta, códigos de haber con mayor variación total y cantidad de casos que requieren revisión manual.

## Prueba con base real reducida

Para una prueba controlada con información institucional, usa una copia reducida o anonimizada de la base. La validación debe hacerse en una carpeta local ignorada por Git, fuera del repositorio si contiene datos personales o remuneracionales reales.

Campos mínimos requeridos:

- `RUN`
- `Código haber`
- `Monto`

Campos altamente recomendados:

- `Ley`
- `Jornada`
- `Correlativo real cargo`
- `Centro de costo`
- `Tipo proceso`
- `Corr pago`
- `Mes pago`
- `Mes devengo`
- `Nombre haber`

Advertencia de privacidad: no subas bases reales a GitHub, no subas RUN ni remuneraciones reales a servicios externos, y no guardes archivos reales dentro del repositorio. Si necesitas conservar evidencias de prueba, usa nombres de archivo neutros y una carpeta local excluida por `.gitignore`.

## Datos ficticios

La carpeta `data_ejemplo` contiene dos archivos Excel ficticios para probar la aplicación:

- `mes_anterior_hph.xlsx`
- `mes_actual_hph.xlsx`

No contienen datos personales reales.

## Privacidad y Seguridad

La aplicación trabaja localmente y no se conecta a SIRH, SAE, APIs externas ni bases institucionales. No subas bases reales a GitHub ni a servicios externos. No guardes archivos con datos personales reales en el repositorio.

## Advertencias de uso

Esta herramienta compara pagos y no concluye automáticamente pago indebido, deuda ni error de pago. Entrega diferencias objetivas, causa probable y alertas para revisión. Las conclusiones finales deben ser validadas por Gestión de Personas y por los respaldos administrativos o jurídicos correspondientes.
