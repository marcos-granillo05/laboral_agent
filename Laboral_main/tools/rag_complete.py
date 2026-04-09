from ..tools.rag_function import rag_tool

#Leyes que contemplan 
rag_laboral_publico_privado = rag_tool(
    name="leyes-laboral-publico-privado",
    description="Leyes que contemplan sector público y privado.",
    corpus_env_var="RAG_LEYES_LABORALES_PUBLICO_PRIVADO"
)

# Leyes solo para sector privado
rag_laboral_privado = rag_tool(
    name="leyes-laboral-privado",
    description="Leyes que contemplan sector privado.",
    corpus_env_var="RAG_LEYES_LABORALES_PRIVADO"
)

# Leyes de serctor público
rag_laboral_publico = rag_tool(
    name="leyes-laboral-publico",
    description="Leyes que contemplan sector público y privado.",
    corpus_env_var="RAG_LEYES_LABORALES_PUBLICO"
)

# Leyes de sector público -> CARRERAS
rag_laboral_publico_carrera = rag_tool(
    name="leyes-laboral-publico-carrera",
    description="Leyes que contemplan sector público y privado.",
    corpus_env_var="RAG_LEYES_LABORALES_PUBLICO_CARRERAS"
)

# Guia de servicio
rag_guia_de_servicio = rag_tool(
    name="rag_guia_de_servicio",
    description="Guia de servicios de la PGR",
    corpus_env_var="RAG_GUIA_DE_SERVICIO_PGR"
)

# Formatos sugeridos. 
rag_formats_laboral = rag_tool(
    name="rag_formats_laboral",
    description="Conjunto de formatos de formularios de la pgr",
    corpus_env_var="RAG_FORMATOS_LABORAL"
)


# Resoluciones Judiciales. 
rag_resoluciones_judiciales = rag_tool(
    name="rag_resoluciones_judiciales",
    description="Conjunto de resoluciones judiciales",
    corpus_env_var="RAG_RESOLUCIONES_JUDICIALES"
)