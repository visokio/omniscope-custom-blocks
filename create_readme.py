#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: nils
"""




readme_file_name = "README.md"

# a new index.json is created for all individual block manifests that have a supported optionsVersion
supported_options_versions = [1]



import os
import json
from os import path
import urllib.parse
from functools import cmp_to_key

def create_header(f):
    f.write("# Omniscope Custom Blocks")
    f.write(" &middot; ")
    f.write("[![Refresh index](https://github.com/visokio/omniscope-custom-blocks/actions/workflows/refresh_index.yml/badge.svg)](https://github.com/visokio/omniscope-custom-blocks/actions/workflows/refresh_index.yml)")
    f.write("[![Refresh readme](https://github.com/visokio/omniscope-custom-blocks/actions/workflows/refresh_readme.yml/badge.svg)](https://github.com/visokio/omniscope-custom-blocks/actions/workflows/refresh_readme.yml)")
    f.write("\n\n")
    f.write("Public repository for custom blocks for Omniscope Evo.\n")
    f.write("\n")
    f.write("#### [Python / R API docs](https://help.visokio.com/support/solutions/articles/42000071109-custom-block-r-python-api-reference)\n")
    f.write("\n")

def compare(a, b):

    if a is None:
        return 1
    if b is None:
        return -1

    if a > b: return 1
    elif a < b: return -1
    else: return 0


def get_sections(blocks):
    sections = {}

    for block in blocks:

        category = block["category"]
        subcategory = None

        if not block["category"] in sections:
            sections[category] = {}

        if "subcategory" in block and not block["subcategory"] is None:
            subcategory = block["subcategory"]

        if not subcategory in sections[category]:
            sections[category][subcategory] = []

        sections[category][subcategory].append(block)

    return sections




def create_instructions(f):
    f.write("## How to add a block to this repository\n")
    f.write("### The simple way\n")
    f.write("1. Design your custom block in Omniscope Evo 2020.1 or later.\n")
    f.write("   The source code should be reasonably documented and potentially contain sections to describe input fields and parameters.\n")
    f.write("2. Export as a ZIP file from the block dialog.\n")
    f.write("3. Send the file to support@visokio.com and we will include it for you.\n\n")

    f.write("### The hard way\n")

    f.write("1. Follow points 1-2 from the simple way.\n")
    f.write("2. Fork the repository.\n")
    f.write("3. Create or use a directory in the forked repository under one of the main sections that specifies the general area of what the block does.\n")
    f.write("4. Extract the ZIP file into this directory.\n")
    f.write("5. Consider adding a README.md for convenience, and a thumbnail.png.\n")
    f.write("6. Run the python scripts create_index.py and create_readme.py located in the root of the repository.\n")
    f.write("7. Create a pull request.\n\n")



def create_table_of_contents(f, blocks):
    f.write("## Table of blocks (Omniscope 2020+)\n")

    sections = get_sections(blocks)


    category_index = 1
    for category in sections:
        f.write(f"{category_index}. {category}\n")

        subcategories = list(sections[category].keys())
        subcategories.sort(key=cmp_to_key(compare))

        subcategory_index = 1
        for subcategory in subcategories:
            has_subcategory = not subcategory is None

            if has_subcategory:
                f.write(f"   {subcategory_index}. {subcategory}\n")

            block_index = 1 if has_subcategory else subcategory_index
            for block in sections[category][subcategory]:
                if has_subcategory:
                    f.write("   ")
                link = "#"+block["id"]
                f.write(f'   {block_index}. [{block["name"]}]({link})\n')
                block_index = block_index + 1

            subcategory_index = subcategory_index + 1

        category_index = category_index + 1



def create_block_overview(f, blocks):
    f.write("## Block Overview\n")

    sections = get_sections(blocks)

    for category in sections:

        subcategories = list(sections[category].keys())
        subcategories.sort(key=cmp_to_key(compare))

        for subcategory in subcategories:

            for block in sections[category][subcategory]:

                f.write(f'<div id="{block["id"]}"/>\n\n')
                f.write(f'### {block["name"]}\n\n')

                has_thumbnail = "thumbnail" in block

                if has_thumbnail:
                    f.write(f'<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/{block["thumbnail"]}" width="125" height="125"/>\n\n')

                f.write(f'{block["description"]}\n\n')
                f.write(f'[Link to Github page]({block["relative_path"]})\n\n')







def process_directory(root_path: str, path_parts, blocks):
    with open(root_path+"/manifest.json", 'r') as manifest_file:

        try:
            manifest = json.load(manifest_file)
        except Exception as e:
            print(f"JSON error detected, cannot load corrupt manifest at: {root_path}/manifest.json")
            raise e

        if not "optionsVersion" in manifest or not manifest["optionsVersion"] in supported_options_versions:
            return

        relative_path = os.sep.join(path_parts)

        id = "".join(list(map(lambda s: s.replace(" ", ""), path_parts)))

        block = {}
        block["id"] = id
        block["path"] = root_path
        block["relative_path"] = urllib.parse.quote(relative_path)
        block["name"] = manifest["name"]
        block["language"] = manifest["language"]
        block["description"] = manifest["description"]
        block["category"] = manifest["category"]
        if "subcategory" in manifest and not manifest["subcategory"] is None:
            block["subcategory"] = manifest["subcategory"]

        if path.isfile(root_path+"/thumbnail.png"):
            block["thumbnail"] = relative_path+"/thumbnail.png"


        blocks.append(block)




blocks = []

for root, dirs, files in os.walk("."):
    root_path = root.split(os.sep)
    path_parts = root_path[1:]
    for file in files:
        if file == "manifest.json":
            process_directory(root, path_parts, blocks)



with open(readme_file_name, 'w') as readme_file:
    create_header(readme_file)
    create_instructions(readme_file)
    create_table_of_contents(readme_file, blocks)
    create_block_overview(readme_file, blocks)
