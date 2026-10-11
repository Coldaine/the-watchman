@echo off
REM RUN-NOW.bat - Windows version - Execute this immediately!
REM Time: 90 minutes max

echo ==========================================
echo RAPID LIBRARIAN AGENT IMPLEMENTATION
echo Using parallel Claude instances
echo Started at: %date% %time%
echo ==========================================

REM Create necessary directories
mkdir src\models 2>nul
mkdir src\api 2>nul
mkdir src\validation 2>nul
mkdir tests 2>nul
mkdir tasks 2>nul
mkdir logs 2>nul

REM TASK 1: Models and Configuration
echo Creating Task 1: Models and Configuration...
(
echo Create the following files based on docs/architecture.md:
echo.
echo 1. src/models/base.py:
echo - Pydantic BaseModel configurations
echo - Common enums ^(Status, ActionType, etc.^)
echo.
echo 2. src/models/documents.py:
echo - Document, Chunk, ParsedDocument models
echo.
echo 3. src/models/agents.py:
echo - AgentRequest, AgentResponse, Decision models
echo.
echo 4. src/config.py:
echo - Settings class using pydantic-settings
echo - Load from environment variables
echo.
echo 5. requirements.txt with:
echo - fastapi, uvicorn, pydantic, pydantic-settings
echo - neo4j-driver, langchain, ollama
echo.
echo 6. .env.template with all needed variables
echo.
echo Make sure all imports work. Use type hints everywhere.
) > tasks\task1_models.txt

REM TASK 2: Validation
echo Creating Task 2: Validation Engine...
(
echo Create validation system based on docs/subdomains/validation-engine.md:
echo.
echo 1. src/validation/rules.py:
echo - Define validation rules as classes
echo - DocumentStandardsRule, VersionCompatibilityRule, etc.
echo.
echo 2. src/validation/engine.py:
echo - ValidationEngine class
echo - validate_request^(^) method
echo - Returns ValidationResult with status ^(approved/rejected/escalated^)
echo.
echo 3. tests/test_validation.py:
echo - Test each validation rule
echo - Test the engine with various requests
echo - Make all tests pass
echo.
echo Use the models from task1 output. Mock any database calls.
) > tasks\task2_validation.txt

REM TASK 3: API
echo Creating Task 3: FastAPI Server...
(
echo Create FastAPI server based on docs/architecture.md:
echo.
echo 1. src/main.py:
echo - FastAPI app initialization
echo - Error handlers and middleware
echo.
echo 2. src/api/agent_endpoints.py:
echo - POST /agent/request-approval
echo - POST /agent/report-completion
echo - Use validation engine from task2
echo.
echo 3. src/api/health.py:
echo - GET /health endpoint
echo - GET /metrics endpoint ^(basic^)
echo.
echo 4. test_api.sh:
echo - curl commands to test each endpoint
echo - Example request/response
echo.
echo Server must run with: uvicorn src.main:app --reload
echo Mock all database operations for now.
) > tasks\task3_api.txt

REM TASK 4: Integration
echo Creating Task 4: Integration...
(
echo Integrate all components and create:
echo.
echo 1. src/coordinator.py:
echo - Coordinate between validation and API
echo - Handle the full request flow
echo - Return appropriate responses
echo.
echo 2. README.md with:
echo - What's implemented vs mocked
echo - How to run the server
echo - Example API calls
echo - Next steps
echo.
echo 3. run.sh script that:
echo - Checks dependencies
echo - Starts Neo4j ^(if available^)
echo - Runs the FastAPI server
echo.
echo 4. Run pytest and fix any failing tests
echo.
echo Make sure the server handles at least one full agent request flow.
) > tasks\task4_integrate.txt

echo.
echo ==========================================
echo TASKS CREATED! Now run these in SEPARATE terminals:
echo ==========================================
echo.
echo Terminal 1:
echo   claude chat ^< tasks\task1_models.txt
echo.
echo Terminal 2:
echo   claude chat ^< tasks\task2_validation.txt
echo.
echo Terminal 3:
echo   claude chat ^< tasks\task3_api.txt
echo.
echo After all complete, run:
echo   claude chat ^< tasks\task4_integrate.txt
echo.
echo ==========================================
echo GO GO GO! You have 90 minutes!
echo ==========================================

pause