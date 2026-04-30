import asyncio
import httpx
import json

async def force_discover():
    url = "https://order-mcp-74afyau24q-uc.a.run.app/mcp"
    headers = {"Accept": "text/event-stream"}
    
    print(f"Connecting to {url}...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", url, headers=headers) as response:
            print(f"Status: {response.status_code}")
            
            async for line in response.aiter_lines():
                if line.startswith("event: endpoint"):
                    # This is usually where the POST URL for tools is hidden
                    print(f"\n[Endpoint Found]: {line}")
                
                if line.startswith("data:"):
                    data_content = line[5:].strip()
                    try:
                        parsed = json.loads(data_content)
                        # We are looking for the 'tools/list' result
                        print("\n--- Incoming Data ---")
                        print(json.dumps(parsed, indent=2))
                    except:
                        print(f"Raw Data: {data_content}")

                # If we get pings but no tools, we might need to 'poke' it.
                # But first, let's see if it identifies itself.
                if "ping" not in line and line.strip():
                    print(f"Stream: {line}")

if __name__ == "__main__":
    # Install httpx first: uv add httpx
    asyncio.run(force_discover())