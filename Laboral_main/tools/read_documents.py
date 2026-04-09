import os
import re
import uuid
import hashlib
from typing import Dict, Any, Tuple, List

from google.adk.tools import ToolContext
from google.genai import types
from .docai_ocr import ocr_document_bytes

DOCAI_PROJECT_ID = os.getenv("DOCAI_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
DOCAI_LOCATION = os.getenv("DOCAI_LOCATION", "us")
DOCAI_PROCESSOR_ID = os.getenv("DOCAI_PROCESSOR_ID")

# Archivo aparte:
#-------------------------------------------------------------------------------------------
# from google.api_core.client_options import ClientOptions
# from google.cloud import documentai


# def ocr_document_bytes(
#     file_bytes: bytes,
#     project_id: str,
#     processor_id: str,
#     location: str = "us",
#     mime_type: str = "application/pdf",
# ) -> str:
#     """
#     OCR con Document AI usando BYTES (archivo subido), devuelve el texto completo.
#     """
#     client = documentai.DocumentProcessorServiceClient(
#         client_options=ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
#     )

#     name = client.processor_path(project_id, location, processor_id)

#     request = documentai.ProcessRequest(
#         name=name,
#         raw_document=documentai.RawDocument(content=file_bytes, mime_type=mime_type),
#     )

#     result = client.process_document(request=request)
#     return result.document.text or ""
#-------------------------------------------------------------------------------------------


def require_docai_config() -> None:
    missing = []
    if not DOCAI_PROJECT_ID:
        missing.append("DOCAI_PROJECT_ID")
    if not DOCAI_PROCESSOR_ID:
        missing.append("DOCAI_PROCESSOR_ID")
    if missing:
        raise RuntimeError("Faltan variables de entorno: " + ", ".join(missing))


def guess_extension(mime_type: str) -> str:
    return {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
    }.get(mime_type, ".bin")


def sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name or "").strip("._")
    return safe or "documento"


def normalize_mime_type(mime_type: str, filename: str = "") -> str:
    if mime_type != "application/octet-stream":
        return mime_type

    lower_name = (filename or "").lower()
    if lower_name.endswith(".pdf"):
        return "application/pdf"
    if lower_name.endswith(".jpg") or lower_name.endswith(".jpeg"):
        return "image/jpeg"
    if lower_name.endswith(".png"):
        return "image/png"
    if lower_name.endswith(".webp"):
        return "image/webp"
    if lower_name.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return mime_type


def build_artifact_names(
    original_name: str,
    mime_type: str,
    file_bytes: bytes,
) -> Tuple[str, str, str]:
    sha = hashlib.sha256(file_bytes).hexdigest()
    short_sha = sha[:8]
    unique_suffix = uuid.uuid4().hex[:8]

    safe_original = sanitize_filename(original_name)
    base, ext = os.path.splitext(safe_original)
    base = base or "documento"

    if not ext:
        ext = guess_extension(mime_type)

    artifact_name = f"{base}__{short_sha}__{unique_suffix}{ext}"
    ocr_artifact_name = f"{base}__{short_sha}__{unique_suffix}_ocr.txt"

    return artifact_name, ocr_artifact_name, sha


