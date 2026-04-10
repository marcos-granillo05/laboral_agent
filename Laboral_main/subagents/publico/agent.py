import os
from typing import Dict, Any

from datetime import date, datetime
from google.adk.tools import ToolContext
from google.adk.agents import Agent,SequentialAgent, ParallelAgent

from ...tools.rag_complete import rag_laboral_publico_privado, rag_laboral_publico_carrera, rag_laboral_publico, rag_guia_de_servicio
from . import instructions
from ...tools.analytical_summary_document import document_maker, document_maker_V02
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from pydantic import BaseModel, Field 
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

## Output Schemas 
###################
class formatter(BaseModel):
    personal_data_content: str = Field(...,description="Toda la información relacionada al trabajador")
    content : str = Field(...,description="toda la información relacionada al relato de hecho, e información extraida del contenido de documentos complementario")

class formatter_v02(BaseModel):
    personal_data_content: str = Field(...,description="Toda la información relacionada al trabajador")
    content : str = Field(...,description="toda la información relacionada al relato de hecho")
    documents_related: str = Field(...,description="información extraida del contenido de documentos complementario")

class formatter_v03(BaseModel):
    personal_data_content: str = Field(...,description="Toda la información relacionada al trabajador")
    content : str = Field(...,description="toda la información relacionada al relato de hecho")
    claims_statement_facts: str = Field(...,description="Análisis de pretensiones sobre relato de hecho")

########################
class personalData(BaseModel):
    name: str = Field(description="Nombre del trabajador.")
    age: str = Field(description="Edad del trabajador.")
    dui: str = Field(description="DUI del trabajador.")
    phone: str = Field(description="Teléfono del trabajador.")
    email: Optional[str] = Field(default=None, description="Email del trabajador.")
    genrer :str = Field(...,description="Genero del trabajador")

# ------------------------------------    
class laboralpublicoOutput(BaseModel):
    personal_data_summary: str = Field(description="Resumen de información personal del trabajador.")
    personal_data: personalData = Field(description="Información personal del trabajador detallada.")
    summary: str = Field(description="Resumen detallado relato de hecho.")
    justification: str = Field(description="Justificación de qué artículos de cada ley están siendo violados al trabajador.")
    suggestions: str = Field(description="Sugerencias o consejos para el trabajador.")


class laboralPublicoOutput_v03(BaseModel):
    personal_data_summary: str = Field(description="Resumen de información personal del trabajador.")
    personal_data: personalData = Field(description="Información personal del trabajador.")
    summary: str = Field(description="Resumen detallado del relato de hecho.")
    justification: str = Field(description="Justificación de qué artículos de cada ley están siendo violados al trabajador.")
    claims_statement_facts: str = Field(...,description="Identificación de pretensiones sobre relato de hecho")

# ------------------------------------
class evalServiceOutputSchema(BaseModel):
    legal_diagnosis : str = Field(...,description="Trámite específico que el trabajador debería optar")
    presuntion_status: str = Field(...,description="Explicación de si el trabajador aún goza de presunción legal")
    actions : str = Field(...,description="Pasos siguientes que debe realizar el usuario")
    formats : str = Field(...,description="Indica los formatos sugeridos, qué FOLA podría solicitar")


class joinerOutputSchema(BaseModel):
    personal_data_summary: str = Field(description="Resumen de información personal del trabajador.")
    personal_data: personalData = Field(description="Información personal del trabajador.")
    summary: str = Field(description="Resumen del relato de hecho.")
    justification: str = Field(description="Justificación de qué artículos de cada ley están siendo violados al trabajador.")
    suggestions: str = Field(description="Sugerencias o consejos para el trabajador.")
    legal_diagnosis : str = Field(...,description="Trámite específico que el trabajador debería optar")
    presuntion_status: str = Field(...,description="Explicación de si el trabajador aún goza de presunción legal")
    actions : str = Field(...,description="Pasos siguientes que debe realizar el usuario")
    formats : str = Field(...,description="Indica los formatos sugeridos, qué FOLA podría solicitar")


class reporterOutputSchema(BaseModel):
    personal_data_summary: str = Field(description="Resumen de información personal del trabajador.")
    personal_data: personalData = Field(description="Información personal del trabajador.")
    summary: str = Field(description="Resumen del relato de hecho.")
    justification: str = Field(description="Justificación de qué artículos de cada ley están siendo violados al trabajador.")
    suggestions: str = Field(description="Sugerencias o consejos para el trabajador.")
    legal_diagnosis : str = Field(...,description="Trámite específico que el trabajador debería optar")
    presuntion_status: str = Field(...,description="Explicación de si el trabajador aún goza de presunción legal")
    actions : str = Field(...,description="Pasos siguientes que debe realizar el usuario")
    formats : str = Field(...,description="Indica los formatos sugeridos, qué FOLA podría solicitar")
    response_resume_doc: str = Field(...,description="Respuesta de la tool ejecutada.")

class reporterOutputSchema_v02(BaseModel):
    personal_data_summary: str = Field(description="Resumen de información personal del trabajador.")
    personal_data: personalData = Field(description="Información personal del trabajador.")
    summary: str = Field(description="Resumen del relato de hecho.")
    justification: str = Field(description="Justificación de qué artículos de cada ley están siendo violados al trabajador.")
    suggestions: str = Field(description="Sugerencias o consejos para el trabajador.")
    claims_statement_facts: str = Field(...,description="Identificación de pretensiones sobre relato de hecho")
    response_resume_doc: str = Field(...,description="Respuesta de la tool ejecutada")

