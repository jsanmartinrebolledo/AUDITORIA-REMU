import io

import pandas as pd

from app import compare_dataframes, export_report_excel, guess_mapping


def test_guess_mapping_recognizes_sirh_movement_aliases():
    columns = [
        "RUN",
        "DV",
        "NOMBRE_FUNCIONARIO",
        "LEY",
        "JORNADA_HORAS",
        "CORRELATIVO_CARGO",
        "UNIDAD_DESEMPENO",
        "CENTRO_COSTO",
        "CODIGO_MOVIMIENTO",
        "NOMBRE_MOVIMIENTO",
        "MONTO_PAGO",
        "TIPO_PROCESO",
    ]

    mapping = guess_mapping(columns)

    assert mapping["CODIGO_HABER"] == "CODIGO_MOVIMIENTO"
    assert mapping["NOMBRE_HABER"] == "NOMBRE_MOVIMIENTO"
    assert mapping["JORNADA"] == "JORNADA_HORAS"
    assert mapping["CARGO_CORRELATIVO"] == "CORRELATIVO_CARGO"
    assert mapping["CENTRO_COSTO"] == "CENTRO_COSTO"
    assert mapping["UNIDAD"] == "UNIDAD_DESEMPENO"
    assert mapping["MONTO"] == "MONTO_PAGO"
    assert mapping["TIPO_PROCESO"] == "TIPO_PROCESO"


def test_compare_detects_amount_and_new_code():
    previous = pd.DataFrame(
        [
            ["11111111", "1", "Ana Torres", "19.664", 44, "1", "MED", "001", "Sueldo base", 1000000],
            ["11111111", "1", "Ana Torres", "19.664", 44, "1", "MED", "210", "Trienios", 120000],
        ],
        columns=[
            "RUN",
            "DV",
            "Nombre",
            "Ley",
            "Jornada",
            "Cargo",
            "Centro de costo",
            "Codigo haber",
            "Nombre haber",
            "Monto",
        ],
    )
    current = pd.DataFrame(
        [
            ["11111111", "1", "Ana Torres", "19.664", 44, "1", "MED", "001", "Sueldo base", 1000000],
            ["11111111", "1", "Ana Torres", "19.664", 44, "1", "MED", "210", "Trienios", 150000],
            ["11111111", "1", "Ana Torres", "19.664", 44, "1", "MED", "330", "Reforzamiento profesional", 80000],
        ],
        columns=previous.columns,
    )
    mapping = {
        "RUN": "RUN",
        "DV": "DV",
        "NOMBRE": "Nombre",
        "LEY": "Ley",
        "JORNADA": "Jornada",
        "CARGO_CORRELATIVO": "Cargo",
        "UNIDAD": None,
        "CENTRO_COSTO": "Centro de costo",
        "CODIGO_HABER": "Codigo haber",
        "NOMBRE_HABER": "Nombre haber",
        "MONTO": "Monto",
        "PORCENTAJE": None,
    }

    detail, summary = compare_dataframes(
        previous,
        current,
        mapping,
        mapping,
        ["RUN", "DV", "LEY", "CARGO_CORRELATIVO", "JORNADA", "CENTRO_COSTO"],
    )

    assert summary["Total de diferencias detectadas"] == 2
    assert set(detail["Causa probable"]) == {
        "Reforzamiento profesional diurno",
        "Trienios / antigüedad",
    }
    assert detail["Diferencia"].sum() == 110000
    assert summary["Cantidad de casos que requieren revisión manual"] == 0


