#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: nils

Helper script to extract dependencies from all python and R community blocks
"""


python_dependencies = set()

r_dependencies = set()



import os
import json
import re

def process_directory(path: str):
    with open(path+"/manifest.json", 'r') as manifest_file:
        manifest = json.load(manifest_file)

        if manifest["language"] == "PYTHON":

            if not "dependencies" in manifest :
                return

            dependencies = re.split('\r?\n|\s', manifest["dependencies"])

            for dependency in dependencies:

                m = re.search('(?m:^)([a-zA-Z][A-Za-z0-9\.\_\-]+)\s*((?s:.)+)*(?m:$)', dependency)
                if m is not None:
                    python_dependencies.add(m.group(1))

        if manifest["language"] == "R":
            script_filename = manifest["scriptFilename"]
            with open(path+"/"+script_filename, 'r') as script_file:
                script = script_file.read()

                matches = re.findall('(?:[^#]|)\\s*(?:library|require)\\s*\\(\"?([A-Za-z0-9\\.]+)\"?\\)', script, re.DOTALL)

                for match in matches:
                    r_dependencies.add(match)



for root, dirs, files in os.walk("."):
    path = root.split(os.sep)
    for file in files:
        if file == "manifest.json":
            process_directory(root)


print("python dependencies:")
print("\n".join(python_dependencies))

print("\n\n")
print("R dependencies:")
print("\n".join(r_dependencies))

print("\n\n")
print("R libraries as code:")
print("\n".join(list(map(lambda s: "library("+s+")",r_dependencies))))
