# Free deployment and rollback

## Streamlit Community Cloud

1. Push this repository to a GitHub repository.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/) and choose **New app**.
3. Select the repository, branch, and file `app.py`.
4. Set the Python version to 3.12 if the workspace offers a runtime selector.
5. Deploy. Community Cloud will install `requirements.txt` and start the dashboard.

GridPulse runs in deterministic demo mode without secrets. Optional provider
keys belong in the app's Secrets settings, never in Git:

```toml
# Optional only; the MVP does not require these values.
GEMINI_API_KEY = "..."
HF_TOKEN = "..."
LANGCHAIN_API_KEY = "..."
```

## Acceptance checks

- The landing page loads without an API key.
- Select each demo incident and run an investigation.
- Evidence includes source citations.
- The report remains awaiting human review until approval.
- The sidebar can be collapsed and reopened.

## Rollback

If a deployment fails, open the app's deployment menu and redeploy the last
known-good commit. Locally, reproduce the same revision with:

```bash
git checkout <known-good-commit>
streamlit run app.py
```

Return to the latest branch afterward with `git switch main` (or your default
branch name). Do not store secrets in commits while troubleshooting.
