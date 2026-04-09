# Rag
import os

from dotenv import load_dotenv

from google.adk.tools.retrieval.vertex_ai_rag_retrieval import (
    VertexAiRagRetrieval
)
from vertexai.preview import rag

load_dotenv()

# TODO: Rag Tool por cada corpus. 

def rag_tool(name: str, description: str, corpus_env_var: str): 

    rag_corpus = os.getenv(corpus_env_var)
    if not rag_corpus:
        return None
    
    return VertexAiRagRetrieval(
        name=name,
        description=description,
        rag_resources=[
            rag.RagResource(
                rag_corpus=rag_corpus
            )
        ],
        similarity_top_k=3,
        vector_distance_threshold=0.6
    )