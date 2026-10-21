"""Integración local de nómina, EMHA y Headcount LT2E.

Lee solamente columnas relevantes de Excel usando la biblioteca estándar.
No imprime ni exporta datos personales y no genera habilitaciones operativas.
"""
from __future__ import annotations

import csv
import io
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
M = "{" + MAIN_NS + "}"


def normalize(value) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", str(value or "").lower()).encode("ascii", "ignore").decode("ascii")).split())


def dni_key(value) -> str:
    s = str(value or "").strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    digits = re.sub(r"\D", "", s)
    return digits.lstrip("0") if len(digits) >= 7 else ""


def excel_date(value) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, (datetime, date)):
        return value.date() if isinstance(value, datetime) else value
    s = str(value).strip()
    try:
        n = float(s)
        if 25000 <= n <= 90000:
            return date(1899, 12, 30) + timedelta(days=int(n))
    except (ValueError, OverflowError):
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def fmt_date(d) -> str:
    parsed = excel_date(d)
    return parsed.strftime("%d/%m/%Y") if parsed else "Sin fecha registrada"


def _col(ref: str) -> str:
    m = re.match(r"[A-Z]+", ref)
    return m.group() if m else ""


def _shared(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    with z.open("xl/sharedStrings.xml") as fp:
        root = ET.parse(fp).getroot()
    return ["".join(t.text or "" for t in si.iter(M + "t")) for si in root.findall(M + "si")]


def _worksheet_path(z: zipfile.ZipFile, name: str) -> str:
    w = ET.fromstring(z.read("xl/workbook.xml"))
    relationships = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target_map = {el.get("Id"): el.get("Target") for el in relationships.findall("{" + PKG_NS + "}Relationship")}
    sheet = next((s for s in w.findall("." + "/" + M + "sheets" + "/" + M + "sheet") if s.get("name", "").casefold() == name.casefold()), None)
    if sheet is None:
        raise ValueError(f"No se encuentra la hoja «{name}»")
    target = target_map[sheet.get("{" + R_NS + "}id")]
    path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
    if path not in z.namelist():
        raise ValueError("No se encontró el contenido de la hoja solicitada")
    return path


def _value(cell: ET.Element, strings: list[str]) -> str:
    value = cell.find(M + "v")
    if value is not None and value.text is not None:
        raw = value.text
        if cell.get("t") == "s":
            return strings[int(raw)]
        if cell.get("t") == "b":
            return "Sí" if raw == "1" else "No"
        return raw
    inline = cell.find(M + "is")
    return "".join(x.text or "" for x in inline.iter(M + "t")) if inline is not None else ""


def read_selected(path: Path, sheet: str, header_row: int, selectors: dict[str, tuple[str, ...]], required: set[str]) -> list[dict]:
    """Selectors are exact normalized header names; verifies mandatory structure."""
    with zipfile.ZipFile(path) as z:
        strings = _shared(z)
        wp = _worksheet_path(z, sheet)
        chosen = None
        output = []
        with z.open(wp) as fp:
            iterator = ET.iterparse(fp, events=("start", "end"))
            root = None
            for event, el in iterator:
                if root is None and event == "start":
                    root = el
                if event != "end" or el.tag != M + "row":
                    continue
                rn = int(el.get("r", "0"))
                if rn == header_row:
                    headers = {_col(c.get("r", "")): normalize(_value(c, strings)) for c in el.findall(M + "c")}
                    chosen = {}
                    for key, aliases in selectors.items():
                        found = next((col for col, text in headers.items() if text in {normalize(a) for a in aliases}), None)
                        if found:
                            chosen[found] = key
                        elif key in required:
                            raise ValueError(f"La hoja «{sheet}» no tiene la columna requerida «{aliases[0]}»")
                elif rn > header_row and chosen:
                    record = {"_row": rn}
                    for c in el.findall(M + "c"):
                        key = chosen.get(_col(c.get("r", "")))
                        if key:
                            s = _value(c, strings).strip()
                            if s:
                                record[key] = s
                    if dni_key(record.get("dni")):
                        record["dni"] = dni_key(record["dni"])
                        output.append(record)
                el.clear()
                if root is not None and rn % 500 == 0:
                    root.clear()
        if chosen is None:
            raise ValueError(f"No se pudo leer el encabezado de la hoja «{sheet}»")
        return output


TRAIN_COLS = {
    "name": ("NOMBRE Y APELLIDO",),
    "dni": ("DNI",),
    "puesto": ("PUESTO",),
    "especialidad": ("ESPECIALIDAD",),
    "ta_teorico": ("TRABAJO EN ALTURA  -TEORICO   3HS",),
    "ta_practico": ("PRACTICA DE TRABAJO EN ALTURA",),
    "ec_teorico": ("ESPACIOS CONFINADOS - TEORICO 3HS",),
    "ec_practico": ("PRACTICA DE ESPACIO CONFINADO",),
    "cmd": ("CMD INTERNO              4HS",),
}
MED_COLS = {
    "dni": ("RFC / DNI / No. Doc",), "name": ("Nombre",),
    "apellido": ("Apellidos",), "puesto": ("Puesto",),
    "proyecto": ("Proyecto",), "tipo_examen": ("Tipo Examen",),
    "estatus": ("Estatus",), "fecha_examen": ("Fecha Examen",),
    "fecha_apto": ("Fecha Apto",), "fecha_real": ("Fecha Real Examen",),
    "vigencia": ("Vigencia Apto",),
    "ta": ("Aptitud Alturas",), "ec": ("Aptitud Espacios Confinados",),
    "conduccion": ("Aptitud Conducción",),
}
HC_COLS = {
    "dni": ("Dni",), "name": ("Empleado",), "puesto": ("Puesto",),
    "fase": ("Fase_PyCP",), "condicion": ("Condición",),
}


def load_files(training: Path, emha: Path, headcount: Path, subcontract_csv: Path | None = None) -> dict:
    cap = read_selected(training, "TECHINT", 6, TRAIN_COLS, set(TRAIN_COLS))
    med = read_selected(emha, "Sheet", 1, MED_COLS, set(MED_COLS) - {"fecha_real", "tipo_examen", "apellido", "name", "puesto"})
    hc = read_selected(headcount, "HeadCount_LosToldos", 1, HC_COLS, {"dni", "name", "puesto", "fase"})
    med = [r for r in med if normalize(r.get("proyecto", "")) == "arg los toldos 2 este"]
    subcontract = []
    if subcontract_csv and subcontract_csv.is_file():
        with subcontract_csv.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                item = {normalize(k).replace(" ", "_"): str(v or "").strip() for k, v in row.items() if k}
                d = dni_key(item.get("dni"))
                if d:
                    subcontract.append({"dni": d, "name": item.get("apellido_y_nombre") or item.get("apellido_nombre") or "", "puesto": item.get("puesto", ""), "especialidad": item.get("especialidad", ""), "empresa": item.get("empresa", "")})
    return build_index(cap, med, hc, subcontract)


def build_index(cap: list[dict], med: list[dict], hc: list[dict], subs: list[dict]) -> dict:
    index = defaultdict(lambda: {"capac": [], "med": [], "hc": [], "sub": []})
    for kind, rows in (("capac", cap), ("med", med), ("hc", hc), ("sub", subs)):
        for row in rows:
            d = dni_key(row.get("dni"))
            if d:
                index[d][kind].append(row)
    return dict(index)


def newest_medical(records: list[dict]):
    """Latest exam/request, including pending result, to avoid reuse of older APTO."""
    valid = [r for r in records if normalize(r.get("estatus", "")) not in ("cancelado", "retiro")]
    if not valid:
        return None
    return max(valid, key=lambda r: (max((excel_date(r.get(c)) or date.min) for c in ("fecha_examen", "fecha_real", "fecha_apto")), excel_date(r.get("fecha_apto")) or date.min, int(r.get("_row", 0))))


def course_result(records: list[dict], key: str) -> dict:
    values = [r.get(key, "") for r in records]
    dates = [d for v in values if (d := excel_date(v)) is not None]
    if dates:
        latest = max(dates)
        return {"registered": True, "date": latest, "label": "Registrada", "source_value": fmt_date(latest)}
    raw = next((str(v).strip() for v in reversed(values) if str(v or "").strip()), "")
    return {"registered": False, "date": None, "label": "Sin fecha registrada", "source_value": raw or "Sin dato"}


def medical_result(record: dict | None, key: str, today: date) -> dict:
    if not record:
        return {"label": "Sin registro EMHA", "level": "muted", "raw": "", "date": None, "vigencia": None}
    raw = str(record.get(key, "")).strip()
    expiry = excel_date(record.get("vigencia"))
    status = normalize(raw)
    if status == "apto":
        if not expiry:
            label, level = "APTO / sin vigencia verificable", "warn"
        elif expiry < today:
            label, level = "APTO VENCIDO", "danger"
        else:
            label, level = "APTO VIGENTE", "good"
    elif status == "no apto":
        label, level = "NO APTO", "danger"
    elif status in ("no aplica", "no corresponde"):
        label, level = raw.upper(), "muted"
    elif status in ("examen faltante", "falta examen", "falta espirometria", "verificar y asignar", "nc"):
        label, level = raw.upper(), "warn"
    else:
        label, level = "EN EVALUACIÓN / SIN RESULTADO", "warn"
    return {"label": label, "level": level, "raw": raw, "date": excel_date(record.get("fecha_apto")), "vigencia": expiry}


def person_report(index: dict, dni: str, today: date | None = None) -> dict | None:
    key = dni_key(dni)
    p = index.get(key)
    if not key or p is None:
        return None
    today = today or date.today()
    hc = p["hc"][-1] if p["hc"] else {}
    sub = p["sub"][-1] if p["sub"] else {}
    cap = p["capac"][-1] if p["capac"] else {}
    med = newest_medical(p["med"])
    med_name = " ".join(v.strip() for v in (med or {}).get("apellido", "").split()) + " " + " ".join(v.strip() for v in (med or {}).get("name", "").split()) if med else ""
    ident = sub or hc or cap or med or {}
    own = bool(hc)
    contractor = bool(sub)
    name = ident.get("name", "") or cap.get("name", "") or med_name
    especialidad = (sub.get("especialidad") or cap.get("especialidad") or hc.get("fase", "")).strip()
    return {
        "dni": key,
        "nombre": name.strip() or med_name.strip() or "Sin nombre identificado",
        "puesto": sub.get("puesto") or hc.get("puesto") or cap.get("puesto") or (med or {}).get("puesto") or "No informado",
        "especialidad": especialidad or "No informada",
        "tipo_personal": "Subcontrato" if contractor else "Propio – Techint" if own else "No identificado",
        "empresa": sub.get("empresa") or ("Techint Ingeniería y Construcción" if own and not contractor else "No informada"),
        "med": {k: medical_result(med, k, today) for k in ("ta", "ec", "conduccion")},
        "teoria_altura": course_result(p["capac"], "ta_teorico"),
        "practica_altura": course_result(p["capac"], "ta_practico"),
        "teoria_espacios": course_result(p["capac"], "ec_teorico"),
        "practica_espacios": course_result(p["capac"], "ec_practico"),
        "cmd": course_result(p["capac"], "cmd"),
        "tipo_examen": (med or {}).get("tipo_examen") or "No informado",
        "fecha_examen": excel_date((med or {}).get("fecha_examen")),
        "fecha_apto": excel_date((med or {}).get("fecha_apto")),
        "tiene_fuente_cap": bool(p["capac"]),
        "tiene_fuente_emha": bool(p["med"]),
        "tiene_fuente_hc": bool(p["hc"]),
        "tiene_sub": contractor,
    }
