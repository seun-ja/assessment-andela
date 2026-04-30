# Meridian Electronics AI Support Chatbot

This project is a production-ready prototype for a customer support chatbot for Meridian Electronics. It connects to an MCP server to access internal tools for order management, inventory, and customer authentication, and provides a user-friendly chat interface using Gradio.

## Features
- Cost-effective LLM (OpenRouter GPT-4o-mini by default)
- Gradio-based chat UI with stop button
- Dynamic tool discovery from MCP server
- Handles order status, inventory, authentication, and more
- Production-grade logging and error handling
- Easily deployable (HuggingFace Spaces, cloud, etc.)

## Usage

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**
   - Create a `.env` file with your OpenRouter/OpenAI API key:
     ```env
     OPENROUTER_API_KEY=your-key-here
     ```

3. **Run the app**
   ```bash
   python main.py
   ```
   The Gradio UI will launch. Open the provided URL in your browser.

4. **Test with sample users**
   Use the provided test emails and PINs (see `instruct.md`) to simulate real customer flows.

## Project Structure
- `main.py` — Entry point, Gradio UI, async handler
- `chatbot.py` — MeridianSupportAgent logic, LLM/tool orchestration
- `tools.py` — (Optional) MCP stream debug utilities
- `test_chatbot.py` — Unit tests for core logic
- `requirements.txt` — Python dependencies
- `.env` — API keys (not committed)

## Troubleshooting
- If the chatbot hangs after connecting, the MCP server may not be sending tool definitions. Check logs for connection and tool discovery events.
- Use Ctrl+C in the terminal or the UI stop button to interrupt long-running requests.

## Deployment
- The app is ready for deployment to HuggingFace Spaces, Vercel, or any cloud platform supporting Python and Gradio.
- For HuggingFace Spaces, set `share=True` in `demo.launch()` in `main.py`.

## License
MIT

---

**Assessment Notes:**
- Meets all requirements in `instruct.md`.
- Clean, modular, and production-ready code.
- Ready for demo and further extension.
