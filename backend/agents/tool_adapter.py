"""Adaptador: tus herramientas de `tools/` → `StructuredTool` de LangChain.

NO reescribe lógica de negocio. Cada función de `tools/*_tools.py` sigue
viviendo donde estaba y devolviendo JSON (str); aquí solo la envolvemos para que
un agente de LangGraph pueda invocarla.

Beneficio extra (seguridad): el esquema de argumentos se genera con **Pydantic**
a partir del `input_schema` que ya definías, así LangChain valida los argumentos
ANTES de tocar la base de datos. Tipos incorrectos se rechazan solos.
"""
from typing import Optional

from pydantic import Field, create_model
from langchain_core.tools import StructuredTool

from config import DB_PATH

# Mapeo del tipo declarado (OpenAPI-like) al tipo Python para Pydantic.
_PY_TYPES = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def _args_model(tool_def: dict):
    """Construye dinámicamente un modelo Pydantic con los args de la herramienta."""
    name = tool_def["name"]
    schema = tool_def.get("input_schema", {})
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    fields = {}
    for field_name, spec in props.items():
        py_type = _PY_TYPES.get(spec.get("type", "string"), str)
        desc = spec.get("description", "")
        if field_name in required:
            fields[field_name] = (py_type, Field(description=desc))
        else:
            fields[field_name] = (Optional[py_type], Field(default=None, description=desc))

    # Modelo vacío válido cuando la herramienta no recibe argumentos.
    return create_model(f"{name}_Args", **fields)


def make_tools(tool_defs: list, executor, needs_db_path: bool = True) -> list:
    """Convierte una lista de definiciones de herramientas en StructuredTools.

    Args:
        tool_defs: lista de dicts con `name`, `description`, `input_schema`
            (el formato que ya usaba `tools/`).
        executor: la función `execute_*_tool(name, input, db_path)` del dominio.
        needs_db_path: False para ejecutores que NO reciben db_path (p. ej. email).
    """
    tools = []
    for td in tool_defs:
        tool_name = td["name"]
        args_model = _args_model(td)

        def _make_runner(name, exec_fn, with_db):
            def _run(**kwargs):
                # Quita los opcionales no provistos para no pisar defaults del dominio.
                clean = {k: v for k, v in kwargs.items() if v is not None}
                if with_db:
                    return exec_fn(name, clean, DB_PATH)
                return exec_fn(name, clean)
            return _run

        tools.append(
            StructuredTool.from_function(
                func=_make_runner(tool_name, executor, needs_db_path),
                name=tool_name,
                description=td["description"],
                args_schema=args_model,
            )
        )
    return tools
