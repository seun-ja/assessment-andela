import json
import logging
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent")

api_key = os.getenv("OPENROUTER_API_KEY")


class MeridianSupportAgent:
    def __init__(self):
        self.mcp_url = "https://order-mcp-74afyau24q-uc.a.run.app/mcp"

        self.client = AsyncOpenAI( # Change this
            base_url="http://localhost:11434/v1", 
            api_key="ollama"
        )

        self.model = "llama3.2:latest"

        self.messages = [
            {
                "role": "system",
                "content": "You are a helpful support agent for Meridian Electronics."
            }
        ]

    async def chat_loop_gradio(self, user_input, mcp_session, stop_event=None):
        self.messages.append({"role": "user", "content": user_input})

        logger.info("Fetching MCP tools...")
        mcp_tools = await mcp_session.list_tools()

        tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema,
                },
            }
            for t in mcp_tools.tools
        ]

        logger.info("Calling LLM...")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=tools
        )

        msg = response.choices[0].message
        self.messages.append(msg)

        if not msg.tool_calls:
            return msg.content

        logs = []

        for tool_call in msg.tool_calls:
            if stop_event and stop_event.is_set():
                stop_event.clear()
                return "⏹️ Stopped."

            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            logs.append(f"⚙️ Executing `{name}`...")

            try:
                logger.info(f"Calling tool: {name}")
                result = await mcp_session.call_tool(name, args)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result.content)
                })

            except Exception as e:
                logger.exception("Tool error")

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": f"Error: {str(e)}"
                })

        final = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages
        )

        return "\n".join(logs) + "\n\n---\n\n" + final.choices[0].message.content