#### 

# Herramienta que me extraiga la data cruda del OCR. 
def get_documents_ocr(tool_context: ToolContext)->Dict[str, Any]:
    documents = tool_context.state.get("documents", [])
    blocks = []

    for doc in documents:
        original_name = doc.get("original_name", "documento")
        ocr_text = (doc.get("ocr_text") or "").strip()
        if ocr_text:
            blocks.append(f"[Documento: {original_name}]\n{ocr_text}")

    combined_text = "\n\n".join(blocks).strip()

    return {
        "status": "ok",
        "documents_count": len(documents),
        "documents_ocr": combined_text,
    } 

# Herramienta de consulta de fecha. 
# def get_current_date():
#   """
#   Gets the current local date.

#   Returns:
#       datetime.date: An object representing the current date in the format 'YYYY-MM-DD'.
#   """
#   response = {
#     "today_is": datetime.date.today().strftime("%Y-%m-%d")

#   }

#   return response

#### 
def after_model_callback_formatter(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    
    print(f'Request de Formatter: {llm_response.content.parts[0].text}')


def after_model_callback_eval_service(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    
    print(f'Response de laboral_publico_eval_service: {llm_response.content.parts[0].text}')


def after_model_callback_legal_advisor(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    
    print(f'Response de legal_advisor: {llm_response.content.parts[0].text}')

def after_model_callback_response_joiner(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    
    print(f'Response de response_joiner: {llm_response.content.parts[0].text}')

def after_model_callback_publico_reporter(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    result = llm_response.content
    print(f'Resultado respuesta de after model callback de publico reporter {result}')
    #print(f'Response de publico_reporter: {llm_response.content.parts[0].text}')


def before_model_callback_formatter(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmRequest]:
    print(f'Request de Formatter: {llm_request.contents}')


laboral_publico_formatter = Agent(
    name="laboral_publico_formatter",
    model="gemini-2.5-flash",
    description="Agente formateador de contenido",
    instruction=instructions.formatter_instructions_v03,
    output_key="laboral_publico_formatter_output",
    output_schema=formatter_v03,
   # tools=[get_documents_ocr]
   before_model_callback=before_model_callback_formatter,
    after_model_callback=after_model_callback_formatter
)

laboral_publico_eval_service = Agent(
    name="laboral_publico_eval_service",
    model="gemini-2.5-pro",
    description="Agente encargado de evaluar los pasos siguientes a realizar",
    instruction=instructions.eval_service_instruction,
    #tools=[rag_guia_de_servicio, get_current_date],
    tools=[rag_guia_de_servicio],
    output_key="laboral_publico_eval_service_output",
    output_schema=evalServiceOutputSchema,
    after_model_callback=after_model_callback_eval_service
)

laboral_publico_legal_advisor = Agent(
    name="laboral_publico_legal_advisor",
    model="gemini-2.5-pro",
    description="Agente formateador de contenido",
    instruction=instructions.legal_advisor_instructions_v02,
    tools=[rag_laboral_publico,rag_laboral_publico_privado, rag_laboral_publico_carrera],
    output_key="laboral_publico_legal_advisor_output",
    output_schema=laboralPublicoOutput_v03,
    after_model_callback=after_model_callback_legal_advisor

)

laboral_publico_response_joiner = Agent(
    name="laboral_publico_response_joiner",
    model="gemini-2.5-pro",
    description="Agente encargado de consolidar respuestas.",
    instruction=instructions.response_joiner_instructions,
    output_key="laboral_publico_response_joiner_output",
    output_schema=joinerOutputSchema,
    after_model_callback=after_model_callback_response_joiner
)

laboral_publico_reporter = Agent(
    name="laboral_publico_reporter",
    model="gemini-2.5-flash",
    description="Agente formateador de contenido",
    instruction=instructions.reporter_instructions_v02,
    tools=[document_maker],
    output_key="laboral_publico_reporter_output",
    output_schema=reporterOutputSchema_v02,
    after_model_callback=after_model_callback_publico_reporter
)


# laboral_publico_parallel = ParallelAgent(
#     name="laboral_publico_parallel",
#     description="Agente encargado de ejecutar análisis en paralelo",
#     sub_agents=[laboral_publico_legal_advisor, laboral_publico_eval_service]
# )

# laboral_publico_sequential = SequentialAgent(
#     name="laboral_publico_sequential",
#     description="Agente encargado de gestionar la secuencia de funcionamiento de agete en el flujo de sector público",
#     sub_agents=[laboral_publico_formatter,laboral_publico_parallel, laboral_publico_response_joiner,laboral_publico_reporter]
# )

## Version recortada.
laboral_publico_sequential_v02 = SequentialAgent(
    name="laboral_publico_sequential",
    description="Agente encargado de gestionar la secuencia de funcionamiento de agete en el flujo de sector público",
    sub_agents=[laboral_publico_formatter, laboral_publico_legal_advisor,laboral_publico_reporter]
)