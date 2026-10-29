import os
import anthropic


class QuotaExceededError(Exception):
    """Raised when the Anthropic API monthly usage limit has been reached."""
    pass


def get_client(api_key: str):
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)

def generate_structured_content(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    schema: dict,
    operation: str = "claude_call",
) -> dict:
    """
    Calls Claude using Tool Use (Structured Output) to force JSON adherence based on a JSON schema.
    Raises QuotaExceededError if the Anthropic monthly spend limit has been hit.

    Args:
        operation: Name logged to the AI usage tracker (e.g. 'ai_extractor', 'generate_post').
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
            model=os.environ.get("DEFAULT_MODEL", "claude-sonnet-4-5"),
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            tool_choice={"type": "tool", "name": "output_formatter"},
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        # ── Log token usage ────────────────────────────────────────────────
        try:
            from app.services.ai_usage_tracker import log_usage
            log_usage(
                operation=operation,
                model=os.environ.get("DEFAULT_MODEL", "claude-sonnet-4-5"),
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        except Exception:
            pass

        # The result will be in the tool use block
        for content in response.content:
            if content.type == "tool_use" and content.name == "output_formatter":
                return content.input

        return {}
    except Exception as e:
        err_str = str(e)
        # ── Detect monthly quota / spend-limit errors ──────────────────────
        if "usage limits" in err_str or "regain access" in err_str or (
            hasattr(e, "status_code") and e.status_code == 400
            and "usage" in err_str.lower()
        ):
            raise QuotaExceededError(err_str) from e
        print(f"Error calling Claude API: {e}")
        return {}
