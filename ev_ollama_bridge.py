import requests

def list_ollama_models(base_url="http://localhost:11434"):
    """Fetch all installed models in local Ollama."""
    try:
        res = requests.get(f"{base_url}/api/tags", timeout=3)
        if res.status_code == 200:
            return [m.get("name") for m in res.json().get("models", [])]
    except Exception:
        pass
    return []

def query_ollama(prompt, model=None, base_url="http://localhost:11434"):
    """Query local Ollama using an auto-detected or specified model (defaulting to lightweight Qwen)."""
    if model is None:
        installed = list_ollama_models(base_url)
        # Prefer available lightweight models over heavy 30B
        candidates = ["qwen2.5:3b", "qwen3:4b", "phi4-mini:3.8b", "llama3:latest", "llama3"]
        for cand in candidates:
            if cand in installed:
                model = cand
                break
        if model is None:
            model = installed[0] if installed else "qwen2.5:3b"

    url = f"{base_url}/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(url, json=data, timeout=30)
        return response.json().get("response", "[No Response]")
    except Exception as e:
        return f"[Error querying {model}: {e}]"

# Example test
if __name__ == "__main__":
    models = list_ollama_models()
    print("📋 Installed Ollama models:", models)
    if models:
        result = query_ollama("What minerals are associated with pegmatites?")
        print("🧠 Ollama says:", result)
    else:
        print("⚪ No models currently installed or Ollama is not running.")
