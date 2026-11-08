from kedro.pipeline import Pipeline

from orders_summary.pipelines import summary


def register_pipelines() -> dict[str, Pipeline]:
    pipelines = {"summary": summary.create_pipeline(), "clean": summary.create_clean_pipeline()}
    pipelines["__default__"] = pipelines["summary"]
    return pipelines
