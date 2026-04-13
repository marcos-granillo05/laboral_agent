from google.adk.agents import Agent, SequentialAgent
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


#### Secuenciales FOLA 01.

formatter_fola01_agent = Agent(
    name="formatter_fola01_agent",
    model="gemini-2.5-flash",
    description="",
    instruction=fola_01_instructions.formatter_fola01_prompt_v0
)

fola_01_generator = Agent(
    name="fola_01_generator",
    model="gemini-2.5-flash",
    description="",
    instruction=fola_01_instructions.fola_01_generator_prompt_v0
)


sequential_fola01_agent = SequentialAgent(
    name="sequential_fola01_agent",
    description="Agente encargado de ejecutar la secuencia de pasos entre agentes.",
    sub_agents=[formatter_fola01_agent,fola_01_generator]
)

### Secuenciales FOLA02

formatter_fola02_agent = Agent(
    name="formatter_fola02_agent",
    model="gemini-2.5-flash",
    description="",
    instruction="",
)

fola_02_generator = Agent(
    name="fola_02_generator",
    model="gemini-2.5-flash",
    description="",
    instruction=""
)


sequential_fola02_agent = SequentialAgent(
    name="sequential_fola02_agent",
    description="Agente encargado de ejecutar la secuencia de pasos entre agentes.",
    sub_agents=[formatter_fola02_agent,fola_02_generator]
)

###



fola_generator_agent = Agent(
    name="fola_generator_agent",
    model="gemini-2.5-flash",
    description="Agente encargado de generar el documento fola generado",
    instruction=fola_generator_instructions.fola_generator_v0,
    output_key="fola_generator_agent_output_key"
)