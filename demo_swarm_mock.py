import os
import sys
import sqlite3
from datetime import datetime
from ant_safe_swarm import PheromoneMemory, SwarmBrain

def run_manual_mock_demo():
    print("[Init] Initializing Ant-Safe Swarm Manual Mock Demo...")

    # 1. Initialize Memory
    memory = PheromoneMemory(db_path="pheromones.db")
    brain = SwarmBrain(filepath="swarm_brain.md")

    prompts = [
        "Build a simple user registration API.",
        "Implement AES encryption for user passwords.",
        "Optimize database queries for high traffic."
    ]

    mock_results = {
        "Architect": "System architecture designed with scalability in mind.",
        "Coder": "def register_user(): pass # Implementation complete",
        "Safety Officer": "Safety audit passed. No PII or vulnerabilities detected."
    }

    for prompt in prompts:
        print(f"\n--- Simulating Task: {prompt} ---")

        # Simulate Pheromone Deposits
        task_type = "coding_task"
        for role in ["Architect", "Coder", "Safety Officer"]:
            print(f"[Task] {role} completed task. Depositing pheromone...")
            memory.deposit_pheromone(task_type, role, 0.5)

        # Simulate Brain Recording
        results_str = "\n".join([f"{k}: {v}" for k, v in mock_results.items()])
        brain.record_success(prompt, results_str)

        # Simulate Evaporation
        memory.evaporate()

        # Check for high pheromone logic trigger
        if memory.get_pheromone(task_type, "Architect") > 2.0:
            print("[Evolution] High Pheromone detected! Swarm intelligence evolving...")

    print("\n[Done] Manual Mock Demo Complete!")
    print("-" * 30)

    # Show Brain Status
    print("\n[Brain] Swarm Brain (Long-Term Memory) Updated:")
    with open("swarm_brain.md", "r") as f:
        print(f.read())

    # Show Pheromone Status
    print("\n[Pheromone] Pheromone (Short-Term Memory) Status:")
    conn = sqlite3.connect("pheromones.db")
    cursor = conn.execute("SELECT role, level FROM pheromones ORDER BY level DESC")
    for row in cursor:
        print(f"Role: {row[0]:<15} | Pheromone Level: {row[1]:.2f}")
    conn.close()

if __name__ == "__main__":
    # Clean previous demo runs
    if os.path.exists("pheromones.db"): os.remove("pheromones.db")
    if os.path.exists("swarm_brain.md"): os.remove("swarm_brain.md")

    run_manual_mock_demo()
