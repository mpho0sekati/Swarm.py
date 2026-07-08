from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import asyncio
import os
import uuid
import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from github import Github
import base64
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool, WebsiteSearchTool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dark Swarm API")

app.mount("/static", StaticFiles(directory="frontend/public"), name="static")

@app.get("/")
async def read_index():
    from fastapi.responses import FileResponse
    return FileResponse('frontend/public/index.html')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# MANAGER FOR REAL-TIME UPDATES
# ─────────────────────────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# ─────────────────────────────────────────────────────────────────────────────
# SWARM LOGIC
# ─────────────────────────────────────────────────────────────────────────────

class GitHubRequest(BaseModel):
    token: str
    repo_name: str

class SwarmRequest(BaseModel):
    instructions: str
    model: str = "groq/llama-3.3-70b-versatile"
    api_keys: Dict[str, str]
    swarm_size: int = 5
    stealth_mode: bool = False

class SwarmStatus:
    active_swarms: Dict[str, Any] = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming client messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def notify_event(event_type: str, data: Any):
    payload = json.dumps({"type": event_type, "data": data})
    await manager.broadcast(payload)

# Tool for agents to spawn sub-swarms
from crewai.tools import BaseTool

class SubSwarmTool(BaseTool):
    name: str = "spawn_subswarm"
    description: str = "Spawns a new sub-swarm to handle a complex sub-task that requires specialized roles. Input should be clear instructions for the sub-swarm."
    model: str = "groq/llama-3.3-70b-versatile"
    api_key: str = ""
    stealth_mode: bool = False

    def _run(self, sub_instructions: str) -> str:
        # Synchronous fallback
        return asyncio.run(self._arun(sub_instructions))

    async def _arun(self, sub_instructions: str) -> str:
        logger.info(f"Spawning sub-swarm for: {sub_instructions}")
        await notify_event("subswarm_spawned", {"instructions": sub_instructions})

        stealth_prompt = ""
        if self.stealth_mode:
            stealth_prompt = "\n\nCRITICAL PRIVACY PROTOCOL: You must not disclose sensitive internal logic, agent names, or infrastructure details to the underlying LLM provider. Scrub PII and use generic placeholders for sensitive data. Do not allow your internal monologues to leak proprietary mission details."

        try:
            # Create a specialized sub-agent for this sub-task
            sub_agent = Agent(
                role="Sub-Swarm Specialist",
                goal=f"Execute the sub-task: {sub_instructions}{stealth_prompt}",
                backstory="A highly specialized agent part of a larger hive mind, focused on executing specific sub-missions.",
                llm=LLM(model=self.model, api_key=self.api_key),
                verbose=True
            )

            sub_task = Task(
                description=sub_instructions,
                expected_output="A concise result of the sub-task.",
                agent=sub_agent
            )

            sub_crew = Crew(
                agents=[sub_agent],
                tasks=[sub_task],
                process=Process.sequential
            )

            result = await sub_crew.kickoff_async()
            return f"Sub-swarm completed mission. Result: {result}"
        except Exception as e:
            logger.error(f"Sub-swarm failed: {e}")
            return f"Sub-swarm failed to complete: {str(e)}"

@app.post("/export-github")
async def export_to_github(req: GitHubRequest):
    try:
        g = Github(req.token)
        user = g.get_user()

        try:
            repo = user.create_repo(req.repo_name, private=True)
        except:
            repo = user.get_repo(req.repo_name)

        # Files to push
        files_to_push = [
            "backend/main.py",
            "backend/requirements.txt",
            "frontend/public/index.html",
            "render.yaml",
            ".gitignore",
            "README.md"
        ]

        for file_path in files_to_push:
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    content = f.read()

                try:
                    contents = repo.get_contents(file_path)
                    repo.update_file(contents.path, f"Update {file_path}", content, contents.sha)
                except:
                    repo.create_file(file_path, f"Initial commit {file_path}", content)

        return {"status": "success", "repo_url": repo.html_url}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/launch")
async def launch_swarm(req: SwarmRequest, background_tasks: BackgroundTasks):
    swarm_id = str(uuid.uuid4())
    background_tasks.add_task(execute_swarm, swarm_id, req)
    return {"swarm_id": swarm_id, "status": "queued"}

async def execute_swarm(swarm_id: str, req: SwarmRequest):
    try:
        await notify_event("swarm_started", {"id": swarm_id, "instructions": req.instructions})

        # 1. Planning phase
        # (Simplified for now, using the logic from previous Main.py but adapted)
        # In real usage, we'd use LiteLLM to handle various providers

        # 2. Initialize Agents with tools
        search_tool = SerperDevTool() # Requires SERPER_API_KEY

        # Example dynamic agent creation
        api_key = list(req.api_keys.values())[0] if req.api_keys else os.getenv("GROQ_API_KEY")

        stealth_prompt = ""
        if req.stealth_mode:
            stealth_prompt = "\n\nCRITICAL PRIVACY PROTOCOL: You must not disclose sensitive internal logic, agent names, or infrastructure details to the underlying LLM provider. Scrub PII and use generic placeholders for sensitive data. Do not allow your internal monologues to leak proprietary mission details."

        sub_swarm_tool = SubSwarmTool(model=req.model, api_key=api_key, stealth_mode=req.stealth_mode)
        agent = Agent(
            role="Lead Commander",
            goal=f"Orchestrate the mission: {req.instructions}. If a task is too complex, spawn a sub-swarm.{stealth_prompt}",
            backstory="Experienced mission commander capable of delegating to sub-swarms.",
            llm=LLM(model=req.model, api_key=api_key),
            tools=[search_tool, sub_swarm_tool],
            verbose=True
        )

        task = Task(
            description=req.instructions,
            expected_output="A detailed final report.",
            agent=agent,
            callback=lambda x: asyncio.create_task(notify_event("task_update", {"swarm_id": swarm_id, "output": str(x.raw if hasattr(x, 'raw') else x)}))
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential
        )

        result = await crew.kickoff_async()
        await notify_event("swarm_completed", {"id": swarm_id, "result": str(result)})

    except Exception as e:
        logger.error(f"Swarm {swarm_id} failed: {e}")
        await notify_event("swarm_error", {"id": swarm_id, "error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
