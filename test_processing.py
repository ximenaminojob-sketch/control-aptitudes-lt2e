"""Pruebas sintéticas: no usar ni compartir datos de trabajadores."""
from datetime import date
from processing import build_index, course_result, medical_result, newest_medical, person_report

def check():
    today = date(2026, 10, 21)
    cap = [{"dni":"99.999.999", "name":"PERSONA DEMO", "ta_teorico":"46200", "ta_practico":"S/N", "ec_teorico":"2026-08-10", "ec_practico":"PENDIENTE", "cmd":"N/A"}]
    med = [
        {"dni":"99999999", "proyecto":"ARG - Los Toldos 2 Este", "fecha_examen":"2026-05-01", "fecha_apto":"2026-05-03", "vigencia":"2027-05-01", "ta":"APTO", "ec":"APTO", "conduccion":"APTO", "estatus":"Asignacion de Apto B"},
        {"dni":"99999999", "proyecto":"ARG - Los Toldos 2 Este", "fecha_examen":"2026-10-10", "estatus":"Solicitud inicial de examen"},
    ]
    hc = [{"dni":"99999999", "name":"PERSONA DEMO", "puesto":"AYUDANTE", "fase":"PIPING"}]
    idx = build_index(cap, med, hc, [])
    r = person_report(idx, "99.999.999", today)
    assert r["med"]["ta"]["level"] == "warn", "No reutilizar APTO antiguo si hay solicitud posterior sin evaluar"
    assert r["practica_altura"]["registered"] is False
    assert r["teoria_espacios"]["registered"] is True
    assert r["tipo_personal"] == "Propio – Techint"
    assert medical_result({"ta":"APTO", "vigencia":"2026-10-20"}, "ta", today)["label"] == "APTO VENCIDO"
    assert medical_result({"ta":"NO APTO", "vigencia":"2027-01-01"}, "ta", today)["label"] == "NO APTO"
    sub = [{"dni":"12345678", "name":"SUBCONTRATISTA DEMO", "empresa":"EMPRESA DEMO", "especialidad":"MONTAJE"}]
    s = person_report(build_index([], [], [], sub), "12.345.678", today)
    assert s["tipo_personal"] == "Subcontrato" and s["empresa"] == "EMPRESA DEMO"
    print("OK: 8 validaciones sintéticas aprobadas")

if __name__ == '__main__':
    check()
