import asyncio
from llama_cpp import Llama
from typing import AsyncGenerator

# Using a generic class to encapsulate the synchronous LLM call into async tasks
class LlamaService:
    def __init__(self, model_path: str = "model.gguf"):
        self.model_path = model_path
        self._llm = None
        self._lock = asyncio.Lock()
        
    def _get_llm(self):
        if not self._llm:
            try:
                # We attempt to load the model. If it's missing, it will raise an exception
                self._llm = Llama(
                    model_path=self.model_path,
                    n_ctx=2048,
                    n_threads=4,
                    verbose=False
                )
            except Exception as e:
                print(f"Error loading model: {e}")
                # We do not crash the app, but returning None means LLM is unavailable
        return self._llm

    async def stream_chat(self, history: list[dict], new_prompt: str) -> AsyncGenerator[str, None]:
        """
        Takes a history list like [{"role": "user", "content": "..."}, {"role": "assistant", ...}]
        and returns a streaming async generator.
        """
        
        # We need a lock so multiple concurrent requests don't crash llama-cpp-python
        async with self._lock:
            llm = self._get_llm()
            if not llm:
                yield "I'm sorry, my model file seems to be missing. Please contact the administrator.\n"
                return
                
            # Build the prompt
            prompt = ""
            for msg in history:
                role_str = "User:" if msg["role"] == "user" else "Assistant:"
                prompt += f"{role_str} {msg['content']}\n"
                
            prompt += f"User: {new_prompt}\nAssistant:"
            
            # To run a synchronous generator asynchronously, we could run each step in threadpool, 
            # but since llama_cpp streams nicely, we iterate and yield.
            # However, for true non-blocking we should wrap it. For simplicity we use asyncio.to_thread
            
            def get_stream():
                return llm(
                    prompt,
                    max_tokens=200,
                    stream=True,
                    stop=["User:", "\nUser"]
                )
                
            stream = await asyncio.to_thread(get_stream)
            
            for chunk in stream:
                token = chunk["choices"][0]["text"]
                yield token
                await asyncio.sleep(0) # Yield control back to event loop

llm_service = LlamaService()
