# ConversationLoopOrchestrator Contract

Manages overall conversation loops and timeout checks.

## Constructor
`ConversationLoopOrchestrator(turn_manager: ConversationTurnManager, logger: SimulationLogger)`

## Public Methods
- `async run_conversation_loop(swarm: Swarm, user_agent: AssistantAgent, initial_message: str, context: ConversationContext) -> ConversationContext`
