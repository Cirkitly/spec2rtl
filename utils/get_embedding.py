import os
import requests
import logging
import json

logger = logging.getLogger("llm_logger")

def get_embedding(text: str, model: str = None) -> list[float]:
    """
    Generates an embedding for the given text using the Ollama API.
    """
    if model is None:
        model = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")
    
    try:
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": model,
                "prompt": text,
            },
            timeout=30.0 # Add a timeout
        )
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to Ollama for embedding: {e}")
        raise ConnectionError(f"Could not connect to Ollama for embedding. Is it running? Error: {e}")
    
    data = response.json()
    embedding = data.get("embedding")

    if not embedding:
        raise ValueError("API response did not contain an embedding.")
        
    logger.info(f"Successfully generated embedding for text: '{text[:50]}...'")
    return embedding

if __name__ == "__main__":
    try:
        print("Fetching embedding for 'Hello, world!'...")
        embedding_vector = get_embedding("Hello, world!")
        print(f"Successfully got a vector of dimension: {len(embedding_vector)}")
        print(f"First 5 values: {embedding_vector[:5]}")
        print("\nEmbedding utility seems to be working.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure Ollama is running and you have pulled the embedding model with 'ollama pull mxbai-embed-large'.")