# Backend Development Status

> **Updated 2026-05-02.** This document originally tracked the US-tax-filing
> prototype phase work. The historical sections below are kept for context, but
> the canonical current status is the section directly below. For the full
> migration changelog see [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md).

---

## Current Status — Phase 0-4 complete (Indian ITR-1)

**Date:** 2026-05-02
**Branch:** `develop`
**Status:** 🟢 End-to-end Indian ITR-1 pipeline operational. 75/75 tests pass, 0 warnings.

### What works end-to-end
- Deterministic Indian tax engine (`backend/app/services/tax_engine_in.py`)
- Indian ITR-1 schema in Postgres — 7 tables (see `app/models.py`)
- **pgvector** RAG over the curated FY 2024-25 rulebook — 29 sections (~57 chunks)
- LangGraph workflow: interviewer -> researcher -> calculator -> auditor (AutoGen retired)
- Multi-provider LLM in `nodes.py`: Gemini / OpenAI / Ollama — switch via `LLM_PROVIDER` in `.env`
- `interviewer_node` uses `await asyncio.wait_for(llm.ainvoke(), timeout=30)` — proper async, cancellable, with graceful error messages on quota/timeout/disconnect
- Form 16 OCR upload + structured extraction -> `form16` table
- ITR-1 JSON in IT Dept schema + ITR-1 PDF (INR Indian grouping)
- WebSocket `filing.starting / .calculating / .complete` events keyed to `client_id`
- 19 REST routes, all India-aligned

### Endpoints
- `POST /api/v2/calc/preview` — stateless tax computation
- `POST /api/v2/filing/start` — manual entry or `form16_id`
- `GET /api/v2/filing/{id}/{pdf,json,status}`
- `POST /api/v2/filing/chat/{start,message}` — LangGraph chat workflow
- `WS /api/ws/{client_id}` — realtime filing events

### Stack changes vs. the historical sections below
- Postgres image: `postgres:18` -> `pgvector/pgvector:pg16`
- Vector store: ChromaDB -> pgvector (`Vector(384)` column on `rag_documents`)
- Multi-agent: LangGraph + AutoGen (parallel) -> LangGraph only
- Tax math: 3 places (LangGraph + frontend + PDF) -> single `tax_engine_in`
- Tables: dropped W2Form / Form1099 / Dependent / TaxForm / UserInputData; added Form16, ITR1Filing, RagDocument; added pan_encrypted / aadhaar_encrypted on User
- LangGraph checkpointer: `InMemorySaver` (Phase 0); `AsyncPostgresSaver` deferred to Phase 3+

### Known gaps (intentional, deferred)
- Real IT Dept PDF ingestion (currently uses curated `tax_rules.txt`)
- E-filing submission to incometax.gov.in
- Frontend tool modules outside the data pipeline (`complianceTools.ts`, `advisoryTools.ts`) still contain US thresholds — not on the `tax_engine_in` path

---

## Historical sections — US prototype (preserved for context)

> Everything below describes the original US-tax-filing scaffolding. It is no
> longer accurate for the running system but is kept so older PRs, commits, and
> tickets remain readable.

---

## ✅ COMPLETED: Task 1 - FastAPI Backend Core (historical, US scaffolding)

**Date Completed:** December 2024
**Status:** 🟢 FULLY OPERATIONAL

---

## Overview

Successfully built complete FastAPI backend with PostgreSQL database, authentication, and full CRUD operations for the tax filing system. The API is now running and accessible at:

- **API Server:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/api/docs (Swagger UI)
- **Alternative Docs:** http://localhost:8000/api/redoc
- **Health Check:** http://localhost:8000/api/health

---

## Files Created

### 1. **Backend Core (CRUD Operations)**

**File:** `backend/app/crud.py` (400+ lines)

**Functions Created:** 30+ CRUD operations

- **User Management (7 functions)**
  - `get_user()` - Get user by ID
  - `get_user_by_email()` - Get user by email
  - `get_users()` - List users with pagination
  - `create_user()` - Create user with hashed password + default profile
  - `update_user()` - Update user information
  - `delete_user()` - Delete user (cascades to all data)
  - `authenticate_user()` - Email/password authentication

