import os
from typing import Dict, Any, Optional
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import AgentTool
from google.genai import types 
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from pydantic import BaseModel, Field 
#from .instructions import reporter_instructions, reporter_fola03_instruction, reporter_instructions_v02, reporter_fola03_instruction_v02
from . import instructions
from . tools.generate_document import generate_docx_from_html
from ...tools.read_documents import process_document

# Debuggimg

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
    instruction= instructions.formatter_agent_instructions_v02,
    output_schema=formatterData,
    output_key="formatter_agent_ok"
)

pdf_generator_agent = Agent(
    name="pdf_generator_agent",
    model="gemini-2.5-flash",
    description="Agente encargado de generar pdf",
    instruction=instructions.pdf_generator_agent_instructions,
    tools=[generate_docx_from_html]
)

sequential_generator_agent = SequentialAgent(
    name="sequential_generator_agent",
    description="Agente encargado de formatear",
    sub_agents=[formatter_agent,pdf_generator_agent]

)

### Agentes redactores.
#TODO: No mostrar digitos si no en letras.
fola_03_reporter = Agent(
    name="fola_03_reporter",
    model="gemini-2.5-pro",
    description="Agente encargado de generar el formato sugerido",
    instruction=instructions.reporter_fola03_instruction_v07,
    output_key="fola_03_reporter_output",
   # tools=[ rag_formats_laboral, generate_pdf_from_html ]
    #tools=[ generate_pdf_from_html ]
    #tools=[generate_docx_from_html, process_document]
    tools=[process_document, AgentTool(agent=sequential_generator_agent)]
)

fola_07I_reporter = Agent(
    name="fola_07I_reporter",
    model="gemini-2.5-pro",
    description="Agente encargado de generar el formato sugerido",
    instruction=instructions.reporter_fola07I_instruction,
    output_key="fola_07I_reporter_output",
    tools=[process_document, AgentTool(agent=sequential_generator_agent)]
)

fola_07II_reporter = Agent(
    name="fola_07II_reporter",
    model="gemini-2.5-pro",
    description="Agente encargado de generar el formato sugerido",
    instruction=instructions.reporter_fola07II_instruction,
    output_key="fola_07II_reporter_output",
    tools=[process_document, AgentTool(agent=sequential_generator_agent)]
)

fola_08II_reporter = Agent(
    name="fola_08II_reporter",
    model="gemini-2.5-pro",
    description="Agente encargado de generar el formato sugerido",
    instruction=instructions.reporter_fola08II_instruction,
    output_key="fola_08II_reporter_output",
    tools=[process_document, AgentTool(agent=sequential_generator_agent)]
)

### Agentes redactores.

reporter_generator = Agent(
    name="reporter_generator",
    model="gemini-2.5-pro",
    description="Agente encargado de generar el formato sugerido",
    instruction=instructions.reporter_instructions_v02,
    output_key="reporter_generator_output",
    #tools=[AgentTool(agent=fola_03_reporter)]
    sub_agents=[
        fola_03_reporter,
        fola_07I_reporter,
        fola_07II_reporter,
        fola_08II_reporter,
    ]
)
