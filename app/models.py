"""
SQLAlchemy database models for QualifyAI.

Defines the core entities:
- Lead: a prospect / client in the qualification pipeline
- Conversation: session state for ongoing WhatsApp dialogues
- Property: properties listed by the agency
- Agent: real estate agents who handle handovers
"""

import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _uuid() -> str:
    """Generate a UUID primary key as a string."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Lead(db.Model):
    """A real-estate prospect captured from WhatsApp."""

    __tablename__ = "leads"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    name = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=False, index=True, unique=True)

    # Qualification funnel
    buy_or_rent = db.Column(db.String(10), nullable=True)  # "buy" | "rent"
    property_type = db.Column(db.String(100), nullable=True)
    budget = db.Column(db.Float, nullable=True)
    income = db.Column(db.Float, nullable=True)
    property_price = db.Column(db.Float, nullable=True)

    qualification_status = db.Column(
        db.String(50),
        default="new",
        index=True,
    )  # new | qualifying | qualified | disqualified | follow_up
    qualification_score = db.Column(db.Float, nullable=True)  # 0.0 – 1.0
    urgency = db.Column(db.String(20), nullable=True)  # immediate | this_month | flexible

    email = db.Column(db.String(255), nullable=True)

    # Viewing flow
    viewing_requested = db.Column(db.Boolean, default=False)
    viewing_booked = db.Column(db.Boolean, default=False)
    viewing_date = db.Column(db.DateTime, nullable=True)
    viewing_completed = db.Column(db.Boolean, default=False)
    follow_up_sent = db.Column(db.Boolean, default=False)

    lead_score = db.Column(db.Float, nullable=True)
    conversation_summary = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    conversations = db.relationship(
        "Conversation",
        backref="lead",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Lead {self.phone} ({self.qualification_status})>"

    def to_dict(self) -> dict:
        """Serialize to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "buy_or_rent": self.buy_or_rent,
            "property_type": self.property_type,
            "budget": self.budget,
            "income": self.income,
            "property_price": self.property_price,
            "qualification_status": self.qualification_status,
            "qualification_score": self.qualification_score,
            "urgency": self.urgency,
            "email": self.email,
            "viewing_requested": self.viewing_requested,
            "viewing_booked": self.viewing_booked,
            "viewing_date": self.viewing_date.isoformat() if self.viewing_date else None,
            "viewing_completed": self.viewing_completed,
            "follow_up_sent": self.follow_up_sent,
            "lead_score": self.lead_score,
            "conversation_summary": self.conversation_summary,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Conversation(db.Model):
    """Tracks the session state and message history for a lead."""

    __tablename__ = "conversations"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    lead_id = db.Column(
        db.String(36),
        db.ForeignKey("leads.id"),
        nullable=False,
        index=True,
    )

    session_state = db.Column(db.String(50), default="greeting")
    # session_state tracks progression: greeting -> asking_intent -> qualifying -> booking -> done

    messages = db.Column(db.JSON, default=list)
    # List of message dicts: [{"role": "assistant"|"user", "content": "...", "timestamp": "..."}]

    context = db.Column(db.JSON, default=dict)
    # Temporary context extracted during conversation (e.g. preferences, objections)

    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self) -> str:
        return f"<Conversation {self.id} lead={self.lead_id} state={self.session_state}>"


class Property(db.Model):
    """A property listed by the agency."""

    __tablename__ = "properties"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    title = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # "rent" | "buy"
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(512), nullable=True)

    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self) -> str:
        return f"<Property {self.title} ({self.type})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "price": self.price,
            "location": self.location,
            "description": self.description,
            "url": self.url,
        }


class Agent(db.Model):
    """A real estate agent who can take over conversations."""

    __tablename__ = "agents"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(50), nullable=True)
    agency = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self) -> str:
        return f"<Agent {self.name} ({self.email})>"