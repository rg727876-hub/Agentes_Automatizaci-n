"""Esquemas Pydantic de salida estructurada del Deep Agent.

Cada uno es el contrato de salida de un nodo del grafo y se aplica con
`llm.with_structured_output(Esquema)`: garantiza que el LLM devuelva datos
tipados y validados (no texto libre que haya que parsear a mano).

Las descripciones de los `Field` NO son decorativas: `with_structured_output`
las pasa al modelo como parte del esquema, así que actúan como micro-instrucción
de cada campo. Manténlas precisas y en español, igual que los prompts del sistema.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Plan(BaseModel):
    """Salida del nodo `planificar`: descomposición de la consulta del usuario.

    El planificador NO responde: solo descompone el problema y prepara una
    consulta de búsqueda optimizada para el retriever del Vector Store.
    """

    razonamiento: str = Field(
        description=(
            "Razonamiento breve (Chain-of-Thought) de cómo se descompone la "
            "consulta. Una o dos frases; no resuelve la pregunta, solo planifica."
        )
    )
    subpreguntas: List[str] = Field(
        description=(
            "Lista de 1 a 5 sub-preguntas atómicas en las que se descompone la "
            "consulta original. Cada una debe ser respondible por separado."
        )
    )
    consulta_busqueda: str = Field(
        description=(
            "Consulta única y optimizada para buscar en el Vector Store "
            "(retriever semántico). Debe ser concisa y rica en palabras clave; "
            "NO es una pregunta conversacional sino términos de recuperación."
        )
    )


class RespuestaGenerada(BaseModel):
    """Salida del nodo `generar`: respuesta redactada a partir del contexto.

    El generador SOLO puede usar la información del contexto recuperado. Si el
    contexto no alcanza, debe declararlo en `informacion_suficiente=False` en
    lugar de inventar (esto alimenta la decisión del crítico).
    """

    respuesta: str = Field(
        description=(
            "Respuesta final redactada para el usuario, en español, basada "
            "EXCLUSIVAMENTE en el contexto recuperado."
        )
    )
    fuentes_usadas: List[str] = Field(
        default_factory=list,
        description=(
            "Identificadores o fragmentos del contexto recuperado (p. ej. SKU o "
            "una cita textual corta) en los que se apoya la respuesta. Permite "
            "que el crítico verifique el sustento (groundedness)."
        ),
    )
    informacion_suficiente: bool = Field(
        description=(
            "True si el contexto recuperado bastaba para responder; False si "
            "faltó información (señal para que el crítico ordene reintentar)."
        )
    )


class VeredictoCritico(BaseModel):
    """Salida del nodo `evaluar`: juicio del sub-agente crítico.

    El crítico verifica la veracidad/sustento (*groundedness*) de la respuesta
    frente al contexto recuperado y decide si el bucle finaliza o se reintenta.
    Su salida es la que lee la arista condicional para enrutar el grafo.
    """

    fundamentada: bool = Field(
        description=(
            "True si CADA afirmación de la respuesta está sustentada por el "
            "contexto recuperado (sin alucinaciones); False en caso contrario."
        )
    )
    puntuacion: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Grado de sustento de la respuesta en el contexto, de 0.0 (sin "
            "sustento) a 1.0 (totalmente fundamentada)."
        ),
    )
    accion: Literal["finalizar", "reintentar"] = Field(
        description=(
            "Decisión de control del bucle: 'finalizar' si la respuesta es "
            "fiable y completa; 'reintentar' si hay que re-planificar y "
            "reformular la búsqueda."
        )
    )
    problemas: List[str] = Field(
        default_factory=list,
        description=(
            "Lista de problemas concretos detectados (afirmaciones sin sustento, "
            "lagunas, contradicciones). Vacía si la respuesta es correcta."
        ),
    )
    consulta_reformulada: Optional[str] = Field(
        default=None,
        description=(
            "Si accion='reintentar', nueva consulta de búsqueda sugerida para "
            "el retriever en la siguiente vuelta. None si accion='finalizar'."
        ),
    )
