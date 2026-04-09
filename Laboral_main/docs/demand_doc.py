import json
import os
import uuid
import traceback
from io import BytesIO
from datetime import datetime, timezone

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from google.cloud import storage
from google.oauth2 import service_account
from google.genai import types
from google.adk.agents.callback_context import CallbackContext


def build_storage_client():
    key_path = os.environ.get("ADK_CREDENTIALS_PATH")

    if key_path and os.path.exists(key_path):
        creds = service_account.Credentials.from_service_account_file(key_path)
        client = storage.Client(credentials=creds, project=creds.project_id)
        return client, creds

    client = storage.Client()
    return client, None


def upload_to_gcs(bucket_name: str, object_name: str, data: bytes) -> dict:
    client, _ = build_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    blob.upload_from_string(
        data,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    print(f"DEBUG: upload ok bucket={bucket_name} object={object_name}")

    return {
        "bucket_name": bucket_name,
        "object_name": object_name,
    }


def _apply_font(run, font_name="Arial", size_pt=12, color_rgb=(0, 0, 0), bold=False, italic=False):
    run.font.name = font_name

    rPr = run._element.get_or_add_rPr()

    rFonts = rPr.rFonts
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)

    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:cs"), font_name)

    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(*color_rgb)
    run.font.size = Pt(size_pt)


def _set_default_font(doc: Document, font_name="Arial", size_pt=12):
    style = doc.styles["Normal"]
    style.font.name = font_name
    style.font.size = Pt(size_pt)

    rPr = style.element.get_or_add_rPr()
    rfonts = rPr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rPr.append(rfonts)

    rfonts.set(qn("w:ascii"), font_name)
    rfonts.set(qn("w:hAnsi"), font_name)
    rfonts.set(qn("w:cs"), font_name)


def _configure_paragraph(
    paragraph,
    align=WD_ALIGN_PARAGRAPH.JUSTIFY,
    first_line_indent_cm=1.25,
    space_before_pt=0,
    space_after_pt=0,
    line_spacing=1.0,
):
    paragraph.alignment = align
    paragraph.paragraph_format.first_line_indent = Cm(first_line_indent_cm)
    paragraph.paragraph_format.space_before = Pt(space_before_pt)
    paragraph.paragraph_format.space_after = Pt(space_after_pt)
    paragraph.paragraph_format.line_spacing = line_spacing


def _add_run(paragraph, text, *, bold=False, color_rgb=(0, 0, 0), uppercase=False, font_name="Arial", size_pt=12):
    value = "" if text is None else str(text)
    if uppercase:
        value = value.upper()

    run = paragraph.add_run(value)
    _apply_font(run, font_name=font_name, size_pt=size_pt, color_rgb=color_rgb, bold=bold)
    return run


def _add_blank_line(doc: Document):
    p = doc.add_paragraph()
    _configure_paragraph(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent_cm=0)
    return p


def _heading(doc: Document, text: str, font_name="Arial"):
    p = doc.add_paragraph()
    _configure_paragraph(
        p,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        first_line_indent_cm=0,
        space_before_pt=0,
        space_after_pt=0,
        line_spacing=1.0,
    )
    _add_run(p, text, bold=True, uppercase=True, font_name=font_name, size_pt=12)
    return p


def _body(doc: Document, font_name="Arial"):
    p = doc.add_paragraph()
    _configure_paragraph(
        p,
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        first_line_indent_cm=1.25,
        space_before_pt=0,
        space_after_pt=0,
        line_spacing=1.0,
    )
    return p


