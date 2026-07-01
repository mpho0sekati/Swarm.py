#!/bin/bash

# Ant-Safe Swarm Setup Script
# Author: Jules (AI)

set -e

echo "🐜 Initializing Ant-Safe Swarm Environment..."

# 1. Check Python version
if ! command -v python3 &> /dev/null
then
    echo "❌ Error: python3 could not be found. Please install Python 3.10+."
    exit 1
fi

# 2. Install dependencies
echo "📦 Installing required packages..."
pip install streamlit crewai crewai_tools groq litellm gradio sqlite3-binary 2>/dev/null || pip install streamlit crewai crewai_tools groq litellm gradio

# 3. Create initial data files if they don't exist
touch swarm_brain.md
echo "🧠 Memory files initialized."

echo ""
echo "✅ Setup Complete!"
echo "--------------------------------------------------"
echo "🚀 To get started, you can run:"
echo ""
echo "1. The Mock Demo (No API Key):"
echo "   python demo_swarm_mock.py"
echo ""
echo "2. The Web UI (Requires GROQ_API_KEY):"
echo "   python ant_safe_swarm.py --ui"
echo ""
echo "3. The Project Factory:"
echo "   streamlit run Main.py"
echo "--------------------------------------------------"
