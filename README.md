# Control de Aptitudes y Habilitaciones | LT2E

Aplicación Streamlit desarrollada para el Proyecto Los Toldos II Este, MASS. Diseño basado en el manual de marca Techint. **Consulta de datos médicos sensibles: acceso exclusivamente autorizado.**

## Qué muestra

- **Identificación:** apellido y nombre, DNI, puesto, especialidad/fase y empresa (si está informada).
- **Altura:** aptitud médica, vigencia, capacitación teórica y práctica con sus fechas.
- **Espacios confinados:** aptitud médica, vigencia, capacitación teórica y práctica con sus fechas.
- **Conducción:** aptitud médica, vigencia y fecha del CMD interno.
- **Trazabilidad:** fecha del examen seleccionado y avisos de fuentes inexistentes o incompletas.

Los resultados médicos conservan categorías como APTO, NO APTO, NO APLICA, examen faltante, evaluación en curso y APTO VENCIDO. No se declara a nadie habilitado operativamente; falta la validación formal de MASS/Servicio Médico, y para conducir pueden existir requisitos adicionales.

## Archivos utilizados (NO se incluyen en este paquete)

Crear o usar una carpeta interna `data/` **fuera de un repositorio público** y colocar/copiar estas tres bases, con estos nombres:

1. `base_capacitaciones.xlsx`: hoja **TECHINT**, encabezados fila 6, DNI y capacitaciones de altura, espacios confinados y **CMD INTERNO**.
2. `SeguimientoSolicitudesData.xlsx`: hoja **Sheet**, exportación de EMHA; se filtra estrictamente por proyecto **ARG - Los Toldos 2 Este**.
3. `HC.xlsx`: hoja **HeadCount_LosToldos**, campos de identificación laboral del personal propio.

### Subcontratistas

Los archivos entregados no identifican inequívocamente la **empresa de cada subcontratista**. Para completar este campo se admite opcionalmente `padron_subcontratos.csv` (codificación UTF-8, separador coma), en la misma carpeta `data/`, con encabezado:

```csv
dni,apellido_y_nombre,puesto,especialidad,empresa
```

**No cargues nombres reales en el repositorio**: el archivo contiene datos personales. Si no hay padrón y el DNI no está en HC, la interfaz mostrará «No identificado» / «No informada», sin inventar el vínculo laboral. No se presupone que todos los exámenes del EMHA pertenezcan a subcontratistas activos.

## Duplicaciones de aptos y reglas

- Conciliación por DNI normalizado (evita diferencias por puntos/espacios).
- Registros del EMHA: se descartan los cancelados, se toma el examen/solicitud **más reciente** a partir de fechas del examen y del apto. Una nueva solicitud pendiente puede desplazar un apto antiguo: se muestra **EN EVALUACIÓN**, no se reutiliza automáticamente el APTO anterior.
- Si el resultado dice APTO pero la vigencia ya pasó, se indica **APTO VENCIDO**. Si la fecha de vigencia es desconocida, **APTO / sin vigencia verificable**.
- La capacitación solo figura «Registrada» cuando hay una fecha válida; `PENDIENTE`, `S/N` o `N/A` no se consideran realizadas.
- El valor **Vigencia Apto** de EMHA se muestra en cada disciplina (cuando procede), porque el archivo aporta **una sola vigencia general**, no tres vencimientos específicos.
- La aptitud médica NO significa por sí sola autorización de trabajo o conducción. Validar periodicidades y otras condiciones con Servicio Médico.

## Acceso y despliegue

**No publicar este buscador de datos médicos de manera anónima.** La app requiere OIDC (p. ej. Microsoft Entra ID) y una lista expresa de usuarios autorizados. Pide a IT crear la app/registro OIDC y configurar estos parámetros en los secretos del servidor, nunca en GitHub:

```toml
[auth]
redirect_uri = "https://TU-APP.streamlit.app/oauth2callback"
cookie_secret = "VALOR_LARGO_ALEATORIO_GENERADO_POR_IT"
client_id = "VALOR_PROVISTO_POR_IT"
client_secret = "VALOR_PROVISTO_POR_IT"
server_metadata_url = "URL_OIDC_PROVISTA_POR_IT"

APP_ALLOWED_EMAILS = ["correo-autorizado@empresa.com"]
# Opcional: carpeta sincronizada en un servidor corporativo aprobado
APP_DATA_DIR = "/ruta/segura/carpeta/datos"
```

La lista APP_ALLOWED_EMAILS restringe la consulta incluso entre las identidades autenticadas. **No** reemplazarla por un dominio entero sin evaluación de acceso y permisos. Streamlit `st.login` identifica al usuario; la aplicación comprueba la autorización de manera adicional. El alojamiento, almacenamiento, retención, seguridad y la disponibilidad de OIDC deben ser aprobados por IT y las áreas responsables del tratamiento de datos médicos.

Dependencias: `pip install -r requirements.txt`, ejecutar `streamlit run app.py`.

### Prueba sin datos reales

Para probar exclusivamente la presentación con una persona ficticia:

```bash
APP_DEMO_MODE=1 streamlit run app.py
```

Consultar el DNI **99999999** (ficticio). El modo demo no lee archivos ni muestra información médica real. **No usar este modo en la publicación real**.

### Actualizaciones

Al reemplazar las tres bases en la **carpeta segura** por nuevas exportaciones manteniendo los nombres, la app identifica la modificación de archivos y recarga la información (caché de hasta 5 minutos). Esto supone que la carpeta se mantiene actualizada; **Streamlit no consulta SharePoint automáticamente**. Para automatizar esa transferencia, IT deberá configurar sincronización interna o conexión autorizada mediante API y comprobar permisos. Nunca subir estas bases a GitHub ni incluirlas en un ZIP para distribución pública.

Una vez desplegada con accesos correctamente configurados, es posible generar un QR con **la URL final de esta segunda página**. El QR dirigirá al acceso corporativo, no eliminará la autenticación.
