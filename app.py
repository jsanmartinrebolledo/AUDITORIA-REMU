from __future__ import annotations

import io
import re
import unicodedata
from datetime import datetime
from typing import Any

import pandas as pd

try:
    import streamlit as st
except ModuleNotFoundError:  # Permite ejecutar pruebas sin tener Streamlit instalado.
    st = None


APP_TITLE = "Auditor Remuneracional Ley Médica HPH"

STANDARD_FIELDS = {
    "RUN": "RUN",
    "DV": "DV",
    "NOMBRE": "Nombre",
    "LEY": "Ley",
    "JORNADA": "Jornada",
    "CARGO_CORRELATIVO": "Cargo/correlativo",
    "CORR_PAGO": "Corr pago",
    "UNIDAD": "Unidad",
    "CENTRO_COSTO": "Centro de costo",
    "CODIGO_HABER": "Código haber",
    "NOMBRE_HABER": "Nombre haber",
    "MONTO": "Monto",
    "PORCENTAJE": "Porcentaje",
    "TIPO_PROCESO": "Tipo proceso",
}

DEFAULT_KEY_FIELDS = [
    "RUN",
    "DV",
    "LEY",
    "JORNADA",
    "CARGO_CORRELATIVO",
    "CORR_PAGO",
    "CENTRO_COSTO",
    "CODIGO_HABER",
    "TIPO_PROCESO",
]

DEFAULT_HABER_CODE_LENGTH = 4
OPTIONAL_KEY_FIELDS: list[str] = []
REQUIRED_MAPPING_FIELDS = ["RUN", "MONTO", "CODIGO_HABER"]
LINE_KEY_EXCLUDED_FROM_FUNCTION_KEY = {"CODIGO_HABER", "TIPO_PROCESO", "CORR_PAGO"}

FIELD_CANDIDATES = {
    "RUN": ["RUN", "RUT", "RUT_FUNCIONARIO", "RUN FUNCIONARIO", "RUT FUNCIONARIO"],
    "DV": ["DV", "DIGITO VERIFICADOR", "DÍGITO VERIFICADOR"],
    "NOMBRE": ["NOMBRE", "FUNCIONARIO", "NOMBRE FUNCIONARIO", "NOMBRES", "NOMBRE COMPLETO"],
    "LEY": ["LEY", "REGIMEN", "RÉGIMEN", "LEY MEDICA", "LEY MÉDICA"],
    "JORNADA": ["JORNADA_HORAS", "HORAS", "HORAS_CONTRATO", "JORNADA", "HRS", "HRS_CONTRATO", "JORNADA HORARIA"],
    "CARGO_CORRELATIVO": [
        "CORRELATIVO_CARGO",
        "CORR_PAGO",
        "CARGO",
        "CORRELATIVO",
        "CARGO CORRELATIVO",
        "CARGO/CORRELATIVO",
        "NRO CARGO",
        "NUMERO CARGO",
        "ID_CARGO",
        "CORR",
        "CORREL",
    ],
    "CORR_PAGO": ["CORR_PAGO", "CORR PAGO", "CORR"],
    "UNIDAD": ["UNIDAD", "DEPENDENCIA", "SERVICIO", "UNIDAD_DESEMPENO", "UNIDAD DE DESEMPENO", "UNIDAD DE DESEMPEÑO"],
    "CENTRO_COSTO": ["CENTRO_COSTO", "CC", "CENTRO", "COD_CENTRO_COSTO", "CENTRO COSTO", "CENTRO DE COSTO", "CCOSTO", "C COSTO", "COD CENTRO COSTO"],
    "CODIGO_HABER": [
        "CODIGO_MOVIMIENTO",
        "COD_MOVIMIENTO",
        "CODIGO_HABER",
        "COD_HABER",
        "CODIGO HABER",
        "CÓDIGO HABER",
        "COD HABER",
        "CODIGO",
        "CÓDIGO",
        "COD_MOV",
        "HABER_CODIGO",
        "CODHABER",
        "CODIGO ITEM",
    ],
    "NOMBRE_HABER": [
        "NOMBRE_MOVIMIENTO",
        "NOMBRE_HABER",
        "DESC_MOVIMIENTO",
        "DESCRIPCION_MOVIMIENTO",
        "GLOSA",
        "HABER",
        "NOMBRE_CODIGO",
        "NOMBRE HABER",
        "GLOSA HABER",
        "DESCRIPCION",
        "DESCRIPCIÓN",
    ],
    "MONTO": ["MONTO", "VALOR", "MONTO_PAGO", "HABER_MONTO", "TOTAL", "MONTO_HABER", "MONTO HABER", "HABERES", "TOTAL HABER"],
    "PORCENTAJE": ["PORCENTAJE", "PORC", "%", "PORCENTAJE HABER"],
    "TIPO_PROCESO": ["TIPO_PROCESO", "PROCESO", "TIPO_PAGO", "ORDINARIO_ACCESORIO"],
}

DISPLAY_COLUMNS = [
    "RUN",
    "DV",
    "NOMBRE",
    "LEY",
    "JORNADA",
    "CARGO_CORRELATIVO",
    "CORR_PAGO",
    "UNIDAD",
    "CENTRO_COSTO",
    "CODIGO_HABER",
    "NOMBRE_HABER",
    "TIPO_PROCESO",
]

DETAIL_COLUMNS = [
    "RUN",
    "DV",
    "Nombre",
    "Ley",
    "Jornada",
    "Cargo/correlativo",
    "Unidad",
    "Centro de costo",
    "Código haber",
    "Nombre haber",
    "TIPO_DIFERENCIA",
    "Monto anterior",
    "Monto actual",
    "Diferencia",
    "Diferencia absoluta",
    "Porcentaje anterior",
    "Porcentaje actual",
    "Causa probable",
    "Nivel de alerta",
    "Observación",
    "Dato faltante",
]

