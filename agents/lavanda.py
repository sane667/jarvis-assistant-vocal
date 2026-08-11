"""Lavanda placeholder: web-research agent contract.

The manager and tool contract are ready; the web connector is intentionally
kept out of the first autonomous loop until its browser/search capabilities are
wired and tested.
"""
from core.agent_manager import AgentTask


def run(task: AgentTask):
    return "Lavanda n'est pas encore branchée au moteur web. La tâche est restée sans action."


def register(manager):
    manager.register("lavanda", run)
