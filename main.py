import asyncio
import logging
import traceback

import gradio as gr
from dotenv import load_dotenv

from chatbot import MeridianSupportAgent
from mcp.client.sse import sse_client
from mcp import ClientSession

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("main")

# Initialize Agent and Async Stop Event
agent = MeridianSupportAgent()
stop_event = asyncio.Event()

# Global variable to hold the persistent MCP session
mcp_session = None
client_context = None

async def get_mcp_session():
    global mcp_session, client_context
    if mcp_session is None:
        logger.info("🔌 Step 1: Opening SSE Connection...")
        client_context = sse_client(agent.mcp_url, timeout=30)
        
        # If it hangs here, the network is blocking the stream
        read, write = await client_context.__aenter__() 
        logger.info("🔌 Step 2: SSE Stream Connected. Starting Session...")
        
        session = ClientSession(read, write)
        
        # If it hangs here, the server isn't sending the 'initialize' response
        await session.initialize()
        logger.info("✅ Step 3: MCP Session Initialized!")
        
        mcp_session = session
    return mcp_session

async def _chat_async(user_message, history):
    """
    Asynchronous handler for Gradio ChatInterface.
    """
    print(f"\n--- MESSAGE RECEIVED: {user_message} ---\n", flush=True)
    logger.info("🔥 HANDLER HIT")

    # Rebuild conversation context for the LLM
    agent.messages = [
        {
            "role": "system",
            "content": "You are a helpful support agent for Meridian Electronics. Use tools to check inventory and orders."
        }
    ]

    for human, assistant in history:
        agent.messages.append({"role": "user", "content": human})
        agent.messages.append({"role": "assistant", "content": assistant})

    try:
        # Retrieve the reused session
        session = await get_mcp_session()

        if stop_event.is_set():
            stop_event.clear()
            return "⏹️ Chat stopped."

        # Execute the agent loop
        result = await agent.chat_loop_gradio(
            user_message,
            session,
            stop_event
        )

        return result

    except Exception as e:
        traceback.print_exc()
        logger.exception("FULL ERROR:")
        return f"⚠️ Connection Error: {str(e)}. Please ensure the MCP server is awake."

# Build the Gradio UI
with gr.Blocks(title="Meridian Electronics Support") as demo:
    gr.Markdown("# 🤖 Meridian Electronics AI Support")
    gr.Markdown("Testing identity: **Laura Henderson (laurahenderson@example.org)** | PIN: **1488**")

    stop_btn = gr.Button("⏹️ Stop Generation", variant="stop")

    chat_interface = gr.ChatInterface(
        fn=_chat_async,
        chatbot=gr.Chatbot(height=500),
        textbox=gr.Textbox(
            placeholder="Ask about orders, inventory, or account status...",
            container=False
        ),
    )

    async def stop_chat():
        logger.info("🛑 Stop requested by user.")
        stop_event.set()
        return

    stop_btn.click(fn=stop_chat, inputs=None, outputs=None)

if __name__ == "__main__":
    # Launch with a queue to handle multiple requests if needed
    demo.queue().launch(server_port=7861)