CAUSE_KEYWORD_RULES = [
    {
        "cause": "Sueldo base",
        "keywords": ["SUELDO BASE", "SUELDO", "BASE"],
    },
    {
        "cause": "Trienios / antigüedad",
        "keywords": ["TRIENIO", "TRIENIOS", "ANTIGUEDAD", "ANTIGUEDAD", "ASIGNACION DE ANTIGUEDAD"],
    },
    {
        "cause": "Experiencia calificada EDF/EPS",
        "keywords": ["EXPERIENCIA", "CALIFICADA", "EDF", "EPS"],
    },
    {
        "cause": "Reforzamiento profesional diurno",
        "keywords": ["REFORZAMIENTO", "RPD", "PROFESIONAL DIURNO"],
    },
    {
        "cause": "Asignación de responsabilidad",
        "keywords": ["RESPONSABILIDAD"],
    },
    {
        "cause": "Asignación de estímulo / competencias",
        "keywords": ["ESTIMULO", "ESTIMULO", "COMPETENCIA", "COMPETENCIAS"],
    },
    {
        "cause": "Jornadas prioritarias",
        "keywords": ["JORNADA PRIORITARIA", "PRIORITARIA", "JP"],
    },
    {
        "cause": "Proyecto específico",
        "keywords": ["PROYECTO", "ESPECIFICO", "ESPECIFICO", "PEE"],
    },
    {
        "cause": "Especialidad / permanencia",
        "keywords": ["ESPECIALIDAD", "SUBESPECIALIDAD", "PERMANENCIA"],
    },
    {
        "cause": "Planilla suplementaria HPH",
        "keywords": ["PLANILLA SUPLEMENTARIA", "SUPLEMENTARIA HPH", "SUPLEMENTARIA", "HPH"],
    },
    {
        "cause": "Retroactivo / accesorio",
        "keywords": ["RETRO", "RETROACTIVO", "ACCESORIO"],
    },
    {
        "cause": "Días trabajados / ausentismo",
        "keywords": ["DIAS", "DIAS", "AUSENTISMO", "LICENCIA"],
    },
]


def normalize_text(value: Any) -> str:
    """Normaliza textos para comparación conservando solo diferencias significativas."""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text)
    return text.upper()


def normalize_header(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", normalize_text(value))


def find_best_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {normalize_header(col): col for col in columns}
    for candidate in candidates:
        found = normalized.get(normalize_header(candidate))
        if found is not None:
            return found
    return None


def guess_mapping(columns: list[str]) -> dict[str, str | None]:
    return {
        field: find_best_column(columns, candidates)
        for field, candidates in FIELD_CANDIDATES.items()
    }


def parse_number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"[^0-9,.\-]", "", text)
    if not text or text in {"-", ",", "."}:
        return None

    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        parts = text.split(".")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[-1]) == 3):
            text = text.replace(".", "")

    try:
        return float(text)
    except ValueError:
        return None


def number_or_zero(value: Any) -> float:
    parsed = parse_number(value)
    return parsed if parsed is not None else 0.0


def bool_or_false(value: Any) -> bool:
    return bool(value) if pd.notna(value) else False


def first_non_empty(values: pd.Series) -> Any:
    for value in values:
        if pd.notna(value) and str(value).strip() != "":
            return value
    return ""


def clean_display_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return value


def format_law_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().replace(",", ".")
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    return f"{number:.3f}".rstrip("0").rstrip(".")


def format_haber_code(value: Any, width: int = DEFAULT_HABER_CODE_LENGTH) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = text.replace(",", ".")
    if re.fullmatch(r"\d+(\.0+)?", text):
        number = int(float(text))
        return str(number).zfill(width)
    if re.fullmatch(r"\d+", text):
        return text.zfill(width)
    return text


def make_key(row: pd.Series, fields: list[str]) -> str:
    return "||".join(normalize_text(row.get(field, "")) for field in fields)


def function_key_fields(key_fields: list[str]) -> list[str]:
    return [field for field in key_fields if field not in LINE_KEY_EXCLUDED_FROM_FUNCTION_KEY]


def standardize_dataframe(
    df: pd.DataFrame,
    mapping: dict[str, str | None],
    key_fields: list[str],
    code_length: int = DEFAULT_HABER_CODE_LENGTH,
) -> pd.DataFrame:
    data = pd.DataFrame(index=df.index)

    for field in STANDARD_FIELDS:
        source_column = mapping.get(field)
        if source_column and source_column in df.columns:
            data[field] = df[source_column]
        else:
            data[field] = ""

    data["LEY"] = data["LEY"].map(format_law_text)
    data["CODIGO_HABER"] = data["CODIGO_HABER"].map(lambda value: format_haber_code(value, code_length))
    raw_amount = data["MONTO"]
    parsed_amount = raw_amount.map(parse_number)
    data["MONTO_INVALIDO"] = raw_amount.apply(lambda value: pd.notna(value) and str(value).strip() != "") & parsed_amount.isna()
    data["MONTO"] = parsed_amount.fillna(0.0)
    data["PORCENTAJE"] = data["PORCENTAJE"].map(parse_number)

    valid_key_fields = [field for field in key_fields if field in data.columns]
    valid_function_key_fields = function_key_fields(valid_key_fields)
    data["LLAVE_FUNCIONARIO"] = data.apply(lambda row: make_key(row, valid_function_key_fields), axis=1)
    data["LLAVE_PERSONA"] = data.apply(lambda row: make_key(row, ["RUN", "DV"]), axis=1)
    data["LLAVE_COMPARACION"] = data.apply(lambda row: make_key(row, valid_key_fields), axis=1)
    return data


def has_conflicting_values(values: pd.Series) -> bool:
    normalized = {normalize_text(value) for value in values if pd.notna(value) and str(value).strip() != ""}
    return len(normalized) > 1


def duplicate_conflicts(data: pd.DataFrame) -> pd.DataFrame:
    conflict_columns = ["RUN", "DV", "NOMBRE", "LEY", "JORNADA", "CARGO_CORRELATIVO", "UNIDAD", "CENTRO_COSTO", "CODIGO_HABER", "NOMBRE_HABER"]
    rows = []
    for key, group in data.groupby("LLAVE_COMPARACION", dropna=False):
        rows.append(
            {
                "LLAVE_COMPARACION": key,
                "DUPLICADO_CRITICO": any(has_conflicting_values(group[column]) for column in conflict_columns),
            }
        )
    return pd.DataFrame(rows, columns=["LLAVE_COMPARACION", "DUPLICADO_CRITICO"])


