"""NVIDIA API-powered Word document generation harness."""

from legal_doc_agent.agents import NvidiaAgentRouter
from legal_doc_agent.config import NvidiaConfig
from legal_doc_agent.harness import LegalDocumentAgent

__all__ = ["LegalDocumentAgent", "NvidiaAgentRouter", "NvidiaConfig"]
