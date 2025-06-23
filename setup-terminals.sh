#!/bin/bash

# Quick setup script for agent terminals
# Run this from the biomapper directory

echo "Setting up agent terminals..."

# Create terminal setup command
TERMINAL_CMD="su - ubuntu -c 'cd /home/ubuntu/biomapper && . agent.sh && exec bash'"

# Option 1: Use gnome-terminal if available (for Ubuntu desktop)
if command -v gnome-terminal &> /dev/null; then
    echo "Opening terminals with gnome-terminal..."
    for i in {1..8}; do
        gnome-terminal --window -- bash -c "$TERMINAL_CMD" &
        sleep 0.5
    done
    echo "8 terminals opened!"

# Option 2: Use tmux if available
elif command -v tmux &> /dev/null; then
    echo "Creating tmux session with 8 panes..."
    
    # Create new tmux session
    tmux new-session -d -s agent-session -c /home/ubuntu/biomapper
    
    # Create 7 more panes (total 8)
    for i in {2..8}; do
        tmux split-window -t agent-session -c /home/ubuntu/biomapper
        tmux select-layout -t agent-session tiled
    done
    
    # Send the command to all panes
    for i in {0..7}; do
        tmux send-keys -t agent-session:0.$i "$TERMINAL_CMD" Enter
    done
    
    # Attach to the session
    echo "Attaching to tmux session..."
    tmux attach-session -t agent-session

# Option 3: Instructions for VS Code
else
    echo ""
    echo "Automated terminal opening not available."
    echo ""
    echo "For VS Code/Windsurf:"
    echo "1. Use Ctrl+Shift+P (or Cmd+Shift+P on macOS)"
    echo "2. Type 'Tasks: Run Task'"
    echo "3. Select 'Open 8 Agent Terminals'"
    echo ""
    echo "Or manually:"
    echo "1. Open 8 terminals (Ctrl+Shift+` or from Terminal menu)"
    echo "2. In each terminal, run:"
    echo "   $TERMINAL_CMD"
    echo ""
    echo "Tip: The command has been copied to your clipboard (if supported)"
    
    # Try to copy to clipboard
    if command -v xclip &> /dev/null; then
        echo "$TERMINAL_CMD" | xclip -selection clipboard
    elif command -v pbcopy &> /dev/null; then
        echo "$TERMINAL_CMD" | pbcopy
    fi
fi