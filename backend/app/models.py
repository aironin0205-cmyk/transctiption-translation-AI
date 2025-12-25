import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Integer, Numeric, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from .db import Base

def uuid4():
    return str(uuid.uuid4())

class Job(Base):
    __tablename__ = "jobs"
    job_id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    source_lang: Mapped[str] = mapped_column(String, default="en")
    target_lang: Mapped[str] = mapped_column(String, default="fa")
    status: Mapped[str] = mapped_column(String, default="UPLOADED")
    input_type: Mapped[str] = mapped_column(String, default="upload")
    input_uri: Mapped[str] = mapped_column(String)
    normalized_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    asr_json_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    final_srt_uri: Mapped[str | None] = mapped_column(String, nullable=True)

    max_lines: Mapped[int] = mapped_column(Integer, default=2)
    max_chars_per_line: Mapped[int] = mapped_column(Integer, default=42)
    target_cps: Mapped[float] = mapped_column(Numeric(5,2), default=15.0)
    min_cue_ms: Mapped[int] = mapped_column(Integer, default=900)
    max_cue_ms: Mapped[int] = mapped_column(Integer, default=6500)

    risk_level: Mapped[str | None] = mapped_column(String, nullable=True)
    difficulty_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strategist_conf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    genre: Mapped[str | None] = mapped_column(String, nullable=True)
    tone: Mapped[str | None] = mapped_column(String, nullable=True)
    domain_tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    cues: Mapped[list["JobCue"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    glossary: Mapped[list["JobGlossaryTerm"]] = relationship(back_populates="job", cascade="all, delete-orphan")

class JobCue(Base):
    __tablename__ = "job_cues"
    cue_id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.job_id", ondelete="CASCADE"))
    cue_index: Mapped[int] = mapped_column(Integer)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    en_text: Mapped[str] = mapped_column(Text)
    fa_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    fa_text_qa: Mapped[str | None] = mapped_column(Text, nullable=True)
    tm_reused: Mapped[bool] = mapped_column(Boolean, default=False)
    tm_entry_id: Mapped[str | None] = mapped_column(String, nullable=True)
    needs_translation: Mapped[bool] = mapped_column(Boolean, default=True)
    tm_confidence: Mapped[float | None] = mapped_column(Numeric(5,2), nullable=True)
    qa_score: Mapped[float | None] = mapped_column(Numeric(5,2), nullable=True)
    issues: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    job: Mapped["Job"] = relationship(back_populates="cues")

class JobGlossaryTerm(Base):
    __tablename__ = "job_glossary_terms"
    term_id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.job_id", ondelete="CASCADE"))
    en_term: Mapped[str] = mapped_column(String)
    fa_term: Mapped[str] = mapped_column(String)
    term_type: Mapped[str | None] = mapped_column(String, nullable=True)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    job: Mapped["Job"] = relationship(back_populates="glossary")

class TMEntry(Base):
    __tablename__ = "tm_entries"
    tm_entry_id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    source_lang: Mapped[str] = mapped_column(String, default="en")
    target_lang: Mapped[str] = mapped_column(String, default="fa")
    en_text: Mapped[str] = mapped_column(Text)
    fa_text: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    quality_grade: Mapped[str] = mapped_column(String, default="candidate")
    qa_score: Mapped[float | None] = mapped_column(Numeric(5,2), nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    en_hash: Mapped[str] = mapped_column(String)
    domain_tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(3072), nullable=True)

class LLMRun(Base):
    __tablename__ = "llm_runs"
    run_id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    job_id: Mapped[str | None] = mapped_column(String, ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=True)
    cue_id: Mapped[str | None] = mapped_column(String, ForeignKey("job_cues.cue_id", ondelete="CASCADE"), nullable=True)
    agent_name: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10,4), nullable=True)
    status: Mapped[str] = mapped_column(String, default="success")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    output_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
