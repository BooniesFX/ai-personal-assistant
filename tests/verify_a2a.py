import asyncio
import httpx
import sys

async def verify_sidecar():
    print("🚀 Verifying Sidecar Health...")
    
    async with httpx.AsyncClient() as client:
        # 1. Health Check
        try:
            resp = await client.get("http://localhost:8001/health")
            if resp.status_code == 200:
                print(f"✅ Sidecar is healthy: {resp.json()}")
            else:
                print(f"❌ Sidecar health check failed: {resp.status_code}")
                return
        except Exception as e:
            print(f"❌ Could not connect to Sidecar: {e}")
            print("💡 Make sure you started the sidecar with: uv run sidecar/app.py --adapter cli --command 'echo hello' --port 8001")
            return

        # 2. Send Message
        print("\n📧 Sending Test Message...")
        payload = {
            "from_agent_id": "test_script",
            "conversation_id": "test_conv_1",
            "content": "hello world"
        }
        
        try:
            resp = await client.post("http://localhost:8001/agent/message", json=payload)
            if resp.status_code == 200:
                result = resp.json()
                print(f"✅ Response received:\n{result}")
                
                # Check ECHO output (since we recommend testing with 'echo hello')
                if "hello" in result['content'] or "Echo" in result['content']:
                     print("✅ Content verification passed.")
                else:
                     print("⚠️ Content verification warning: Unexpected output (ignore if not using echo)")
                     
            else:
                print(f"❌ Message sending failed: {resp.text}")
        except Exception as e:
            print(f"❌ Error sending message: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(verify_sidecar())
    except KeyboardInterrupt:
        pass
