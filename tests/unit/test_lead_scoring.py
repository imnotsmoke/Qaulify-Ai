from app.services.lead_scoring import score_lead

def test_score_lead_perfect():
    # budget > 0 (0.5 * 0.35 = 0.175)
    # urgency 'immediate' (1.0 * 0.25 = 0.25)
    # engagement 20 messages (1.0 * 0.20 = 0.20)
    # status 'qualified' (0.8 * 0.20 = 0.16)
    # Total: 0.175 + 0.25 + 0.20 + 0.16 = 0.785 -> 0.79
    score = score_lead(
        budget=500000,
        urgency="immediate",
        message_count=20,
        qualification_status="qualified"
    )
    assert score == 0.79

def test_score_lead_cold():
    # budget None (0.0)
    # urgency None (0.0)
    # engagement 0 (0.0)
    # status 'new' (0.0)
    score = score_lead(
        budget=None,
        urgency=None,
        message_count=0,
        qualification_status="new"
    )
    assert score == 0.0

def test_score_lead_flexible():
    # budget 200k (0.5 * 0.35 = 0.175)
    # urgency 'flexible' (0.3 * 0.25 = 0.075)
    # engagement 5 (5/20 * 0.20 = 0.05)
    # status 'qualifying' (0.3 * 0.20 = 0.06)
    # Total: 0.175 + 0.075 + 0.05 + 0.06 = 0.36
    score = score_lead(
        budget=200000,
        urgency="flexible",
        message_count=5,
        qualification_status="qualifying"
    )
    assert score == 0.36

def test_score_lead_disqualified():
    score = score_lead(
        budget=1000000,
        urgency="immediate",
        message_count=20,
        qualification_status="disqualified"
    )
    # 0.175 + 0.25 + 0.20 + 0.0 = 0.625 -> 0.62 (banker's rounding)
    assert score == 0.62
