from google.adk.agents import Agent 
from .instructions import fola_01_instructions,fola_02_instructions,fola_generator_instructions




fola_01_agent = Agent(
    name="fola_01_agent",
    model="gemini-2.5-flash",
    description="Agente encargado de generar el documento fola generado",
    instruction=fola_01_instructions.fola_01_prompt_v0,
    output_key="fola_01_agent_output_key"
)



fola_02_agent = Agent(
    name="fola_02_agent",
    model="gemini-2.5-flash",
    description="Agente encargado de generar el documento fola generado",
    instruction=fola_02_instructions.fola_02_prompt_v0,
    output_key="fola_02_agent_output_key"
)



fola_generator_agent = Agent(
    name="fola_generator_agent",
    model="gemini-2.5-flash",
    description="Agente encargado de generar el documento fola generado",
    instruction=fola_generator_instructions.fola_generator_v0,
    output_key="fola_generator_agent_output_key"
)