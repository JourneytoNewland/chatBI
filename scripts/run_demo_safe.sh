#!/bin/bash

# Configuration
VENV_DIR=".venv"
PORT=8000
MAIN_SCRIPT="scripts/run_demo_server.py"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting ChatBI Demo Server Safe Mode...${NC}"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 could not be found.${NC}"
    exit 1
fi

# 2. Check Virtual Environment
if [ -d "$VENV_DIR" ]; then
    echo -e "${GREEN}✅ Found virtual environment: $VENV_DIR${NC}"
    source "$VENV_DIR/bin/activate"
else
    echo -e "${YELLOW}⚠️  Warning: Virtual environment not found at $VENV_DIR.${NC}"
    echo -e "Attempting to create one..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    echo -e "${GREEN}✅ Virtual environment created and activated.${NC}"
    
    echo -e "📦 Installing dependencies..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        echo -e "${YELLOW}⚠️  No requirements.txt found. Installing basic dependencies manually...${NC}"
        pip install fastapi uvicorn pydantic python-dotenv qdrant-client neo4j zhipuai
    fi
fi

# 3. Check & Release Port
echo -e "🔍 Checking port $PORT..."
PID=$(lsof -ti :$PORT)
if [ ! -z "$PID" ]; then
    echo -e "${YELLOW}⚠️  Port $PORT is in use by PID $PID. Killing it...${NC}"
    kill -9 $PID
    sleep 1
    echo -e "${GREEN}✅ Port $PORT released.${NC}"
else
    echo -e "${GREEN}✅ Port $PORT is free.${NC}"
fi

# 4. Start Server
echo -e "${GREEN}🔥 Starting server...${NC}"
export PYTHONPATH=$PYTHONPATH:.
python3 "$MAIN_SCRIPT"
