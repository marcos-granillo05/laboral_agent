from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools import AgentTool
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field 

#from . import instruction
#from .tools.generate_document import generate_docx_from_html
from .instructions import demand_instructions,formatter_instructions, demand_generator
from .docs.demand import complaint_maker
from ...tools.read_documents import process_document

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
class WorkerPersonalData(BaseModel):  # Outputschema  
    worker_name: str = Field(description="Nombre completo del trabajador")
    worker_age: str = Field(description="Edad del trabajador")
    worker_marital_status: str = Field(description="Estado marital del trabajador")
    worker_profession_or_trade: str = Field(description="Profesion del trabajador")
    worker_nationality: str = Field(description="Nacionalidad del trabajador")
    worker_address: str = Field(description="Domicilio del trabajador")
    worker_dui: str = Field(description="Dui del trabajador")

class PersonalLawyerData(BaseModel):
    lawyer_name: str = Field(description="Nombre del abogado en turno")
    lawyer_age: str = Field(description="Nombre del abogado en turno")
    lawyer_dui: str = Field(description="Nombre del abogado en turno")
    lawyer_home: str = Field(description="Nombre del abogado en turno")
    lawyer_card: str = Field(description="Nombre del abogado en turno")

class EmploymentRelationshipData(BaseModel):
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

class complete_information(BaseModel):
    worker_information: WorkerPersonalData = Field(description="Información completa del Trabajador")
    lawyer_information: PersonalLawyerData = Field(description="Información completa del abotado")
    employment_relationship_data: EmploymentRelationshipData = Field(description="Información asociada al Trabajador respecto a su relación laboral")
    law_suggestions: str = Field(description="Leyes asociadas violadas al caso")

# class formatterData(BaseModel):
#     personal_data: personal_worker_data = Field(description="Toda la información del usuario.")
#     html_content : str = Field(description="HTML generado")

## Flujo para creación de document y guardado. 
formatter_agent= Agent(
    name="formatter_agent",
    model="gemini-2.5-flash",
    description="Agente encargado de formatear",
    instruction= formatter_instructions.formatter_agent_instructions_v0,
   # output_schema=formatterData,
    output_schema=complete_information,
    output_key="formatter_agent_output_key",
   
)

# pdf_generator_agent = Agent(
#     name="pdf_generator_agent",
#     model="gemini-2.5-flash",
#     description="Agente encargado de generar pdf",
#     instruction=instruction.pdf_generator_agent_instructions_v02,
#     #tools=[generate_docx_from_html],
#     tools=[demanda_despido_directo_document_maker],
#     before_model_callback=before_model_callback
# )

demand_generator_agent = Agent(
    name="pdf_generator_agent",
    model="gemini-2.5-flash",
    description="Agente encargado de generar demanda en formato Docx",
    instruction=demand_generator.demand_generator_agent_prompt_v0,
    tools=[complaint_maker],
)


# sequential_generator_agent = SequentialAgent(
#     name="sequential_generator_agent",
#     description="Agente secuencial encargado de guiar la generación de documento apropiado",
#     sub_agents=[formatter_agent,pdf_generator_agent]
# )

sequential_generator_agent = SequentialAgent(
    name="sequential_generator_agent",
    description="Agente secuencial encargado de guiar la generación de documento apropiado",
    sub_agents=[formatter_agent,demand_generator_agent]
)

## Agente que hace la demanda. 
#TODO: No mostrar digitos si no en letras.
demand_agent = Agent(
    name="demand_agent",
    model="gemini-2.5-pro",
    description="Eres un agente que crea demandas preliminares.",
    instruction=demand_instructions.demand_agent_instruction_v0,
    tools=[process_document, AgentTool(agent=sequential_generator_agent)],
    # before_model_callback=before_model_callback,
    # after_model_callback=after_model_callback

)
