"""
Claude Integration module for providing MCP tools for Home Assistant.
"""

from src.claude_integration.mcp import HomeAssistantMCP
from src.claude_integration.tools import register_tools
from src.claude_integration.automation_tools import AutomationTools

__all__ = ['HomeAssistantMCP', 'register_tools', 'AutomationTools']