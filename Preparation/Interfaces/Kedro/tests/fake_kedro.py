"""A stand-in for the parts of Kedro the block uses (kedro.framework.session.KedroSession and
kedro.framework.startup.bootstrap_project), so the tests run without Kedro installed.

The fake catalog holds named datasets in memory; the fake run calls a Python function given by the test with the
catalog and returns what Kedro returns (the run's free outputs). Every call is recorded in `calls`."""
import sys
import types


class FakeCatalog:
    def __init__(self, data):
        self.data = data

    def __contains__(self, name):
        return name in self.data

    def save(self, name, value):
        calls.append(("save", name, len(value)))
        self.data[name] = value.copy()

    def load(self, name):
        calls.append(("load", name))
        return self.data[name]


calls = []
state = {"datasets": {}, "pipeline": None, "bootstrap_error": None}


class FakeSession:
    @classmethod
    def create(cls, project_path=None, env=None, **kw):
        calls.append(("create", str(project_path), env))
        return cls()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        calls.append(("close",))
        return False

    def load_context(self):
        return types.SimpleNamespace(catalog=FakeCatalog(state["datasets"]))

    def run(self, pipeline_name=None, **kw):
        calls.append(("run", pipeline_name))
        return state["pipeline"](FakeCatalog(state["datasets"]), pipeline_name)


def bootstrap_project(path):
    calls.append(("bootstrap", str(path)))
    if state["bootstrap_error"]:
        raise state["bootstrap_error"]


def install(monkeypatch, datasets, pipeline):
    """Put the fake modules in sys.modules (monkeypatch restores them) and reset the state."""
    calls.clear()
    state.update(datasets=datasets, pipeline=pipeline, bootstrap_error=None)
    kedro = types.ModuleType("kedro")
    framework = types.ModuleType("kedro.framework")
    session = types.ModuleType("kedro.framework.session")
    startup = types.ModuleType("kedro.framework.startup")
    session.KedroSession = FakeSession
    startup.bootstrap_project = bootstrap_project
    kedro.framework = framework
    framework.session, framework.startup = session, startup
    for name, mod in [("kedro", kedro), ("kedro.framework", framework), ("kedro.framework.session", session),
                      ("kedro.framework.startup", startup)]:
        monkeypatch.setitem(sys.modules, name, mod)
