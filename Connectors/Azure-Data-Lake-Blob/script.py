"""Azure Data Lake Storage Gen2 Blob: reads one CSV or Parquet blob from an Azure storage container."""
import io
import json
from decimal import Decimal

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def text_option(name):
    value = omniscope_api.get_option(name)
    return value.strip() if isinstance(value, str) else ""


connection_string = text_option("connectionString")
container_name = text_option("containerName")
blob_path = text_option("blobPath").lstrip("/")
file_type = omniscope_api.get_option("fileType") or "Auto"

if not connection_string:
    omniscope_api.abort("Enter the storage account's connection string (Access keys in the Azure portal).")
if not container_name or not blob_path or blob_path.endswith("/"):
    omniscope_api.abort("Enter the container name and the path of a file in it, for example sales/2026/march.parquet.")

name = blob_path.lower()
if name.endswith(".gz"):
    name = name[:-3]
if file_type == "Auto":
    if name.endswith((".parquet", ".pq")):
        file_type = "Parquet"
    elif name.endswith((".csv", ".txt", ".tsv")):
        file_type = "CSV"
    else:
        omniscope_api.abort(f"Can't tell the file type of {blob_path!r} from its extension; choose CSV or Parquet.")

HINTS = {
    "ResourceNotFoundError": " Check the container name and the blob path (they are case-sensitive).",
    "ClientAuthenticationError": " Check the connection string; the account key may have been rotated.",
    "ValueError": " Check the connection string: copy the whole value from Access keys in the Azure portal.",
}

try:
    from azure.storage.blob import BlobServiceClient

    service = BlobServiceClient.from_connection_string(connection_string)
    blob = service.get_container_client(container_name).get_blob_client(blob_path)
    omniscope_api.update_message(f"Downloading {blob_path}")
    content = blob.download_blob().readall()
except ImportError:
    raise
except Exception as exc:  # the Azure SDK's own errors, without importing azure.core here
    kind = type(exc).__name__
    first_line = (str(exc).strip().splitlines() or [""])[0].rstrip(".")
    omniscope_api.abort(f"Could not read {container_name}/{blob_path}: {kind}: {first_line}.{HINTS.get(kind, '')}")

if not content:
    omniscope_api.abort(f"{container_name}/{blob_path} is empty.")

# Read from memory: nothing is written to the working folder
compression = "gzip" if blob_path.lower().endswith(".gz") else None
try:
    if file_type == "Parquet":
        if compression:
            import gzip
            content = gzip.decompress(content)
        data = pd.read_parquet(io.BytesIO(content))
    else:
        sep = "\t" if name.endswith(".tsv") else ","
        data = pd.read_csv(io.BytesIO(content), sep=sep, compression=compression)
except Exception as exc:
    omniscope_api.abort(f"Could not read {blob_path} as {file_type}: {type(exc).__name__}: {exc}. "
                        "Check the file type option.")


def json_text(value):
    return json.dumps(value, ensure_ascii=False,
                      default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


def to_omniscope(df):
    """Make types a Parquet file can hold but an Omniscope field can't (categories, decimals, lists, structs,
    durations) into numbers or text."""
    df = df.reset_index(drop=True)
    for col in df.columns:
        s = df[col]
        if isinstance(s.dtype, pd.CategoricalDtype):
            s = s.astype(object).where(s.notna(), None)
        if pd.api.types.is_timedelta64_dtype(s.dtype):
            s = s.dt.total_seconds()
        elif s.dtype == object:
            present = s.dropna()
            if len(present) and present.map(lambda v: isinstance(v, Decimal)).all():
                s = pd.to_numeric(s.map(lambda v: None if v is None else float(v)))
            elif present.map(lambda v: isinstance(v, (list, dict, tuple, np.ndarray))).any():
                s = s.map(lambda v: v if not isinstance(v, (list, dict, tuple, np.ndarray)) else json_text(v))
            elif present.map(lambda v: isinstance(v, bytes)).any():
                s = s.map(lambda v: v.hex() if isinstance(v, bytes) else v)
        df[col] = s
    return df


data = to_omniscope(data)
omniscope_api.write_output_records(data, output_number=0)
omniscope_api.close(f"{len(data)} records from {blob_path}")
