import numpy as np
import pandas as pd
import opendp.prelude as dp
from omniscope.api import OmniscopeApi

dp.enable_features("contrib")

omniscope_api = OmniscopeApi()
input_1 = omniscope_api.read_input_records(input_number=0)
if input_1 is None:
    omniscope_api.abort("Connect a data source to the block's input.")


# --------------------------------------------------------------------------
# Options
# --------------------------------------------------------------------------

def get_option(name, default=None):
    """Read a block option, falling back to a default if it is unregistered."""
    try:
        value = omniscope_api.get_option(name)
    except KeyError:
        return default
    return default if value is None else value


def get_float_option(name, default):
    value = get_option(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        omniscope_api.abort(f"Option {name} must be a number, not {value!r}.")


epsilon_numeric = get_float_option("epsilon_numeric", 5.0)
sensitivity_numeric = get_float_option("sensitivity_numeric", 10.0)

epsilon_date = get_float_option("epsilon_date", 5.0)
sensitivity_date = get_float_option("sensitivity_date", 3600.0)  # one hour

if not (epsilon_numeric > 0 and epsilon_date > 0):
    omniscope_api.abort("The privacy budgets (numbers and dates) must be greater than zero.")
if not (sensitivity_numeric > 0 and sensitivity_date > 0):
    omniscope_api.abort("The sensitivities (numbers and dates) must be greater than zero.")


# --------------------------------------------------------------------------
# Noise
# --------------------------------------------------------------------------

def laplace_array(values, scale):
    """Add Laplace(scale) noise to a 1-D float array, leaving NaN entries as NaN.

    scale = sensitivity / epsilon, matching the diffprivlib parameterisation.
    """
    values = np.asarray(values, dtype=float)
    out = values.copy()
    finite = np.isfinite(values)
    if not finite.any():
        return out

    space = (
        dp.vector_domain(dp.atom_domain(T=float, nan=False)),
        dp.l1_distance(T=float),
    )
    measurement = dp.m.make_laplace(*space, scale=scale)
    out[finite] = (measurement >> dp.as_array())(out[finite].tolist())
    return out


# --------------------------------------------------------------------------
# Field handlers
# --------------------------------------------------------------------------

BASE_WORDS = [
    "apple", "banana", "cherry", "grape", "honeydew", "kiwi", "lemon", "mango",
    "nectarine", "orange", "papaya", "quince", "raspberry", "strawberry",
    "tangerine", "vanilla", "watermelon", "courgette", "abandon", "ability",
    "accept", "account", "achieve", "activity", "actually", "addition",
    "address", "adventure", "agreement", "alternative", "analysis", "analyse",
    "appearance", "application", "appropriate", "argument", "arrangement",
    "association", "assumption", "attraction", "authority", "available",
    "beautiful", "behaviour", "believe", "beneficial", "billion", "business",
    "calendar", "capability", "celebration", "challenge", "character",
    "children", "circular", "citizens", "clarity", "collection",
    "comfortable", "community", "competition", "complaint", "conclusion",
    "condition", "conference", "connection", "consideration", "construction",
    "consultation", "consumer", "conversation", "corporation", "creative",
    "critical", "customer", "database", "decision", "definition", "democracy",
    "development", "difference", "discussion", "education", "effective",
    "emergency", "emotional", "encouragement", "environment", "essential",
    "evaluation", "experience", "explanation", "exploration", "expression",
    "fascinate", "favourable", "financial", "foundation", "freedom",
    "friendship", "generally", "government", "guidance", "happiness",
    "historical", "immediate", "important", "impressive", "influence",
    "information", "inspiration", "interaction", "interesting", "introduction",
    "investigation", "knowledge", "leadership", "legislation", "literature",
    "management", "motivation", "observation", "opportunity", "organisation",
    "participation", "performance", "perspective", "political", "population",
    "presentation", "professional", "protection", "publication",
    "relationship", "representation", "responsibility", "satisfaction",
    "scientific", "significant", "situation", "sophisticated", "strategic",
    "successful", "technology", "treatment", "understanding", "volunteer",
    "wonderful", "workplace",
]


def is_text_column(series):
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


def is_noisable_numeric_column(series):
    # Booleans satisfy is_numeric_dtype but must not be noised.
    return (
        pd.api.types.is_numeric_dtype(series)
        and not pd.api.types.is_bool_dtype(series)
    )


def anonymize_text_fields(df, selected_fields):
    """Replace each distinct text value with a generated pseudonym.

    This is pseudonymisation, not anonymisation: the mapping is consistent
    within a run, so value frequencies survive and the same value in two
    columns maps to the same word. The mapping is re-randomised on every run.
    Nulls are preserved as nulls.
    """
    text_cols = [
        col for col in selected_fields
        if col in df.columns and is_text_column(df[col])
    ]
    if not text_cols:
        return

    unique_values = set()
    for col in text_cols:
        unique_values.update(df[col].dropna().unique())

    # Sort first so the shuffle starts from a defined order, then shuffle so
    # the pseudonyms do not preserve the sort order of the originals.
    ordered = sorted(unique_values, key=str)
    np.random.default_rng().shuffle(ordered)

    mapping = {
        value: f"{BASE_WORDS[i % len(BASE_WORDS)]}{(i // len(BASE_WORDS)) + 1}"
        for i, value in enumerate(ordered)
    }

    for col in text_cols:
        # map() of an empty or all-missing field gives float64; keep the field as text
        df[col] = df[col].map(mapping).astype(df[col].dtype)


def anonymize_numeric_fields(df, selected_fields, epsilon, sensitivity):
    scale = sensitivity / epsilon
    for col in selected_fields:
        if col in df.columns and is_noisable_numeric_column(df[col]):
            values = df[col].to_numpy(dtype=float, na_value=np.nan)
            noisy = laplace_array(values, scale)
            if pd.api.types.is_integer_dtype(df[col]):
                # whole-number fields stay whole numbers (rounding the noise keeps the privacy guarantee)
                df[col] = pd.array(np.round(noisy), dtype="Float64").astype("Int64")
            else:
                df[col] = noisy


def anonymize_date_fields(df, selected_fields, epsilon, sensitivity):
    scale = sensitivity / epsilon  # in seconds
    for col in selected_fields:
        if col not in df.columns or not pd.api.types.is_datetime64_any_dtype(df[col]):
            continue

        series = df[col]
        tz = getattr(series.dtype, "tz", None)
        epoch = pd.Timestamp(0, tz="UTC") if tz is not None else pd.Timestamp(0)

        seconds = (series - epoch).dt.total_seconds().to_numpy(dtype=float)
        noisy = laplace_array(seconds, scale)

        with np.errstate(invalid="ignore"):  # missing dates stay missing (NaN -> NaT)
            result = epoch + pd.to_timedelta(np.round(noisy), unit="s")
        result = pd.Series(result, index=df.index)
        if tz is not None:
            result = result.dt.tz_convert(tz)
        df[col] = result


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------

selected_fields = get_option("selectedFields")
if not selected_fields:
    selected_fields = list(input_1.columns)

output = input_1.copy()

anonymize_text_fields(output, selected_fields)
anonymize_numeric_fields(output, selected_fields, epsilon_numeric, sensitivity_numeric)
anonymize_date_fields(output, selected_fields, epsilon_date, sensitivity_date)

omniscope_api.write_output_records(output, output_number=0)
omniscope_api.close()