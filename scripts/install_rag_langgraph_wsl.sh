#!/usr/bin/env bash
# ==============================================================================
# install_rag_langgraph_wsl.sh
# Installs LangGraph, RAG, and Vector dependencies in WSL2 (Ubuntu).
# Ensures WSL2 uses native Linux binaries (NVM Node + native Linux Python).
# ==============================================================================

set -e

echo "=== [WSL2] Installing Native LangGraph & RAG Packages ==="

# 1. NVM / Node.js
if [ -d "$HOME/.nvm" ]; then
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
fi

if command -v node >/dev/null 2>&1; then
    echo "Node.js detected: $(node -v)"
    echo "Installing global NPM LangGraph & RAG packages..."
    npm install -g \
        @langchain/langgraph \
        @langchain/core \
        @langchain/community \
        @langchain/ollama \
        @langchain/openai \
        chromadb \
        vectordb || true
else
    echo "Node.js not detected in Linux PATH. Install via NVM first."
fi

# 2. Python Linux packages
if command -v python3 >/dev/null 2>&1; then
    echo "Python detected: $(python3 --version)"
    echo "Installing Python LangGraph, LangChain, RAG packages..."
    python3 -m pip install --quiet --upgrade \
        langgraph \
        langchain \
        langchain-core \
        langchain-community \
        langchain-ollama \
        langchain-openai \
        chromadb \
        sentence-transformers \
        faiss-cpu || true
fi

echo "=== [WSL2] LangGraph & RAG Installation Finished ==="