async def extract_uploads(tool_context: ToolContext) -> List[Tuple[bytes, str, str]]:
    user_content = getattr(tool_context, "user_content", None)
    parts = getattr(user_content, "parts", None) if user_content else None

    uploads: List[Tuple[bytes, str, str]] = []

    allowed_mime_types = {
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "application/octet-stream",
        # "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    # 1) Archivos del mensaje actual - Cuando utilizamos esto en LOCAL viene en inline_data
    if parts:
        for idx, part in enumerate(parts):
            inline = getattr(part, "inline_data", None)

            if inline and getattr(inline, "data", None):
                raw_mime = getattr(inline, "mime_type", None) or "application/octet-stream"
                filename = getattr(part, "filename", None) or f"doc_{idx}{guess_extension(raw_mime)}"
                mime_type = normalize_mime_type(raw_mime, filename)

                if mime_type in allowed_mime_types:
                    uploads.append((inline.data, mime_type, filename))

    # 2) Comportamiento en gemini enterprise -> allá cada documento cargado lo adjunta como artifact. 
    if not uploads:
        available_files = await tool_context.list_artifacts()

        for fname in available_files:
            # Evitar re-procesar OCR txt u otros artifacts no originales
            if fname.endswith("_ocr.txt"):
                continue

            try:
                file = await tool_context.load_artifact(filename=fname)
                inline_data = getattr(file, "inline_data", None)
                if not inline_data or not getattr(inline_data, "data", None):
                    continue

                raw_mime = getattr(inline_data, "mime_type", None) or "application/octet-stream"
                mime_type = normalize_mime_type(raw_mime, fname)

                if mime_type in allowed_mime_types:
                    uploads.append((inline_data.data, mime_type, fname))

            except Exception as e:
                print(f"Error cargando artifact {fname}: {e}")

    if not uploads:
        raise ValueError("Los archivos subidos no son compatibles o no se pudieron leer.")

    return uploads


async def process_document(tool_context: ToolContext) -> Dict[str, Any]:
    print(f'DEBUG --- Proces Document --- DEBUG')
    require_docai_config()

    try:
        uploads = await extract_uploads(tool_context)
    except ValueError as e:
        return {
            "status": "no_files",
            "processed_count": 0,
            "documents": [],
            "message": str(e),
        }

    processed_docs = []
    full_docs = []
    state_docs = tool_context.state.setdefault("documents", [])

    for idx, (file_bytes, mime_type, original_name) in enumerate(uploads):
        text = ocr_document_bytes(
            file_bytes=file_bytes,
            project_id=str(DOCAI_PROJECT_ID),
            processor_id=str(DOCAI_PROCESSOR_ID),
            location=DOCAI_LOCATION,
            mime_type=mime_type,
        )

        artifact_name, ocr_artifact_name, sha = build_artifact_names(
            original_name=original_name,
            mime_type=mime_type,
            file_bytes=file_bytes,
        )
        # El ish de esto es que en gemini enterprise se muestran y esto hace que se bugee 
        # await tool_context.save_artifact(
        #     artifact_name,
        #     types.Part(
        #         inline_data=types.Blob(
        #             mime_type=mime_type,
        #             data=file_bytes,
        #         )
        #     ),
        # )

        # await tool_context.save_artifact(
        #     ocr_artifact_name,
        #     types.Part(
        #         inline_data=types.Blob(
        #             mime_type="text/plain",
        #             data=text.encode("utf-8"),
        #         )
        #     ),
        # )

        doc_record = {
            "doc_index": idx,
            "original_name": original_name,
            #"artifact_name": artifact_name,
           # "ocr_artifact_name": ocr_artifact_name,
            "mime_type": mime_type,
            "sha256": sha,
            "ocr_text": text,
            "preview": text[:600],
        }

        # guardar completo en estado
        state_docs.append(doc_record)

        # guardar completo para combined_ocr_text de esta ejecución
        full_docs.append(doc_record)

        # guardar versión resumida para el return
        processed_docs.append({
            "doc_index": doc_record["doc_index"],
            "original_name": doc_record["original_name"],
            #"artifact_name": doc_record["artifact_name"],
           # "ocr_artifact_name": doc_record["ocr_artifact_name"],
            "mime_type": doc_record["mime_type"],
            "preview": doc_record["preview"][:200],
        })

    print(f'{"\n\n".join(doc["ocr_text"] for doc in full_docs)}')

    return {
        "status": "ok",
        "processed_count": len(processed_docs),
        "documents": processed_docs,
        "combined_ocr_text": "\n\n".join(doc["ocr_text"] for doc in full_docs),
        "message": f"Se procesaron correctamente {len(processed_docs)} documento(s).",
    }