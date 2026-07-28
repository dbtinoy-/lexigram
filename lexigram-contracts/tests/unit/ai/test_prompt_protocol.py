"""Tests for Prompt Template contracts."""
from __future__ import annotations


def test_prompt_template():
    """PromptTemplate should format prompts."""
    from lexigram.contracts.ai.prompt import PromptTemplate
    
    template = PromptTemplate(template="Hello {name}, your order is {order_id}")
    prompt = template.format(name="Alice", order_id="12345")
    assert "Alice" in prompt
    assert "12345" in prompt


def test_chat_prompt_template():
    """ChatPromptTemplate should format chat messages."""
    from lexigram.contracts.ai.prompt import ChatPromptTemplate
    
    template = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("user", "Hello {name}"),
    ])
    prompt = template.format(name="Bob")
    assert len(prompt.messages) == 2
