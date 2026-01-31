#!/bin/bash
#
# Marketing Agent v2 - Development Startup Script
# Run this script to start both frontend and backend
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Marketing Agent v2 - Development Startup ===${NC}\n"

# Check if we're in the right directory
if [ ! -f "frontend/package.json" ] || [ ! -f "backend/requirements.txt" ]; then
    echo -e "${RED}Error: Run this script from the project root directory${NC}"
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is required but not installed${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Setting up Python virtual environment...${NC}"
if [ ! -d "backend/venv" ]; then
    cd backend
    python3 -m venv venv
    cd ..
fi
source backend/venv/bin/activate

echo -e "${YELLOW}Step 2: Installing Python dependencies...${NC}"
cd backend
pip install --upgrade pip
pip install -r requirements.txt
cd ..

echo -e "${YELLOW}Step 3: Installing Node.js dependencies...${NC}"
cd frontend
npm install
cd ..

echo -e "${YELLOW}Step 4: Starting services...${NC}"

# Create a function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}Starting backend (FastAPI) on port 8000...${NC}"
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo -e "${GREEN}Starting frontend (Vite) on port 3000...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n${GREEN}=== Services Started ===${NC}"
echo -e "Frontend: http://localhost:3000"
echo -e "Backend:  http://localhost:8000"
echo -e "API Docs: http://localhost:8000/docs"
echo -e "Health:   http://localhost:8000/health"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for both processes
wait
