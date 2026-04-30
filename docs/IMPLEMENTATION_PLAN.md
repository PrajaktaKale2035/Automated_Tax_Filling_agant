# Automated Tax Filing System - Implementation Plan

> **Historical document.** This plan was written for the original US-tax-filing
> prototype. The project has since been migrated to Indian ITR-1 filing
> (FY 2024-25 / AY 2025-26). For current implementation status see
> [`BACKEND_STATUS.md`](BACKEND_STATUS.md). For the migration changelog see
> [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md). For the post-migration plan see
> [`superpowers/plans/2026-04-30-indian-tax-data-pipeline-phase0.md`](superpowers/plans/2026-04-30-indian-tax-data-pipeline-phase0.md).

---

## Project Vision (historical)

Build a fully automated tax filing system with **3 intelligent modes** that adapts question flows based on user expertise, automatically processes documents, calculates taxes, validates compliance, and generates ready-to-file forms.

---

## 🎮 Three Filing Modes

### 1. 🟢 Novice Mode (Guided Step-by-Step)
**Target Users**: First-time filers, students, simple returns

**Behavior**:
- Ask ALL questions with detailed explanations
- Simple language, no tax jargon
- Show examples for each input
- Provide context-sensitive help tooltips
- Break complex topics into simple steps
- Visual progress indicators
- Offer to explain each deduction/credit

**Question Flow Example**:
```
1. "Let's start with your personal information..."
   - Full name (with example: "John Smith")
   - Date of birth (with calendar picker)
   - Social Security Number (with "Why do we need this?" explanation)

2. "Did you work for an employer in 2024?"
   → YES: "Great! Do you have your W-2 form?"
      → YES: "You can upload it or enter manually"
      → NO: "No problem! Let me guide you through entering the information"
   → NO: "Did you have any other income?" (with examples)

3. For EACH deduction:
   "Did you make charitable donations?" 
   [?] Info: "Charitable donations can reduce your tax bill..."
```

### 2. 🟡 Intermediate Mode (Semi-Automated)
**Target Users**: Experienced filers, moderate complexity

**Behavior**:
- Ask only RELEVANT questions based on detected scenarios
- Skip obvious questions if documents are uploaded
- Provide brief explanations
- Auto-populate from uploaded documents
- Ask clarifying questions only when needed
- Show calculations in real-time

**Question Flow Example**:
```
1. Basic info (quick form)
2. Upload documents (W-2, 1099, receipts)
3. AI extracts data automatically
4. Ask ONLY about detected scenarios:
   "We found $5,000 in charitable donations. Are these all correct?"
   "You have investment income. Did you have any capital gains?"
5. Review and confirm
```

### 3. 🔴 Expert Mode (Fully Automated)
**Target Users**: Tax professionals, repeat filers, complex returns

**Behavior**:
- Upload ALL documents at once
- AI extracts EVERYTHING automatically
- Ask ONLY critical decision questions
- Auto-populate all standard fields
- Show comprehensive summary for review
- Minimal interaction required

**Question Flow Example**:
```
1. Upload all documents (batch upload)
2. AI processes everything in background
3. Ask ONLY critical decisions:
   "Multiple income sources detected. Choose filing status:
    ☐ Married Filing Jointly (recommended - saves $2,340)
    ☐ Married Filing Separately
    ☐ Head of Household"
4. Show complete return for review
5. One-click e-file
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE (Vue 3)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Mode Selector│  │Progress Track│  │  Form Preview│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATOR AGENT (Coordinator)                │
│  • Determines which questions to ask based on mode           │
│  • Routes to specialized agents                              │
│  • Manages conversation flow                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  DOCUMENT    │    │     TAX      │    │  COMPLIANCE  │
│  PROCESSOR   │    │  CALCULATOR  │    │   VALIDATOR  │
│              │    │              │    │              │
│ • OCR Extract│    │ • Calculate  │    │ • IRS Rules  │
│ • AI Parse   │    │ • Deductions │    │ • Validate   │
│ • Verify Data│    │ • Credits    │    │ • Explain    │
└──────────────┘    └──────────────┘    └──────────────┘
        ↓                     ↓                     ↓
┌─────────────────────────────────────────────────────────────┐
│                    VECTOR DATABASE (RAG)                     │
│  • IRS Publications (indexed)                                │
│  • Tax Code Reference (searchable)                           │
│  • Previous Returns (user history)                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQL DATABASE                         │
│  • User data • Tax forms • Documents • Calculations          │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Detailed Task Breakdown

### ✅ TASK 1: Complete FastAPI Backend Core
**Status**: In Progress (40% complete)

**Subtasks**:
- [ ] Create `backend/app/crud.py` with functions for all models
- [ ] Build `backend/app/api/auth.py` - login, register, JWT refresh
- [ ] Build `backend/app/api/users.py` - user profile management
- [ ] Build `backend/app/api/tax_forms.py` - CRUD for tax forms
- [ ] Build `backend/app/api/documents.py` - document upload/download
- [ ] Build `backend/app/api/agents.py` - chat with AI agents
- [ ] Add middleware: CORS, error handling, rate limiting
- [ ] Create health check endpoint
- [ ] Write API tests

**Acceptance Criteria**:
- ✅ All CRUD operations work
- ✅ Authentication flow complete
- ✅ API documented in /docs
- ✅ Error handling tested

---

### 🆕 TASK 2: Implement Mode-Based Question Flow System
**Status**: Not Started (HIGH PRIORITY)

**Implementation**:

1. **Create Mode Configuration** (`backend/app/mode_config.py`):
```python
MODES = {
    "novice": {
        "name": "Guided Step-by-Step",
        "detail_level": "maximum",
        "skip_obvious": False,
        "explain_all": True,
        "auto_populate": "minimal"
    },
    "intermediate": {
        "name": "Semi-Automated",
        "detail_level": "medium",
        "skip_obvious": True,
        "explain_all": False,
        "auto_populate": "smart"
    },
    "expert": {
        "name": "Fully Automated",
        "detail_level": "minimal",
        "skip_obvious": True,
        "explain_all": False,
        "auto_populate": "maximum"
    }
}
```

2. **Create Question Engine** (`backend/app/question_engine.py`):
```python
class QuestionEngine:
    def get_questions_for_scenario(
        self, 
        mode: str,
        scenario: dict,
        uploaded_docs: list
    ) -> list[Question]:
        """
        Generate questions based on:
        - Selected mode
        - Detected scenario (W-2, 1099, self-employed, etc.)
        - Already uploaded documents
        """
