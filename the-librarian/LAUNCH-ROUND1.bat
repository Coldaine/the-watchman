@echo off
REM LAUNCH-ROUND1.bat - Deploy 3 parallel agents for Round 1 implementation

echo ================================================
echo ROUND 1: PARALLEL AGENT DEPLOYMENT
echo Graph, Processing, and Validation Specialists
echo ================================================
echo.

REM Update coordination file with start time
echo Starting Round 1 agents...
echo.

REM Launch Agent 1: Graph Operations
echo Launching Agent 1: Graph Operations Specialist...
start "Agent 1 - Graph" cmd /k "echo AGENT 1: GRAPH OPERATIONS && echo. && echo Copy the contents of prompts\round1_agent1_graph.md && echo and paste into Claude when ready. && echo. && echo When complete, update coordination.json && echo. && pause && claude chat"

timeout /t 2 /nobreak >nul

REM Launch Agent 2: Document Processing
echo Launching Agent 2: Document Processing Specialist...
start "Agent 2 - Processing" cmd /k "echo AGENT 2: DOCUMENT PROCESSING && echo. && echo Copy the contents of prompts\round1_agent2_processing.md && echo and paste into Claude when ready. && echo. && echo When complete, update coordination.json && echo. && pause && claude chat"

timeout /t 2 /nobreak >nul

REM Launch Agent 3: Validation Engine
echo Launching Agent 3: Validation Engine Specialist...
start "Agent 3 - Validation" cmd /k "echo AGENT 3: VALIDATION ENGINE && echo. && echo Copy the contents of prompts\round1_agent3_validation.md && echo and paste into Claude when ready. && echo. && echo When complete, update coordination.json && echo. && pause && claude chat"

echo.
echo ================================================
echo 3 AGENTS LAUNCHED IN SEPARATE WINDOWS
echo ================================================
echo.
echo Instructions:
echo 1. In each window, copy the respective prompt file
echo 2. Let each agent work on their module
echo 3. Agents should update coordination.json
echo 4. When all complete, return here
echo.
echo Prompt files:
echo - Agent 1: prompts\round1_agent1_graph.md
echo - Agent 2: prompts\round1_agent2_processing.md
echo - Agent 3: prompts\round1_agent3_validation.md
echo.
echo Press any key when all agents have completed...
pause