"""Consulta de Aptitudes LT2E.

La demo utiliza un DNI y resultados ficticios. Nunca publica bases reales sin
configurar inicio de sesión corporativo y una lista de usuarios autorizados.
"""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Control de Aptitudes | LT2E", page_icon="✅", layout="wide", initial_sidebar_state="collapsed")


def config(key, default=None):
    """Lee Secrets sin bloquear el inicio cuando todavía no hay Secrets."""
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def on(key: str) -> bool:
    return str(config(key, os.environ.get(key, "0"))).strip().lower() in ("1", "true", "on", "yes")


def emit_status(med):
    label, level = med.get("label", "Sin registro"), med.get("level", "muted")
    if level == "good":
        st.success(label, icon="✅")
    elif level == "danger":
        st.error(label, icon="⛔")
    elif level == "warn":
        st.warning(label, icon="⚠️")
    else:
        st.info(label, icon="ℹ️")


def shown_date(value) -> str:
    if value is None or value == "":
        return "Sin fecha registrada"
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    try:
        from processing import fmt_date
        return fmt_date(value)
    except Exception:
        return str(value)


def show_course(label, result):
    st.caption(label)
    if result.get("registered"):
        st.markdown(f"**{shown_date(result.get('date'))}**")
    else:
        st.write("Sin fecha registrada")


def show_panel(title, medical, courses):
    with st.container(border=True):
        st.subheader(title)
        st.caption("APTITUD MÉDICA")
        emit_status(medical)
        st.caption("VIGENCIA DEL APTO")
        st.markdown(f"**{shown_date(medical.get('vigencia'))}**" if medical.get('vigencia') else "**Sin fecha verificable**")
        st.divider()
        st.markdown("**Capacitaciones**")
        for label, course in courses:
            show_course(label, course)


def demo_report():
    def med(label, level, vig):
        return {"label":label,"level":level,"vigencia":vig}
    def cap(day=None):
        return {"registered":bool(day),"date":day,"source_value":day or "PENDIENTE"}
    return {
        "nombre":"PERSONA DE DEMOSTRACIÓN", "dni":"99999999", "puesto":"OPERARIO/A",
        "especialidad":"PIPING", "tipo_personal":"Ejemplo ficticio", "empresa":"—",
        "fecha_examen":date(2026,10,1),
        "med":{
            "ta": med("APTO VIGENTE","good",date(2027,4,30)),
            "ec": med("NO APTO","danger",date(2027,4,30)),
            "conduccion": med("APTO VIGENTE","good",date(2027,4,30)),
        },
        "teoria_altura":cap(date(2026,8,7)),"practica_altura":cap(date(2026,9,2)),
        "teoria_espacios":cap(),"practica_espacios":cap(),"cmd":cap(date(2026,9,10)),
        "tiene_fuente_emha":True,"tiene_fuente_cap":True,
    }


def login_allowed():
    # No se puede habilitar el uso con datos reales sin OIDC y lista de acceso.
    if not config("auth"):
        st.warning("Acceso restringido. Para usar registros reales, IT debe configurar autenticación corporativa (OIDC) y usuarios autorizados.")
        return False
    try:
        logged = bool(st.user.is_logged_in)
    except Exception:
        logged = False
    if not logged:
        st.info("Ingresá con una cuenta corporativa autorizada.")
        if st.button("Ingresar con cuenta corporativa"):
            st.login()
        return False
    allow = config("APP_ALLOWED_EMAILS", [])
    if isinstance(allow, str):
        allow = re.split(r"[,;]", allow)
    emails = {str(v).strip().lower() for v in allow if str(v).strip()}
    email = str(st.user.get("email", "")).strip().lower()
    if not email or email not in emails:
        st.error("Tu cuenta no tiene permiso para consultar registros médicos del proyecto.")
        return False
    if st.sidebar.button("Cerrar sesión"):
        st.logout()
    return True


@st.cache_data(ttl=300, show_spinner=False)
def load_authorized_data(file_info):
    from processing import load_files
    names = [Path(info[0]) if info is not None else None for info in file_info]
    return load_files(*names)


