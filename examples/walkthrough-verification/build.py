"""Build synthetic fixtures using the same approval and export path as a real guide."""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from cqa_artifacts import core


def build(target):
    target.mkdir(parents=True, exist_ok=False)
    with TemporaryDirectory() as private:
        for name, titles in (
            ("three", ["Choose a guide", "Review the instructions", "Finish the walkthrough"]),
            ("one", ["Review the instructions"]),
        ):
            workspace = Path(private) / name
            core.init(workspace, "SoFa Docs navigation pilot")
            for title in titles:
                core.add_step(workspace, title, "Synthetic walkthrough for navigation verification.")
            core.approve(workspace, "Synthetic fixture", True)
            core.export(workspace, target / name, "https://docs.example.com/" + name)
    shutil.copyfile(Path(__file__).with_name("checks.html"), target / "checks.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="new directory for public synthetic exports")
    build(parser.parse_args().destination)