def aggregate_for_comparison(data: pd.DataFrame) -> pd.DataFrame:
    aggregations: dict[str, str | Any] = {
        "MONTO": "sum",
        "PORCENTAJE": first_non_empty,
        "LLAVE_FUNCIONARIO": first_non_empty,
        "LLAVE_PERSONA": first_non_empty,
        "MONTO_INVALIDO": "sum",
    }
    for column in DISPLAY_COLUMNS:
        aggregations[column] = first_non_empty

    grouped = data.groupby("LLAVE_COMPARACION", dropna=False).agg(aggregations).reset_index()
    counts = data.groupby("LLAVE_COMPARACION", dropna=False).size().rename("DUPLICADOS").reset_index()
    conflicts = duplicate_conflicts(data)
    return grouped.merge(counts, on="LLAVE_COMPARACION", how="left").merge(conflicts, on="LLAVE_COMPARACION", how="left")


def row_value(row: pd.Series, field: str) -> Any:
    current = row.get(f"{field}_actual", "")
    previous = row.get(f"{field}_anterior", "")
    if pd.notna(current) and str(current).strip() != "":
        return clean_display_value(current)
    if pd.notna(previous) and str(previous).strip() != "":
        return clean_display_value(previous)
    return ""


def detect_structural_change(
    row: pd.Series,
    previous_by_person: dict[str, dict[str, Any]],
    current_by_person: dict[str, dict[str, Any]],
) -> tuple[str | None, str]:
    person_key = row_value(row, "LLAVE_PERSONA")
    if not person_key:
        return None, ""

    previous = previous_by_person.get(person_key)
    current = current_by_person.get(person_key)
    if previous is None or current is None:
        return None, ""

    checks = [
        ("JORNADA", "Cambio de jornada"),
        ("LEY", "Cambio de ley"),
        ("CENTRO_COSTO", "Cambio de unidad o centro de costo"),
        ("UNIDAD", "Cambio de unidad o centro de costo"),
        ("CARGO_CORRELATIVO", "Cambio de cargo o correlativo"),
    ]
    changes = [
        label
        for field, label in checks
        if normalize_text(previous.get(field, "")) != normalize_text(current.get(field, ""))
    ]
    if not changes:
        return None, ""

    unique_changes = list(dict.fromkeys(changes))
    return unique_changes[0], "El RUN existe en ambos meses, pero cambió: " + ", ".join(unique_changes)


def build_classification_text(row: pd.Series) -> str:
    fields = [
        "CODIGO_HABER",
        "NOMBRE_HABER",
        "TIPO_PROCESO",
    ]
    return " ".join(normalize_text(row_value(row, field)) for field in fields)


def classify_hph_cause(row: pd.Series, context: str) -> tuple[str, str, str]:
    text = build_classification_text(row)
    for rule in CAUSE_KEYWORD_RULES:
        if any(keyword in text for keyword in rule["keywords"]):
            return (
                rule["cause"],
                f"{context} Clasificación sugerida por código, nombre de haber o columnas disponibles; validar respaldo administrativo.",
                "",
            )

    return (
        "Diferencia no clasificada",
        f"{context} No se encontraron palabras clave suficientes para clasificar con certeza.",
        "glosa/código específico o respaldo administrativo",
    )


def alert_level(
    cause: str,
    difference: float,
    medium_threshold: float,
    high_threshold: float,
    difference_type: str = "",
) -> str:
    if difference_type == "Requiere revisión" or cause == "Requiere revisión manual":
        return "Revisión manual"
    if abs(difference) >= high_threshold:
        return "Alto"
    if abs(difference) >= medium_threshold:
        return "Medio"
    return "Bajo"


def build_detail_row(
    row: pd.Series,
    difference_type: str,
    cause: str,
    alert: str,
    observation: str,
    missing_data: str = "",
) -> dict[str, Any]:
    previous_amount = number_or_zero(row.get("MONTO_anterior", 0))
    current_amount = number_or_zero(row.get("MONTO_actual", 0))
    previous_pct = row.get("PORCENTAJE_anterior", None)
    current_pct = row.get("PORCENTAJE_actual", None)
    previous_pct_number = parse_number(previous_pct)
    current_pct_number = parse_number(current_pct)
    difference = current_amount - previous_amount

    return {
        "RUN": row_value(row, "RUN"),
        "DV": row_value(row, "DV"),
        "Nombre": row_value(row, "NOMBRE"),
        "Ley": row_value(row, "LEY"),
        "Jornada": row_value(row, "JORNADA"),
        "Cargo/correlativo": row_value(row, "CARGO_CORRELATIVO"),
        "Unidad": row_value(row, "UNIDAD"),
        "Centro de costo": row_value(row, "CENTRO_COSTO"),
        "Código haber": row_value(row, "CODIGO_HABER"),
        "Nombre haber": row_value(row, "NOMBRE_HABER"),
        "TIPO_DIFERENCIA": difference_type,
        "Monto anterior": previous_amount,
        "Monto actual": current_amount,
        "Diferencia": difference,
        "Diferencia absoluta": abs(difference),
        "Porcentaje anterior": previous_pct_number if previous_pct_number is not None else "",
        "Porcentaje actual": current_pct_number if current_pct_number is not None else "",
        "Causa probable": cause,
        "Nivel de alerta": alert,
        "Observación": observation,
        "Dato faltante": missing_data,
    }


