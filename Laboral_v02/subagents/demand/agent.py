from google.adk.agents import Agent, SequentialAgent
from . import instruction
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools import AgentTool
from typing import Dict, Any, Optional
from ...tools.rag_complete import rag_resoluciones_judiciales
from .tools.generate_document import generate_docx_from_html
from ...tools.read_documents import process_document
from pydantic import BaseModel, Field 

def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    print(f'--------------------------------------------') 
    print(f'AFTER MODEL CALLBACK: {llm_response.content.parts[0].text}')
    print(f'--------------------------------------------') 

def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmRequest]:
    print(f'--------------------------------------------') 
    print(f'BEFORE MODEL CALLBACK PDF GENERATOR: {llm_request.contents}')
    print(f'--------------------------------------------')


# JSON de los formatters.
class personalData(BaseModel):
    name: str = Field(description="Nombre del trabajador.")
    age: str = Field(description="Edad del trabajador.")
    dui: str = Field(description="DUI del trabajador.")
    phone: str = Field(description="Teléfono del trabajador.")
    email: Optional[str] = Field(default=None, description="Email del trabajador.")
    genrer:str = Field(...,description="Genero del trabajador")

class formatterData(BaseModel):
    personal_data: personalData = Field(description="Toda la información del usuario.")
    html_content : str = Field(description="HTML generado")

## Flujo para creación de document y guardado. 
formatter_agent= Agent(
    name="formatter_agent",
    model="gemini-2.5-flash",
    description="Agente encargado de formatear",
    instruction= instruction.formatter_agent_instructions_v02,
    output_schema=formatterData,
    output_key="formatter_agent_ok",
   
)

pdf_generator_agent = Agent(
    name="pdf_generator_agent",
    model="gemini-2.5-flash",
    description="Agente encargado de generar pdf",
    instruction=instruction.pdf_generator_agent_instructions,
    tools=[generate_docx_from_html],
    before_model_callback=before_model_callback
)

sequential_generator_agent = SequentialAgent(
    name="sequential_generator_agent",
    description="Agente encargado de formatear",
    sub_agents=[formatter_agent,pdf_generator_agent]

)

## Agente que hace la demanda. 
#TODO: No mostrar digitos si no en letras.
demand_agent = Agent(
    name="demand_agent",
    model="gemini-2.5-pro",
    description="Eres un agente que crea demandas preliminares.",
    instruction=instruction.demand_instruction_v02,
    #tools=[process_document, generate_pdf_from_html],
    #tools=[process_document, generate_docx_from_html],
    tools=[process_document, AgentTool(agent=sequential_generator_agent)],
    # before_model_callback=before_model_callback,
    # after_model_callback=after_model_callback

)