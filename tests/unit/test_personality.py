import pytest
from app.conversation.personality import PersonalityConfig, get_personality_prompt, CASUAL_PERSONALITY

def test_personality_labels():
    p = PersonalityConfig(formality=0.1, verbosity=0.9)
    assert p.formality_label() == "casual"
    assert p.verbosity_label() == "detailed"
    
    p = PersonalityConfig(formality=0.5, verbosity=0.5)
    assert p.formality_label() == "professional"
    assert p.verbosity_label() == "balanced"
    
    p = PersonalityConfig(formality=0.9, verbosity=0.1)
    assert p.formality_label() == "formal"
    assert p.verbosity_label() == "concise"

def test_get_personality_prompt():
    prompt = get_personality_prompt(CASUAL_PERSONALITY)
    assert "casual" in prompt
    assert "balanced" in prompt
    assert "frequent" in prompt
    assert "Be proactive" in prompt