def compare_dataframes(
    previous_df: pd.DataFrame,
    current_df: pd.DataFrame,
    previous_mapping: dict[str, str | None],
    current_mapping: dict[str, str | None],
    key_fields: list[str],
    medium_threshold: float = 100_000,
    high_threshold: float = 500_000,
    code_length: int = DEFAULT_HABER_CODE_LENGTH,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    missing_required = [
        label
        for field, label in {
            "RUN": "RUN",
            "MONTO": "monto",
            "CODIGO_HABER": "código de haber",
        }.items()
        if not previous_mapping.get(field) or not current_mapping.get(field)
    ]
    if "CODIGO_HABER" not in key_fields:
        key_fields = [*key_fields, "CODIGO_HABER"]
    if not key_fields:
        missing_required.append("llave de comparación")

    previous_standard = standardize_dataframe(previous_df, previous_mapping, key_fields, code_length)
    current_standard = standardize_dataframe(current_df, current_mapping, key_fields, code_length)

    previous_agg = aggregate_for_comparison(previous_standard)
    current_agg = aggregate_for_comparison(current_standard)

    previous_by_person = (
        previous_standard.groupby("LLAVE_PERSONA", dropna=False).agg({col: first_non_empty for col in DISPLAY_COLUMNS}).to_dict("index")
    )
    current_by_person = (
        current_standard.groupby("LLAVE_PERSONA", dropna=False).agg({col: first_non_empty for col in DISPLAY_COLUMNS}).to_dict("index")
    )

    previous_person_keys = set(previous_standard["LLAVE_PERSONA"])
    current_person_keys = set(current_standard["LLAVE_PERSONA"])
    previous_function_keys = set(previous_standard["LLAVE_FUNCIONARIO"])
    current_function_keys = set(current_standard["LLAVE_FUNCIONARIO"])

    merged = previous_agg.merge(
        current_agg,
        on="LLAVE_COMPARACION",
        how="outer",
        suffixes=("_anterior", "_actual"),
        indicator=True,
    )

    detail_rows = []
    for _, row in merged.iterrows():
        previous_amount = number_or_zero(row.get("MONTO_anterior", 0))
        current_amount = number_or_zero(row.get("MONTO_actual", 0))
        difference = current_amount - previous_amount
        previous_pct = parse_number(row.get("PORCENTAJE_anterior", None))
        current_pct = parse_number(row.get("PORCENTAJE_actual", None))
        pct_changed = previous_pct is not None and current_pct is not None and previous_pct != current_pct
        was_consolidated = bool(number_or_zero(row.get("DUPLICADOS_anterior", 0)) > 1 or number_or_zero(row.get("DUPLICADOS_actual", 0)) > 1)
        critical_duplicate = bool_or_false(row.get("DUPLICADO_CRITICO_anterior", False)) or bool_or_false(row.get("DUPLICADO_CRITICO_actual", False))
        invalid_amount = bool(number_or_zero(row.get("MONTO_INVALIDO_anterior", 0)) > 0 or number_or_zero(row.get("MONTO_INVALIDO_actual", 0)) > 0)

        cause = ""
        difference_type = ""
        observation = ""
        missing_data = ""

        if missing_required:
            difference_type = "Requiere revisión"
            cause = "Diferencia no clasificada"
            missing_data = ", ".join(missing_required)
            observation = "No existen datos suficientes para clasificar con certeza."
        elif invalid_amount:
            difference_type = "Requiere revisión"
            cause, _, _ = classify_hph_cause(row, "")
            missing_data = "monto numérico"
            observation = "Existe al menos un monto no numérico en la llave comparada."
        elif critical_duplicate:
            difference_type = "Requiere revisión"
            cause, _, _ = classify_hph_cause(row, "")
            missing_data = "llave única sin valores contradictorios"
            observation = "La misma llave aparece con datos de identificación o haber contradictorios."
        elif row["_merge"] == "left_only":
            structural_cause, structural_observation = detect_structural_change(row, previous_by_person, current_by_person)
            if structural_cause:
                difference_type = "Código eliminado"
                cause, classification_observation, missing_data = classify_hph_cause(row, "Código de haber eliminado por cambio estructural.")
                observation = f"{structural_observation} {classification_observation}"
            elif row.get("LLAVE_PERSONA_anterior") not in current_person_keys:
                difference_type = "Funcionario ausente"
                cause, classification_observation, missing_data = classify_hph_cause(row, "El RUN del mes anterior no aparece en el mes actual.")
                observation = classification_observation
            elif row.get("LLAVE_FUNCIONARIO_anterior") in current_function_keys:
                difference_type = "Código eliminado"
                cause, observation, missing_data = classify_hph_cause(
                    row,
                    "Código de haber eliminado: la llave existe en ambos meses, pero el haber no aparece en el mes actual.",
                )
            else:
                difference_type = "Requiere revisión"
                cause, _, _ = classify_hph_cause(row, "")
                missing_data = "equivalencia de llave entre meses"
                observation = "El RUN existe, pero no se pudo vincular de forma inequívoca con la llave configurada."
        elif row["_merge"] == "right_only":
            structural_cause, structural_observation = detect_structural_change(row, previous_by_person, current_by_person)
            if structural_cause:
                difference_type = "Código nuevo"
                cause, classification_observation, missing_data = classify_hph_cause(row, "Código de haber nuevo por cambio estructural.")
                observation = f"{structural_observation} {classification_observation}"
            elif row.get("LLAVE_PERSONA_actual") not in previous_person_keys:
                difference_type = "Funcionario nuevo"
                cause, classification_observation, missing_data = classify_hph_cause(row, "El RUN del mes actual no aparece en el mes anterior.")
                observation = classification_observation
            elif row.get("LLAVE_FUNCIONARIO_actual") in previous_function_keys:
                difference_type = "Código nuevo"
                cause, observation, missing_data = classify_hph_cause(
                    row,
                    "Código de haber nuevo: la llave existe en ambos meses, pero el haber aparece solo en el mes actual.",
                )
            else:
                difference_type = "Requiere revisión"
                cause, _, _ = classify_hph_cause(row, "")
                missing_data = "equivalencia de llave entre meses"
                observation = "El RUN existe, pero no se pudo vincular de forma inequívoca con la llave configurada."
        elif difference != 0:
            difference_type = "Diferencia de monto"
            cause, observation, missing_data = classify_hph_cause(
                row,
                "Mismo código de haber con monto distinto entre meses.",
            )
        elif pct_changed:
            difference_type = "Diferencia de monto"
            cause, observation, missing_data = classify_hph_cause(
                row,
                "Mismo código de haber con porcentaje distinto entre meses.",
            )
        elif was_consolidated:
            difference_type = "Registro consolidado"
            cause, observation, missing_data = classify_hph_cause(
                row,
                "Registro consolidado por llave duplicada.",
            )
        else:
            continue

        if was_consolidated and difference_type != "Registro consolidado" and difference_type != "Requiere revisión":
            observation = f"{observation} Registro consolidado por llave duplicada."

        alert = alert_level(cause, difference, medium_threshold, high_threshold, difference_type)
        detail_rows.append(build_detail_row(row, difference_type, cause, alert, observation, missing_data))

    detail = pd.DataFrame(detail_rows, columns=DETAIL_COLUMNS)
    if not detail.empty:
        detail = detail.sort_values("Diferencia", key=lambda col: col.abs(), ascending=False).reset_index(drop=True)

    summary = {
        "Fecha de auditoría": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Total de registros mes anterior": len(previous_df),
        "Total de registros mes actual": len(current_df),
        "Total de funcionarios comparados": len(previous_person_keys.union(current_person_keys)),
        "Total de diferencias detectadas": len(detail),
        "Diferencia positiva total": float(detail.loc[detail["Diferencia"] > 0, "Diferencia"].sum()) if not detail.empty else 0.0,
        "Diferencia negativa total": float(detail.loc[detail["Diferencia"] < 0, "Diferencia"].sum()) if not detail.empty else 0.0,
        "Diferencia neta": float(detail["Diferencia"].sum()) if not detail.empty else 0.0,
        "Cantidad de casos de alerta alta": int((detail["Nivel de alerta"] == "Alto").sum()) if not detail.empty else 0,
        "Cantidad de casos que requieren revisión manual": int((detail["Nivel de alerta"] == "Revisión manual").sum()) if not detail.empty else 0,
    }
    summary.update(build_executive_summary(detail))
    return detail, summary


def format_money(value: Any) -> str:
    amount = number_or_zero(value)
    formatted = f"${amount:,.0f}".replace(",", ".")
    return formatted


def format_detail_item(row: pd.Series) -> str:
    run = row.get("RUN", "")
    name = row.get("Nombre", "")
    code = row.get("Código haber", "")
    haber = row.get("Nombre haber", "")
    difference = format_money(row.get("Diferencia", 0))
    return f"{run} - {name} | {code} {haber}: {difference}"


def join_or_default(items: list[str], default: str = "Sin casos") -> str:
    return "; ".join(items) if items else default


TOP_DETAIL_COLUMNS = [
    "RUN",
    "Nombre",
    "Ley",
    "Código haber",
    "Nombre haber",
    "TIPO_DIFERENCIA",
    "Monto anterior",
    "Monto actual",
    "Diferencia",
    "Causa probable",
]


def build_summary_tables(detail: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if "TIPO_DIFERENCIA" not in detail.columns and not detail.empty:
        detail = detail.copy()
        detail["TIPO_DIFERENCIA"] = "Diferencia de monto"
    if "Diferencia absoluta" not in detail.columns and "Diferencia" in detail.columns:
        detail = detail.copy()
        detail["Diferencia absoluta"] = detail["Diferencia"].abs()

    if detail.empty:
        return {
            "principales_aumentos": pd.DataFrame(columns=TOP_DETAIL_COLUMNS),
            "principales_disminuciones": pd.DataFrame(columns=TOP_DETAIL_COLUMNS),
            "top_codigos": pd.DataFrame(
                columns=[
                    "Código haber",
                    "Nombre haber",
                    "Diferencia neta",
                    "Diferencia absoluta total",
                    "Cantidad de funcionarios afectados",
                    "Principal TIPO_DIFERENCIA",
                ]
            ),
            "top_funcionarios": pd.DataFrame(
                columns=[
                    "RUN",
                    "Nombre",
                    "Ley",
                    "Diferencia neta",
                    "Diferencia absoluta total",
                    "Principal TIPO_DIFERENCIA",
                    "Principal causa probable",
                ]
            ),
        }

    increases = detail[detail["Diferencia"] > 0].sort_values("Diferencia", ascending=False).head(10)
    decreases = detail[detail["Diferencia"] < 0].sort_values("Diferencia", ascending=True).head(10)

    def principal_cause(values: pd.Series) -> str:
        counts = values.value_counts()
        return counts.index[0] if not counts.empty else ""

    top_codes = (
        detail.groupby(["Código haber", "Nombre haber"], dropna=False)
        .agg(
            **{
                "Diferencia neta": ("Diferencia", "sum"),
                "Diferencia absoluta total": ("Diferencia absoluta", "sum"),
                "Cantidad de funcionarios afectados": ("RUN", "nunique"),
                "Principal TIPO_DIFERENCIA": ("TIPO_DIFERENCIA", principal_cause),
            }
        )
        .reset_index()
        .sort_values("Diferencia absoluta total", ascending=False)
        .head(20)
    )

    top_staff = (
        detail.groupby(["RUN", "Nombre", "Ley"], dropna=False)
        .agg(
            **{
                "Diferencia neta": ("Diferencia", "sum"),
                "Diferencia absoluta total": ("Diferencia absoluta", "sum"),
                "Principal TIPO_DIFERENCIA": ("TIPO_DIFERENCIA", principal_cause),
                "Principal causa probable": ("Causa probable", principal_cause),
            }
        )
        .reset_index()
        .sort_values("Diferencia absoluta total", ascending=False)
        .head(20)
    )

    return {
        "principales_aumentos": increases[TOP_DETAIL_COLUMNS].copy(),
        "principales_disminuciones": decreases[TOP_DETAIL_COLUMNS].copy(),
        "top_codigos": top_codes,
        "top_funcionarios": top_staff,
    }


def build_executive_summary(detail: pd.DataFrame) -> dict[str, Any]:
    if detail.empty:
        return {
            "Cantidad de casos que requieren revisión manual": 0,
        }
    return {
        "Cantidad de casos que requieren revisión manual": int((detail["Nivel de alerta"] == "Revisión manual").sum()),
    }


def build_summary_dataframe(summary: dict[str, Any], previous_name: str, current_name: str, detail: pd.DataFrame) -> pd.DataFrame:
    rows = [
        ("Fecha de auditoría", summary.get("Fecha de auditoría", "")),
        ("Nombre del archivo mes anterior", previous_name),
        ("Nombre del archivo mes actual", current_name),
        ("Total de registros mes anterior", summary.get("Total de registros mes anterior", 0)),
        ("Total de registros mes actual", summary.get("Total de registros mes actual", 0)),
        ("Total de funcionarios comparados", summary.get("Total de funcionarios comparados", 0)),
        ("Total de diferencias detectadas", summary.get("Total de diferencias detectadas", 0)),
        ("Diferencia positiva total", summary.get("Diferencia positiva total", 0)),
        ("Diferencia negativa total", summary.get("Diferencia negativa total", 0)),
        ("Diferencia neta", summary.get("Diferencia neta", 0)),
        ("Cantidad de casos de alerta alta", summary.get("Cantidad de casos de alerta alta", 0)),
        ("Cantidad de casos que requieren revisión manual", summary.get("Cantidad de casos que requieren revisión manual", 0)),
    ]
    return pd.DataFrame(rows, columns=["Indicador", "Valor"])


def normalize_detail_output(detail: pd.DataFrame, code_length: int = DEFAULT_HABER_CODE_LENGTH) -> pd.DataFrame:
    if detail.empty:
        return detail.copy()
    normalized = detail.copy()
    if "TIPO_DIFERENCIA" not in normalized.columns:
        normalized["TIPO_DIFERENCIA"] = "Diferencia de monto"
    if "Ley" in normalized.columns:
        normalized["Ley"] = normalized["Ley"].map(format_law_text)
    if "Código haber" in normalized.columns:
        normalized["Código haber"] = normalized["Código haber"].map(lambda value: format_haber_code(value, code_length))
    if "Diferencia absoluta" not in normalized.columns and "Diferencia" in normalized.columns:
        normalized["Diferencia absoluta"] = normalized["Diferencia"].abs()
    return normalized


def export_report_excel(
    detail: pd.DataFrame,
    summary: dict[str, Any],
    previous_name: str,
    current_name: str,
    config_used: pd.DataFrame | None = None,
    code_length: int = DEFAULT_HABER_CODE_LENGTH,
) -> bytes:
    buffer = io.BytesIO()
    detail = normalize_detail_output(detail, code_length)
    summary_df = build_summary_dataframe(summary, previous_name, current_name, detail)
    summary_tables = build_summary_tables(detail)

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="RESUMEN", index=False)
        startrow = len(summary_df) + 3
        resumen_sections = [
            ("Principales aumentos", summary_tables["principales_aumentos"]),
            ("Principales disminuciones", summary_tables["principales_disminuciones"]),
            ("Top códigos con mayor variación", summary_tables["top_codigos"]),
            ("Top funcionarios con mayor diferencia absoluta", summary_tables["top_funcionarios"]),
        ]
        for title, table in resumen_sections:
            pd.DataFrame({"Resumen ejecutivo": [title]}).to_excel(
                writer,
                sheet_name="RESUMEN",
                index=False,
                startrow=startrow,
            )
            table.to_excel(writer, sheet_name="RESUMEN", index=False, startrow=startrow + 2)
            startrow += max(len(table), 1) + 5

        detail.to_excel(writer, sheet_name="DIF_DETALLE", index=False)

        alert_cases = detail[detail["Nivel de alerta"].isin(["Medio", "Alto", "Revisión manual"])] if not detail.empty else detail
        alert_cases.to_excel(
            writer,
            sheet_name="CASOS_ALERTA",
            index=False,
        )

        summary_tables["principales_aumentos"].to_excel(writer, sheet_name="PRINCIPALES_AUMENTOS", index=False)
        summary_tables["principales_disminuciones"].to_excel(writer, sheet_name="PRINCIPALES_DISMINUCIONES", index=False)
        summary_tables["top_codigos"].to_excel(writer, sheet_name="TOP_CODIGOS", index=False)
        summary_tables["top_funcionarios"].to_excel(writer, sheet_name="TOP_FUNCIONARIOS", index=False)

        funcionarios_nuevos = detail[detail["Causa probable"] == "Funcionario nuevo"] if not detail.empty else detail
        funcionarios_ausentes = detail[detail["Causa probable"] == "Funcionario ausente"] if not detail.empty else detail
        codigos_nuevos = detail[detail["Observación"].astype(str).str.contains("Código de haber nuevo", case=False, na=False)] if not detail.empty else detail
        codigos_eliminados = detail[detail["Observación"].astype(str).str.contains("Código de haber eliminado", case=False, na=False)] if not detail.empty else detail

        funcionarios_nuevos.to_excel(writer, sheet_name="FUNCIONARIOS_NUEVOS", index=False)
        funcionarios_ausentes.to_excel(writer, sheet_name="FUNCIONARIOS_AUSENTES", index=False)
        codigos_nuevos.to_excel(writer, sheet_name="CODIGOS_NUEVOS", index=False)
        codigos_eliminados.to_excel(writer, sheet_name="CODIGOS_ELIMINADOS", index=False)

        if config_used is None:
            config_used = pd.DataFrame(
                [
                    {"Campo": "Archivo mes anterior", "Valor": previous_name},
                    {"Campo": "Archivo mes actual", "Valor": current_name},
                    {"Campo": "Generado", "Valor": datetime.now().strftime("%Y-%m-%d %H:%M")},
                ]
            )
        config_used.to_excel(writer, sheet_name="CONFIG_USADA", index=False)

        workbook = writer.book
        for sheet in workbook.worksheets:
            sheet.freeze_panes = "A2"
            headers = {cell.value: cell.column for cell in sheet[1] if cell.value is not None}
            for text_column in ["Ley", "Código haber"]:
                column_index = headers.get(text_column)
                if column_index is None:
                    continue
                for row_cells in sheet.iter_rows(min_row=2, min_col=column_index, max_col=column_index):
                    row_cells[0].number_format = "@"
            for money_column in MONEY_COLUMNS:
                column_index = headers.get(money_column)
                if column_index is None:
                    continue
                for row_cells in sheet.iter_rows(min_row=2, min_col=column_index, max_col=column_index):
                    row_cells[0].number_format = '$#,##0'
            for column_cells in sheet.columns:
                max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 45)

    buffer.seek(0)
    return buffer.getvalue()


