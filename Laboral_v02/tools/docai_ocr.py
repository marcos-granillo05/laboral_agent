from google.api_core.client_options import ClientOptions
from google.cloud import documentai


def ocr_document_bytes(
    file_bytes: bytes,
    project_id: str,
    processor_id: str,
    location: str = "us",
    mime_type: str = "application/pdf",
) -> str:
    """
    OCR con Document AI usando BYTES (archivo subido), devuelve el texto completo.
    """
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    )

    name = client.processor_path(project_id, location, processor_id)

    request = documentai.ProcessRequest(
        name=name,
        raw_document=documentai.RawDocument(content=file_bytes, mime_type=mime_type),
    )

    result = client.process_document(request=request)
    return result.document.text or ""