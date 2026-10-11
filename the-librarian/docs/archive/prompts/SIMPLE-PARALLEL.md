# Simple Parallel Claude Approach

## The Truth

I need to be honest - I don't actually know:
1. If `claude chat` accepts piped input
2. If there's a non-interactive batch mode
3. The exact command-line arguments available

## What We DO Know Works

### Manual Approach (Guaranteed to Work)

Open 4 terminal windows and in each one:
1. Run `claude chat`
2. Copy-paste a specific task
3. Let it work
4. Move to next window

### What to Copy-Paste

#### Window 1: Models
```
Read docs/architecture.md and create:
- src/models/base.py
- src/models/documents.py
- src/models/agents.py
- src/config.py
- requirements.txt
- .env.template

Use Pydantic for all models. Make sure code works.
```

#### Window 2: Validation
```
Read docs/subdomains/validation-engine.md and create:
- src/validation/rules.py
- src/validation/engine.py
- tests/test_validation.py

Mock database calls. Make tests pass.
```

#### Window 3: API
```
Read docs/architecture.md API section and create:
- src/main.py (FastAPI app)
- src/api/agent.py (agent endpoints)
- src/api/health.py (health check)

Must run with: uvicorn src.main:app
```

#### Window 4: Integration (After 1-3 done)
```
Integrate the code from the other 3 tasks:
- Make sure imports work
- Wire up the API to use validation
- Create a README.md
- Make sure server runs
```

## Testing Claude CLI Options

Before automating, test these in your terminal:

```powershell
# Test 1: Does Claude accept piped input?
echo "What is 2+2?" | claude chat

# Test 2: Does Claude have a batch mode?
claude chat --help

# Test 3: Can Claude read from file?
echo "What is 2+2?" > test.txt
claude chat < test.txt

# Test 4: Does --continue false work?
claude chat --continue false

# Test 5: Can we use Here-strings? (PowerShell)
@"
What is 2+2?
"@ | claude chat
```

## If Piping Works

If any of the above tests work, use this PowerShell script:

```powershell
# Start 3 Claude instances in parallel
Start-Job {
    @"
Read docs/architecture.md and create models...
[full task 1 text]
"@ | claude chat > logs/task1.log
}

Start-Job {
    @"
Read docs/subdomains/validation-engine.md...
[full task 2 text]
"@ | claude chat > logs/task2.log
}

Start-Job {
    @"
Create FastAPI server...
[full task 3 text]
"@ | claude chat > logs/task3.log
}

# Wait for all jobs
Get-Job | Wait-Job
```

## If Nothing Works Automatically

Just open 4 terminals and copy-paste. It's not elegant but it WILL work and you'll use your credits.

## Alternative: Use the API

If you have an API key, you could use the Claude API directly:

```python
import anthropic
from concurrent.futures import ThreadPoolExecutor

client = anthropic.Anthropic(api_key="...")

def run_task(task_prompt):
    response = client.messages.create(
        model="claude-3-opus-20240229",
        messages=[{"role": "user", "content": task_prompt}]
    )
    return response.content

tasks = [task1_text, task2_text, task3_text]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(run_task, tasks))
```

## The 90-Minute Reality

With your time constraint:
1. **Don't** try to build complex orchestration
2. **Don't** worry about elegance
3. **DO** open 4 terminals and start copying tasks
4. **DO** focus on getting code generated

The manual approach is inelegant but it WORKS and you'll get code written.