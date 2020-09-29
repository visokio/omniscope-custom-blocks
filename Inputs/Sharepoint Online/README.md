# Sharepoint Online Downloader

## Download a file locally from a Sharepoint Online site
#### Insert the file URL (absolute path e.g. *https://yourdomain.sharepoint.com/sites/yoursite/Shared Documents/myExcelFile.xlsx*  ) to download the file locally.
#### Once executed the block will download the file locally in a temp location, writing its path to the block output data.
#### Connect this block to an 'Append files' block configured to 'use file names from the upstream block' to download the file and load its content in Omniscope.  See example [here](https://omniscope.me/internal/Forums/Custom+block/Sharepoint+Online.iox/)

## Language
Python

## Dependencies
Office365-REST-Python-Client

## Source
[script.py](https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/Sharepoint%20Online/script.py)