def _safe_text(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def _list_or_empty(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


async def demanda_despido_directo_document_maker(analysis_json: str, tool_context: CallbackContext) -> dict:
    try:
        analysis = json.loads(analysis_json) if isinstance(analysis_json, str) else analysis

        doc = Document()

        section = doc.sections[0]
        section.page_width = Cm(21.59)
        section.page_height = Cm(27.94)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(3.0)

        font_name = "Arial"
        _set_default_font(doc, font_name=font_name, size_pt=12)

        # =========================
        # DATOS
        # =========================
        abogado_nombre = _safe_text(analysis.get("abogado_nombre", "DIEGO FRANCISCO BRIZUELA HUEZO"))
        abogado_domicilio = _safe_text(analysis.get("abogado_domicilio"))
        abogado_dui = _safe_text(analysis.get("abogado_dui"))
        abogado_tarjeta = _safe_text(analysis.get("abogado_tarjeta_abogado"))
        abogado_edad = _safe_text(analysis.get("abogado_edad"))

        trabajador_nombre = _safe_text(analysis.get("trabajador_nombre"))
        trabajador_edad = _safe_text(analysis.get("trabajador_edad"))
        trabajador_estado_familiar = _safe_text(analysis.get("trabajador_estado_familiar"))
        trabajador_profesion = _safe_text(analysis.get("trabajador_profesion_u_oficio"))
        trabajador_nacionalidad = _safe_text(analysis.get("trabajador_nacionalidad"))
        trabajador_domicilio = _safe_text(analysis.get("trabajador_domicilio"))
        trabajador_dui = _safe_text(analysis.get("trabajador_dui"))

        empresa_demandada = _safe_text(analysis.get("empresa_demandada"))
        empresa_domicilio = _safe_text(analysis.get("empresa_domicilio"))
        representante_legal_nombre = _safe_text(analysis.get("representante_legal_nombre"))
        representante_legal_domicilio = _safe_text(analysis.get("representante_legal_domicilio"))
        direccion_notificacion_empresa = _safe_text(analysis.get("direccion_notificacion_empresa"))

        fecha_ingreso_texto = _safe_text(analysis.get("fecha_ingreso_texto"))
        cargo_nominal = _safe_text(analysis.get("cargo_nominal"))
        lugar_trabajo = _safe_text(analysis.get("lugar_trabajo"))
        funciones_reales = _safe_text(analysis.get("funciones_reales"))
        jornada_descripcion = _safe_text(analysis.get("jornada_descripcion"))
        horario_trabajo = _safe_text(analysis.get("horario_trabajo"))
        salario_texto = _safe_text(analysis.get("salario_texto"))
        forma_pago = _safe_text(analysis.get("forma_pago"))

        fecha_despido_texto = _safe_text(analysis.get("fecha_despido_texto"))
        hora_despido_texto = _safe_text(analysis.get("hora_despido_texto"))
        nombre_quien_despide = _safe_text(analysis.get("nombre_quien_despide"))
        cargo_quien_despide = _safe_text(analysis.get("cargo_quien_despide"))
        lugar_despido = _safe_text(analysis.get("lugar_despido"))
        relato_hechos_adicional = _safe_text(analysis.get("relato_hechos_adicional"))

        pretensiones = _list_or_empty(analysis.get("pretensiones_o_prestaciones", []))

        # =========================
        # DOCUMENTO
        # =========================
        p = doc.add_paragraph()
        _configure_paragraph(
            p,
            align=WD_ALIGN_PARAGRAPH.LEFT,
            first_line_indent_cm=0,
            space_before_pt=0,
            space_after_pt=0,
            line_spacing=1.0,
        )
        _add_run(p, "SEÑOR JUEZ DE LO LABORAL", bold=True, uppercase=True, font_name=font_name, size_pt=12)

        _add_blank_line(doc)

        p = _body(doc, font_name=font_name)
        _add_run(p, abogado_nombre, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, ", de ", font_name=font_name)
        _add_run(p, abogado_edad, uppercase=True, font_name=font_name)
        _add_run(p, " años de edad, Abogado y del domicilio de ", font_name=font_name)
        _add_run(p, abogado_domicilio, uppercase=True, font_name=font_name)
        _add_run(p, " con Documento Único de Identidad número ", font_name=font_name)
        _add_run(p, abogado_dui, uppercase=True, font_name=font_name)
        _add_run(p, ", Tarjeta de Identificación de la Abogacía ", font_name=font_name)
        _add_run(p, abogado_tarjeta, uppercase=True, font_name=font_name)
        _add_run(p, ", a usted atentamente ", font_name=font_name)
        _add_run(p, "EXPONGO", bold=True, uppercase=True, font_name=font_name)
        _add_run(p, ":", font_name=font_name)

        _add_blank_line(doc)

        _heading(doc, "PARTE EXPOSITIVA", font_name=font_name)

        p = _body(doc, font_name=font_name)
        _add_run(p, "En mi calidad de Defensor Publico Laboral, vengo a promover Proceso Abreviado Laboral, en nombre y representación del trabajador ", font_name=font_name)
        _add_run(p, trabajador_nombre, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, ", de ", font_name=font_name)
        _add_run(p, trabajador_edad, uppercase=True, font_name=font_name)
        _add_run(p, " años de edad, ", font_name=font_name)
        _add_run(p, trabajador_estado_familiar, uppercase=True, font_name=font_name)
        _add_run(p, ", ", font_name=font_name)
        _add_run(p, trabajador_profesion, uppercase=True, font_name=font_name)
        _add_run(p, ", de nacionalidad ", font_name=font_name)
        _add_run(p, trabajador_nacionalidad, uppercase=True, font_name=font_name)
        _add_run(p, " y del domicilio de ", font_name=font_name)
        _add_run(p, trabajador_domicilio, uppercase=True, font_name=font_name)
        _add_run(p, ", con Documento Único de Identidad número ", font_name=font_name)
        _add_run(p, trabajador_dui, uppercase=True, font_name=font_name)
        _add_run(p, " contra ", font_name=font_name)
        _add_run(p, empresa_demandada, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, ", y del domicilio de ", font_name=font_name)
        _add_run(p, empresa_domicilio, uppercase=True, font_name=font_name)
        _add_run(p, ", representada legalmente por ", font_name=font_name)
        _add_run(p, representante_legal_nombre, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, ", mayor de edad y del domicilio de ", font_name=font_name)
        _add_run(p, representante_legal_domicilio, uppercase=True, color_rgb=(255, 0, 0), font_name=font_name)
        _add_run(p, ", pudiendo ser citada, notificada y emplazada dicha persona jurídica por medio de su representante legal en ", font_name=font_name)
        _add_run(p, direccion_notificacion_empresa, uppercase=True, color_rgb=(255, 0, 0), font_name=font_name)
        _add_run(p, ", para mejor ubicación agrego croquis, lugar donde habitualmente atiende sus negocios, para reclamarle prestaciones laborales.", font_name=font_name)

        _heading(doc, "RELACION DE TRABAJO", font_name=font_name)

        p = _body(doc, font_name=font_name)
        _add_run(p, "Mi representado ingresó a laborar para y a las órdenes de ", font_name=font_name)
        _add_run(p, empresa_demandada, uppercase=True, font_name=font_name)
        _add_run(p, ", el ", font_name=font_name)
        _add_run(p, fecha_ingreso_texto, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, ", con el cargo de ", font_name=font_name)
        _add_run(p, cargo_nominal, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, "; desarrollando sus labores en ", font_name=font_name)
        _add_run(p, lugar_trabajo, uppercase=True, font_name=font_name)
        _add_run(p, " y las cuales consistían en ", font_name=font_name)
        _add_run(p, funciones_reales, uppercase=True, font_name=font_name)
        _add_run(p, "; estando sujeto a una jornada ordinaria de trabajo de ", font_name=font_name)
        _add_run(p, jornada_descripcion, uppercase=True, font_name=font_name)
        _add_run(p, ", y un horario de trabajo ", font_name=font_name)
        _add_run(p, horario_trabajo, uppercase=True, font_name=font_name)
        _add_run(p, "; devengando por sus servicios un salario de ", font_name=font_name)
        _add_run(p, salario_texto, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, ", los cuales eran cancelados ", font_name=font_name)
        _add_run(p, forma_pago, uppercase=True, font_name=font_name)
        _add_run(p, ".", font_name=font_name)

        _heading(doc, "RELACION DE HECHOS", font_name=font_name)

        p = _body(doc, font_name=font_name)
        _add_run(p, "En las condiciones de trabajo antes mencionadas laboró mi patrocinado para y a las órdenes de ", font_name=font_name)
        _add_run(p, empresa_demandada, uppercase=True, font_name=font_name)
        _add_run(p, ", desde la fecha de su ingreso hasta el ", font_name=font_name)
        _add_run(p, fecha_despido_texto, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, ", fecha en la cual como a eso de las ", font_name=font_name)
        _add_run(p, hora_despido_texto, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, " ", font_name=font_name)
        _add_run(p, nombre_quien_despide, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, ", ", font_name=font_name)
        _add_run(p, cargo_quien_despide, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, ", quien tiene facultades para contratar, despedir, dirigir y administrar trabajadores, le manifestó que a partir de ese momento estaba despedido de su trabajo, hecho que ocurrió en ", font_name=font_name)
        _add_run(p, lugar_despido, uppercase=True, font_name=font_name)
        _add_run(p, ".", font_name=font_name)

        if relato_hechos_adicional:
            _add_run(p, " ", font_name=font_name)
            _add_run(p, relato_hechos_adicional, font_name=font_name)

        _add_blank_line(doc)

        _heading(doc, "PARTE PETITORIA", font_name=font_name)

        p = _body(doc, font_name=font_name)
        _add_run(p, "Por lo antes expuesto, a usted respetuosamente PIDO:", font_name=font_name)

        _add_blank_line(doc)

        p = _body(doc, font_name=font_name)
        _add_run(p, "Me admita la presente demanda, me tenga por parte en la calidad en que comparezco, cite a conciliación a ", font_name=font_name)
        _add_run(p, empresa_demandada, bold=True, uppercase=True, font_name=font_name)
        _add_run(p, " por medio de su representante legal antes mencionado, y si no llegásemos a ningún acuerdo en dicha audiencia, previo los trámites legales y las pruebas que oportunamente aportaré, sea condenada en la sentencia definitiva a pagarle a mi representado:", font_name=font_name)

        for item in pretensiones:
            bp = doc.add_paragraph(style="List Bullet")
            bp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            bp.paragraph_format.space_before = Pt(0)
            bp.paragraph_format.space_after = Pt(0)
            bp.paragraph_format.line_spacing = 1.0

            if isinstance(item, str):
                r = bp.add_run(item)
                _apply_font(r, font_name=font_name, size_pt=12)
            elif isinstance(item, dict):
                texto = _safe_text(item.get("texto"))
                prestacion = _safe_text(item.get("prestacion"))
                fundamento = _safe_text(item.get("fundamento_legal"))

                contenido = texto
                if not contenido:
                    contenido = prestacion
                    if fundamento:
                        contenido = f"{prestacion}. ({fundamento})"

                r = bp.add_run(contenido)
                _apply_font(r, font_name=font_name, size_pt=12)

        _add_blank_line(doc)

        # Estáticos por ahora
        p = _body(doc, font_name=font_name)
        _add_run(
            p,
            "Legitimo mi personería con copia certificada por notario de la Credencial Única y sus respectivas copias de ley.",
            font_name=font_name,
        )

        _add_blank_line(doc)

        p = _body(doc, font_name=font_name)
        _add_run(p, "Señalo para oír notificaciones, ", font_name=font_name)
        _add_run(p, "uddt.sansalvador@pgr.gob.sv", font_name=font_name)

        _add_blank_line(doc)

        p = _body(doc, font_name=font_name)
        _add_run(
            p,
            "Distrito de San Salvador, Municipio de San Salvador Centro, Departamento de San Salvador, veintiuno de enero de dos mil veintiséis.",
            font_name=font_name,
        )

        # Footer
        footer_para = doc.sections[0].footer.paragraphs[0]
        footer_text = f'Generado el {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'
        footer_para.text = footer_text
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if footer_para.runs:
            _apply_font(footer_para.runs[0], font_name=font_name, size_pt=8, color_rgb=(128, 128, 128))

        # Guardar en memoria
        buffer = BytesIO()
        doc.save(buffer)
        docx_bytes = buffer.getvalue()
        buffer.seek(0)

        bucket_name = os.environ["GCS_BUCKET_LABORAL"]

        case_id = uuid.uuid4().hex
        safe_dui = "".join(ch for ch in str(trabajador_dui) if ch.isalnum()) or "sin_dui"

        object_name = f"case_{safe_dui}/demandas/{case_id}_{safe_dui}_demanda_despido_directo.docx"
        output_filename = f"{case_id}_{safe_dui}_demanda_despido_directo.docx"

        save_gcp = upload_to_gcs(
            bucket_name=bucket_name,
            object_name=object_name,
            data=docx_bytes,
        )

        artifact_part = types.Part(
            inline_data=types.Blob(
                data=docx_bytes,
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        )

        version = await tool_context.save_artifact(
            filename=output_filename,
            artifact=artifact_part
        )

        return {
            "status": "ok",
            "message": f"El documento {output_filename} version {version} ha sido creado y disponible para descargar.",
            "gcs": save_gcp,
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
        }
    

## Ejemplo: 
{
    "abogado_nombre": "DIEGO FRANCISCO BRIZUELA HUEZO",
    "abogado_domicilio": "Distrito de San Salvador, Municipio de San Salvador Centro, Departamento de San Salvador",
    "abogado_dui": "CERO CUATRO SEIS SEIS TRES SIETE UNO OCHO GUION OCHO",
    "abogado_tarjeta_abogado": "CERO SEIS UNO SIETE CUATRO CUATRO CUATRO DOS DOS CERO CERO SIETE CINCO DOS SEIS",

    "trabajador_nombre": "JONATHAN EDENILSON MAURICIO ORELLANA",
    "trabajador_edad": "DIECIOCHO",
    "trabajador_estado_familiar": "SOLTERO",
    "trabajador_profesion_u_oficio": "EMPLEADO",
    "trabajador_nacionalidad": "SALVADOREÑA",
    "trabajador_domicilio": "DISTRITO DE SAN MARCOS, MUNICIPIO DE SAN SALVADOR SUR, DEPARTAMENTO DE SAN SALVADOR",
    "trabajador_dui": "CERO SIETE SIETE CERO UNO CUATRO NUEVE CUATRO GUION NUEVE",

    "empresa_demandada": "GRUPO FRANCO SOCIEDAD POR ACCIONES SIMPLIFICADA DE CAPITAL VARIABLE",
    "empresa_domicilio": "DISTRITO DE SAN SALVADOR, MUNICIPIO DE SAN SALVADOR CENTRO, DEPARTAMENTO DE SAN SALVADOR",
    "representante_legal_nombre": "DIANA AYMEE FRANCO RECINOS",
    "representante_legal_domicilio": "DISTRITO DE EL PAISNAL, MUNICIPIO DE SAN SALVADOR NORTE, DEPARTAMENTO DE SAN SALVADOR",
    "direccion_notificacion_empresa": "CARRETERA TRONCAL DEL NORTE, DECIMA CALLE ORIENTE Y AVENIDA CENTRAL NORTE, EDIFICIO TEXTILES GILTON AGUILARES, DISTRITO DE AGUILARES, MUNICIPIO DE SAN SALVADOR NORTE, DEPARTAMENTO DE SAN SALVADOR",

    "fecha_ingreso_texto": "DIA CATORCE DE JULIO DE DOS MIL VEINTICINCO",
    "cargo_nominal": "AUXILIAR DE CARGA",
    "lugar_trabajo": "KILOMETRO DOCE, AUTOPISTA A COMALAPA, PUNTO DE DESCARGA SAN MARCOS, CONTIGUO A RESORTES MAHLER, DISTRITO DE SAN MARCOS, MUNICIPIO DE SAN SALVADOR SUR, DEPARTAMENTO DE SAN SALVADOR",
    "funciones_reales": "PREPARADOR DE CARGA DE RESIDUOS SOLIDOS DE RASTRAS",
    "jornada_descripcion": "OCHO HORAS DIARIAS",
    "horario_trabajo": "DE LUNES A VIERNES DE NUEVE DE LA MAÑANA A CINCO DE LA TARDE, SABADO DE DIEZ DE LA MAÑANA A CUATRO DE LA TARDE, DESCANSANDO DIA DOMINGO",
    "salario_texto": "CUATROCIENTOS DIEZ DOLARES EXACTOS DE LOS ESTADOS UNIDOS DE AMERICA MENSUALES",
    "forma_pago": "QUINCENALMENTE POR MEDIO DE DEPÓSITO EN CUENTA BANCARIA DEL BANCO AGRICOLA",

    "fecha_despido_texto": "DIA TRECE DE DICIEMBRE DE DOS MIL VEINTICINCO",
    "hora_despido_texto": "TRES CON DIEZ MINUTOS DE LA TARDE",
    "nombre_quien_despide": "DAVID FRANCO ABREGO",
    "cargo_quien_despide": "SUPERVISOR DE PLANTA",
    "lugar_despido": "EL LUGAR DE TRABAJO ANTES MENCIONADO ESPECÍFICAMENTE EN LA ZONA DE DESCARGA DE RASTRAS",
    "relato_hechos_adicional": "",

    "pretensiones_o_prestaciones": [
        {
            "prestacion": "Indemnización por despido injusto",
            "fundamento_legal": "Art. 38 Ord. 11° de la Cn. y Art. 58 del C. de T."
        },
        {
            "prestacion": "Vacación y Aguinaldo Proporcional",
            "fundamento_legal": "Art. 187, 202 del C. de T."
        }
    ]
}
