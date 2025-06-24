#!/bin/bash
# Script to create git worktree branches for fixing test failures

# Ensure we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Get the current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"

# Create a base directory for worktrees
WORKTREE_BASE="worktrees"
mkdir -p "$WORKTREE_BASE"

# Define branches and their purposes
declare -A BRANCHES=(
    ["fix-yaml-strategy"]="Fix YAML strategy tests"
    ["fix-mapping-executor"]="Fix mapping executor tests"
    ["fix-session-manager"]="Fix session manager tests"
    ["fix-path-finder"]="Fix path finder tests"
    ["fix-mapping-services"]="Fix mapping service tests"
    ["fix-integration-tests"]="Fix integration tests"
    ["fix-metadata-tests"]="Fix metadata tests"
    ["fix-client-tests"]="Fix client tests"
)

echo "Setting up git worktree branches for test fixes..."
echo "============================================="

for BRANCH in "${!BRANCHES[@]}"; do
    WORKTREE_PATH="$WORKTREE_BASE/$BRANCH"
    DESCRIPTION="${BRANCHES[$BRANCH]}"
    
    echo -e "\nBranch: $BRANCH"
    echo "Purpose: $DESCRIPTION"
    echo "Worktree path: $WORKTREE_PATH"
    
    # Check if branch already exists
    if git show-ref --verify --quiet refs/heads/$BRANCH; then
        echo "  Branch already exists, checking worktree..."
        
        # Check if worktree already exists
        if git worktree list | grep -q "$WORKTREE_PATH"; then
            echo "  Worktree already exists at $WORKTREE_PATH"
        else
            echo "  Creating worktree for existing branch..."
            git worktree add "$WORKTREE_PATH" "$BRANCH"
        fi
    else
        echo "  Creating new branch and worktree..."
        git worktree add -b "$BRANCH" "$WORKTREE_PATH" "$CURRENT_BRANCH"
    fi
done

echo -e "\n============================================="
echo "Worktree setup complete!"
echo ""
echo "To work on a specific test module:"
echo "  cd worktrees/<branch-name>"
echo "  # Make your fixes"
echo "  git add ."
echo "  git commit -m 'Fix: <description>'"
echo ""
echo "To remove a worktree when done:"
echo "  git worktree remove worktrees/<branch-name>"
echo ""
echo "Current worktrees:"
git worktree list