"""SQLAlchemy database models for the Indian Tax Filing System (ITR-1).

Phase 0: replaces US-shaped tables (W2Form, Form1099, Dependent, TaxForm) with
Indian-shaped tables (Form16, ITR1Filing) and adds PAN/Aadhaar to User.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

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


class ITR1Filing(Base):
    """A computed ITR-1 (Sahaj) filing draft."""
    __tablename__ = "itr1_filings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    form16_id = Column(Integer, ForeignKey("form16.id"), nullable=True)

    assessment_year = Column(String, nullable=False)
    regime = Column(String, nullable=False)  # "old" | "new"

    # Computed values (from tax_engine_in.compute_filing)
    gross_income = Column(Float, default=0.0)
    taxable_income = Column(Float, default=0.0)
    slab_tax = Column(Float, default=0.0)
    rebate_87a = Column(Float, default=0.0)
    surcharge = Column(Float, default=0.0)
    cess = Column(Float, default=0.0)
    total_tax = Column(Float, default=0.0)
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
