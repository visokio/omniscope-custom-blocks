# Multipart Form Upload

Uploads files from a path column to a remote HTTP endpoint using multipart/form-data. For each row, posts the file, captures HTTP status, response body (truncated), and an error message if something goes wrong.

## Configuration
- Upload URL: target endpoint to POST to.
- File path: choose a single file on disk to upload (no input table required).
- Form field name: multipart field name (defaults to `file`).

## Behaviour
- Validates required options and file presence; missing/absent paths record an error without sending.
- Uses `requests.post` with a 30s timeout; records status, truncated body, and errors. Add headers by editing `CUSTOM_HEADERS` in `script.py` if needed.
- Output table preserves all input columns and adds `http_status`, `response_body`, and `error`.

## Language
Python

## Dependencies
requests

## Header example
Edit `CUSTOM_HEADERS` in `script.py` if your API needs auth or other headers:

```python
CUSTOM_HEADERS = {
    "Authorization": "Bearer YOUR_TOKEN_HERE",
    "ApiKey": "abc123"
}
```

## Source
[script.py](script.py)
