import pandas as pd
from datetime import datetime
from dateutil import parser as dateutil_parser
from omniscope.api import OmniscopeApi

api = OmniscopeApi()

# ============================================================================
# OMNISCOPE CUSTOM BLOCK: Smart Date Parser (Streaming)
# ============================================================================

def opt(name, default):
    """Get option value with fallback to default."""
    v = api.get_option(name)
    return default if v is None or str(v).strip() == "" else v

# Configuration options
fields_to_parse = api.get_option("fields_to_parse")  # This is an array/list
output_suffix = api.get_option("output_suffix")  # Can be None/empty
if output_suffix:
    output_suffix = str(output_suffix).strip()
else:
    output_suffix = ""

prefer_day_first = str(opt("prefer_day_first", "false")).strip().lower() in ("true", "1", "yes", "y")
add_failure_flag = str(opt("add_failure_flag", "true")).strip().lower() in ("true", "1", "yes", "y")
custom_formats = str(opt("custom_formats", "")).strip()
keep_original = str(opt("keep_original_fields", "true")).strip().lower() in ("true", "1", "yes", "y")

# Validate fields_to_parse
if not fields_to_parse or len(fields_to_parse) == 0:
    api.abort("fields_to_parse option is required. Select at least one field to parse.")

parse_fields = fields_to_parse  # Already a list

# Parse custom formats (this one IS comma-separated text)
extra_formats = []
if custom_formats:
    extra_formats = [f.strip() for f in custom_formats.split(",") if f.strip()]

# ============================================================================
# Date Parsing Logic
# ============================================================================

def parse_flexible_date(date_value, day_first=False, extra_fmts=None):
    """
    Attempts to parse a date string using multiple strategies.
    Returns datetime object or None if parsing fails.
    """
    if pd.isna(date_value) or date_value == '':
        return None
    
    date_str = str(date_value).strip()
    if not date_str:
        return None
    
    # Strategy 1: Try dateutil parser with specified day_first preference
    try:
        parsed_date = dateutil_parser.parse(date_str, dayfirst=day_first)
        return parsed_date  # Return datetime object, not ISO string
    except:
        pass
    
    # Strategy 2: Try opposite day_first setting as fallback
    try:
        parsed_date = dateutil_parser.parse(date_str, dayfirst=not day_first)
        return parsed_date
    except:
        pass
    
    # Strategy 3: Try custom formats first (if provided)
    if extra_fmts:
        for fmt in extra_fmts:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date
            except:
                continue
    
    # Strategy 4: Explicit common format attempts
    common_formats = [
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d',
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%m-%d-%Y',
        '%d-%m-%Y',
        '%Y/%m/%d %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%Y%m%d',
        '%d %b %Y',
        '%d %B %Y',
        '%b %d, %Y',
        '%B %d, %Y',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S',
    ]
    
    for fmt in common_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date
        except:
            continue
    
    return None

# ============================================================================
# Chunk Processing
# ============================================================================

def handle_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Process each chunk of data."""
    
    # Preserve original column order
    original_columns = list(chunk.columns)
    result = chunk.copy()
    
    for field in parse_fields:
        if field not in chunk.columns:
            continue
        
        # Determine output field name
        if output_suffix:
            output_field = field + output_suffix
        else:
            output_field = field  # Overwrite in place
        
        # Parse the date field - returns datetime objects
        parsed_values = chunk[field].apply(
            lambda x: parse_flexible_date(x, day_first=prefer_day_first, extra_fmts=extra_formats)
        )
        
        # Convert to pandas datetime (handles NaT properly)
        parsed_values = pd.to_datetime(parsed_values, errors='coerce')
        
        # If overwriting, replace the original column
        if output_field == field:
            result[field] = parsed_values
        else:
            # Add new column right after the original field
            col_idx = original_columns.index(field) + 1
            original_columns.insert(col_idx, output_field)
            result[output_field] = parsed_values
        
        # Add failure flag if requested
        if add_failure_flag:
            flag_field = output_field + "_failed"
            flag_values = parsed_values.isna() & chunk[field].notna()
            
            # Insert flag right after the parsed field
            if output_field in original_columns:
                flag_idx = original_columns.index(output_field) + 1
            else:
                flag_idx = original_columns.index(field) + 1
            original_columns.insert(flag_idx, flag_field)
            result[flag_field] = flag_values
    
    # Drop original fields if requested and we're using a suffix
    if not keep_original and output_suffix:
        fields_to_drop = [f for f in parse_fields if f in result.columns]
        if fields_to_drop:
            result = result.drop(columns=fields_to_drop)
            original_columns = [c for c in original_columns if c not in fields_to_drop]
    
    # Return with preserved column order
    return result[original_columns]

# ============================================================================
# Execute Streaming Processing
# ============================================================================

api.process_stream(handle_chunk)