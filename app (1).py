"""Diagnóstico mínimo para Streamlit Community Cloud (sin datos reales)."""
import streamlit as st

st.set_page_config(page_title="Diagnóstico LT2E", page_icon="✅", layout="centered")
st.title("✅ Prueba de conexión — LT2E")
st.success("Si ves este mensaje, la aplicación de Streamlit puede mostrar contenido.")
st.write("Esta página no consulta Excel, información médica ni datos personales.")
if st.button("Probar interacción"):
    st.info("¡La interacción también funciona!")
