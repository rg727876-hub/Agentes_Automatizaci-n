"""Construcción de agentes especializados sobre LangGraph.

Reemplaza el antiguo bucle manual de *function calling* de Gemini por
`create_react_agent`: un grafo ReAct autónomo que, dado un objetivo, decide por
sí mismo qué herramientas llamar y en qué orden hasta resolver la consulta. Eso
hace a los agentes **más dinámicos** sin que tengamos que programar el flujo.

Prompts NO estáticos: el *system prompt* se arma en cada llamada con una función
que inyecta contexto vivo (hoy, la fecha actual; el orquestador además inyecta
memoria). Las instrucciones por dominio son la base; la composición es dinámica.
"""
from datetime import date

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from llm import get_llm


def make_dynamic_prompt(instructions: str):
    """Devuelve un prompt *callable* para create_react_agent.

    LangGraph lo ejecuta en cada paso del razonamiento con el estado actual, así
    el system prompt se construye al vuelo (fecha de hoy + instrucciones).
    """
    def _prompt(state):
        today = date.today().isoformat()
        system = SystemMessage(
            content=f"{instructions}\n\n[Contexto dinámico] Fecha actual: {today}."
        )
        return [system] + state["messages"]

    return _prompt


def build_agent(instructions: str, tools: list, model: str):
    """Crea un agente ReAct de LangGraph con sus herramientas y prompt dinámico."""
    return create_react_agent(
        model=get_llm(model),
        tools=tools,
        prompt=make_dynamic_prompt(instructions),
    )


def run_agent(agent, query: str) -> str:
    """Ejecuta un agente con una consulta y devuelve el texto de la respuesta final."""
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    messages = result.get("messages", [])
    return messages[-1].content if messages else ""
