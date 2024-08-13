import json
from pathlib import Path
import click


def tree_item(dir_path: Path):
    filter = "*.txt"
    if dir_path.match(filter):
        return str(dir_path.name)
    elif dir_path.is_dir():
        return build_tree(dir_path)
    else:
        return None


def build_tree(dir_path: Path):
    """A recursive tree builder, given a directory Path object
    will build a list based tree of folder names and text file names
    """
    items = [tree_item(path) for path in dir_path.iterdir()]
    return {str(dir_path.name): [item for item in items if item is not None]}


@click.command()
@click.option(
    "--folder",
    type=click.Path(file_okay=False, exists=True),
)
@click.argument(
    "outputfile",
    type=click.Path(dir_okay=False, writable=True),
)
def folder_to_json_tree(folder, outputfile):
    with open(outputfile, "w", encoding="utf-8") as file:
        json.dump(build_tree(Path(folder)), file, ensure_ascii=False)


# generate-cards from-text input.txt pipeline "ru_core" translate output-sidebyside output.html
