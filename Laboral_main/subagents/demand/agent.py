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
class worker_personal_data(BaseModel):
    worker_name: str = Field(description="Nombre completo del trabajador")
    worker_age: str = Field(description="Edad del trabajador")
    worker_marital_status: str = Field(description="Estado marital del trabajador")
    worker_profession_or_trade: str = Field(description="Profesion del trabajador")
    worker_nationality: str = Field(description="Nacionalidad del trabajador")
    worker_address: str = Field(description="Domicilio del trabajador")
    worker_dui: str = Field(description="Dui del trabajador")

class personal_lawyer_data(BaseModel):
    lawyer_name: str = Field(description="Nombre del abogado en turno")
    lawyer_age: str = Field(description="Nombre del abogado en turno")
    lawyer_dui: str = Field(description="Nombre del abogado en turno")
    lawyer_home: str = Field(description="Nombre del abogado en turno")
    lawyer_card: str = Field(description="Nombre del abogado en turno")

class employment_relationship_data(BaseModel):
    company_defendant: str = Field(description="Nombre de la empresa demandada")
    company_address: str = Field(description="Domicilio de la empresa demandada")
    legal_representative_name: str = Field(description="Nombre del representante legal de la empresa")
    legal_representative_address: str = Field(description="Domicilio del representante legal de la empresa")
    company_notification_address: str = Field(description="Dirección para notificaciones de la empresa")
    employment_start_date_text: str = Field(description="Fecha de inicio de la relación laboral en formato texto")
    job_title: str = Field(description="Cargo nominal del trabajador")
    workplace: str = Field(description="Lugar donde se desempeñaban las labores")
    actual_functions: str = Field(description="Funciones reales desempeñadas por el trabajador")
    workday_description: str = Field(description="Descripción de la jornada laboral")
    work_schedule: str = Field(description="Horario de trabajo")
    salary_text: str = Field(description="Salario mensual en formato texto")
    payment_method: str = Field(description="Forma de pago del salario")
    dismissal_date_text: str = Field(description="Fecha del despido en formato texto")
    dismissal_time_text: str = Field(description="Hora del despido en formato texto")
    person_who_dismissed_name: str = Field(description="Nombre de la persona que realizó el despido")
    person_who_dismissed_position: str = Field(description="Cargo de la persona que realizó el despido")
    dismissal_place: str = Field(description="Lugar donde ocurrió el despido")

# class formatterData(BaseModel):
#     personal_data: personal_worker_data = Field(description="Toda la información del usuario.")
#     html_content : str = Field(description="HTML generado")

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