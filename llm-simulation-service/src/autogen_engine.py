"""AutoGen-based conversation engine"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

from src.prompt_specification import PromptSpecificationManager
from src.config import Config

class AutoGenConversationEngine:
    """Conversation engine utilizing AutoGen group chat"""

    def __init__(self, prompt_spec_name: str = "default_prompts") -> None:
        self.prompt_manager = PromptSpecificationManager()
        self.prompt_specification = self.prompt_manager.load_specification(prompt_spec_name)
        self.llm_config = {
            "config_list": [{
                "model": Config.OPENAI_MODEL,
                "api_key": Config.OPENAI_API_KEY,
            }]
        }

    def _format_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """Basic variable substitution using Python format syntax"""
        try:
            return template.format(**variables)
        except Exception:
            return template

    def _create_agents(self, variables: Dict[str, Any]) -> List[AssistantAgent]:
        agents = []
        for name, spec in self.prompt_specification.agents.items():
            system_prompt = self._format_prompt(spec.prompt, variables)
            agents.append(
                AssistantAgent(
                    name=name,
                    system_message=system_prompt,
                    llm_config=self.llm_config,
                )
            )
        return agents

    async def run_conversation(self, scenario: Dict[str, Any], max_turns: Optional[int] = None,
                               timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        max_turns = max_turns or Config.MAX_TURNS
        variables = scenario.get("variables", {})
        session_id = str(uuid.uuid4())
        agents = self._create_agents(variables)

        groupchat = GroupChat(agents=agents, messages=[], max_round=max_turns)
        manager = GroupChatManager(groupchat=groupchat, llm_config=self.llm_config)
        user_proxy = UserProxyAgent("user_proxy")
        manager.register_reply([user_proxy])

        start_message = variables.get("start_message", "Начало разговора")
        start_time = datetime.now()
        await asyncio.to_thread(manager.run, {"user_input": start_message})
        end_time = datetime.now()

        history = []
        turn = 1
        for msg in groupchat.messages:
            if msg.get("role") in ["assistant", "user"]:
                speaker = msg.get("name") or msg.get("role")
                history.append({
                    "turn": turn,
                    "speaker": speaker,
                    "content": msg.get("content", ""),
                    "timestamp": datetime.now().isoformat(),
                })
                turn += 1

        return {
            "session_id": session_id,
            "scenario": scenario.get("name", "unknown"),
            "status": "completed",
            "total_turns": len(history),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "conversation_history": history,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
