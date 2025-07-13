# spec2test/utils/call_llm.py

import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# You can switch between 'azure' and 'ollama' here
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "azure")

# --- Setup Logging ---
log_directory = os.getenv("LOG_DIR", "logs")
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(log_directory, f"llm_calls_{datetime.now().strftime('%Y%m%d')}.log")

logger = logging.getLogger("llm_logger")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

# --- Caching ---
cache_file = "llm_cache.json"

def _load_cache():
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Failed to load or parse cache file, starting with empty cache.")
    return {}

def _save_cache(cache):
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.warning(f"Failed to save cache: {e}")

def _call_azure_openai(prompt: str, max_tokens: int) -> str:
    from openai import AzureOpenAI

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

    if not all([endpoint, api_key, deployment]):
        raise ValueError("Azure OpenAI environment variables not set. Please check your .env file.")

    client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=endpoint
    )
    
    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        timeout=120.0
    )
    return response.choices[0].message.content.strip()

def _call_ollama(prompt: str, max_tokens: int) -> str:
    import requests
    
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

    payload = {
        "model": ollama_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
             "num_ctx": max_tokens  # Not all models respect this, but it's a hint
        }
    }
    
    response = requests.post(ollama_url, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()['message']['content'].strip()

def call_llm(prompt: str, use_cache: bool = True, max_tokens: int = 4096) -> str:
    """
    Calls the configured LLM provider (Azure or Ollama) with the given prompt.
    """
    logger.info(f"PROMPT (first 100 chars): {prompt[:100]}...")
    cache = _load_cache()

    if use_cache and prompt in cache:
        logger.info("RESPONSE (from cache)")
        return cache[prompt]

    try:
        if LLM_PROVIDER == "azure":
            response_text = _call_azure_openai(prompt, max_tokens)
        elif LLM_PROVIDER == "ollama":
            response_text = _call_ollama(prompt, max_tokens)
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise

    logger.info(f"RESPONSE (first 100 chars): {response_text[:100]}...")
    if use_cache:
        cache[prompt] = response_text
        _save_cache(cache)

    return response_text

if __name__ == "__main__":
    try:
        test_prompt = "Explain the concept of a state machine in one sentence."
        print(f"Testing LLM call with provider: {LLM_PROVIDER}")
        print(f"Prompt: {test_prompt}")
        response = call_llm(test_prompt, use_cache=False)
        print(f"Response: {response}")
        print("\nLLM utility seems to be working.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please check your .env configuration and ensure the AI service (Azure/Ollama) is running and accessible.")