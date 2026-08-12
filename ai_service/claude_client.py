import json
import os
import anthropic

def get_client(api_key: str):
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)

def generate_structured_content(api_key: str, system_prompt: str, user_prompt: str, schema: dict) -> dict:
    """
    Calls Claude using Tool Use (Structured Output) to force JSON adherence based on a JSON schema.
    """
    
    tools = [
        {
            "name": "output_formatter",
            "description": "Formats the output exactly to the required JSON schema.",
            "input_schema": schema
        }
    ]

    client = get_client(api_key)
    if not client:
        print("Anthropic API key not configured")
        return {}

    try:
        response = client.messages.create(
            model=os.environ.get("DEFAULT_MODEL", ""),
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            tool_choice={"type": "tool", "name": "output_formatter"},
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # The result will be in the tool use block
        for content in response.content:
            if content.type == "tool_use" and content.name == "output_formatter":
                return content.input
                
        return {}
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        return {}
