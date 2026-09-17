"""Common generic tools registry for LangGraph persona agents."""

from typing import List

from langchain_core.tools import BaseTool

from app.domain.memory.debate_memory_tool import search_debate_memory
from app.domain.memory.my_library_tool import search_my_library
from app.domain.memory.rag_tool import search_scrap_memory
from app.domain.tools.search_books_tool import search_recent_books

# Universal tools accessible to librarian and debate persona agents
GENERIC_TOOLS: List[BaseTool] = [
    search_scrap_memory,
    search_debate_memory,
    search_recent_books,
    search_my_library,
]

__all__ = [
    "GENERIC_TOOLS",
    "search_scrap_memory",
    "search_debate_memory",
    "search_recent_books",
    "search_my_library",
]
