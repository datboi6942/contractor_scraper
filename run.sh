#!/bin/bash

# Contractor Data Scraper - Startup Script
# Backend: http://localhost:8002
# Frontend: http://localhost:6731

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  Contractor Data Scraper${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3 first.${NC}"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is not installed. Please install Node.js first.${NC}"
    exit 1
fi

# Setup Backend
echo -e "${YELLOW}Setting up backend...${NC}"
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install --quiet --disable-pip-version-check -r requirements.txt

echo -e "${GREEN}Backend dependencies installed.${NC}"

# Start backend server in background
echo -e "${YELLOW}Starting backend server on port 8002...${NC}"
python main.py &
BACKEND_PID=$!

cd ..

# Setup Frontend
echo -e "${YELLOW}Setting up frontend...${NC}"
cd frontend

# Install npm dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo -e "${GREEN}Frontend dependencies installed.${NC}"

# Start frontend server
echo -e "${YELLOW}Starting frontend server on port 6731...${NC}"
npm run dev &
FRONTEND_PID=$!

cd ..

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  Servers are running!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo -e "  Backend API:  ${YELLOW}http://localhost:8002${NC}"
echo -e "  Frontend UI:  ${YELLOW}http://localhost:6731${NC}"
echo ""
echo -e "  Press ${RED}Ctrl+C${NC} to stop all servers."
echo ""

# Wait for both processes
wait
