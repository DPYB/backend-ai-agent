"""LangGraph workflow definition for 8-Persona StateGraph with dynamic routing."""

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.domain.graph.nodes import (
    cat_node,
    debate_counselor_node,
    debate_critic_node,
    debate_observer_node,
    debate_storyteller_node,
    gecko_node,
    sea_slug_node,
    shoebill_node,
    summarizer_node,
)
from app.domain.graph.state import AgentState
from app.domain.graph.tools import GENERIC_TOOLS

logger = logging.getLogger(__name__)

# Mapping from persona ID to graph node name
PERSONA_NODE_MAP = {
    # Core API aligned IDs
    "CAT": "cat_node",
    "SHOEBILL": "shoebill_node",
    "SEA_SLUG": "sea_slug_node",
    "GECKO": "gecko_node",
    # Backward compatibility aliases
    "BLUE": "cat_node",
    "RUSSIAN_BLUE": "cat_node",
    "LIBRARIAN_3": "sea_slug_node",
    "LIBRARIAN_4": "gecko_node",
    # Debate IDs
    "DEBATE_CRITIC": "debate_critic_node",
    "DEBATE_STORYTELLER": "debate_storyteller_node",
    "DEBATE_COUNSELOR": "debate_counselor_node",
    "DEBATE_OBSERVER": "debate_observer_node",
}

ALL_PERSONA_NODES = {
    "cat_node": cat_node,
    "shoebill_node": shoebill_node,
    "sea_slug_node": sea_slug_node,
    "gecko_node": gecko_node,
    "debate_critic_node": debate_critic_node,
    "debate_storyteller_node": debate_storyteller_node,
    "debate_counselor_node": debate_counselor_node,
    "debate_observer_node": debate_observer_node,
}


def _get_node_for_persona(persona_id: str) -> str:
    """Return corresponding graph node name for a persona ID."""
    return PERSONA_NODE_MAP.get(persona_id, "cat_node")


def route_entry(state: AgentState) -> str:
    """Route initial execution to the active persona node among the 8 personas."""
    active = state.get("active_persona", "CAT")
    return _get_node_for_persona(active)


def route_persona_exit(state: AgentState) -> str:
    """Route from persona node to summarizer (handoff), tool_node, or END."""
    # 1. Handoff takes priority if switch is triggered
    if state.get("handoff_target"):
        logger.info("Routing to summarizer_node for persona handoff.")
        return "summarizer_node"

    # 2. Check for tool calls
    messages = state.get("messages", [])
    if messages and hasattr(messages[-1], "tool_calls") and messages[-1].tool_calls:
        logger.info("Routing to tool_node for tool execution.")
        return "tool_node"

    # 3. Otherwise conversation turn finishes
    return END


def route_from_tools(state: AgentState) -> str:
    """Return from tool execution back to the active persona node."""
    active = state.get("active_persona", "CAT")
    return _get_node_for_persona(active)


def route_from_summarizer(state: AgentState) -> str:
    """Route from summarizer to the newly activated target persona node."""
    active = state.get("active_persona", "CAT")
    return _get_node_for_persona(active)


def create_agent_graph():
    """Build and compile the 8-Persona LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # 1. Register all 8 Persona nodes
    for node_name, node_func in ALL_PERSONA_NODES.items():
        workflow.add_node(node_name, node_func)

    # 2. Register common nodes
    workflow.add_node("summarizer_node", summarizer_node)
    workflow.add_node("tool_node", ToolNode(GENERIC_TOOLS))

    # 3. Dynamic entry point routing to any of the 8 personas
    workflow.add_conditional_edges(
        START,
        route_entry,
        {node_name: node_name for node_name in ALL_PERSONA_NODES.keys()},
    )

    # 4. Conditional edges out of every persona node
    for node_name in ALL_PERSONA_NODES.keys():
        workflow.add_conditional_edges(
            node_name,
            route_persona_exit,
            {
                "summarizer_node": "summarizer_node",
                "tool_node": "tool_node",
                END: END,
            },
        )

    # 5. Route back from tool execution to the calling persona
    workflow.add_conditional_edges(
        "tool_node",
        route_from_tools,
        {node_name: node_name for node_name in ALL_PERSONA_NODES.keys()},
    )

    # 6. Route from summarizer to newly activated persona node
    workflow.add_conditional_edges(
        "summarizer_node",
        route_from_summarizer,
        {node_name: node_name for node_name in ALL_PERSONA_NODES.keys()},
    )

    return workflow.compile()