- **User Profile Management (3 functions)**
  - `get_user_profile()` - Get profile settings
  - `update_user_profile()` - Update mode, theme, language, notifications
  - `update_user_interaction_stats()` - Track proficiency for adaptive UI

- **Tax Form Management (5 functions)**
  - `get_tax_form()` - Get form by ID
  - `get_user_tax_forms()` - List forms (with year filter)
  - `create_tax_form()` - Create new form with initial values
  - `update_tax_form()` - Update form data and calculations
  - `delete_tax_form()` - Delete form (cascades)

- **Dependent Management (2 functions)**
  - `create_dependent()` - Add dependent (encrypts SSN automatically)
  - `get_form_dependents()` - List dependents for form

- **W-2 Form Management (2 functions)**
  - `create_w2_form()` - Add W-2 with all boxes
  - `get_form_w2s()` - List W-2s for form

- **1099 Form Management (2 functions)**
  - `create_1099_form()` - Add 1099 (all types)
  - `get_form_1099s()` - List 1099s for form

- **User Input Tracking (2 functions)**
  - `log_user_input()` - Log input for audit trail
  - `get_form_input_history()` - Get input history

- **Compliance Checks (2 functions)**
  - `create_compliance_check()` - Log validation result
  - `get_form_compliance_checks()` - Get all checks

- **Audit Logging (2 functions)**
  - `create_audit_log()` - Log user action
  - `get_user_audit_logs()` - Get user activity logs

**Key Features:**
- Automatic password hashing with bcrypt
- Automatic SSN encryption with Fernet
- Default profile creation on user registration
- Comprehensive error handling with SQLAlchemy IntegrityError
- Audit trail logging for all major actions
- Cascade deletes for data integrity

---

### 2. **API Routers (3 Files)**

#### A. Authentication Router
**File:** `backend/app/api/auth.py` (150+ lines)

**Endpoints (5):**
- `POST /api/auth/register` - Register new user
  - Validates email uniqueness
  - Enforces password complexity (8+ chars, uppercase, digit)
  - Creates user + default profile automatically
  - Returns 201 Created with user object

- `POST /api/auth/login` - Login with OAuth2 form
  - Uses OAuth2PasswordRequestForm (username=email, password)
  - Returns JWT access token (30-day expiry)
  - Logs login event to audit trail
  - Checks if user is active

- `GET /api/auth/me` - Get current user
  - Requires Bearer token authentication
  - Returns authenticated user object

- `POST /api/auth/logout` - Logout user
  - Logs logout event to audit trail
  - Client should discard JWT token

- **Helper Functions:**
  - `get_current_user()` - Decode JWT and fetch user (dependency)
  - `get_current_active_user()` - Ensure user is active (dependency)

**Security Features:**
- JWT token authentication with python-jose
- Password hashing with bcrypt (passlib)
- OAuth2 with Password flow (RFC 6749)
- Token includes user_id and email in payload

---

#### B. Users Router
**File:** `backend/app/api/users.py` (180+ lines)

**Endpoints (6):**
- `GET /api/users/me` - Get current user info
- `PUT /api/users/me` - Update user info
  - Validates email uniqueness if changed
  - Logs update to audit trail
  
- `DELETE /api/users/me` - Delete account (WARNING: permanent)
  - Logs deletion before removing
  - Cascades to all tax forms and data
  
- `GET /api/users/me/profile` - Get profile settings
- `PUT /api/users/me/profile` - Update profile
  - Update mode (novice/intermediate/expert)
  - Update theme (light/dark)
  - Update language
  - Update notifications
  
- `GET /api/users/` - List users (admin placeholder)
  - Currently returns only current user
  - TODO: Add admin role check

**Authorization:**
- All endpoints require authentication
- Users can only access/modify their own data
- Admin endpoints prepared for future role-based access

---

#### C. Tax Forms Router
**File:** `backend/app/api/tax_forms.py` (370+ lines)

