#!/bin/bash

echo "💥 Stopping any running Biomapper servers..."

# Kill any existing Vite servers
echo "🔄 Stopping Vite servers..."
pkill -f "vite" || echo "No Vite processes found"

# Kill any existing FastAPI/Uvicorn servers
echo "🔄 Stopping FastAPI/Uvicorn servers..."
pkill -f "uvicorn" || echo "No FastAPI/Uvicorn processes found"

# Kill any processes on our specific ports
echo "🔄 Stopping any processes on Biomapper ports..."
# Kill API port
pkill -f ":8000" || echo "No process on port 8000"

# Kill ALL UI ports in the 3000-range (3000, 3001, 3002, etc.) using multiple methods
echo "Thoroughly cleaning up ports 3000-3009..."

# First pass: Kill everything we can find on these ports
for port in $(seq 3000 3009); do
  # Find and kill all processes using these ports with different methods
  if lsof -ti:$port > /dev/null 2>&1; then
    echo "Killing process on port $port (lsof method)"
    lsof -ti:$port | xargs kill -9 2>/dev/null
  fi
  
  if ss -tlpn | grep ":$port " > /dev/null 2>&1; then
    echo "Found socket on port $port (ss method)"
    pid=$(ss -tlpn | grep ":$port " | sed -E 's/.*pid=([0-9]+).*/\1/g')
    if [ ! -z "$pid" ]; then
      echo "Killing process $pid on port $port"
      kill -9 $pid 2>/dev/null
    fi
  fi
  
  if netstat -tlpn 2>/dev/null | grep ":$port " > /dev/null 2>&1; then
    echo "Found socket on port $port (netstat method)"
    pid=$(netstat -tlpn 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1)
    if [ ! -z "$pid" ] && [ "$pid" != "-" ]; then
      echo "Killing process $pid on port $port"
      kill -9 $pid 2>/dev/null
    fi
  fi
  
  # Generic checks for any process mentioning the port
  pkill -9 -f ":$port" 2>/dev/null
  pkill -9 -f "port.*$port" 2>/dev/null
  pkill -9 -f "$port.*port" 2>/dev/null
done

# Wait to ensure ports are released
echo "Waiting for TCP sockets to be fully released..."
sleep 5

# Second pass: Verify and attempt again for any stubborn ports
for port in $(seq 3000 3009); do
  # Check if port is still in use
  if ss -tlpn | grep ":$port " > /dev/null 2>&1 || lsof -ti:$port > /dev/null 2>&1; then
    echo "Port $port is still in use! Attempting extreme measures..."
    # Try even more aggressively to kill it
    lsof -ti:$port | xargs kill -9 2>/dev/null
    # Wait a bit longer for this specific port
    sleep 2
  fi
done

echo "✅ All Biomapper servers stopped"
echo

# Start the backend API server
echo "🚀 Starting the Biomapper API server..."
cd /home/ubuntu/biomapper/biomapper-api
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > api.log 2>&1 &
API_PID=$!
echo "✅ API server started on port 8000 (PID: $API_PID)"
echo

# Wait a moment for the API server to start
sleep 2

# Start the frontend Vite server
echo "🚀 Starting the Biomapper UI server..."
cd /home/ubuntu/biomapper/biomapper-ui
# Run the UI server with Node.js v18 and ESM preload for crypto polyfill
NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # Load nvm
nvm use 18 && NODE_OPTIONS="--import ./vite-preload.mjs" npm run dev -- --host 0.0.0.0 > ui.log 2>&1 &
UI_PID=$!
echo "✅ UI server started (PID: $UI_PID)"
echo

echo "🎉 All Biomapper servers are running!"
echo "📝 Logs are available in:"
echo "   - API: /home/ubuntu/biomapper/biomapper-api/api.log"
echo "   - UI: /home/ubuntu/biomapper/biomapper-ui/ui.log"
echo
echo "🌐 Access the application at:"
echo "   - UI: http://localhost:3000"
echo "   - API: http://localhost:8000"
