import os
import json
import uuid
from typing import Dict, Any
from json import JSONDecoder
from html2docx import html2docx
from io import BytesIO
from datetime import datetime, timezone, timedelta
from google.oauth2 import service_account
from google.cloud import storage
from google.api_core import exceptions
from fpdf import FPDF
import google.genai.types as types
from google.adk.agents.callback_context import CallbackContext


def parse_analysis_json(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw

    if not isinstance(raw, str):
        raise ValueError(f"analysis_json debe ser str o dict, pero llegó: {type(raw)}")

    text = raw.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"DEBUG json.loads failed: {e}")

    try:
        decoder = JSONDecoder()
        obj, idx = decoder.raw_decode(text)
        rest = text[idx:].strip()
        if rest:
            print(f"WARNING: contenido extra después del JSON: {rest[:300]!r}")
        return obj
    except Exception as e:
        print(f"DEBUG raw_decode failed: {e}")
        print(f"DEBUG analysis_json start: {text[:500]!r}")
        print(f"DEBUG analysis_json end: {text[-500:]!r}")
        raise ValueError("No se pudo parsear analysis_json correctamente.")


def sanitize_unicode(text: str) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "--",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u2026": "...",
        "\u00a0": " ",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


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


async def generate_docx_from_html(
    analysis_json: str,
    tool_context: CallbackContext = None
):
    print('-----------------------------------------------------------')
    print('DEBUG: def generate_docx_from_html')
    print('-----------------------------------------------------------')
    print(f'TYPE analysis_json: {type(analysis_json)}')

    if isinstance(analysis_json, str):
        print(f'LEN analysis_json: {len(analysis_json)}')
        print(f'START analysis_json: {analysis_json[:300]!r}')
        print(f'END analysis_json: {analysis_json[-300:]!r}')
    else:
        print(f'RAW analysis_json: {analysis_json}')

    try:
        analysis = parse_analysis_json(analysis_json)
    except Exception as e:
        return {
            "status": "error",
            "message": f"No se pudo interpretar el JSON recibido: {str(e)}",
        }

    if not isinstance(analysis, dict):
        return {
            "status": "error",
            "message": "El contenido recibido no tiene estructura JSON válida.",
        }

    if "html_content" not in analysis:
        return {
            "status": "error",
            "message": "No se encontró 'html_content' en el JSON recibido.",
        }

    html_content = analysis.get("html_content", "")
    personal_data = analysis.get("personal_data", {}) or {}
    user_dui = personal_data.get("dui", "")

    print(f'HTML length: {len(html_content)} chars')
    print(f'Extracted DUI: {user_dui!r}')

    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing, cannot save artifact.",
        }

    try:
        html_sanitized = html_content
        docx_buffer = html2docx(html_sanitized, title="Fola 03")
        content_bytes = docx_buffer.getvalue()
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ocurrió un error al convertir el HTML a DOCX: {str(e)}",
        }

    safe_dui = "".join(ch for ch in str(user_dui) if ch.isalnum()) or "sin_dui"

    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    case_id = uuid.uuid4().hex
    object_name = f"case_{safe_dui}/fola_document/{case_id}_{safe_dui}_fola_document.docx"
    output_filename = f"{case_id}_{safe_dui}_fola_document.docx"
    bucket_name = os.environ["GCS_BUCKET_LABORAL"]

    try:
        save_gcp = upload_to_gcs(
            bucket_name=bucket_name,
            object_name=object_name,
            data=content_bytes,
        )
        print(f"DEBUG save_gcp: {save_gcp}")
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ocurrió un error al subir el documento a GCS: {str(e)}",
        }

    try:
        artifact_part = types.Part(
            inline_data=types.Blob(data=content_bytes, mime_type=mime_type)
        )

        version = await tool_context.save_artifact(
            filename=output_filename,
            artifact=artifact_part
        )

        print(f'TOOL_CONTEXT.SAVE_ARTIFACTS {version}')
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ocurrió un error al guardar el artifact: {str(e)}",
        }

    return {
        "status": "success",
        "message": f"Archivo '{output_filename}' (version {version}) ha sido creado y disponible para descargar.",
    }