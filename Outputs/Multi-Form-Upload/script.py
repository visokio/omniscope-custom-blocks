"""Uploads files from a path column to a remote HTTP endpoint using multipart/form-data."""

import mimetypes
import os
from typing import Optional

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

# Limits and defaults to keep cells tidy and requests reasonable.
MAX_RESPONSE_LENGTH = 8000
REQUEST_TIMEOUT_SECONDS = 30

# Manual headers: edit this dict to include any headers your API requires,
# for example {"Authorization": "Bearer YOUR_TOKEN", "ApiKey": "abc123"}.
CUSTOM_HEADERS: dict = {}


def truncate_text(text: Optional[str], limit: int = MAX_RESPONSE_LENGTH) -> str:
    """Trim long text responses to keep table cells manageable."""
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "... [truncated]"


def upload_file(upload_url: str, file_path: str, field_name: str, headers: dict) -> requests.Response:
    """Upload a single file using multipart/form-data."""
    mime_type, _ = mimetypes.guess_type(file_path)
    with open(file_path, "rb") as file_handle:
        files = {
            field_name: (
                os.path.basename(file_path),
                file_handle,
                mime_type or "application/octet-stream",
            )
        }
        return requests.post(upload_url, headers=headers, files=files, timeout=REQUEST_TIMEOUT_SECONDS)


def main() -> None:
    api = OmniscopeApi()

    try:
        upload_url = api.get_option("upload_url")
        file_path_option = api.get_option("file_path_column")
        form_field_name = api.get_option("form_field_name") or "file"
        if not upload_url:
            raise ValueError("Upload URL is required.")
        if not file_path_option:
            raise ValueError("File path is required.")

        # Prepare a single output row.
        output_df = pd.DataFrame(
            [
                {
                    "file_path": file_path_option,
                    "http_status": 0,
                    "response_body": "",
                    "error": "",
                }
            ]
        )

        status = 0
        body = ""
        error_msg = ""

        if not os.path.isfile(file_path_option):
            error_msg = f"File not found: {file_path_option}"
        else:
            try:
                response = upload_file(upload_url, file_path_option, form_field_name, headers=CUSTOM_HEADERS)
                status = response.status_code
                body = truncate_text(response.text)
                if not response.ok:
                    error_msg = f"HTTP {status}"
            except requests.RequestException as exc:
                error_msg = str(exc)

        output_df.loc[0, "http_status"] = status
        output_df.loc[0, "response_body"] = body
        output_df.loc[0, "error"] = error_msg

        api.write_output_records(output_df, output_number=0)
    finally:
        api.close()


if __name__ == "__main__":
    main()