def excel_sheet_names(uploaded_file: Any) -> list[str]:
    data = io.BytesIO(uploaded_file.getvalue())
    return pd.ExcelFile(data).sheet_names


def read_uploaded_excel(uploaded_file: Any, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(uploaded_file.getvalue()), sheet_name=sheet_name)


def select_column(label: str, columns: list[str], default: str | None, key: str, required: bool = False) -> str | None:
    options = ["(No usar)"] + columns
    default_index = options.index(default) if default in options else 0
    selected = st.selectbox(label, options, index=default_index, key=key)
    if required and selected == "(No usar)":
        st.warning(f"Falta mapear: {label}.")
    return None if selected == "(No usar)" else selected


def render_mapping_ui(previous_df: pd.DataFrame, current_df: pd.DataFrame) -> tuple[dict[str, str | None], dict[str, str | None]]:
    previous_columns = list(previous_df.columns)
    current_columns = list(current_df.columns)
    previous_guess = guess_mapping(previous_columns)
    current_guess = guess_mapping(current_columns)

    previous_mapping: dict[str, str | None] = {}
    current_mapping: dict[str, str | None] = {}

    st.subheader("Sección 3: Mapeo de columnas")
    st.caption("Puedes dejar campos opcionales sin usar. RUN, Código de haber y monto son necesarios para comparar haberes.")
    for field, label in STANDARD_FIELDS.items():
        required = field in set(REQUIRED_MAPPING_FIELDS)
        left, right = st.columns(2)
        with left:
            previous_mapping[field] = select_column(
                f"{label} - mes anterior",
                previous_columns,
                previous_guess.get(field),
                key=f"prev_{field}",
                required=required,
            )
        with right:
            current_mapping[field] = select_column(
                f"{label} - mes actual",
                current_columns,
                current_guess.get(field),
                key=f"curr_{field}",
                required=required,
            )
    return previous_mapping, current_mapping


