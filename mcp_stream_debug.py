import asyncio
import httpx

MCP_URL = "https://order-mcp-74afyau24q-uc.a.run.app/mcp"

async def print_mcp_stream():
    print(f"Connecting to {MCP_URL} ...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", MCP_URL, headers={"Accept": "text/event-stream"}) as response:
            print(f"Status: {response.status_code}")
            async for line in response.aiter_lines():
                print(f"[MCP STREAM] {line}")

if __name__ == "__main__":
    asyncio.run(print_mcp_stream())
