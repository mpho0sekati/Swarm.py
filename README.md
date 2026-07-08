# 🌑 DARK SWARM: Autonomous Hive Intelligence

A multi-agent orchestration platform designed for recursive swarm operations with real-time visualization and stealth privacy protocols.

## 🚀 Features
- **FastAPI Backend:** High-performance async orchestration.
- **Live Hive Feed:** HTML5 Canvas visualization of agent activity.
- **Sub-Swarm Tool:** Agents can spawn secondary swarms for complex task delegation.
- **Stealth Mode:** Injects privacy protocols to prevent data leakage to LLM providers.
- **One-Click Persistence:** Export your swarm factory to GitHub and deploy to Render for 24/7 operation.

## 🛠 Setup & Local Running
1. **Clone the repository.**
2. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```
3. **Run the server:**
   ```bash
   uvicorn backend.main:app --reload
   ```
4. **Access the UI:** Open `http://localhost:8000` in your browser.

## 📦 Persistence & Render Deployment
To keep your agents running indefinitely:
1. Generate a [GitHub Personal Access Token (PAT)](https://github.com/settings/tokens) with `repo` scope.
2. Enter your PAT and desired repository name in the **Deploy & Persist** section of the UI.
3. Click **PUSH TO GITHUB**.
4. Log into [Render.com](https://render.com).
5. Create a new **Web Service** and connect the newly created GitHub repository.
6. Render will automatically detect the `render.yaml` and deploy your Dark Swarm Factory.

## 🔒 Security & Privacy
The **Stealth Mode** toggle ensures that agents follow strict protocols to scrub PII and proprietary logic from their thought processes, minimizing the footprint shared with LLM providers like Groq, OpenAI, or Anthropic.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)
