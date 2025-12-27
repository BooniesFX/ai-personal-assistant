import asyncio
import logging
from typing import Dict, Any
from .base import AgentAdapter

logger = logging.getLogger("sidecar.cli")

class CLIAdapter(AgentAdapter):
    """
    Adapter that wraps a command-line interface tool.
    It spawns the process and keeps it alive, piping input/output.
    """
    
    def __init__(self, command: str):
        self.command = command
        self.process = None
        self._lock = asyncio.Lock()
        
    async def _ensure_process(self):
        if self.process and self.process.returncode is None:
            return
            
        logger.info(f"Spawning process: {self.command}")
        self.process = await asyncio.create_subprocess_shell(
            self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
    async def process_message(self, content: str, context: Dict[str, Any] = None) -> str:
        async with self._lock:
            await self._ensure_process()
            
            # This is a naive implementation:
            # Write input -> Read output until some delimiter or timeout?
            # Most CLI agents (like 'claude' or REPLs) respond and then wait.
            # But reading valid output from a stream is tricky without a protocol.
            #
            # Hapi solves this by injecting a wrapper or assuming the CLI is "One-Shot" or using PTY.
            #
            # For this MVP, let's assume the tool is "One-Shot" or returns a full response.
            # OR we can assume line-based protocol.
            
            try:
                msg_bytes = f"{content}\n".encode()
                self.process.stdin.write(msg_bytes)
                await self.process.stdin.drain()
                
                # Reading output is the hard part.
                # Idea: Read until silence? Or Read line by line?
                # For `claude` CLI, it might stream.
                
                # Hack for MVP: Read for X seconds or until specific token?
                # Let's try reading a chunk.
                buffer = b""
                try:
                    # Give it time to calculate
                    await asyncio.sleep(2.0)
                    
                    # Read what's available (non-blocking logic simulation)
                    # asyncio.wait_for only works if the stream actually ends, which it won't for REPL.
                    #
                    # Alternative: We just assume the CLI is wrapped by something that closes stdout?
                    # No, we want a persistent session.
                    
                    # Proper way: CLI agents usually print a prompt like "> " when done.
                    # We can read until "> ".
                    
                    buffer = await self.read_until_prompt(self.process.stdout)
                    
                except asyncio.TimeoutError:
                    buffer = b"[Timeout waiting for response]"
                
                return buffer.decode()
                
            except Exception as e:
                logger.error(f"CLI interaction error: {e}")
                return f"Error: {e}"

    async def read_until_prompt(self, stream, timeout=30.0):
        """Read from stream until silence or prompt."""
        # This is tricky. Simplified version:
        # Read lines. If no new line for 1 second, assume done.
        buffer = []
        
        while True:
            try:
                line = await asyncio.wait_for(stream.readline(), timeout=2.0)
                if not line:
                    break
                buffer.append(line)
                # Heuristic: If we see a prompt-like char?
            except asyncio.TimeoutError:
                # 2 seconds of silence -> Assume done for this turn
                break
                
        return b"".join(buffer)

    async def shutdown(self):
        if self.process:
            self.process.terminate()