**Tax Form Endpoints (5):**
- `POST /api/tax-forms/` - Create new tax form
  - Validates no duplicate year for user
  - Initializes with in_progress status
  - Logs creation event
  
- `GET /api/tax-forms/` - List user's tax forms
  - Optional year filter: `?year=2024`
  - Ordered by year (newest first)
  
- `GET /api/tax-forms/{form_id}` - Get specific form
  - Verifies ownership
  - Returns full form with all data
  
- `PUT /api/tax-forms/{form_id}` - Update form
  - Update any field (status, calculations, form_data)
  - Logs update with changed fields
  
- `DELETE /api/tax-forms/{form_id}` - Delete form (WARNING: permanent)
  - Verifies ownership
  - Logs deletion before removing
  - Cascades to dependents, W-2s, 1099s

**Dependent Endpoints (2):**
- `POST /api/tax-forms/{form_id}/dependents` - Add dependent
  - Auto-encrypts SSN before storage
  - Logs creation
  
- `GET /api/tax-forms/{form_id}/dependents` - List dependents

**W-2 Endpoints (2):**
- `POST /api/tax-forms/{form_id}/w2s` - Add W-2
  - All box values (1-20)
  - Box 12 codes as JSON array
  - Box 13 checkboxes as JSON object
  
- `GET /api/tax-forms/{form_id}/w2s` - List W-2s

**1099 Endpoints (2):**
- `POST /api/tax-forms/{form_id}/1099s` - Add 1099
  - Supports all types: INT, DIV, MISC, NEC, etc.
  - form_data as flexible JSON
  
- `GET /api/tax-forms/{form_id}/1099s` - List 1099s

**Compliance Endpoints (1):**
- `GET /api/tax-forms/{form_id}/compliance-checks` - Get validation results

**Authorization:**
- All endpoints verify form ownership
- 403 Forbidden if user doesn't own the form
- 404 Not Found if form doesn't exist

---

### 3. **Main Application**

**File:** `backend/main.py` (170+ lines)

**Application Setup:**
- FastAPI app with title, description, version
- Swagger UI at `/api/docs`
- ReDoc at `/api/redoc`
- Auto-creates database tables on startup

**Middleware (2):**
1. **CORS Middleware**
   - Allows localhost:5173 (Vite dev server)
   - Allows localhost:3000 (alternative port)
   - Enables credentials (cookies, auth headers)
   - Allows all methods and headers

2. **Request Timing Middleware**
   - Adds X-Process-Time header to all responses
   - Tracks request duration in seconds

**Exception Handlers (3):**
1. **Validation Error Handler**
   - Returns 422 Unprocessable Entity
   - Detailed Pydantic validation errors

2. **Database Error Handler**
   - Returns 500 Internal Server Error
   - Catches all SQLAlchemy errors

3. **General Exception Handler**
   - Returns 500 Internal Server Error
   - Catches all other exceptions

**Root Endpoints (2):**
- `GET /` - API information and links
- `GET /api/health` - Health check with database connection test

**Startup Event:**
- Prints startup message
- Shows documentation URLs

---

## Database Schema

**Database:** tax_filing_db  
**User:** taxagent  
**Connection:** postgresql://localhost:5432

**Tables (9):**
1. ✅ `users` - User accounts
2. ✅ `user_profiles` - User preferences and proficiency tracking
3. ✅ `tax_forms` - Main tax form data
4. ✅ `dependents` - Dependent information (SSN encrypted)
5. ✅ `w2_forms` - W-2 wage statements
6. ✅ `form_1099s` - 1099 forms (all types)
7. ✅ `user_input_data` - Input audit trail
8. ✅ `compliance_checks` - Validation results
9. ✅ `audit_logs` - User activity logs

**Relationships:**
- User → UserProfile (1:1)
- User → TaxForm (1:N)
- TaxForm → Dependent (1:N)
- TaxForm → W2Form (1:N)
- TaxForm → Form1099 (1:N)
- TaxForm → UserInputData (1:N)
- TaxForm → ComplianceCheck (1:N)
- User → AuditLog (1:N)

