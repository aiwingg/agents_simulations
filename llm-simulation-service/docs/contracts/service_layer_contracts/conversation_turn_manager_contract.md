# ConversationTurnManager Contract

Handles single turn execution and continuation decisions.

## Constructor
`ConversationTurnManager(logger: SimulationLogger)`

## Public Methods
- `async execute_turn(swarm: Swarm, user_message: str, target_agent: str, context: ConversationContext) -> TurnResult`
- `async generate_user_response(user_agent: AssistantAgent, agent_message: TextMessage) -> str`
