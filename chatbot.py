import logging
import os
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent")

api_key = os.getenv("OPENROUTER_API_KEY")
url = os.getenv("MCP_SERVER_URL")


class MeridianSupportAgent:
    def __init__(self):
        self.mcp_url = url
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = "gpt-4o-mini"
        self.messages = [
            {
                "role": "system",
                "content": "You are a helpful support agent for Meridian Electronics."
            }
        ]
        self._tools_cache: list[dict[str, Any]] | None = None

    async def chat_loop_gradio(self, user_input, tools: list[dict[str, Any]] | None = None):
        self.messages.append({"role": "user", "content": user_input})

        logger.info("Calling LLM...")

        kwargs = {
            "model": self.model,
            "messages": self.messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message
        except Exception as e:
            logger.exception("Tool error")
            return (
                "I'm having trouble completing that request right now. "
                "Let me hand you off to a human agent."
            )
    