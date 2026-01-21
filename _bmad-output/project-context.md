---
project_name: 'sector-strenth'
user_name: 'Mark'
date: '2026-01-20'
sections_completed: ['discovery', 'technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'workflow_rules', 'critical_rules']
existing_patterns_found: 15
status: 'complete'
rule_count: 55
optimized_for_llm: true
---

# Project Context for AI Agents

_本文件包含 AI agents 在实现代码时必须遵循的关键规则和模式。重点关注 agents 可能忽略的不明显细节。_

---

## Technology Stack & Versions

### Frontend
- **Next.js**: 16.1.1 (major release - verify compatibility)
- **React**: 19.2.0 (latest - check hooks changes)
- **TypeScript**: 5 with strict mode enabled
- **Tailwind CSS**: 4.x (latest major version)

### Backend
- **FastAPI**: 0.104.1
- **SQLAlchemy**: 2.0.23 (async patterns required)
- **PostgreSQL**: 14+ via asyncpg 0.29.0
- **Alembic**: 1.12.1 (database migrations)
- **Pydantic**: 2.12.5

### Key Libraries
- **State**: Redux Toolkit 2.11.0 + Zustand 5.0.9
- **Charts**: ECharts 6.0.0
- **Auth**: python-jose 3.3.0 (JWT)
- **Data**: Pandas 2.0+, NumPy 1.24+, AKShare 1.12.0+
- **Testing**: Jest 30.2.0 + Testing Library

### Critical Version Notes
- Next.js 16.x may have breaking changes - test thoroughly
- React 19.2.0 requires correct hooks usage
- TypeScript strict mode is enforced - no implicit any
- SQLAlchemy 2.0+ requires async/await patterns

---

## Critical Implementation Rules

### Language-Specific Rules

#### TypeScript/JavaScript
- **Strict mode enforced** - no implicit any, strict null checks
- **Import paths**: Use `@/` alias, never relative paths like `../../`
- **Component files**: PascalCase.tsx (e.g., ClassificationTable.tsx)
- **Hook files**: camelCase.ts (e.g., useSectorClassification.ts)
- **Type files**: PascalCase.ts or kebab-case-types.ts
- **JSX**: Use new JSX transform (react-jsx)
- **Error messages**: Must be Chinese for user-facing content

#### Python
- **File naming**: snake_case.py (e.g., sector_classification_service.py)
- **Async required**: SQLAlchemy 2.0+ requires async/await patterns
- **Type hints**: Required for all function parameters and returns

### Framework-Specific Rules

#### React/Next.js
- **'use client' directive** required for components using hooks/state
- **Component files** must export named functions, not default exports
- **Props interface** required for all components
- **Hooks**: Only at top level, never in conditions/loops
- **State management**:
  - Redux Toolkit for global state (use createSlice + createAsyncThunk)
  - Zustand for component-local state
- **Performance**:
  - Use react-window for large lists
  - Memoize ECharts configurations
  - Avoid creating new functions/objects in render

#### FastAPI
- **Endpoint naming**: kebab-case for routes (e.g., /sector-classifications)
- **Function naming**: snake_case for Python functions
- **Docstrings**: Chinese required for all endpoint documentation
- **Dependency injection**: Use `Depends()` for database sessions
- **Response models**: Use Pydantic for request/response validation

### Testing Rules

#### Test Organization
- **Test file locations**:
  - `tests/**/__tests__/**/*.{test,spec}.{ts,tsx}`
  - `tests/**/*.{test,spec}.{ts,tsx}`
- **Test naming**: ComponentName.test.tsx or FeatureName.spec.ts
- **Coverage collection**: From `src/**/*.{ts,tsx}` only
- **Exclusions**: layout.tsx, page.tsx, globals.css, .d.ts files

#### Mock Usage
- **API calls** must be mocked in component tests
- **Mock setup** in jest.setup.js for global mocks
- **Use jest-fetch-mock** or jest.mock() for external dependencies

#### Test Structure
- **Unit tests**: Test component behavior in isolation
- **Integration tests**: Test API flows and user journeys
- **Test timeout**: 10000ms default
- **Environment**: jsdom for React component tests

### Code Quality & Style Rules

#### Linting/Formatting
- **ESLint**: Uses nextVitals + nextTs configs
- **TypeScript**: Strict type checking enforced
- **Ignores**: .next, out, build directories

#### Code Organization
- **Frontend**: Layered structure (app/components/lib/store/hooks/types)
- **Backend**: Layered structure (api/endpoints/services/models/tests)
- **Component grouping**: Group by feature (e.g., sector-classification/)
- **UI components**: shadcn/ui base components in components/ui/

#### Naming Conventions
- **Component files**: PascalCase.tsx
- **Hook files**: camelCase.ts (use prefix)
- **Type files**: kebab-case.ts
- **Store files**: camelCase.ts
- **Python files**: snake_case.py
- **API routes**: kebab-case (e.g., /sector-classifications)

#### Documentation Requirements
- **Python docstrings**: Chinese required for all endpoints
- **TypeScript comments**: JSDoc for complex functions
- **README**: Chinese for user-facing docs

### Development Workflow Rules

#### Git/Repository
- **Branch naming**: Use descriptive names (epic-{number}-{name}, feature-{name})
- **Commit format**: Conventional commits (feat/fix/refactor/chore/docs)
- **Language**: Chinese for commit messages
- **PR reviews**: Required before merging

#### Database Migrations
- **Tool**: Alembic (not raw SQL)
- **Commands**:
  - `alembic revision -m "description"` - Create migration
  - `alembic upgrade head` - Apply migrations
  - `alembic downgrade -1` - Rollback one step

#### Deployment
- **Method**: Docker Compose
- **Environment**: .env files for configuration
- **Migrations**: Run Alembic migrations as part of deployment

### Critical Don't-Miss Rules

#### Anti-Patterns to Avoid
- **Never use relative imports** like `../../` - always use `@/` alias
- **Never use default exports** for components - use named exports
- **Never use fetch directly** - always use the ApiClient class
- **Never use PascalCase for API routes** - use kebab-case
- **Never use PascalCase for Python functions** - use snake_case

#### Edge Cases
- **Next.js 16.x**: 'use client' required for any component using hooks/state
- **SQLAlchemy 2.0+**: async/await is mandatory, no sync database calls
- **ChanLun algorithm**: 8 MAs, 9 classifications, 100% accuracy required
- **JWT expiration**: Handle token refresh automatically

#### Security Rules
- **All API endpoints** require JWT authentication (`Depends(get_current_user)`)
- **Admin functions** require RBAC verification
- **Sensitive data** (passwords, tokens) must never be logged
- **Audit logs** must be retained for 6 months

#### Performance Gotchas
- **Large lists**: Use react-window for 100+ items
- **ECharts**: Memoize configuration objects with useMemo
- **No inline functions/objects** in render (useCallback/useMemo)
- **Cache daily data**: 24-hour TTL for classification results

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

**Last Updated:** 2026-01-20
