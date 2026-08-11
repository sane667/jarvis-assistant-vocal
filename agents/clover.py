"""Clover placeholder: local files/document agent contract."""
from core.agent_manager import AgentTask


def run(task: AgentTask):
    return "Clover n'est pas encore branchée au moteur fichiers/bureautique. La tâche est restée sans action."


def register(manager):
    manager.register("clover", run)
