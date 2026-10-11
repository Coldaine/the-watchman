@echo off
REM EXECUTE-PARALLEL.bat - Actually launches parallel Claude instances on Windows
REM This WILL open multiple terminal windows with Claude running

echo ==========================================
echo PARALLEL CLAUDE EXECUTION - WINDOWS
echo This will open 4 NEW terminal windows
echo Each running a Claude instance
echo ==========================================
echo.

REM Create the task files first
mkdir tasks 2>nul

REM Task 1: Core Models (Simple, no dependencies)
(
echo You are building the Librarian Agent system. Your task: Create the data models.
echo.
echo Read: docs/architecture.md sections on Data Model
echo Read: docs/ADR/001-technology-stack-and-architecture-decisions.md
echo.
echo Create these files:
echo.
echo src/models/__init__.py
echo src/models/base.py - Base classes, enums, common types
echo src/models/documents.py - Document, Chunk, ParsedDocument using Pydantic
echo src/models/agents.py - AgentRequest, AgentResponse, Decision models
echo src/models/graph_schema.py - Node type definitions
echo.
echo src/config.py - Settings class using pydantic-settings
echo.
echo requirements.txt with: fastapi, uvicorn, pydantic, pydantic-settings, neo4j-driver
echo.
echo .env.template with all configuration variables
echo.
echo Write actual working Python code. Make sure all imports work.
echo When done, write "TASK 1 COMPLETE" to tasks/status.txt
) > tasks\claude_task1.txt

REM Task 2: Validation Engine (Can work independently)
(
echo You are building the Librarian Agent system. Your task: Create the validation engine.
echo.
echo Read: docs/subdomains/validation-engine.md
echo Read: docs/architecture.md section on Validation Rules
echo.
echo Create these files:
echo.
echo src/validation/__init__.py
echo src/validation/rules.py - Validation rule classes
echo src/validation/engine.py - Main ValidationEngine class with validate_request method
echo src/validation/exceptions.py - Custom exceptions
echo.
echo The engine should:
echo - Check document standards
echo - Validate architecture alignment
echo - Return ValidationResult with status: approved/rejected/escalated
echo.
echo Mock any database calls. Use dict/list for data storage.
echo Write actual working Python code.
echo When done, write "TASK 2 COMPLETE" to tasks/status.txt
) > tasks\claude_task2.txt

REM Task 3: FastAPI Server (Basic endpoints)
(
echo You are building the Librarian Agent system. Your task: Create the FastAPI server.
echo.
echo Read: docs/architecture.md section on API Design
echo Read: docs/subdomains/agent-protocol.md
echo.
echo Create these files:
echo.
echo src/__init__.py
echo src/main.py - FastAPI app with basic configuration
echo src/api/__init__.py
echo src/api/agent.py - Agent endpoints: POST /agent/request-approval
echo src/api/health.py - GET /health endpoint
echo.
echo Mock all database operations using in-memory dicts.
echo Server must run with: uvicorn src.main:app --reload
echo.
echo Write actual working Python code that starts successfully.
echo When done, write "TASK 3 COMPLETE" to tasks/status.txt
) > tasks\claude_task3.txt

REM Task 4: Basic Tests
(
echo You are building the Librarian Agent system. Your task: Create tests.
echo.
echo Create these test files:
echo.
echo tests/__init__.py
echo tests/test_models.py - Test all Pydantic models
echo tests/test_validation.py - Test validation engine
echo tests/test_api.py - Test API endpoints with TestClient
echo.
echo pytest.ini with basic configuration
echo.
echo All tests must pass when run with: pytest
echo Write actual working test code.
echo When done, write "TASK 4 COMPLETE" to tasks/status.txt
) > tasks\claude_task4.txt

echo Task files created!
echo.
echo Launching 4 Claude instances in parallel...
echo Each will open in a NEW window.
echo.

REM Launch Claude instances in new windows
REM Using 'start' command to open new terminal windows

echo Starting Claude Task 1: Models...
start "Claude Task 1 - Models" cmd /k claude chat ^< tasks\claude_task1.txt

timeout /t 2 /nobreak >nul

echo Starting Claude Task 2: Validation...
start "Claude Task 2 - Validation" cmd /k claude chat ^< tasks\claude_task2.txt

timeout /t 2 /nobreak >nul

echo Starting Claude Task 3: API...
start "Claude Task 3 - API" cmd /k claude chat ^< tasks\claude_task3.txt

timeout /t 2 /nobreak >nul

echo Starting Claude Task 4: Tests...
start "Claude Task 4 - Tests" cmd /k claude chat ^< tasks\claude_task4.txt

echo.
echo ==========================================
echo 4 CLAUDE INSTANCES NOW RUNNING!
echo ==========================================
echo.
echo Check each window to see progress.
echo They will write "TASK X COMPLETE" when done.
echo.
echo After all complete, run: claude chat
echo Then say: "Integrate the work from all 4 tasks"
echo.
pause