**Cascade Deletes:**
- Delete user → deletes all tax forms
- Delete tax form → deletes dependents, W-2s, 1099s, inputs, checks

---

## API Testing

### Test with cURL:

```bash
# 1. Register new user
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234","full_name":"Test User"}'

# 2. Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=Test1234"

# Response: {"access_token":"eyJ...","token_type":"bearer"}

# 3. Get current user (replace TOKEN)
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer TOKEN"

# 4. Create tax form
curl -X POST "http://localhost:8000/api/tax-forms/" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"year":2024,"filing_status":"single"}'

# 5. Health check (no auth required)
curl -X GET "http://localhost:8000/api/health"
```

---

## Python Packages Installed

**Core Framework:**
- ✅ fastapi==0.121.2
- ✅ uvicorn==0.38.0 (with standard extras: httptools, watchfiles, websockets)
- ✅ starlette==0.49.3

**Database:**
- ✅ sqlalchemy==2.0.44
- ✅ psycopg2-binary==2.9.11

**Security:**
- ✅ python-jose==3.5.0 (JWT tokens)
- ✅ cryptography==46.0.3 (encryption)
- ✅ passlib==1.7.4 (password hashing)
- ✅ bcrypt==5.0.0

**Validation:**
- ✅ pydantic==2.12.4
- ✅ pydantic-core==2.41.5
- ✅ pydantic-settings==2.12.0
- ✅ email-validator==2.3.0

**Utilities:**
- ✅ python-dotenv==1.2.1
- ✅ python-multipart==0.0.20 (OAuth2 forms)

**HTTP/Network:**
- ✅ h11==0.16.0
- ✅ httptools==0.7.1
- ✅ websockets==15.0.1
- ✅ dnspython==2.8.0 (email validation)

---

## API Endpoints Summary

### Authentication (4 endpoints)
- `POST /api/auth/register` ✅
- `POST /api/auth/login` ✅
- `GET /api/auth/me` ✅
- `POST /api/auth/logout` ✅

### Users (6 endpoints)
- `GET /api/users/me` ✅
- `PUT /api/users/me` ✅
- `DELETE /api/users/me` ✅
- `GET /api/users/me/profile` ✅
- `PUT /api/users/me/profile` ✅
- `GET /api/users/` ✅ (admin placeholder)

### Tax Forms (12 endpoints)
- `POST /api/tax-forms/` ✅
- `GET /api/tax-forms/` ✅
- `GET /api/tax-forms/{form_id}` ✅
- `PUT /api/tax-forms/{form_id}` ✅
- `DELETE /api/tax-forms/{form_id}` ✅
- `POST /api/tax-forms/{form_id}/dependents` ✅
- `GET /api/tax-forms/{form_id}/dependents` ✅
- `POST /api/tax-forms/{form_id}/w2s` ✅
- `GET /api/tax-forms/{form_id}/w2s` ✅
- `POST /api/tax-forms/{form_id}/1099s` ✅
- `GET /api/tax-forms/{form_id}/1099s` ✅
- `GET /api/tax-forms/{form_id}/compliance-checks` ✅

### Health (2 endpoints)
- `GET /` ✅
- `GET /api/health` ✅

**Total:** 24 API endpoints

---

## Security Features

### 1. **Password Security**
- ✅ Bcrypt hashing (rounds=12)
- ✅ Minimum 8 characters
- ✅ Must contain uppercase letter
- ✅ Must contain digit
- ✅ Never stored in plaintext

### 2. **SSN Encryption**
- ✅ Fernet symmetric encryption (AES-128 CBC)
- ✅ Automatic encryption before database storage
- ✅ Encryption key in .env.dev (SECRET_ENCRYPTION_KEY)
- ✅ Decrypt only when needed

### 3. **JWT Authentication**
- ✅ HS256 algorithm
- ✅ 30-day token expiry (configurable)
- ✅ Token includes user_id and email
- ✅ Bearer token in Authorization header