MONEY_COLUMNS = [
    "Monto anterior",
    "Monto actual",
    "Diferencia",
    "Diferencia absoluta",
    "Diferencia neta",
    "Diferencia absoluta total",
]


def style_money_columns(df: pd.DataFrame):
    formatters = {column: format_money for column in MONEY_COLUMNS if column in df.columns}
    return df.style.format(formatters) if formatters else df


def render_executive_summary(detail: pd.DataFrame, summary: dict[str, Any]) -> None:
    st.subheader("Resumen ejecutivo")
    tables = build_summary_tables(detail)
    tabs = st.tabs(
        [
            "Indicadores generales",
            "Principales aumentos",
            "Principales disminuciones",
            "Top códigos",
            "Top funcionarios",
            "Alertas",
        ]
    )

    with tabs[0]:
        indicators = pd.DataFrame(
            [
                {"Indicador": "Total diferencias", "Valor": summary.get("Total de diferencias detectadas", 0)},
                {"Indicador": "Diferencia positiva total", "Valor": format_money(summary.get("Diferencia positiva total", 0))},
                {"Indicador": "Diferencia negativa total", "Valor": format_money(summary.get("Diferencia negativa total", 0))},
                {"Indicador": "Diferencia neta", "Valor": format_money(summary.get("Diferencia neta", 0))},
                {"Indicador": "Alertas altas", "Valor": summary.get("Cantidad de casos de alerta alta", 0)},
                {"Indicador": "Casos revisión manual", "Valor": summary.get("Cantidad de casos que requieren revisión manual", 0)},
            ]
        )
        st.dataframe(indicators, use_container_width=True, hide_index=True)

    tab_tables = [
        (tabs[1], tables["principales_aumentos"]),
        (tabs[2], tables["principales_disminuciones"]),
        (tabs[3], tables["top_codigos"]),
        (tabs[4], tables["top_funcionarios"]),
    ]
    for tab, table in tab_tables:
        with tab:
            if table.empty:
                st.caption("Sin casos para mostrar.")
            else:
                st.dataframe(style_money_columns(table), use_container_width=True, hide_index=True)

    with tabs[5]:
        alerts = detail[detail["Nivel de alerta"].isin(["Medio", "Alto", "Revisión manual"])] if not detail.empty else detail
        if alerts.empty:
            st.caption("Sin alertas para mostrar.")
        else:
            st.dataframe(style_money_columns(alerts), use_container_width=True, hide_index=True)


