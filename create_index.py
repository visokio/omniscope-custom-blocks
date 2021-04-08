#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 10:42:00 2021

@author: nils
"""


index_file_name = "index.json"

# a new index.json is created for all individual block manifests that have a supported optionsVersion
supported_options_versions = [1]

# the script will raise an error if these keys are not found in the individual block manifests. The key is the manifest
# key and the value the index key
keys_required = {"name": "displayName",  "language": "language", "optionsVersion": "optionsVersion"}

# if these are not found in the individual manifests, they are initialised with the value
keys_with_defaults = {"tags": []}

# optional keys, if not found in the individual manifests they are ignored
keys_optional = ["description", "category", "subcategory", "icon"]



import os
import json


def process_directory(path: str, blocks):
    with open(path+"/manifest.json", 'r') as manifest_file:
        manifest = json.load(manifest_file)
        
        if not "optionsVersion" in manifest or not manifest["optionsVersion"] in supported_options_versions:
            return
        
        for key in keys_required:
            if not key in manifest:
                raise Exception(f"Key {key} is required but not present in manifest {path}")

        folder = os.sep.join(path.split(os.sep)[1:])
        
        block = {"path": folder}
        
        
        for key in keys_required:
            block[keys_required[key]] = manifest[key]
            
        for key in keys_with_defaults:
            if not key in manifest:
                block[key] = keys_with_defaults[key]
            else:
                block[key] = manifest[key]
                
        for key in keys_optional:
            if key in manifest:
                block[key] = manifest[key]
        
        blocks.append(block)
        
        


blocks = []

for root, dirs, files in os.walk("."):
    path = root.split(os.sep)
    for file in files:
        if file == "manifest.json":
            process_directory(root, blocks)
        
        
with open(index_file_name, 'w') as index_file:
    json.dump({"blocks": blocks}, index_file, indent=4)