# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Schedule Concierge is a bilingual (Japanese/English) task and calendar management system with AI-powered NLP scheduling. It consists of a FastAPI backend and Next.js frontend with JWT authentication, smart task recommendations, and external calendar integration.

## Common Development Commands

### Backend (FastAPI/Python)
```bash
cd backend
pip install -e .[dev]  # Install with dev dependencies
pytest  # Run all tests
pytest tests/unit/  # Run unit tests only
pytest tests/integration/  # Run integration tests only
pytest --coverage  # Run with coverage report
uvicorn app.main:app --reload  # Start dev server on port 8000
python -m pytest -xvs tests/  # Run tests with verbose output
```

### Frontend (Next.js/TypeScript)
```bash
cd frontend
npm install  # Install dependencies
npm run dev  # Start dev server on port 3000
npm run build  # Build for production
npm run start  # Start production server
npm run lint  # Lint code
npm test  # Run Jest tests
npm run test:watch  # Run tests in watch mode
npm run test:coverage  # Run tests with coverage
```

### Testing Commands
- Backend uses pytest with asyncio support and coverage reporting (80% minimum)
- Frontend uses Jest with jsdom environment and Testing Library
- Integration tests cover API endpoints and database interactions
- Unit tests focus on service layer logic and components

## Architecture & Structure

### Backend Architecture
- **FastAPI** web framework with async/await support
- **SQLAlchemy** ORM with PostgreSQL (SQLite for tests)
- **JWT authentication** with optional demo mode
- **Prometheus metrics** for monitoring
- **Service layer pattern** with clear separation:
  - `api/` - FastAPI route handlers
  - `services/` - Business logic (auth, events, tasks, recommendations, NLP)
  - `db/` - Database models and session management

### Key Backend Services
- `auth_service.py` - JWT token management and user authentication
- `event_service.py` - Calendar event CRUD and conflict detection
- `task_service.py` - Task management and lifecycle
- `recommendation_service.py` - Slot suggestion algorithm with scoring
- `nlp_service.py` - Natural language parsing for schedule creation
- `conflict_service.py` - Automatic rescheduling and conflict resolution

### Frontend Architecture
- **Next.js 15** with TypeScript and React 19
- **Component-based** with reusable UI elements
- **API client service** for backend communication
- **Jest + Testing Library** for comprehensive testing

### Key Frontend Components
- `TaskManager.tsx` - Task CRUD interface with status management
- `EventManager.tsx` - Calendar event management
- `SlotRecommendation.tsx` - Displays recommended time slots
- `api-client.ts` - Centralized API communication service

### Database Models
- `User` - Authentication and preferences (timezone, locale)
- `Task` - Work items with priority, energy tags, and due dates  
- `Event` - Calendar entries with conflict detection
- `Calendar` - Container for events with external sync support
- `IntegrationAccount` - OAuth tokens for external services

### NLP & Scheduling Features
- Natural language parsing for Japanese and English schedule input
- Smart slot recommendation based on:
  - Due date proximity
  - Priority levels (1-5)
  - Energy tags (morning, afternoon, deep focus)
  - Existing calendar conflicts
  - Work hour availability (9 AM - 5 PM weekdays)
- Automatic conflict detection and rescheduling proposals

## Important Implementation Details

### Authentication Flow
- JWT tokens with optional refresh mechanism
- Demo mode with automatic `demo-user` creation
- Database RLS (Row Level Security) planned for multi-tenant support
- Current implementation uses single-tenant with user_id filtering

### Recommendation Algorithm
The `compute_slots` function implements a scoring system considering:
- Time until due date (urgency factor)
- Task priority (1=highest, 5=lowest)
- Energy tag matching to time of day
- Buffer time between events
- Focus time protection

### Testing Strategy
- **Unit tests** for service layer logic
- **Integration tests** for API endpoints with database
- **Frontend tests** for components and API client
- Shared test utilities in `conftest.py` for database setup
- Async test support with pytest-asyncio

### Error Handling
- Custom exception hierarchy with `BaseAppException`
- Structured error responses with codes and messages
- Prometheus metrics for request counting and latency
- Health check endpoint at `/healthz`

## Development Tips

### Database Development
- SQLite used in tests with in-memory database
- SQLAlchemy models auto-create tables in test environment
- Use `get_db()` dependency injection for database sessions
- Run database operations within service layer, not directly in routes

### API Development
- All routes require authentication except health checks
- Use Pydantic models for request/response validation
- Follow REST conventions with proper HTTP status codes
- Implement proper error handling with structured responses

### Frontend Development  
- Use TypeScript strictly with proper type definitions in `types/api.ts`
- Implement comprehensive tests for all components
- Follow Next.js 15 app router patterns
- Use async/await for API calls with proper error handling

### Code Style
- Backend follows Python conventions with type hints
- Frontend uses TypeScript with strict mode
- No unused imports or variables
- Consistent error handling patterns across layers

### Google Calendar Integration (NEW)
- **Complete OAuth 2.0 flow** with PKCE security
- **Bidirectional sync** - events created locally sync to Google, Google events import to local
- **Real-time webhooks** for incremental updates 
- **Frontend UI** with connect/disconnect/sync controls
- **Token management** with automatic refresh
- **Error handling** with graceful fallbacks

#### Setup Requirements
Set environment variables for Google OAuth:
```bash
export GOOGLE_CLIENT_ID="your_google_client_id"
export GOOGLE_CLIENT_SECRET="your_google_client_secret"
```

#### API Endpoints
- `GET /integrations/google/auth-url` - Get OAuth authorization URL
- `POST /integrations/google/connect` - Exchange code for tokens  
- `POST /integrations/google/sync-calendars` - Import Google calendars
- `POST /integrations/google/sync-events` - Import Google events
- `DELETE /integrations/google/disconnect` - Revoke integration
- `POST /integrations/webhooks/google` - Handle Google webhook notifications

#### Usage Flow
1. User clicks "Connect Google Calendar" in frontend
2. Redirects to Google OAuth with PKCE challenge
3. User authorizes, returns to `/oauth/callback` page
4. Frontend exchanges code for tokens via API
5. User can sync calendars and events bidirectionally
6. Events auto-sync to Google when created locally