def filter_results(detail: pd.DataFrame) -> pd.DataFrame:
    filtered = detail.copy()
    st.subheader("Filtros")
    left, middle, right = st.columns(3)
    with left:
        if "Ley" in filtered:
            selected = st.multiselect("Ley", sorted(filtered["Ley"].dropna().astype(str).unique()))
            if selected:
                filtered = filtered[filtered["Ley"].astype(str).isin(selected)]
        run_filter = st.text_input("RUN")
        if run_filter:
            filtered = filtered[filtered["RUN"].astype(str).str.contains(run_filter, case=False, na=False)]
    with middle:
        nombre = st.text_input("Nombre")
        if nombre:
            filtered = filtered[filtered["Nombre"].astype(str).str.contains(nombre, case=False, na=False)]
        if "Jornada" in filtered:
            selected = st.multiselect("Jornada", sorted(filtered["Jornada"].dropna().astype(str).unique()))
            if selected:
                filtered = filtered[filtered["Jornada"].astype(str).isin(selected)]
    with right:
        codigo = st.text_input("Código de haber")
        if codigo:
            filtered = filtered[filtered["Código haber"].astype(str).str.contains(codigo, case=False, na=False)]
        min_diff = st.number_input("Diferencia absoluta mínima", min_value=0.0, value=0.0, step=10_000.0)
        if min_diff > 0:
            filtered = filtered[filtered["Diferencia"].abs() >= min_diff]

    left, right = st.columns(2)
    with left:
        if "Causa probable" in filtered:
            selected = st.multiselect("Causa probable", sorted(detail["Causa probable"].dropna().astype(str).unique()))
            if selected:
                filtered = filtered[filtered["Causa probable"].astype(str).isin(selected)]
    with right:
        if "Nivel de alerta" in filtered:
            selected = st.multiselect("Nivel de alerta", sorted(detail["Nivel de alerta"].dropna().astype(str).unique()))
            if selected:
                filtered = filtered[filtered["Nivel de alerta"].astype(str).isin(selected)]
    return filtered


def render_charts(detail: pd.DataFrame) -> None:
    if detail.empty:
        return
    st.subheader("Gráficos simples")
    positive = detail.loc[detail["Diferencia"] > 0, "Diferencia"].sum()
    negative = detail.loc[detail["Diferencia"] < 0, "Diferencia"].sum()
    st.markdown("**Variación positiva vs negativa**")
    st.bar_chart(pd.DataFrame({"Monto": [positive, negative]}, index=["Positiva", "Negativa"]))

    left, right = st.columns(2)
    with left:
        st.markdown("**Diferencias por causa probable**")
        st.bar_chart(detail["Causa probable"].value_counts())
    with right:
        st.markdown("**Diferencias por nivel de alerta**")
        st.bar_chart(detail["Nivel de alerta"].value_counts())

    top = (
        detail.assign(Diferencia_abs=detail["Diferencia"].abs())
        .groupby(["RUN", "Nombre"], as_index=False)["Diferencia_abs"]
        .sum()
        .sort_values("Diferencia_abs", ascending=False)
        .head(20)
    )
    if not top.empty:
        top["Funcionario"] = top["RUN"].astype(str) + " - " + top["Nombre"].astype(str)
        st.markdown("**Top funcionarios por diferencia absoluta**")
        st.bar_chart(top.set_index("Funcionario")["Diferencia_abs"])


