import os
import json
from typing import Dict, Any, List
from pydantic import BaseModel
import anthropic

class AgentConfig(BaseModel):
    name: str
    role: str
    goal: str
    backstory: str
    
class AgentClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("api_key must be provided to AgentClient")
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model_name = os.environ.get("DEFAULT_MODEL", "claude-3-5-sonnet-20240620")


    def execute_task(self, agent_config: AgentConfig, task_description: str, tools: List[Any] = None) -> str:
        """Executes a generic task as the specified agent."""
        if not self.client:
            raise ValueError("Anthropic API key not configured")
            
        system_instruction = f"""
You are {agent_config.name}.
Role: {agent_config.role}
Goal: {agent_config.goal}
Backstory: {agent_config.backstory}

Execute the following task exactly as requested.
"""
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=2048,
                system=system_instruction,
                messages=[
                    {"role": "user", "content": task_description}
                ]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            return str(e)

    def execute_structured_task(self, agent_config: AgentConfig, task_description: str, schema: type[BaseModel]) -> dict:
        """Executes a task and strictly returns JSON matching the Pydantic schema using tool use."""
        if not self.client:
            raise ValueError("Anthropic API key not configured")
            
        system_instruction = f"""
You are {agent_config.name}.
Role: {agent_config.role}
Goal: {agent_config.goal}
Backstory: {agent_config.backstory}

Execute the following task exactly as requested. You must respond using the output_formatter tool.
"""
        # Convert pydantic schema to JSON schema
        json_schema = schema.model_json_schema()
        
        tools = [
            {
                "name": "output_formatter",
                "description": "Formats the output exactly to the required JSON schema.",
                "input_schema": json_schema
            }
        ]
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                system=system_instruction,
                tools=tools,
                tool_choice={"type": "tool", "name": "output_formatter"},
                messages=[
                    {"role": "user", "content": task_description}
                ]
            )
            
            # Extract tool use response
            for content in response.content:
                if content.type == "tool_use" and content.name == "output_formatter":
                    return content.input
                    
            raise ValueError(f"Claude API did not return tool_use. Response: {response.content}")
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            raise e