```

3. **Build Scenario Detector** (`backend/app/scenario_detector.py`):
- Analyze uploaded documents
- Detect: Employment income, Investment income, Business income, etc.
- Skip irrelevant questions

4. **Frontend Mode Selector** (`src/components-vue/mode/ModeSelector.vue`):
```vue
<template>
  <div class="mode-selection">
    <h2>Choose Your Filing Mode</h2>
    
    <ModeCard
      mode="novice"
      title="Guided Step-by-Step"
      description="I'm new to filing taxes"
      icon="🟢"
      features="[
        'Detailed explanations',
        'Simple language',
        'Step-by-step guidance'
      ]"
    />
    
    <ModeCard
      mode="intermediate"
      title="Semi-Automated"
      description="I've filed before"
      icon="🟡"
      features="[
        'Smart document processing',
        'Ask only what's needed',
        'Real-time calculations'
      ]"
    />
    
    <ModeCard
      mode="expert"
      title="Fully Automated"
      description="Just process my documents"
      icon="🔴"
      features="[
        'Batch document upload',
        'Automatic extraction',
        'Minimal questions'
      ]"
    />
  </div>
</template>
```

**Acceptance Criteria**:
- ✅ User can select mode
- ✅ Question flow adapts to mode
- ✅ Novice mode asks ALL questions
- ✅ Expert mode asks MINIMAL questions
- ✅ Can switch modes mid-filing

---

### 🤖 TASK 3: Build AutoGen Multi-Agent System
**Status**: Not Started

**Implementation Steps**:

1. **Setup AutoGen** (`backend/app/agents/autogen_config.py`)
2. **Create Tax Logic Agent** - Performs calculations
3. **Create Interaction Agent** - Manages conversation
4. **Create User Proxy** - Executes tools
5. **Integrate with existing LangChain tools**

**Question Examples by Agent**:
```python
# Tax Logic Agent (calculations)
"Based on your income of $75,000, your standard deduction is $13,850"

# Interaction Agent (user-facing)
"I see you had $5,000 in medical expenses. Since this is over 7.5% 
of your income, you can deduct $2,375. Would you like to claim this?"

# Compliance Agent (validation)
"⚠️ IRS requires documentation for charitable donations over $250. 
Do you have receipts for the $1,500 donation you mentioned?"
```

---

### 📄 TASK 4: Document Upload & OCR Pipeline
**Status**: Not Started

**Features**:
- Drag & drop file upload (PDF, PNG, JPG)
- OCR extraction using Tesseract or AWS Textract
- AI-powered field extraction (GPT-4 Vision or Claude)
- Confidence scoring for extracted data
- User verification interface

**Document Types to Support**:
- ✅ W-2 (wages)
- ✅ 1099-INT (interest income)
- ✅ 1099-DIV (dividends)
- ✅ 1099-MISC (miscellaneous income)
- ✅ 1099-NEC (non-employee compensation)
- ✅ Receipts (charitable, medical, business)
- ✅ Prior year tax returns

---

### 🧮 TASK 5: Automated Tax Calculation Engine
**Status**: Not Started (CRITICAL)

**Calculations to Implement**:

1. **Income Calculations**:
   - Gross income
   - Adjusted Gross Income (AGI)
   - Taxable income

2. **Deductions**:
   - Standard deduction vs. itemized
   - Charitable contributions
   - Medical expenses (>7.5% AGI)
   - State and local taxes (SALT, $10k cap)
   - Mortgage interest

3. **Credits**:
   - Earned Income Tax Credit (EITC)
   - Child Tax Credit
   - Education credits (American Opportunity, Lifetime Learning)
   - Saver's credit

4. **Tax Computation**:
   - Federal tax brackets
   - State tax (if applicable)
   - Alternative Minimum Tax (AMT)
   - Self-employment tax

**Real-time Validation**:
- Show running total as user enters data
- Highlight potential errors
- Suggest optimizations

---

### ✅ TASK 6: Compliance & Validation System
**Status**: Not Started

**Validation Checks**:

1. **Math Validation**:
   - All totals add up correctly
   - No negative values where inappropriate
   - Percentage calculations correct

2. **IRS Rule Validation**:
   - Income thresholds
   - Deduction limits
   - Credit phase-outs
   - Filing status requirements

3. **Cross-Reference Checks**:
   - W-2 total matches 1040 wages
   - Dependents meet qualifying criteria
   - Dates are logical

4. **Red Flag Detection**:
   - Unusually high deductions
   - Income inconsistencies
   - Missing required forms

**Output**:
```
✅ All required fields completed
✅ Math checks passed
⚠️ High charitable deduction (15% of income)
   → Ensure you have documentation
