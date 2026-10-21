"""LT2E | Consulta de aptitudes médicas y capacitaciones (acceso restringido).

No colocar Excel de salud en GitHub ni habilitar consultas públicas sin autenticación.
En producción requiere OIDC corporativo y lista explícita de usuarios autorizados.
"""
from __future__ import annotations

import base64
import html
import os
import re
from datetime import date
from pathlib import Path

import streamlit as st

from processing import build_index, dni_key, fmt_date, load_files, person_report

st.set_page_config(page_title="Control de Aptitudes | LT2E", page_icon="✅", layout="wide", initial_sidebar_state="collapsed")
ROOT = Path(__file__).resolve().parent
GREEN, BLUE, GRAY = "#009900", "#002B5C", "#6E6E6E"

STYLE = """
<style>
:root {--verde:#009900;--azul:#002B5C;--gris:#6E6E6E;--borde:#D8E1E5;}
html, body, .stApp, [data-testid="stAppViewContainer"] {font-family:Calibri,Carlito,Arial,sans-serif!important;color:#203249}
.stApp{background:#fff}
.block-container{max-width:1100px;padding-top:2rem;padding-bottom:2.4rem}
#MainMenu, footer{visibility:hidden}
header[data-testid="stHeader"]{background:transparent}
.brand{display:flex;align-items:center;justify-content:space-between;gap:25px;padding:5px 0 19px}
.brand h1{font-size:clamp(1.65rem,3vw,2.35rem);font-weight:750;color:#002B5C;letter-spacing:-.025em;margin:8px 0 4px;line-height:1.09}
.brand .eyebrow{font-size:.8rem;letter-spacing:.095em;text-transform:uppercase;color:#009900;font-weight:800}
.brand .subtitle{color:#65717D;font-size:1rem;margin-top:8px}
.brand img{width:235px;max-width:32%;height:auto;object-fit:contain}
.brand-rule{width:100%;height:5px;background:#009900;margin:0 0 23px}
.hero{border:1px solid #D8E1E5;border-left:5px solid #009900;background:#F9FBFA;padding:18px 21px;margin-bottom:17px;border-radius:4px;color:#34495E;line-height:1.55}
.hero strong{color:#002B5C}
.section-heading{font-size:1.18rem;font-weight:800;color:#002B5C;margin:29px 0 11px}
.person{border:1px solid #D8E1E5;border-left:5px solid #009900;border-radius:4px;padding:20px 22px;background:#fff;margin:16px 0 24px}
.person h2{margin:0 0 15px;font-size:1.45rem;color:#002B5C;line-height:1.2}
.pgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px 24px}
.dat-label{font-size:.72rem;color:#6E6E6E;font-weight:800;letter-spacing:.07em;text-transform:uppercase}
.dat-val{font-size:.96rem;color:#203249;margin-top:4px;overflow-wrap:anywhere}
.tri-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px}
.big-card{border:1px solid #D8E1E5;border-top:4px solid #002B5C;border-radius:5px;min-width:0;background:white;padding:17px}
.big-card h3{font-size:1.19rem;color:#002B5C;margin:0 0 9px;min-height:45px;line-height:1.25}
.card-kicker{font-size:.73rem;font-weight:800;letter-spacing:.07em;color:#6E6E6E;text-transform:uppercase;margin:13px 0 5px}
.chip{display:inline-block;font-size:.81rem;font-weight:750;border-radius:4px;padding:5px 8px;max-width:100%;overflow-wrap:anywhere}
.chip.good{color:#036900;background:#E7F5E8}
.chip.danger{color:#A22B20;background:#FFEEEE}
.chip.warn{color:#946500;background:#FFF5DF}
.chip.muted{color:#566574;background:#EDF0F3}
.valid{font-weight:750;font-size:1.1rem;color:#002B5C;padding-top:4px}
.valid.missing{font-size:.91rem;color:#66727B;font-weight:600}
.divline{border-top:1px solid #D8E1E5;margin:15px 0 11px}
.course{display:flex;justify-content:space-between;gap:7px;align-items:flex-start;margin:12px 0 0}
.course-name{font-size:.89rem;color:#34495E;font-weight:700;max-width:55%;line-height:1.3}
.course-date{font-size:.89rem;font-weight:800;color:#002B5C;text-align:right;line-height:1.4}
.course-date.not{color:#777;font-weight:600}
.course-raw{display:block;font-size:.72rem;color:#777;text-align:right;font-weight:400}
.footer-note{margin:28px 0 0;padding:14px 2px;border-top:4px solid #009900;color:#63707A;font-size:.84rem;line-height:1.6}
[data-testid="stForm"]{border:0;padding:0}
[data-testid="stFormSubmitButton"] button,[data-testid="stBaseButton-primary"]{background:#009900;border-color:#009900;border-radius:4px;color:white;min-height:45px;font-weight:800}
[data-testid="stFormSubmitButton"] button:hover,[data-testid="stBaseButton-primary"]:hover{background:#007900;border-color:#007900}
@media(max-width:780px){.tri-grid{grid-template-columns:1fr}.big-card h3{min-height:0}.pgrid{grid-template-columns:1fr 1fr}.brand img{width:160px;max-width:35%}.block-container{padding:1.45rem 1rem}}
@media(max-width:460px){.brand{gap:10px}.brand h1{font-size:1.44rem}.brand .eyebrow{font-size:.66rem}.brand .subtitle{font-size:.81rem}.brand img{width:112px;max-width:35%}.pgrid{grid-template-columns:1fr}.person{padding:15px}}
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)


def safe(x) -> str:
    return html.escape(str(x or ""), quote=True)


def _secrets(key, fallback=None):
    try:
        return st.secrets.get(key, fallback)
    except (FileNotFoundError, OSError):
        return fallback


def _brand():
    logo = ROOT / "logo_techint.png"
    image = ""
    if logo.is_file():
        data = base64.b64encode(logo.read_bytes()).decode("ascii")
        image = f'<img src="data:image/png;base64,{data}" alt="Techint Ingeniería y Construcción"/>'
    st.markdown(f'''<div class="brand"><div>
      <div class="eyebrow">PROYECTO LOS TOLDOS II ESTE · MASS</div>
      <h1>Control de Aptitudes<br>y Habilitaciones</h1>
      <div class="subtitle">Consulta de aptitud médica y formación registrada</div>
      </div>{image}</div><div class="brand-rule"></div>''', unsafe_allow_html=True)


def _demo_index():
    example = {
        "dni":"99999999", "name":"PERSONA DE DEMOSTRACIÓN", "puesto":"OPERARIO/A", "especialidad":"PIPING",
        "ta_teorico":"2026-08-07", "ta_practico":"2026-09-02", "ec_teorico":"PENDIENTE",
        "ec_practico":"S/N", "cmd":"2026-09-10"
    }
    med = {"dni":"99999999", "proyecto":"ARG - Los Toldos 2 Este", "estatus":"Asignacion de Apto B",
        "ta":"APTO", "ec":"NO APTO", "conduccion":"APTO", "vigencia":"2027-04-30",
        "fecha_apto":"2026-10-01", "fecha_examen":"2026-10-01", "tipo_examen":"Periodico"}
    return build_index([example], [med], [{"dni":"99999999", "name":"PERSONA DE DEMOSTRACIÓN", "puesto":"OPERARIO/A", "fase":"PIPING"}], [])


def _auth():
    # Solo se puede omitir autenticar para la vista con registros inventados.
    if os.getenv("APP_DEMO_MODE", "0") == "1":
        st.warning("MODO DEMOSTRACIÓN: datos completamente ficticios. No utilizar para acreditar habilitaciones.")
        return True
    if not _secrets("auth"):
        st.error("Acceso restringido: falta configurar autenticación corporativa (OIDC). La aplicación no leerá ni mostrará datos médicos.")
        st.info("IT debe configurar Microsoft Entra ID u otro proveedor OIDC y usuarios autorizados. Consultá el README incluido.")
        return False
    if not getattr(st.user, "is_logged_in", False):
        st.info("Esta consulta incluye datos médicos. Ingresá con tu cuenta corporativa autorizada.")
        if st.button("Ingresar con cuenta corporativa", type="primary"):
            st.login()
        return False
    allow = _secrets("APP_ALLOWED_EMAILS", [])
    if isinstance(allow, str):
        allow = [x.strip() for x in re.split(r"[,;]", allow)]
    allowed = {str(x).strip().casefold() for x in (allow or []) if str(x).strip()}
    current = str(st.user.get("email", "")).strip().casefold()
    if not allowed or current not in allowed:
        st.error("Tu cuenta no está autorizada para consultar aptitudes médicas en LT2E.")
        if st.button("Cerrar sesión"):
            st.logout()
        return False
    with st.sidebar:
        st.caption(f"Acceso autorizado: {safe(current)}")
        if st.button("Cerrar sesión"):
            st.logout()
    return True


def _fingerprint(p: Path):
    s = p.stat()
    return str(p), s.st_mtime_ns, s.st_size


@st.cache_data(ttl=300, show_spinner=False)
def _cached_data(info):
    tr, med, hc, sub = (Path(info[i][0]) if info[i] else None for i in range(4))
    return load_files(tr, med, hc, sub)


def _sources():
    basedir = Path(str(_secrets("APP_DATA_DIR", os.environ.get("APP_DATA_DIR", str(ROOT / "data"))))).expanduser()
    paths = [basedir / "base_capacitaciones.xlsx", basedir / "SeguimientoSolicitudesData.xlsx", basedir / "HC.xlsx"]
    if not all(p.is_file() for p in paths):
        st.error("Las bases autorizadas no están disponibles en el servidor.")
        st.caption("Deben existir en la carpeta interna: base_capacitaciones.xlsx, SeguimientoSolicitudesData.xlsx y HC.xlsx. No subirlas a GitHub.")
        return None
    sub = basedir / "padron_subcontratos.csv"
    info = tuple(_fingerprint(p) for p in paths) + (_fingerprint(sub) if sub.is_file() else None,)
    with st.spinner("Sincronizando registros de aptitudes y capacitación..."):
        return _cached_data(info)


def _datum(label, value):
    return f'<div><div class="dat-label">{safe(label)}</div><div class="dat-val">{safe(value)}</div></div>'


def _course(label, result):
    recorded = result["registered"]
    display = fmt_date(result["date"]) if recorded else "Sin fecha registrada"
    raw = "" if recorded or result["source_value"] == "Sin dato" else f'<span class="course-raw">En base: {safe(result["source_value"])}</span>'
    return f'<div class="course"><span class="course-name">{safe(label)}</span><span class="course-date {"" if recorded else "not"}">{safe(display)}{raw}</span></div>'


def _panel(title, medical, courses):
    expiry = fmt_date(medical["vigencia"]) if medical["vigencia"] else "Sin fecha verificable"
    expiry_class = "" if medical["vigencia"] else "missing"
    courses_html = "".join(_course(title, data) for title, data in courses)
    return f'''<section class="big-card"><h3>{safe(title)}</h3>
    <div class="card-kicker">Aptitud médica</div>
    <span class="chip {medical['level']}">{safe(medical['label'])}</span>
    <div class="card-kicker">Vigencia del apto</div>
    <div class="valid {expiry_class}">{safe(expiry)}</div>
    <div class="divline"></div>
    <div class="card-kicker">Capacitaciones</div>{courses_html}</section>'''


def _report(r):
    st.markdown('<div class="section-heading">Datos del personal</div>', unsafe_allow_html=True)
    p = "".join([
        _datum("DNI", r["dni"]),
        _datum("Puesto", r["puesto"]),
        _datum("Especialidad / fase", r["especialidad"]),
        _datum("Vínculo", r["tipo_personal"]),
        _datum("Empresa", r["empresa"]),
        _datum("Último examen considerado", fmt_date(r["fecha_examen"])),
    ])
    st.markdown(f'<section class="person"><h2>{safe(r["nombre"])}</h2><div class="pgrid">{p}</div></section>', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Estado de aptitudes y capacitaciones</div>', unsafe_allow_html=True)
    a = _panel("Trabajo en Altura", r["med"]["ta"], [("Teórico", r["teoria_altura"]), ("Práctica", r["practica_altura"])])
    b = _panel("Espacios Confinados", r["med"]["ec"], [("Teórico", r["teoria_espacios"]), ("Práctica", r["practica_espacios"])])
    c = _panel("Conducción", r["med"]["conduccion"], [("CMD interno", r["cmd"])])
    st.markdown(f'<div class="tri-grid">{a}{b}{c}</div>', unsafe_allow_html=True)
    missing = []
    if not r["tiene_fuente_emha"]:
        missing.append("EMHA: no se encontró examen para este DNI en el proyecto")
    if not r["tiene_fuente_cap"]:
        missing.append("Capacitaciones: DNI sin registro en la nómina provista")
    if r["tipo_personal"] == "No identificado":
        missing.append("Empresa/especialidad: no constan en Headcount ni padrón de subcontratos")
    if missing:
        st.warning(" · ".join(missing))
    st.markdown(f'''<div class="footer-note"><strong>Información de referencia · {date.today().strftime('%d/%m/%Y')}</strong><br>
    Los estados se calculan con las bases cargadas: un “APTO VIGENTE” requiere resultado APTO y vigencia no vencida.
    Un registro de capacitación solo se considera realizado si contiene una fecha válida.
    <strong>Esta consulta no sustituye la autorización formal de MASS, Servicio Médico y responsables operativos</strong> ni verifica credencial de conductor, categoría de licencia u otras exigencias aplicables.</div>''', unsafe_allow_html=True)


_brand()
if not _auth():
    st.stop()

if os.getenv("APP_DEMO_MODE", "0") == "1":
    index = _demo_index()
else:
    try:
        index = _sources()
    except Exception:
        # No entregar trazas ni contenido sensible a la interfaz.
        st.error("No fue posible interpretar las bases. Verificá sus encabezados y formatos con el administrador.")
        st.stop()
    if index is None:
        st.stop()

st.markdown('''<div class="hero"><strong>Consultá los registros de un trabajador ingresando su DNI exacto.</strong><br>
  El sistema relaciona la nómina de capacitaciones, los exámenes del EMHA y el Headcount. No muestra listados generales de personal.</div>''', unsafe_allow_html=True)
with st.form("dni_search", clear_on_submit=False):
    identifier = st.text_input("DNI", placeholder="Ingresá el DNI sin puntos", max_chars=14)
    submitted = st.form_submit_button("Consultar aptitudes", type="primary", use_container_width=True)
if submitted:
    if not dni_key(identifier):
        st.warning("Ingresá un DNI válido para realizar la consulta.")
    else:
        result = person_report(index, identifier, date.today())
        if result is None:
            st.info("No se encontró un registro para ese DNI en las bases disponibles del proyecto.")
        else:
            _report(result)
