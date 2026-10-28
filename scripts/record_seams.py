import importlib.util
import pathlib

FAILED = "fail"


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_items = load_sibling("check_items")


def criterion_seam(criterion):
    seam = criterion.get("seam") if isinstance(criterion, dict) else None
    return seam if check_items.is_text(seam) else None


def builder_seams(seams):
    return frozenset(
        seam["name"]
        for seam in (seams if isinstance(seams, (list, tuple)) else ())
        if isinstance(seam, dict) and check_items.is_text(seam.get("name")) and seam.get("builder_runs") is True
    )


def is_blocking(criterion, status, builders):
    return status == FAILED and criterion_seam(criterion) in builders
