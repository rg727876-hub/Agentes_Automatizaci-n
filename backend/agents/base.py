import re
import time
from google.genai import types
from google.genai.errors import ClientError, ServerError
from config import MAX_ITERATIONS, MAX_RETRIES


def _gemini_call(func, *args, **kwargs):
    """Llama a la API de Gemini con reintentos automáticos ante errores 429/503."""
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except (ClientError, ServerError) as e:
            error_str = str(e)
            if "429" in error_str or "503" in error_str or "UNAVAILABLE" in error_str:
                match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_str)
                wait = min(int(float(match.group(1))) + 2 if match else 10 * (attempt + 1), 30)
                print(f"\n  [API no disponible] Esperando {wait}s antes de reintentar...")
                time.sleep(wait)
                if attempt == MAX_RETRIES - 1:
                    return None
            else:
                raise
    return None


_TYPE_MAP = {
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "object": "OBJECT",
    "array": "ARRAY",
}


def _build_schema(schema_dict: dict) -> types.Schema:
    if not schema_dict:
        return None
    type_key = schema_dict.get("type", "string").lower()
    gemini_type = _TYPE_MAP.get(type_key, "STRING")
    kwargs = {"type": gemini_type}
    if "description" in schema_dict:
        kwargs["description"] = schema_dict["description"]
    if "properties" in schema_dict:
        kwargs["properties"] = {
            k: _build_schema(v) for k, v in schema_dict["properties"].items()
        }
    if "required" in schema_dict:
        kwargs["required"] = schema_dict["required"]
    if "items" in schema_dict:
        kwargs["items"] = _build_schema(schema_dict["items"])
    return types.Schema(**kwargs)


def convert_tools(tools: list) -> list[types.Tool]:
    """Convierte el formato de herramientas (OpenAPI-like) al formato de Gemini."""
    declarations = []
    for tool in tools:
        schema = tool.get("input_schema", {})
        props = schema.get("properties", {})
        required = schema.get("required", [])

        params = None
        if props:
            gemini_props = {name: _build_schema(defn) for name, defn in props.items()}
            params = types.Schema(
                type="OBJECT",
                properties=gemini_props,
                required=required if required else None,
            )

        declarations.append(types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=params,
        ))

    return [types.Tool(function_declarations=declarations)]


class BaseAgent:
    def __init__(self, client, db_path: str, model: str):
        self.client = client
        self.db_path = db_path
        self.model = model

    def execute(self, query: str, tools: list, system_prompt: str) -> str:
        gemini_tools = convert_tools(tools)
        contents = [types.Content(role="user", parts=[types.Part(text=query)])]

        for _ in range(MAX_ITERATIONS):
            response = _gemini_call(
                self.client.models.generate_content,
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=gemini_tools,
                ),
            )

            if not response or not response.candidates:
                return "Lo siento, el servicio no está disponible en este momento. Por favor intenta de nuevo."

            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                return "Lo siento, recibí una respuesta vacía. Por favor intenta de nuevo."

            parts = candidate.content.parts

            func_calls = [
                p.function_call for p in parts
                if hasattr(p, "function_call") and p.function_call and p.function_call.name
            ]

            if not func_calls:
                for p in parts:
                    if hasattr(p, "text") and p.text:
                        return p.text
                return ""

            contents.append(candidate.content)

            response_parts = []
            for fc in func_calls:
                result = self._execute_tool(fc.name, dict(fc.args))
                response_parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": result},
                    )
                ))

            contents.append(types.Content(role="user", parts=response_parts))

        return "Error: Se alcanzó el límite máximo de iteraciones."

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        raise NotImplementedError("Cada agente debe implementar _execute_tool")
