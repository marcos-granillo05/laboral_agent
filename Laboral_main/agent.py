
import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import Agent 


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Carga el .env local del agente aunque ADK se ejecute desde otra carpeta.
load_dotenv(ENV_PATH, override=False)

adk_credentials_path = os.environ.get("ADK_CREDENTIALS_PATH")
if adk_credentials_path and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = adk_credentials_path

from google.adk.tools import  AgentTool
from google.genai import types 
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from typing import Optional
from .subagents.privado import laboral_privado_sequential_v02
from .subagents.publico import laboral_publico_sequential_v02
from .subagents.writer import reporter_generator
from .subagents.demand import demand_agent

#from .tools.tool_files import  get_all_files_from_context
from .tools.read_documents import process_document
from .tools.rag_complete import rag_guia_de_servicio 
from . import instruction

#### Debugging: 
def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    
    print(f'Respuest del modelo LABORAL_ORCHESTATOR: {llm_response.content.parts[0].text}')


def before_model_callback_agent(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmRequest]:
    print(f'--------------------------------------------') 
    print(f'identify_claim: {llm_request.contents}')
    print(f'--------------------------------------------')



# TODO: Agente que identificará Requisitos en función del relato de hecho. 
identify_claim = Agent(
    name="identify_claim",
    description="Tu objetivo es determinar las pretenciones en función de un relato de hecho.",
    model="gemini-2.5-flash",
    instruction=instruction.identify_claims_instructions,
    tools=[rag_guia_de_servicio],
    before_model_callback=before_model_callback_agent
       
)

#TODO: Mostrar que leyes y artículos usa ? al menos en chat luego de análisis. 

laboral_orchestator = Agent(
    name="laboral_orchestator",
    description="Tu objetivo es solicitar información y orquestar los flujos de conversación",
    model="gemini-2.5-flash",
    instruction=instruction.laboral_orchestator_instruction_v05,
    output_key="laboral_orchestator_output",
    tools=[process_document,
          # AgentTool(agent=laboral_privado_sequential), 
           AgentTool(agent=laboral_privado_sequential_v02),
           AgentTool(agent=laboral_publico_sequential_v02),
           AgentTool(agent=identify_claim)
           ],
    # tools=[get_all_files_from_context,AgentTool(agent=laboral_privado_sequential), AgentTool(agent=laboral_publico_sequential)],
    sub_agents=[reporter_generator, demand_agent],
    generate_content_config=types.GenerateContentConfig(
        top_p=0.7,
        # safety_settings=[
        #     types.SafetySetting(
        #         category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        #         threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        #     )
        # ]
    ),
    after_model_callback=after_model_callback
    
)

root_agent = laboral_orchestator