ℹ️  You may qualify for Saver's Credit
   → Consider contributing to IRA before filing
```

---

### 📋 TASK 7: Form Generation & Review System
**Status**: Not Started

**Features**:
- Generate PDF of completed Form 1040
- Generate required schedules (A, B, C, etc.)
- Side-by-side comparison view
- Change tracking (what changed from last year)
- Export to PDF for printing
- Prepare for e-filing

---

### 🎨 TASK 8: Adaptive UI with Progress Tracking
**Status**: Not Started

**Components to Build**:

1. **Progress Tracker** (`src/components-vue/progress/ProgressTracker.vue`):
```vue
<template>
  <div class="progress-tracker">
    <Step name="Personal Info" status="complete" />
    <Step name="Income" status="in-progress" />
    <Step name="Deductions" status="pending" />
    <Step name="Review" status="pending" />
  </div>
</template>
```

2. **Smart Form Fields**:
   - Auto-format SSN, dates, currency
   - Real-time validation
   - Contextual help
   - Pre-fill from uploaded documents

3. **Help System**:
   - Inline tooltips
   - "Why do you need this?" buttons
   - Examples for each field
   - Link to IRS publications

---

### 🗄️ TASK 9: RAG Vector Database for Tax Knowledge
**Status**: Not Started

**Implementation**:

1. **Ingest IRS Publications**:
   - Publication 17 (Your Federal Income Tax)
   - Publication 501 (Dependents)
   - Publication 970 (Tax Benefits for Education)
   - Form instructions

2. **Create Embeddings**:
   - Use OpenAI or Anthropic embeddings
   - Store in ChromaDB/FAISS

3. **Semantic Search**:
   - User asks: "Can I deduct my home office?"
   - System retrieves relevant IRS guidance
   - AI summarizes in simple language

---

### 🧪 TASK 10: End-to-End Testing
**Status**: Not Started

**Test Scenarios**:

1. **Novice Mode - Simple Return**:
   - Single W-2
   - Standard deduction
   - No dependents
   - Expected: ~50 questions asked

2. **Intermediate Mode - Moderate Return**:
   - 2 W-2s
   - 1 1099-INT
   - Itemized deductions
   - Expected: ~20 questions asked

3. **Expert Mode - Complex Return**:
   - Multiple income sources
   - Self-employment
   - Rental property
   - Expected: ~5 critical questions only

---

## 🎯 Implementation Priority Order

### Phase 1 (Weeks 1-2): Core Foundation
1. ✅ Complete FastAPI Backend (Task 1)
2. ✅ Mode-Based Question System (Task 2)
3. ✅ Basic UI Progress Tracking (Task 8 - partial)

### Phase 2 (Weeks 3-4): Document Processing & Calculation
4. ✅ Document Upload & OCR (Task 4)
5. ✅ Tax Calculation Engine (Task 5)
6. ✅ Form Preview Interface

### Phase 3 (Weeks 5-6): AI & Intelligence
7. ✅ AutoGen Multi-Agent (Task 3)
8. ✅ RAG Vector Database (Task 9)
9. ✅ Advanced Validation (Task 6)

### Phase 4 (Week 7): Polish & Testing
10. ✅ Form Generation (Task 7)
11. ✅ End-to-End Testing (Task 10)
12. ✅ UI/UX refinements

---

## 📊 Success Metrics

- **Novice Mode**: User completes return with 100% confidence
- **Intermediate Mode**: 50% reduction in questions vs. novice
- **Expert Mode**: 80% reduction in questions vs. novice
- **Accuracy**: 99%+ tax calculation accuracy
- **Speed**: Complete simple return in < 10 minutes (expert mode)
- **User Satisfaction**: 4.5+ stars

---

## 🚀 Let's Start!

**Ready to begin?** I recommend starting with:

1. **Task 2 (Mode-Based Questions)** - This is the foundation
2. **Complete Task 1 (FastAPI Backend)** - Finish what's started
3. **Task 5 (Tax Calculator)** - Core functionality

**Which task would you like to start with?**

