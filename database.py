import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy setup
Base = declarative_base()
engine = None
SessionLocal = None


class User(Base):
    """User table - identified by phone number"""
    __tablename__ = "users"

    phone_number = Column(String(50), primary_key=True)  # e.g., "whatsapp:+31634829116"
    display_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)

    # Active Intelligence Fields
    timezone = Column(String(50), default='Europe/Amsterdam', nullable=False)
    quiet_hours_start = Column(Integer, default=22, nullable=False)  # 10 PM
    quiet_hours_end = Column(Integer, default=9, nullable=False)  # 9 AM
    onboarding_step = Column(Integer, default=0, nullable=False)  # 0=New, 99=Complete
    last_interaction_at = Column(DateTime, nullable=True)  # Last sent OR received message

    # JSON Fields for State Management
    open_loops = Column(JSONB, default={}, nullable=False)
    # Structure: {"topic_name": {"status": "active", "last_updated": "ISO-DATE", "next_event_date": "ISO-DATE", "weight": 1-5}}

    pending_questions = Column(JSONB, default=[], nullable=False)
    # Structure: [{"question": "...", "weight": 5, "created_at": "..."}]

    # Relationships
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    corpus = relationship("UserCorpus", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(phone_number='{self.phone_number}', display_name='{self.display_name}')>"


class Message(Base):
    """Message table - stores all incoming/outgoing messages"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(50), ForeignKey("users.phone_number"), nullable=False)
    direction = Column(String(10), nullable=False)  # 'incoming' or 'outgoing'
    message_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)  # For human-in-the-loop queue

    # Relationship
    user = relationship("User", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, phone_number='{self.phone_number}', direction='{self.direction}')>"


class UserCorpus(Base):
    """User corpus table - stores markdown knowledge graph per user"""
    __tablename__ = "user_corpus"

    phone_number = Column(String(50), ForeignKey("users.phone_number"), primary_key=True)
    corpus_markdown = Column(Text, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="corpus")

    def __repr__(self):
        return f"<UserCorpus(phone_number='{self.phone_number}')>"


class PendingNudge(Base):
    """Pending nudge messages awaiting admin approval before sending"""
    __tablename__ = "pending_nudges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(50), ForeignKey("users.phone_number"), nullable=False)
    topic = Column(String(200), nullable=False)  # The open loop topic this nudge is about
    weight = Column(Integer, nullable=False)  # Priority weight (1-5)
    message_text = Column(Text, nullable=False)  # Generated message text
    scheduled_send_time = Column(DateTime, nullable=False)  # When to send if approved
    status = Column(String(20), default='pending', nullable=False)  # pending, approved, sent, skipped
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<PendingNudge(id={self.id}, phone_number='{self.phone_number}', topic='{self.topic}', status='{self.status}')>"


def init_db():
    """Initialize database connection and create tables"""
    global engine, SessionLocal

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")

    # Railway PostgreSQL URLs start with postgres://, but SQLAlchemy needs postgresql://
    db_url = DATABASE_URL.replace("postgres://", "postgresql://") if DATABASE_URL.startswith("postgres://") else DATABASE_URL

    engine = create_engine(db_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")


def get_db():
    """Get database session"""
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e


def create_user(phone_number, display_name=None):
    """Create a new user"""
    db = get_db()
    try:
        user = User(phone_number=phone_number, display_name=display_name)
        db.add(user)

        # Create initial corpus for user
        initial_corpus = f"""# Personal Knowledge Graph - {display_name or phone_number}

## Worldview
_No information yet._

## Personal History
_No information yet._

## Values & Beliefs
_No information yet._

## Goals & Aspirations
_No information yet._

## Relationships
_No information yet._

## Interests & Hobbies
_No information yet._

---
_Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_
"""
        corpus = UserCorpus(phone_number=phone_number, corpus_markdown=initial_corpus)
        db.add(corpus)

        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_or_create_user(phone_number, display_name=None):
    """Get existing user or create new one"""
    db = get_db()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            db.close()
            user = create_user(phone_number, display_name)
        return user
    finally:
        if db:
            db.close()


def store_message(phone_number, direction, message_text):
    """Store a message in the database"""
    db = get_db()
    try:
        # Ensure user exists
        get_or_create_user(phone_number)

        # Create message
        message = Message(
            phone_number=phone_number,
            direction=direction,
            message_text=message_text,
            processed=False
        )
        db.add(message)

        # Update user's last_message_at
        user = db.query(User).filter(User.phone_number == phone_number).first()
        user.last_message_at = datetime.utcnow()

        db.commit()
        db.refresh(message)
        return message
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_user_messages(phone_number, limit=50):
    """Get message history for a user"""
    db = get_db()
    try:
        messages = db.query(Message).filter(
            Message.phone_number == phone_number
        ).order_by(Message.timestamp.desc()).limit(limit).all()
        return messages
    finally:
        db.close()


def get_user_corpus(phone_number):
    """Get user's corpus markdown"""
    db = get_db()
    try:
        corpus = db.query(UserCorpus).filter(UserCorpus.phone_number == phone_number).first()
        return corpus.corpus_markdown if corpus else None
    finally:
        db.close()


def update_user_corpus(phone_number, new_corpus_markdown):
    """Update user's corpus"""
    db = get_db()
    try:
        corpus = db.query(UserCorpus).filter(UserCorpus.phone_number == phone_number).first()
        if corpus:
            corpus.corpus_markdown = new_corpus_markdown
            corpus.last_updated = datetime.utcnow()
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_unprocessed_messages(limit=10):
    """Get unprocessed messages for human-in-the-loop queue"""
    db = get_db()
    try:
        messages = db.query(Message).filter(
            Message.processed == False,
            Message.direction == 'incoming'
        ).order_by(Message.timestamp.asc()).limit(limit).all()
        return messages
    finally:
        db.close()


def mark_message_processed(message_id):
    """Mark a message as processed"""
    db = get_db()
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if message:
            message.processed = True
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_all_users():
    """Get all users with their message counts"""
    db = get_db()
    try:
        users = db.query(User).order_by(User.last_message_at.desc()).all()
        return users
    finally:
        db.close()


def get_user(phone_number):
    """Get a user by phone number"""
    db = get_db()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        return user
    finally:
        db.close()


def update_user_interaction(phone_number):
    """Update last_interaction_at timestamp"""
    db = get_db()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if user:
            user.last_interaction_at = datetime.utcnow()
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def update_user_onboarding_step(phone_number, step):
    """Update user's onboarding step"""
    db = get_db()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if user:
            user.onboarding_step = step
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def update_user_field(phone_number, **kwargs):
    """Update specific user fields"""
    db = get_db()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_users_for_dispatch():
    """Get all users who have completed onboarding"""
    db = get_db()
    try:
        users = db.query(User).filter(
            User.onboarding_step == 99
        ).all()
        return users
    finally:
        db.close()


# ===== Pending Nudge Functions =====

def create_pending_nudge(phone_number, topic, weight, message_text, scheduled_send_time):
    """Create a new pending nudge"""
    db = get_db()
    try:
        nudge = PendingNudge(
            phone_number=phone_number,
            topic=topic,
            weight=weight,
            message_text=message_text,
            scheduled_send_time=scheduled_send_time,
            status='pending'
        )
        db.add(nudge)
        db.commit()
        db.refresh(nudge)
        return nudge
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_pending_nudges(status=None, limit=50):
    """Get pending nudges, optionally filtered by status"""
    db = get_db()
    try:
        query = db.query(PendingNudge)
        if status:
            query = query.filter(PendingNudge.status == status)
        nudges = query.order_by(PendingNudge.scheduled_send_time.asc()).limit(limit).all()
        return nudges
    finally:
        db.close()


def get_pending_nudge_by_id(nudge_id):
    """Get a specific pending nudge by ID"""
    db = get_db()
    try:
        nudge = db.query(PendingNudge).filter(PendingNudge.id == nudge_id).first()
        return nudge
    finally:
        db.close()


def update_pending_nudge(nudge_id, **kwargs):
    """Update a pending nudge"""
    db = get_db()
    try:
        nudge = db.query(PendingNudge).filter(PendingNudge.id == nudge_id).first()
        if nudge:
            for key, value in kwargs.items():
                if hasattr(nudge, key):
                    setattr(nudge, key, value)
            db.commit()
            db.refresh(nudge)
            return nudge
        return None
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def check_existing_pending_nudge(phone_number, topic):
    """Check if a pending nudge already exists for this user/topic"""
    db = get_db()
    try:
        nudge = db.query(PendingNudge).filter(
            PendingNudge.phone_number == phone_number,
            PendingNudge.topic == topic,
            PendingNudge.status.in_(['pending', 'approved'])
        ).first()
        return nudge is not None
    finally:
        db.close()


def get_approved_nudges_ready_to_send():
    """Get approved nudges that are ready to be sent (scheduled_send_time has passed)"""
    db = get_db()
    try:
        now = datetime.utcnow()
        nudges = db.query(PendingNudge).filter(
            PendingNudge.status == 'approved',
            PendingNudge.scheduled_send_time <= now
        ).all()
        return nudges
    finally:
        db.close()
