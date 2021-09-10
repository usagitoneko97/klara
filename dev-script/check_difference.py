#!/bin/env python3

from typing import *
import json
import click


@click.command()
@click.argument("inputs", nargs=2)
@click.option("-o", "--output", "output_file")
def check(inputs: List[str], output_file: str):
    file1, file2 = inputs
    items = []
    with open(file1, "r") as f:
        items.append(json.load(f))
    with open(file2, "r") as f:
        items.append(json.load(f))
    items = list(sorted(items, key=lambda x: len(x), reverse=True))
    long_item = items[0]
    long_item = process_item(long_item)
    short_item = items[1]
    short_item = process_item(short_item)
    missing = []
    for i, long in long_item.items():
        if i not in short_item:
            missing.append(long)
    print("Missing {} of instances".format(len(missing)))
    with open(output_file, "w") as f:
        json.dump(missing, f, indent=4)


def process_item(items):
    result = {}
    for ins in items:
        result[ins["#return-ori"]] = ins
    return result


if __name__ == "__main__":
    check()
