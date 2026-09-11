<#
.SYNOPSIS
    Installs LangGraph, RAG, Vector Search, and Node-RED AI nodes for Windows & EV_Node runtime.
.DESCRIPTION
    Installs both npm (JavaScript/TypeScript + Node-RED) and pip (Python LangGraph engine)
    dependencies required by the EV Ecosystem on PC5000:
    - Node runtime: C:\EV_Node or global Node v24.18.0
    - Python runtime: Python 3.10+ in GEMBotSys / EV_Core virtual environment
#>

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EV STACK: RAG & LANGGRAPH RUNTIME INSTALLER            " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. VERIFY NODE & NPM
Write-Host "`n[1] Checking Node & NPM Environment..." -ForegroundColor Yellow
$nodeVersion = node -v 2>$null
$npmVersion = npm -v 2>$null
Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green
Write-Host "  NPM:     $npmVersion" -ForegroundColor Green

# 2. NPM PACKAGES (LangGraph JS, LangChain, RAG, Vectors, Node-RED AI)
Write-Host "`n[2] Installing NPM LangGraph, RAG & Vector Packages..." -ForegroundColor Yellow
$npmPackages = @(
    "@langchain/langgraph",
    "@langchain/core",
    "@langchain/community",
    "@langchain/ollama",
    "@langchain/openai",
    "chromadb",
    "@pinecone-database/pinecone",
    "faiss-node",
    "hnswlib-node",
    "vectordb"
)

foreach ($pkg in $npmPackages) {
    Write-Host "  Installing npm: $pkg..." -ForegroundColor Cyan
    npm install -g $pkg --prefer-online 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] $pkg" -ForegroundColor Green
    } else {
        Write-Host "    [WARN] Failed or already installed: $pkg" -ForegroundColor DarkYellow
    }
}

# 3. NODE-RED RAG & AI NODES (For Node-RED broker at C:\EV_AI / Port 1880)
Write-Host "`n[3] Checking Node-RED Global / User Directory for AI Nodes..." -ForegroundColor Yellow
$nodeRedUserDir = "$env:USERPROFILE\.node-red"
if (Test-Path "C:\EV_AI\node-red") {
    $nodeRedUserDir = "C:\EV_AI\node-red"
}

if (-not (Test-Path $nodeRedUserDir)) {
    New-Item -ItemType Directory -Path $nodeRedUserDir -Force | Out-Null
}

$nodeRedAiNodes = @(
    "node-red-contrib-langchain",
    "node-red-contrib-ollama",
    "node-red-contrib-openai",
    "node-red-contrib-vector-database"
)

Push-Location $nodeRedUserDir
foreach ($node in $nodeRedAiNodes) {
    Write-Host "  Installing Node-RED node in $nodeRedUserDir: $node..." -ForegroundColor Cyan
    npm install $node --save 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] $node" -ForegroundColor Green
    } else {
        Write-Host "    [WARN] Notice for $node (Verify if package exists in registry)" -ForegroundColor DarkYellow
    }
}
Pop-Location

# 4. PYTHON PACKAGES (LangGraph Core, RAG, Embeddings, SQLite/Chroma Vector)
Write-Host "`n[4] Installing Python LangGraph & RAG Packages..." -ForegroundColor Yellow
$pipPackages = @(
    "langgraph",
    "langchain",
    "langchain-core",
    "langchain-community",
    "langchain-ollama",
    "langchain-openai",
    "chromadb",
    "sentence-transformers",
    "faiss-cpu",
    "scikit-learn"
)

foreach ($p in $pipPackages) {
    Write-Host "  Installing pip package: $p..." -ForegroundColor Cyan
    python -m pip install --quiet --upgrade $p 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] $p" -ForegroundColor Green
    } else {
        Write-Host "    [WARN] Pip install returned exit code $LASTEXITCODE for $p" -ForegroundColor DarkYellow
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "   RAG & LangGraph Installation Completed!                " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
