import os

from dotenv import load_dotenv

import litellm


def call_llm(prompt: str, model: str | None = None) -> str:
    """
    Call LLM with a prompt and return the response.
    
    Uses LiteLLM to support multiple providers via LITELLM_MODEL environment variable.
    If model is provided, it overrides the default from environment.
    
    Args:
        prompt: The prompt to send to the LLM
        model: Optional model name to use (overrides LITELLM_MODEL env var)
    
    ============================================================================
    HOW TO SWITCH BETWEEN MODELS:
    ============================================================================
    
    Set LITELLM_MODEL in your .env file to one of the following:
    
    AZURE OPENAI (requires AZURE_API_KEY, AZURE_API_BASE, AZURE_DEPLOYMENT_NAME):
        LITELLM_MODEL=azure/<your-deployment-name>
        Example: LITELLM_MODEL=azure/gpt-4o
    
    OPENAI (requires OPENAI_API_KEY):
        LITELLM_MODEL=gpt-4o
        LITELLM_MODEL=gpt-4-turbo
        LITELLM_MODEL=gpt-4o-mini
        LITELLM_MODEL=o1-preview
    
    ANTHROPIC/CLAUDE (requires ANTHROPIC_API_KEY):
        LITELLM_MODEL=claude-sonnet-4-20250514
        LITELLM_MODEL=claude-3-5-sonnet-20241022
        LITELLM_MODEL=claude-3-opus-20240229
        LITELLM_MODEL=claude-3-haiku-20240307
    
    GEMINI (requires GEMINI_API_KEY or GEMINI_TOKEN):
        LITELLM_MODEL=gemini/gemini-2.0-flash
        LITELLM_MODEL=gemini/gemini-1.5-pro
        LITELLM_MODEL=gemini/gemini-1.5-flash
        LITELLM_MODEL=gemini/gemini-3.0-flash
    
    ============================================================================
    """
    load_dotenv()
    
    # Use provided model or fall back to environment variable
    if model is None:
        model = os.environ.get("LITELLM_MODEL", "").strip()
        if not model:
            raise ValueError("LITELLM_MODEL environment variable is not set")
    
    # Map GEMINI_TOKEN to GEMINI_API_KEY if needed (for backwards compatibility)
    gemini_token = os.environ.get("GEMINI_TOKEN", "").strip()
    if gemini_token and not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = gemini_token
    
    # For Azure, construct the full base URL if only resource name is provided
    azure_base = os.environ.get("AZURE_API_BASE", "").strip()
    if azure_base and not azure_base.startswith("http"):
        os.environ["AZURE_API_BASE"] = f"https://{azure_base}.openai.azure.com"
    
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content or ""


if __name__ == "__main__":
    prompt = "Say hello in one word."
    print(f"prompt: {prompt}")
    print(f"response: {call_llm(prompt)}")