def load_index():
    folder = Path(str(config("APP_DATA_DIR", os.environ.get("APP_DATA_DIR", str(ROOT / "data"))))).expanduser()
    base = [folder / "base_capacitaciones.xlsx", folder / "SeguimientoSolicitudesData.xlsx", folder / "HC.xlsx"]
    if not all(p.is_file() for p in base):
        st.error("Faltan archivos en el almacenamiento privado del servidor. No los cargues en GitHub.")
        st.caption("Archivos esperados: base_capacitaciones.xlsx, SeguimientoSolicitudesData.xlsx, HC.xlsx")
        return None
    sub = folder / "padron_subcontratos.csv"
    files = base + [sub if sub.is_file() else None]
    info = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) if p else None for p in files)
    try:
        return load_authorized_data(info)
    except Exception as exc:
        # No mostramos a los usuarios trazas con datos de las fuentes.
        st.error("No se pudieron procesar las bases de datos. Pedí al administrador que revise el registro de errores.")
        print(f"ERROR PROCESAMIENTO LT2E: {type(exc).__name__}: {exc}")
        return None


# Encabezado nativo: aparece incluso si no hay Secrets, procesador o bases.
a, b = st.columns([4, 1.35], vertical_alignment="center")
with a:
    st.markdown("**:green[PROYECTO LOS TOLDOS II ESTE · MASS]**")
    st.title("Control de Aptitudes y Habilitaciones")
    st.caption("Consulta individual de aptitud médica y capacitaciones registradas")
with b:
    logo = ROOT / "logo_techint.png"
    if logo.is_file():
        st.image(str(logo), use_container_width=True)
st.divider()

DEMO = on("APP_DEMO_MODE")
if DEMO:
    st.warning("MODO DEMOSTRACIÓN · Solo datos inventados. No acredita habilitaciones ni lee archivos del personal.")
    index = None
else:
    if not login_allowed():
        st.stop()
    index = load_index()
    if index is None:
        st.stop()

st.write("Ingresá un **DNI exacto** para consultar la información disponible. No se publican listados de trabajadores.")
with st.form("consulta_dni"):
    dni = st.text_input("DNI", placeholder="Ej.: 99999999 (solo en demostración)", max_chars=14)
    search = st.form_submit_button("Consultar", type="primary", use_container_width=True)

if search:
    dni_digits = re.sub(r"\D", "", dni.strip()).lstrip("0")
    if len(dni_digits) < 7:
        st.warning("Ingresá un DNI válido.")
    elif DEMO:
        result = demo_report() if dni_digits == "99999999" else None
    else:
        from processing import person_report
        result = person_report(index, dni_digits, date.today())

    if len(dni_digits) >= 7:
        if result is None:
            st.info("No se encontró el DNI en los registros disponibles.")
        else:
            st.subheader(result["nombre"])
            with st.container(border=True):
                x, y, z = st.columns(3)
                x.metric("DNI", result.get("dni") or "—")
                y.metric("Puesto", result.get("puesto") or "—")
                z.metric("Especialidad", result.get("especialidad") or "—")
                st.caption(f"Personal: {result.get('tipo_personal') or 'No identificado'}  ·  Empresa: {result.get('empresa') or 'No informada'}  ·  Examen considerado: {shown_date(result.get('fecha_examen'))}")
            c1, c2, c3 = st.columns(3)
            with c1:
                show_panel("Trabajo en Altura", result["med"]["ta"], [("Teórico", result["teoria_altura"]), ("Práctica", result["practica_altura"])])
            with c2:
                show_panel("Espacios Confinados", result["med"]["ec"], [("Teórico", result["teoria_espacios"]), ("Práctica", result["practica_espacios"])])
            with c3:
                show_panel("Conducción", result["med"]["conduccion"], [("CMD interno", result["cmd"])])
            st.caption("Información de referencia: los resultados no sustituyen las autorizaciones de MASS, Servicio Médico ni las exigencias operativas de conducción.")

st.divider()
st.caption("LT2E · Área MASS · Plataforma de consulta individual · Acceso a datos reales únicamente con autorización corporativa")
