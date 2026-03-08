# TODO items for this project

**IMPORTANT FOR AI: IGNORE THIS FILE**

- Fix bugs, end-end test
 ```
 given this note: {                                                                                                                                                                                                                                                                                                                                                             
    "guid": "01767038-6860-852a-4240-e1b23757e346",                                                                                                                                                                                                                                                                                                                              
    "title": "Dilip Kumar",                                                                                                                                                                                                                                                                                                                                                      
    "notebook_guid": "93dac817-9741-4f2d-9f9a-fb2bf0741994",                                                                                                                                                                                                                                                                                                                     
    "tag_guids": [],                                                                                                                                                                                                                                                                                                                                                             
    "created": "2025-05-06T08:30:56Z",                                                                                                                                                                                                                                                                                                                                       
    "updated": "2026-02-24T19:24:47Z",                                                                                                                                                                                                                                                                                                                                       
    "content_length": 2303                                                                                                                                                                                                                                                                                                                                                       
  }\                                                                                                                                                                                                                                                                                                                                                                         
  test and debug all encl cli commands, add and remove a tag "fcto", create a new note, etc. Once these are debugged and fixed, plan the creation of a proper end-end testsuite on the cli using the real evernote client                                                                                                                                                    
  ⎿  You've hit your limit · resets 2pm (Europe/Amsterdam)
  ```

## Todo items

- Add support for notes with a "private" tag:
```
Add support for ignoring notes with a "private" tag:
- Never read content of these notes
- Never remove the private tag on a note
- Never remove the private tag from the tags set
- Exclude the note from search results
- Add proper tests
- Think of other ways a hacker still could try to get access to these notes, and prevent this.
```

- Update docs
- Claude security review
- Add Evernote creds as MCP env (already supported?) when not in .env
- Refactor tests with shared conftest?
- Return tag names, not only tag guids on get note
- More advanced search

- More features, see full-evernote-mcp and tools-evernote-mcp
- Option to select or exclude features in MCP and cli setup in .env (too dangerous)
- OCR, attachments, see full-evernote-mcp

```
Evernote’s Developer API enforces rate limits on a per-API-key, per-user, per-hour basis to ensure service performance. Exceeding these triggers an  EDAMSystemException  with  RATE_LIMIT_REACHED  and a  rateLimitDuration  in seconds before retrying.
Key Limits
Exact numerical limits aren’t publicly specified and vary by API key, but third-party reports indicate around 1000 requests per hour as a typical threshold, with some apps limited to as low as 60 requests per hour.
https://dev.evernote.com/doc/articles/rate_limits.php
https://moldstud.com/articles/p-effective-strategies-for-managing-api-rate-limit-exceedances-in-evernote-solutions
Solution: Queue API requests to evernote to handle rate limits. Persist tasks to file to make sure the client survices restarts. Combine with tenacity for API errors.
Sample code:
import time
import requests
from requests.exceptions import HTTPError

from persistqueue import Queue
from ratelimit import limits, sleep_and_retry
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)

API_URL = "https://api.example.com/endpoint"
QUEUE_PATH = "api_tasks"

# Persistent queue survives restarts
task_queue = Queue(QUEUE_PATH)


# Rate-limited + retrying API call
@sleep_and_retry
@limits(calls=10, period=60)  # 10 calls per minute
@retry(
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(min=1, max=60),
    retry=retry_if_exception_type(HTTPError),
)
def make_api_call(payload: dict) -> dict:
    response = requests.post(API_URL, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def add_task(payload: dict) -> None:
    task_queue.put(payload)


def process_queue(poll_interval: float = 0.5) -> None:
    while True:
        if task_queue.empty():
            time.sleep(poll_interval)
            continue

        task = task_queue.get()
        try:
            result = make_api_call(task)
            print(f"SUCCESS: {task} → {result}")
        except Exception as exc:
            print(f"FAILED after retries: {exc} | Task: {task}")
        finally:
            task_queue.task_done()

```

- Implement resilience and integrations and Markdown convert options from https://github.com/verygoodplugins/mcp-evernote