def main() -> None:
    if st is None:
        raise RuntimeError("Streamlit no está instalado. Ejecuta: pip install -r requirements.txt")

    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.info(
        "Esta herramienta entrega alertas y diferencias objetivas. No reemplaza la revisión administrativa, "
        "jurídica ni la validación de Gestión de Personas."
    )

    st.header("Sección 1: Carga de archivos")
    previous_file = st.file_uploader("Archivo Excel mes anterior", type=["xlsx", "xls"], key="previous_file")
    current_file = st.file_uploader("Archivo Excel mes actual", type=["xlsx", "xls"], key="current_file")

    if not previous_file or not current_file:
        st.stop()

    st.header("Sección 2: Selección de hojas")
    previous_sheets = excel_sheet_names(previous_file)
    current_sheets = excel_sheet_names(current_file)
    left, right = st.columns(2)
    with left:
        previous_sheet = st.selectbox("Hoja mes anterior", previous_sheets)
    with right:
        current_sheet = st.selectbox("Hoja mes actual", current_sheets)

    previous_df = read_uploaded_excel(previous_file, previous_sheet)
    current_df = read_uploaded_excel(current_file, current_sheet)

    with st.expander("Columnas detectadas", expanded=False):
        st.write("Mes anterior", list(previous_df.columns))
        st.write("Mes actual", list(current_df.columns))

    previous_mapping, current_mapping = render_mapping_ui(previous_df, current_df)

    st.header("Sección 4: Configuración de auditoría")
    missing_required_mapping = [
        STANDARD_FIELDS[field]
        for field in REQUIRED_MAPPING_FIELDS
        if not previous_mapping.get(field) or not current_mapping.get(field)
    ]
    can_execute = not missing_required_mapping
    if not previous_mapping.get("CODIGO_HABER") or not current_mapping.get("CODIGO_HABER"):
        st.error(
            "No es posible ejecutar una auditoría remuneracional por haberes sin mapear Código haber. "
            "Selecciona CODIGO_MOVIMIENTO u otra columna equivalente."
        )
    elif missing_required_mapping:
        st.error("Falta mapear columnas obligatorias: " + ", ".join(missing_required_mapping) + ".")

    available_key_fields = [
        field
        for field in DEFAULT_KEY_FIELDS
        if previous_mapping.get(field) and current_mapping.get(field)
    ]
    optional_key_fields = [
        field
        for field in OPTIONAL_KEY_FIELDS
        if previous_mapping.get(field) and current_mapping.get(field)
    ]
    key_options = [field for field in DEFAULT_KEY_FIELDS + optional_key_fields if field in STANDARD_FIELDS]
    key_fields = st.multiselect(
        "Columnas lógicas para construir la llave de comparación",
        options=key_options,
        default=available_key_fields,
        format_func=lambda field: STANDARD_FIELDS[field],
    )
    if previous_mapping.get("CODIGO_HABER") and current_mapping.get("CODIGO_HABER") and "CODIGO_HABER" not in key_fields:
        key_fields = [*key_fields, "CODIGO_HABER"]
        st.warning("Código haber es obligatorio en la llave y se agregará automáticamente a la comparación.")
    if not key_fields:
        st.warning("Selecciona al menos una columna lógica para la llave de comparación.")

    left, right = st.columns(2)
    with left:
        medium_threshold = st.number_input("Umbral alerta media", min_value=0.0, value=100_000.0, step=10_000.0)
    with right:
        high_threshold = st.number_input("Umbral alerta alta", min_value=0.0, value=500_000.0, step=10_000.0)
    code_length = int(
        st.number_input(
            "Largo código de haber",
            min_value=1,
            max_value=12,
            value=DEFAULT_HABER_CODE_LENGTH,
            step=1,
        )
    )

    st.header("Sección 5: Ejecutar auditoría")
    if st.button("Ejecutar auditoría", type="primary", disabled=not can_execute):
        detail, summary = compare_dataframes(
            previous_df,
            current_df,
            previous_mapping,
            current_mapping,
            key_fields,
            medium_threshold=medium_threshold,
            high_threshold=high_threshold,
            code_length=code_length,
        )
        st.session_state["detail"] = detail
        st.session_state["summary"] = summary
        st.session_state["previous_name"] = previous_file.name
        st.session_state["current_name"] = current_file.name
        st.session_state["config_used"] = pd.DataFrame(
            [
                {"Campo": field, "Mes anterior": previous_mapping.get(field), "Mes actual": current_mapping.get(field)}
                for field in STANDARD_FIELDS
            ]
            + [
                {"Campo": "Llave", "Mes anterior": ", ".join(key_fields), "Mes actual": ", ".join(key_fields)},
                {"Campo": "Umbral alerta media", "Mes anterior": medium_threshold, "Mes actual": medium_threshold},
                {"Campo": "Umbral alerta alta", "Mes anterior": high_threshold, "Mes actual": high_threshold},
                {"Campo": "Largo código de haber", "Mes anterior": code_length, "Mes actual": code_length},
            ]
        )
        st.session_state["code_length"] = code_length

    if "detail" not in st.session_state:
        st.stop()

    detail = st.session_state["detail"]
    summary = st.session_state["summary"]

    st.header("Sección 6: Resultados")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Diferencias", summary["Total de diferencias detectadas"])
    col2.metric("Positiva total", format_money(summary["Diferencia positiva total"]))
    col3.metric("Negativa total", format_money(summary["Diferencia negativa total"]))
    col4.metric("Diferencia neta", format_money(summary["Diferencia neta"]))
    col5.metric("Alertas altas", summary["Cantidad de casos de alerta alta"])
    col6.metric("Revisión manual", summary["Cantidad de casos que requieren revisión manual"])
    render_executive_summary(detail, summary)

    if detail.empty:
        st.success("No se detectaron diferencias con la configuración actual.")
    else:
        filtered = filter_results(detail)
        st.dataframe(style_money_columns(filtered), use_container_width=True, hide_index=True)
        render_charts(filtered)

    st.header("Sección 7: Exportar reporte")
    report_bytes = export_report_excel(
        detail,
        summary,
        st.session_state["previous_name"],
        st.session_state["current_name"],
        st.session_state.get("config_used"),
        st.session_state.get("code_length", DEFAULT_HABER_CODE_LENGTH),
    )
    st.download_button(
        "Descargar reporte Excel",
        data=report_bytes,
        file_name=f"reporte_auditoria_hph_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
