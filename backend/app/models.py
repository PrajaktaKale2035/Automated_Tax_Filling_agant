"""SQLAlchemy database models for the Indian Tax Filing System (ITR-1).

Phase 0: replaces US-shaped tables (W2Form, Form1099, Dependent, TaxForm) with
Indian-shaped tables (Form16, ITR1Filing) and adds PAN/Aadhaar to User.
Phase 1: adds RagDocument with pgvector embedding column for IT Dept rulebook RAG.
Phase 2: adds UserRole enum (filer/helper/read_only) + role column on User,
         age_category on ITR1Filing for senior-citizen slab logic.
"""
import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, Text, JSON, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base


class UserRole(str, enum.Enum):
    """Role that governs what actions a user may perform in the filing system."""
    filer = "filer"          # Default: can create and submit own filings
    helper = "helper"        # Tax professional helping a filer: read + compute, no submit
    read_only = "read_only"  # Auditor / observer: view only, cannot compute or submit


# Embedding dimension for SentenceTransformer all-MiniLM-L6-v2 (used by Phase 1 RAG).
RAG_EMBEDDING_DIM = 384


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Role-based access control
    role = Column(SAEnum(UserRole), default=UserRole.filer, server_default="filer", nullable=False)

    # India identifiers (encrypted at rest via app.security)
    pan_encrypted = Column(String, nullable=True, index=True)
    aadhaar_encrypted = Column(String, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    form16s = relationship("Form16", back_populates="user", cascade="all, delete-orphan")
    filings = relationship("ITR1Filing", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class UserProfile(Base):
    """User profile with adaptive UI preferences."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Adaptive UI Settings
    preferred_mode = Column(String, default="novice")  # novice, intermediate, expert
    interaction_count = Column(Integer, default=0)
    help_requests = Column(Integer, default=0)
    interaction_speed_avg_ms = Column(Integer, default=0)
    error_rate_percent = Column(Float, default=0.0)
    cognitive_load_score = Column(Float, default=0.0)

    # User Preferences
    theme = Column(String, default="light")
    language = Column(String, default="en")
    notifications_enabled = Column(Boolean, default=True)

    # Tax-specific preferences (Indian)
    preferred_regime = Column(String, default="new")  # "old" | "new"
    filing_history = Column(JSON, default=list)
    preferred_assessment_year = Column(String)  # e.g. "2025-26"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, mode={self.preferred_mode})>"


class Form16(Base):
    """Extracted Form 16 data. One row per uploaded Form 16 (Indian Part A + Part B)."""
    __tablename__ = "form16"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_year = Column(String, nullable=False)  # e.g. "2025-26"

    # Part A
    employer_name = Column(String)
    employer_tan = Column(String)
    employer_pan = Column(String)
    period_from = Column(DateTime)
    period_to = Column(DateTime)
    quarter_wise_tds = Column(JSON, default=dict)  # {"q1": 12345, "q2": ...}

    # Part B
    gross_salary = Column(Float, default=0.0)
    exempt_allowances = Column(Float, default=0.0)
    standard_deduction_claimed = Column(Float, default=0.0)
    professional_tax = Column(Float, default=0.0)
    deductions_80c = Column(Float, default=0.0)
    deductions_80d = Column(Float, default=0.0)
    deductions_other = Column(JSON, default=dict)
    tds_deducted = Column(Float, default=0.0)

    # Provenance
    raw_ocr_text = Column(Text)
    source_document_id = Column(Integer, nullable=True)  # FK in Phase 2 once Document model lands
    extraction_status = Column(String, default="manual")  # manual | extracted | review_required

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="form16s")
    filings = relationship("ITR1Filing", back_populates="form16")

    def __repr__(self):
        return f"<Form16(id={self.id}, employer={self.employer_name}, ay={self.assessment_year})>"


class ITRImport(Base):
    """A previous-year ITR (PDF or JSON) uploaded by the user.

    The ingestion agent parses it into normalized fields so a new filing can be
    pre-populated. Stored alongside `Form16` rows but distinct because an ITR
    return is a far broader document (full income statement, not just salary).
    """
    __tablename__ = "itr_imports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Source file metadata
    source_filename = Column(String, nullable=True)
    source_format = Column(String, nullable=False)        # "json" | "pdf"
    stored_path = Column(String, nullable=True)

    # Identifiers extracted from the return
    assessment_year = Column(String, nullable=True)       # e.g. "2024-25"
    form_type = Column(String(10), nullable=True)         # "ITR-1" | "ITR-2" | "ITR-4" | ...
    pan = Column(String, nullable=True)
    name = Column(String, nullable=True)
    regime = Column(String, nullable=True)                # "old" | "new" | None

    # Normalized line items (best-effort; default 0)
    gross_salary = Column(Float, default=0.0)
    house_property_income = Column(Float, default=0.0)
    capital_gains = Column(Float, default=0.0)
    business_income = Column(Float, default=0.0)
    other_income = Column(Float, default=0.0)
    deductions_80c = Column(Float, default=0.0)
    deductions_80d = Column(Float, default=0.0)
    deductions_other = Column(Float, default=0.0)
    taxable_income = Column(Float, default=0.0)
    total_tax = Column(Float, default=0.0)
    tds_paid = Column(Float, default=0.0)
    refund_due = Column(Float, default=0.0)
    tax_due = Column(Float, default=0.0)

    # Provenance
    raw_text = Column(Text)                                # OCR/extracted text or raw JSON
    parsed_payload = Column(JSON, default=dict)            # full structured parse
    extraction_status = Column(String, default="parsed")   # parsed | review_required | failed
    extraction_confidence = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ITRImport(id={self.id}, ay={self.assessment_year}, form={self.form_type})>"


class ITR1Filing(Base):
    """A computed ITR-1 (Sahaj) filing draft."""
    __tablename__ = "itr1_filings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    form16_id = Column(Integer, ForeignKey("form16.id"), nullable=True)

    assessment_year = Column(String, nullable=False)
    form_type = Column(String(10), default="ITR-1", nullable=False)
    regime = Column(String, nullable=False)  # "old" | "new"
    # Age category drives senior-citizen and super-senior slab boundaries.
    # Values: "general" (<60), "senior" (60-79), "super_senior" (80+)
    age_category = Column(String(20), default="general", nullable=False)

    # Computed values (from tax_engine_in.compute_filing)
    gross_income = Column(Float, default=0.0)
    taxable_income = Column(Float, default=0.0)
    slab_tax = Column(Float, default=0.0)
    rebate_87a = Column(Float, default=0.0)
    surcharge = Column(Float, default=0.0)
    cess = Column(Float, default=0.0)
    total_tax = Column(Float, default=0.0)
    capital_gains_stcg_equity = Column(Float, default=0.0)
    capital_gains_ltcg_equity = Column(Float, default=0.0)
    capital_gains_stcg_tax = Column(Float, default=0.0)
    capital_gains_ltcg_tax = Column(Float, default=0.0)
    house_property_income = Column(Float, default=0.0)
    business_income = Column(Float, default=0.0)
    tds_paid = Column(Float, default=0.0)
    refund_due = Column(Float, default=0.0)
    tax_due = Column(Float, default=0.0)

    # Output artefacts
    itr1_json = Column(JSON, default=dict)
    pdf_path = Column(String, nullable=True)

    status = Column(String, default="draft")  # draft | computed | finalized
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="filings")
    form16 = relationship("Form16", back_populates="filings")
    compliance_checks = relationship("ComplianceCheck", back_populates="filing", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ITR1Filing(id={self.id}, ay={self.assessment_year}, regime={self.regime}, status={self.status})>"


class ComplianceCheck(Base):
    """Store compliance check results for an ITR-1 filing."""
    __tablename__ = "compliance_checks"

    id = Column(Integer, primary_key=True, index=True)
    filing_id = Column(Integer, ForeignKey("itr1_filings.id"), nullable=False)

    check_type = Column(String, nullable=False)  # pan_aadhaar_link, regime_choice_consistency, math_check
    check_name = Column(String, nullable=False)
    status = Column(String, nullable=False)  # passed | failed | warning

    message = Column(Text)
    details = Column(JSON, default=dict)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    filing = relationship("ITR1Filing", back_populates="compliance_checks")

    def __repr__(self):
        return f"<ComplianceCheck(id={self.id}, type={self.check_type}, status={self.status})>"


class RagDocument(Base):
    """Embedded chunks of the ITR rulebook for retrieval-augmented generation.

    Phase 1 ingests `tax_rules.txt` (curated Indian content) into this table.
    Future ingestion runs may add Income Tax Act sections, ITR-1 instructions,
    Finance Act 2024, CBDT circulars, etc.

    Embedding model: SentenceTransformer all-MiniLM-L6-v2 (384 dim).
    Distance metric: cosine.
    """
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, index=True)
    collection = Column(String, nullable=False, default="itr_rulebook", index=True)
    source = Column(String, nullable=False)  # e.g., "tax_rules.txt", "ITR-1-instructions-AY2025-26.pdf"
    chunk_index = Column(Integer, nullable=False, default=0)
    topic = Column(String, index=True)  # e.g., "80C", "slabs", "surcharge" - optional metadata
    content = Column(Text, nullable=False)
    embedding = Column(Vector(RAG_EMBEDDING_DIM), nullable=False)
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<RagDocument(id={self.id}, source={self.source}, chunk={self.chunk_index})>"


class AuditLog(Base):
    """Comprehensive audit trail for compliance and security."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    action = Column(String, nullable=False)  # login, logout, filing_created, filing_updated, etc.
    resource_type = Column(String)  # user, itr1_filing, form16, etc.
    resource_id = Column(Integer)

    details = Column(JSON, default=dict)
    ip_address = Column(String)
    user_agent = Column(String)

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, timestamp={self.timestamp})>"
