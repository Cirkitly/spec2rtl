import os

PROMPTS_DIR = "prompts"

def load_prompt(file_path: str) -> str:
    """
    Loads a prompt template from the prompts directory.
    The file_path is relative to the 'prompts/' directory.
    """
    full_path = os.path.join(PROMPTS_DIR, file_path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Prompt template not found at: {full_path}")
    
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
