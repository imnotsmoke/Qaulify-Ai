# QualifyAI

An AI Property Consultant that lives on WhatsApp — qualifying real estate leads, booking viewings, and following up automatically.

## Backend

Built with Python Flask, PostgreSQL, OpenAI, and Meta WhatsApp Cloud API.

### Quick Start

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run development server
python run.py
```

### Project Structure

```
app/
├── __init__.py        # Flask app factory
├── config.py          # Configuration
├── models.py          # SQLAlchemy models
├── routes/
│   ├── whatsapp.py    # WhatsApp webhooks
│   ├── calendly.py    # Calendly webhooks
│   └── agent.py       # Agent handover endpoints
├── services/
│   ├── ai_service.py       # OpenAI integration
│   ├── whatsapp_service.py # WhatsApp Cloud API
│   ├── affordability.py    # Affordability engine
│   ├── lead_scoring.py     # Lead scoring
│   └── scheduler.py        # APScheduler tasks
├── conversation/
│   ├── flow.py        # State machine
│   ├── prompts.py     # System prompts
│   └── personality.py # Personality engine
└── utils/
    ├── delays.py      # Human-like delays
    └── templates.py   # Message templates
```