def test_law_and_haber_code_are_formatted_as_text():
    previous = pd.DataFrame(
        [[11111111, "1", "Ana Torres", "19.664000", 44, "1", "MED", 21, "Trienios", 120000]],
        columns=[
            "RUN",
            "DV",
            "Nombre",
            "Ley",
            "Jornada",
            "Cargo",
            "Centro de costo",
            "Codigo haber",
            "Nombre haber",
            "Monto",
        ],
    )
    current = previous.copy()
    current.loc[0, "Monto"] = 150000
    mapping = {
        "RUN": "RUN",
        "DV": "DV",
        "NOMBRE": "Nombre",
        "LEY": "Ley",
        "JORNADA": "Jornada",
        "CARGO_CORRELATIVO": "Cargo",
        "UNIDAD": None,
        "CENTRO_COSTO": "Centro de costo",
        "CODIGO_HABER": "Codigo haber",
        "NOMBRE_HABER": "Nombre haber",
        "MONTO": "Monto",
        "PORCENTAJE": None,
    }

    detail, _ = compare_dataframes(
        previous,
        current,
        mapping,
        mapping,
        ["RUN", "DV", "LEY", "JORNADA", "CARGO_CORRELATIVO", "CENTRO_COSTO", "CODIGO_HABER"],
    )

    assert detail.loc[0, "Ley"] == "19.664"
    assert detail.loc[0, "Código haber"] == "0021"
    assert detail.loc[0, "TIPO_DIFERENCIA"] == "Diferencia de monto"


def test_export_report_generates_workbook_bytes():
    detail = pd.DataFrame(
        [
            {
                "RUN": "11111111",
                "DV": "1",
                "Nombre": "Ana Torres",
                "Ley": "19.664",
                "Jornada": 44,
                "Cargo/correlativo": "1",
                "Unidad": "Medicina",
                "Centro de costo": "MED",
                "Código haber": "210",
                "Nombre haber": "Trienios",
                "Monto anterior": 120000,
                "Monto actual": 150000,
                "Diferencia": 30000,
                "Porcentaje anterior": "",
                "Porcentaje actual": "",
                "Diferencia porcentaje": "",
                "Causa probable": "Posible diferencia por trienios",
                "Nivel de alerta": "Bajo",
                "Observación": "Caso de prueba",
                "Dato faltante": "",
            }
        ]
    )
    summary = {
        "Fecha de auditoría": "2026-05-30 01:00",
        "Total de registros mes anterior": 2,
        "Total de registros mes actual": 3,
        "Total de funcionarios comparados": 1,
        "Total de diferencias detectadas": 1,
        "Diferencia positiva total": 30000,
        "Diferencia negativa total": 0,
        "Diferencia neta": 30000,
        "Cantidad de casos de alerta alta": 0,
        "Cantidad de casos que requieren revisión manual": 0,
    }

    data = export_report_excel(detail, summary, "anterior.xlsx", "actual.xlsx")
    workbook = pd.ExcelFile(io.BytesIO(data))

    assert {"RESUMEN", "DIF_DETALLE"}.issubset(set(workbook.sheet_names))
    assert "CASOS_ALERTA" in workbook.sheet_names


def test_unclassified_amount_difference_requires_manual_review():
    previous = pd.DataFrame(
        [["99999999", "9", "Caso Sin Glosa", "19.664", 44, "1", "MED", "999", "Haber generico", 100000]],
        columns=[
            "RUN",
            "DV",
            "Nombre",
            "Ley",
            "Jornada",
            "Cargo",
            "Centro de costo",
            "Codigo haber",
            "Nombre haber",
            "Monto",
        ],
    )
    current = previous.copy()
    current.loc[0, "Monto"] = 125000
    mapping = {
        "RUN": "RUN",
        "DV": "DV",
        "NOMBRE": "Nombre",
        "LEY": "Ley",
        "JORNADA": "Jornada",
        "CARGO_CORRELATIVO": "Cargo",
        "UNIDAD": None,
        "CENTRO_COSTO": "Centro de costo",
        "CODIGO_HABER": "Codigo haber",
        "NOMBRE_HABER": "Nombre haber",
        "MONTO": "Monto",
        "PORCENTAJE": None,
    }

    detail, summary = compare_dataframes(
        previous,
        current,
        mapping,
        mapping,
        ["RUN", "DV", "LEY", "CARGO_CORRELATIVO", "JORNADA", "CENTRO_COSTO"],
    )

    assert detail.loc[0, "Causa probable"] == "Diferencia no clasificada"
    assert detail.loc[0, "Nivel de alerta"] == "Bajo"
    assert summary["Cantidad de casos que requieren revisión manual"] == 0