### 4. **Authorization**
- ✅ All endpoints (except register/login/health) require authentication
- ✅ Users can only access their own data
- ✅ Form ownership verification before CRUD operations
- ✅ 403 Forbidden for unauthorized access

### 5. **Audit Trail**
- ✅ All major actions logged (create, update, delete, login, logout)
- ✅ Logs include timestamp, user_id, action, resource_type, resource_id
- ✅ Optional IP address and user agent tracking

---

## Performance Features

### 1. **Database Connection Pooling**
- Pool size: 10 connections
- Max overflow: 20 connections
- Pool recycle: 3600 seconds (1 hour)
- Echo: True (logs SQL queries in development)

### 2. **Request Timing**
- X-Process-Time header on all responses
- Tracks request duration in seconds

### 3. **Efficient Queries**
- Pagination support (skip/limit parameters)
- Filtered queries (e.g., tax forms by year)
- Ordered results (e.g., tax forms by year DESC)

---

## Error Handling

### 1. **HTTP Status Codes**
- `200 OK` - Successful GET/PUT
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Validation error (duplicate email, duplicate year)
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource doesn't exist
- `422 Unprocessable Entity` - Pydantic validation error
- `500 Internal Server Error` - Database or server error

### 2. **Detailed Error Messages**
- Validation errors include field names and reasons
- Database errors caught and logged
- User-friendly error messages

---

## Next Steps

### ⏳ Task 2: Mode-Based Question Flow System (IN PROGRESS)

**Files to Create:**
1. `backend/app/mode_config.py` - Define 3 modes with question sets
2. `backend/app/question_engine.py` - Generate mode-appropriate questions
3. `backend/app/scenario_detector.py` - Analyze documents to skip questions
4. `src/components-vue/mode/ModeSelector.vue` - UI for mode selection

**Mode Definitions:**
- **Novice Mode:** Ask ALL ~50 questions with explanations
- **Intermediate Mode:** Ask ~20 smart questions based on documents
- **Expert Mode:** Ask ~5 critical questions with full automation

**API Endpoints to Add:**
- `GET /api/modes` - List available modes
- `GET /api/questions/{mode}` - Get questions for selected mode
- `POST /api/scenarios/detect` - Analyze uploaded documents
- `GET /api/forms/{form_id}/questions/next` - Get next question

---

## Testing Results

### ✅ Server Started Successfully
- No startup errors
- Database connection working
- All tables created
- API documentation accessible

### ✅ Swagger UI Accessible
- Interactive API docs at http://localhost:8000/api/docs
- All 24 endpoints visible
- Try-it-out functionality working

### ⚠️ Minor Warnings (Non-Critical)
- DeprecationWarning: `on_event` is deprecated
  - Solution: Migrate to lifespan event handlers (FastAPI 0.122+)
  - Impact: None - feature still works

---

## Documentation

### API Documentation
- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc

### Code Documentation
- All functions have docstrings
- Parameter descriptions included
- Return types annotated
- Example usage in comments

### Project Documentation
- ✅ `docs/README.md` - Documentation index
- ✅ `docs/PROJECT_STRUCTURE.md` - File structure guide
- ✅ `docs/IMPLEMENTATION_PLAN.md` - 10-task roadmap
- ✅ `docs/setup/QUICKSTART_DATABASE.md` - Database setup
- ✅ `docs/api/API_REFERENCE.md` - API documentation
- ✅ `docs/BACKEND_STATUS.md` - This file

---

## Conclusion

**Task 1 is 100% COMPLETE!** 🎉

The FastAPI backend is fully operational with:
- ✅ 9 database tables created
- ✅ 30+ CRUD operations
- ✅ 24 API endpoints
- ✅ JWT authentication
- ✅ Password hashing + SSN encryption
- ✅ Audit trail logging
- ✅ CORS middleware
- ✅ Error handling
- ✅ Health check
- ✅ API documentation

The system is now ready for Task 2: Mode-Based Question Flow System.

---

**Last Updated:** December 2024  
**API Version:** 1.0.0  
**Status:** 🟢 PRODUCTION READY
