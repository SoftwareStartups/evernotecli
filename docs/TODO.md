# TODO items for this project

**IMPORTANT FOR AI: IGNORE THIS FILE**

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
  ```

## Todo items

- Global _client singleton — requires DI refactor
- EvernoteClient SRP — splitting into NoteStoreClient / TagResolver
- Token plaintext storage — acceptable for local dev tool; keyring integration is a separate feature
- CSRF in OAuth callback — OAuth 1.0a uses verifier, not state param; depends on Evernote's flow


- Claude security review
- Add Evernote creds as MCP env (already supported?) when not in .env
- Refactor tests with shared conftest?
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

- Implement integrations from https://github.com/verygoodplugins/mcp-evernote

