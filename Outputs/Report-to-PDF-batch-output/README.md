# Multi-tenant Report to PDF batch output

#### This block will produce a PDF of a Report tab for each multi-tenant config row, saving the PDF files in a specified output folder, with filenames equal to the Report name + scenario ID.
#### Connect a Multi-tenant report configuration to this block with the "scenario" field configured, set the base Report URL pointing to the tab you want to print as PDF (copy it from your browser address bar or from the Report Sharing dialog). 
##### It requires Google Chrome installed on your machine, used to print the report as PDF.
##### It requires Visokio "Omniprint" app, downloadable here for [Windows](https://visokio.com/wp-content/uploads/2021/01/Omniscope-Evo-Omniprint.zip), [Mac](https://visokio.com/wp-content/uploads/2021/01/Omniscope-Evo-Omniprint-macos.zip) and [Linux](https://visokio.com/wp-content/uploads/2021/01/Omniscope-Evo-Omniprint-linux.tar.gz).

## Language
Python

## Dependencies
omniprint , GoogleChrome

## Source
[script.py](https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Report%20to%20PDF%20batch%20output/script.py)
