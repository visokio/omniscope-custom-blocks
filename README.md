# Omniscope Custom Blocks &middot; [![Refresh index](https://github.com/visokio/omniscope-custom-blocks/actions/workflows/refresh_index.yml/badge.svg)](https://github.com/visokio/omniscope-custom-blocks/actions/workflows/refresh_index.yml)[![Refresh readme](https://github.com/visokio/omniscope-custom-blocks/actions/workflows/refresh_readme.yml/badge.svg)](https://github.com/visokio/omniscope-custom-blocks/actions/workflows/refresh_readme.yml)

Public repository for custom blocks for Omniscope Evo.

#### [Python / R API docs](https://help.visokio.com/support/solutions/articles/42000071109-custom-block-r-python-api-reference)

## How to add a block to this repository
### The simple way
1. Design your custom block in Omniscope Evo 2020.1 or later.
   The source code should be reasonably documented and potentially contain sections to describe input fields and parameters.
2. Export as a ZIP file from the block dialog.
3. Send the file to support@visokio.com and we will include it for you.

### The hard way
1. Follow points 1-2 from the simple way.
2. Fork the repository.
3. Create or use a directory in the forked repository under one of the main sections that specifies the general area of what the block does.
4. Extract the ZIP file into this directory.
5. Consider adding a README.md for convenience, and a thumbnail.png.
6. Run the python scripts create_index.py and create_readme.py located in the root of the repository.
7. Create a pull request.

## Table of blocks (Omniscope 2020+)
1. Inputs
   1. Databases
      1. [MongoDB](#InputsDatabasesMongoDB)
      2. [Snowflake Custom Query](#InputsDatabasesSnowflake-custom-query)
   2. R
      1. [R Data Reader](#InputsRdata)
      2. [Rds Batch Append](#InputsRds-Batch-Append)
   3. [SFTP Downloader](#InputsSFTP-Downloader)
   4. [PDF Reader](#InputsPDF-Reader)
   5. [Sharepoint Online Downloader](#InputsSharepoint-Online)
2. Code & AI
   1. [Execute Command](#Custom-scriptsExecuteCommand)
   2. [AI Chat - Local LLM](#ConnectorsAI-Chat-Local-LLM)
   3. [AI Chat - DeepSeek](#ConnectorsAI-Chat-DeepSeek)
   4. [AI Chat - OpenAI GPT](#ConnectorsOpenAI-GPT)
   5. [AI Chat - Claude](#ConnectorsAI-Chat-Anthropic-Claude)
3. Preparation
   1. ForEach
      1. [Project Parameters Batch Setting](#PreparationForEachProjectParameters)
      2. [ForEach multi stage](#PreparationForEachForEachMultiStage)
   2. Geo
      1. [Shapefile](#PreparationGeoShapefile)
      2. [Gridsquare](#PreparationGeoGridsquare)
   3. Interfaces
      1. [Kedro](#PreparationInterfacesKedro)
   4. JSON
      1. [JSON Expand fields](#PreparationJSONExpand_Fields)
      2. [JSON Normalise](#PreparationJSONNormalise)
   5. Join
      1. [Interval Join](#PreparationJoinInterval-Join)
      2. [Inequality Join](#PreparationJoinInequality-Join)
      3. [Fuzzy Terms Join](#PreparationJoinFuzzy-Join)
   6. Partition
      1. [Partition](#PreparationPartition)
   7. Pivot
      1. [Melt De-pivot](#PreparationPivotMelt-De-pivot)
   8. Standardisation
      1. [Standardise](#PreparationStandardisationStandardise)
   9. Workflow
      1. [For Each (Separate Workflows)](#PreparationForEachForEach)
   10. [Sort fields](#PreparationSort-fields)
   11. [Split Address](#PreparationSplit-Address)
   12. [Conditional Execution](#PreparationConditionalExecution)
   13. [Anonymise](#PreparationAnonymise)
   14. [Centroids from GeoJSON](#PreparationGeoCentroids)
   15. [Add row ID field](#PreparationAdd-row-ID-field)
   16. [Unstack Records](#PreparationUnstack-rows)
   17. [Streaming Field Renamer](#PreparationStreaming-Field-Renamer)
   18. [URL Encode](#PreparationURL-Encode)
   19. [Unescape HTML](#PreparationUnescape-HTML)
   20. [Time Duration Unit Converter](#PreparationTime-Duration-Unit-Converter)
   21. [Field Renamer](#PreparationField-Renamer)
   22. [Set Project Parameters](#PreparationSetProjectParameters)
   23. [Markdown to HTML](#PreparationMarkdown-to-HTML)
4. Connectors
   1. Azure
      1. [Azure Data Lake Storage Gen2 Blob](#ConnectorsAzure-Data-Lake-Blob)
   2. Flightstats
      1. [Flightstats Airports](#ConnectorsFlightstatsAirports)
      2. [Flightstats Flights](#ConnectorsFlightstatsFlights)
      3. [Flightstats Airlines](#ConnectorsFlightstatsAirlines)
   3. Overpass
      1. [Overpass Street Coordinates](#ConnectorsOverpassStreet-Coordinates)
   4. Slack
      1. [Slack API WebClient](#ConnectorsSlack-API-WebClient)
   5. Weather
      1. [OpenWeatherMap](#ConnectorsWeatherOpenWeatherMap)
   6. [Dune](#ConnectorsDune)
   7. [XPT Reader](#ConnectorsXPT-Reader)
   8. [Flipside](#ConnectorsFlipside)
   9. [Jira](#ConnectorsJira)
   10. [Google BigQuery Custom SQL](#ConnectorsBigQueryGoogle-BigQuery-Custom-SQL)
   11. [Google BigQuery Import Table](#ConnectorsBigQueryGoogle-BigQuery-Import-Table)
   12. [HubSpot](#ConnectorsHubSpot)
   13. [Etherscan](#ConnectorsEtherscan)
   14. [Trello](#ConnectorsTrello)
   15. [Yahoo Finance](#ConnectorsYahooFinance)
5. Analytics
   1. Clustering
      1. [KMeans](#AnalyticsClusteringKMeans)
      2. [DBScan](#AnalyticsClusteringDBScan)
      3. [Gaussian Mixture Model](#AnalyticsClusteringGMM)
   2. Network Analysis
      1. [Attribute Analysis](#AnalyticsNetwork-AnalysisAttribute-Analysis)
      2. [TSNE](#AnalyticsNetwork-AnalysisTSNE)
   3. Prediction
      1. [Support Vector Machine](#AnalyticsPredictionSVM)
      2. [K-Nearest-Neighbours](#AnalyticsPredictionKNN)
   4. Validation
      1. [Model Validation](#AnalyticsValidationModel-Validation)
   5. Website
      1. [Website Analysis](#AnalyticsWebsitesWebsite-Analysis)
   6. [Survival Analysis](#AnalyticsSurvival)
   7. [Data Profiler](#AnalyticsData-Profiler)
6. Outputs
   1. BigQuery
      1. [Google BigQuery Export](#OutputsGoogle-BigQuery-Writer)
   2. Github
      1. [GitHub](#OutputsGitHub)
   3. PDF
      1. [Report tab to PDF](#OutputsReport-tab-to-PDF)
      2. [Append PDF files](#OutputsAppend-PDF-files)
      3. [Multi-tenant Report to PDF](#OutputsReport-to-PDF-batch-output)
      4. [Web Image-PDF output](#OutputsWeb-Image-PDF-output)
   4. PowerPoint
      1. [Report to PowerPoint](#OutputsReport-to-PowerPoint)
   5. Slack
      1. [Slack Bot](#OutputsSlack-Bot)
## Block Overview
<div id="InputsDatabasesMongoDB"/>

### MongoDB

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/Databases/MongoDB/thumbnail.png" width="125" height="125"/>

A connector for MongoDB

[Link to Github page](Inputs/Databases/MongoDB)

<div id="InputsDatabasesSnowflake-custom-query"/>

### Snowflake Custom Query

Executes a SQL query on a Snowflake database.

[Link to Github page](Inputs/Databases/Snowflake-custom-query)

<div id="InputsRdata"/>

### R Data Reader

Joins regions defined in a shapefile with points defined as latitudes and longitudes, and gives meta information about the content of the shapefile

[Link to Github page](Inputs/Rdata)

<div id="InputsRds-Batch-Append"/>

### Rds Batch Append

Reads multiple rds files either from an upstream block, or a folder, and appends them

[Link to Github page](Inputs/Rds-Batch-Append)

<div id="InputsSFTP-Downloader"/>

### SFTP Downloader

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/SFTP-Downloader/thumbnail.png" width="125" height="125"/>

Download files from a SFTP server folder.

[Link to Github page](Inputs/SFTP-Downloader)

<div id="InputsPDF-Reader"/>

### PDF Reader

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/PDF-Reader/thumbnail.png" width="125" height="125"/>

Extract text from PDF files.

[Link to Github page](Inputs/PDF-Reader)

<div id="InputsSharepoint-Online"/>

### Sharepoint Online Downloader

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/Sharepoint-Online/thumbnail.png" width="125" height="125"/>

Download a file from a Sharepoint Online site.

[Link to Github page](Inputs/Sharepoint-Online)

<div id="Custom-scriptsExecuteCommand"/>

### Execute Command

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Custom-scripts/ExecuteCommand/thumbnail.png" width="125" height="125"/>

Execute a system command.

[Link to Github page](Custom-scripts/ExecuteCommand)

<div id="ConnectorsAI-Chat-Local-LLM"/>

### AI Chat - Local LLM

Executes a one-off prompt to a local LLM and returns the generated text result

[Link to Github page](Connectors/AI-Chat-Local-LLM)

<div id="ConnectorsAI-Chat-DeepSeek"/>

### AI Chat - DeepSeek

Executes a one-off prompt to DeepSeek and returns the generated text result

[Link to Github page](Connectors/AI-Chat-DeepSeek)

<div id="ConnectorsOpenAI-GPT"/>

### AI Chat - OpenAI GPT

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/OpenAI-GPT/thumbnail.png" width="125" height="125"/>

Executes a one-off prompt to OpenAI GPT and returns the generated text result

[Link to Github page](Connectors/OpenAI-GPT)

<div id="ConnectorsAI-Chat-Anthropic-Claude"/>

### AI Chat - Claude

Executes a one-off prompt to Anthropic Claude and returns the generated text result

[Link to Github page](Connectors/AI-Chat-Anthropic-Claude)

<div id="PreparationForEachProjectParameters"/>

### Project Parameters Batch Setting

None

[Link to Github page](Preparation/ForEach/ProjectParameters)

<div id="PreparationForEachForEachMultiStage"/>

### ForEach multi stage

The ForEach multi stage block allows to orchestrate the execution of another Omniscope project and running the workflow multiple times, each time with a different set of parameter values. Unlike the ForEach block allows multiple stages of execution, executing/refreshing from source a different set of blocks in each stage.

[Link to Github page](Preparation/ForEach/ForEachMultiStage)

<div id="PreparationGeoShapefile"/>

### Shapefile

Match regions in shapefile with geographical points having latitude and longitude

[Link to Github page](Preparation/Geo/Shapefile)

<div id="PreparationGeoGridsquare"/>

### Gridsquare

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Geo/Gridsquare/thumbnail.png" width="125" height="125"/>

Converts gridsquare / Maidenhead 

[Link to Github page](Preparation/Geo/Gridsquare)

<div id="PreparationInterfacesKedro"/>

### Kedro

Intefaces with kedro workflows

[Link to Github page](Preparation/Interfaces/Kedro)

<div id="PreparationJSONExpand_Fields"/>

### JSON Expand fields

Expands JSON strings in a specified field into separate columns, optionally including the original input data

[Link to Github page](Preparation/JSON/Expand_Fields)

<div id="PreparationJSONNormalise"/>

### JSON Normalise

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/JSON/Normalise/thumbnail.png" width="125" height="125"/>

Normalise semi-structured JSON strings into a flat table, appending data record by record.

[Link to Github page](Preparation/JSON/Normalise)

<div id="PreparationJoinInterval-Join"/>

### Interval Join

Performs a join between values in the first input and intervals in the second input. Rows are joined if the value is contained in an interval.

[Link to Github page](Preparation/Join/Interval-Join)

<div id="PreparationJoinInequality-Join"/>

### Inequality Join

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Join/Inequality-Join/thumbnail.png" width="125" height="125"/>

Performs a join between the first (left) and second (right) input. The join can be performed using equality/inequality comparators ==, <=, >=, <, > , which means the result will be a constraint cartesian join including all records that match the inequalities.

[Link to Github page](Preparation/Join/Inequality-Join)

<div id="PreparationJoinFuzzy-Join"/>

### Fuzzy Terms Join

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Join/Fuzzy-Join/thumbnail.png" width="125" height="125"/>

Performs a join between the first (left) and second (right) input. The field on which the join is performed must be text containing multiple terms. The result will contain joined records based on how many terms they share, weighted by inverse document frequency.

[Link to Github page](Preparation/Join/Fuzzy-Join)

<div id="PreparationPartition"/>

### Partition

Partitions the data into chunks of the desired size. There will be a new field called "Partition" which contains a number unique to each partition.

[Link to Github page](Preparation/Partition)

<div id="PreparationPivotMelt-De-pivot"/>

### Melt De-pivot

Keep all selected fixed fields in the output, de-pivot all other fields

[Link to Github page](Preparation/Pivot/Melt-De-pivot)

<div id="PreparationStandardisationStandardise"/>

### Standardise

Standardises the values in the selected fields so that they are in the range between 0 and 1. I.e. The new value of the highest value in each field is going to be 1, and the lowest value 0. All other values are scaled proportionally.

[Link to Github page](Preparation/Standardisation/Standardise)

<div id="PreparationForEachForEach"/>

### For Each (Separate Workflows)

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/ForEach/ForEach/thumbnail.png" width="125" height="125"/>

Executes another Omniscope project multiple times, each time with a different set of parameter values.

[Link to Github page](Preparation/ForEach/ForEach)

<div id="PreparationSort-fields"/>

### Sort fields

Sort fields in the input data by name or type

[Link to Github page](Preparation/Sort-fields)

<div id="PreparationSplit-Address"/>

### Split Address

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Split-Address/thumbnail.png" width="125" height="125"/>

Splits an address field into streetname, streetnumber, and suffix.

[Link to Github page](Preparation/Split-Address)

<div id="PreparationConditionalExecution"/>

### Conditional Execution

This block conditionally triggers the execution of specified workflow blocks via the Workflow API, running them only when the Conditional Parameter is set to true.

[Link to Github page](Preparation/Conditional%20Execution)

<div id="PreparationAnonymise"/>

### Anonymise

Anonymise sensitive text data within the input data.

[Link to Github page](Preparation/Anonymise)

<div id="PreparationGeoCentroids"/>

### Centroids from GeoJSON

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Geo/Centroids/thumbnail.png" width="125" height="125"/>

Calculates the centroid points (lat,long) and output them together with the shape ID from a specified GeoJSON file.

[Link to Github page](Preparation/Geo/Centroids)

<div id="PreparationAdd-row-ID-field"/>

### Add row ID field

Adds a Row ID field with a sequential number.

[Link to Github page](Preparation/Add-row-ID-field)

<div id="PreparationUnstack-rows"/>

### Unstack Records

Unstack all records by splitting on text fields with stacked values, filling records with empty strings where needed.

[Link to Github page](Preparation/Unstack-rows)

<div id="PreparationStreaming-Field-Renamer"/>

### Streaming Field Renamer

Renames the fields of a input data, optimised for streaming and big data, given a set of rules  defined in a CSV file

[Link to Github page](Preparation/Streaming-Field-Renamer)

<div id="PreparationURL-Encode"/>

### URL Encode

URL encode strings in a field using the UTF-8 encoding scheme

[Link to Github page](Preparation/URL-Encode)

<div id="PreparationUnescape-HTML"/>

### Unescape HTML

Convert all named and numeric character references to the corresponding Unicode characters

[Link to Github page](Preparation/Unescape-HTML)

<div id="PreparationTime-Duration-Unit-Converter"/>

### Time Duration Unit Converter

Converts specified datetime, time duration, or time string fields into a chosen time unit

[Link to Github page](Preparation/Time-Duration-Unit-Converter)

<div id="PreparationField-Renamer"/>

### Field Renamer

Renames the fields of a data set given a list of current names and new names.

[Link to Github page](Preparation/Field-Renamer)

<div id="PreparationSetProjectParameters"/>

### Set Project Parameters

The block updates project parameters using the input data

[Link to Github page](Preparation/Set%20Project%20Parameters)

<div id="PreparationMarkdown-to-HTML"/>

### Markdown to HTML

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Markdown-to-HTML/thumbnail.png" width="125" height="125"/>

None

[Link to Github page](Preparation/Markdown-to-HTML)

<div id="ConnectorsAzure-Data-Lake-Blob"/>

### Azure Data Lake Storage Gen2 Blob

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Azure-Data-Lake-Blob/thumbnail.png" width="125" height="125"/>

Storage Gen2 Blob connector to load a CSV or Parquet blob/file in Omniscope.

[Link to Github page](Connectors/Azure-Data-Lake-Blob)

<div id="ConnectorsFlightstatsAirports"/>

### Flightstats Airports

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Airports/thumbnail.png" width="125" height="125"/>

Downloads a list of airports as provided by flightstats (https://www.flightstats.com). The script needs your flightstats app id and key which needs to be obtained either through buying their service or signing up for a test account.

[Link to Github page](Connectors/Flightstats/Airports)

<div id="ConnectorsFlightstatsFlights"/>

### Flightstats Flights

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Flights/thumbnail.png" width="125" height="125"/>

Requests information about flights specified in the input data from flightstats (https://www.flightstats.com). If the flight exists the result will contain live information, otherwise it will not be part of it. The script needs your flightstats app id and key which needs to be obtained either through buying their service or signing up for a test account.

[Link to Github page](Connectors/Flightstats/Flights)

<div id="ConnectorsFlightstatsAirlines"/>

### Flightstats Airlines

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Airlines/thumbnail.png" width="125" height="125"/>

Downloads a list of airlines as provided by flightstats (https://www.flightstats.com). The script needs your flightstats app id and key which needs to be obtained either through buying their service or signing up for a test account.

[Link to Github page](Connectors/Flightstats/Airlines)

<div id="ConnectorsOverpassStreet-Coordinates"/>

### Overpass Street Coordinates

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Overpass/Street-Coordinates/thumbnail.png" width="125" height="125"/>

Finds all matching streets given a street name and requests multiple coordinates along the street using data from Overpass API. It will create a row for each point found that is part of a street that matches the given street name. The resulting rows will include the street name, the street Id and the coordinates of the point. The script needs an input with a field with the street name.

[Link to Github page](Connectors/Overpass/Street-Coordinates)

<div id="ConnectorsSlack-API-WebClient"/>

### Slack API WebClient

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Slack-API-WebClient/thumbnail.png" width="125" height="125"/>

Allows you to call public Slack endpoints.

[Link to Github page](Connectors/Slack-API-WebClient)

<div id="ConnectorsWeatherOpenWeatherMap"/>

### OpenWeatherMap

Retrieves current weather and forecasts from OpenWeatherMap

[Link to Github page](Connectors/Weather/OpenWeatherMap)

<div id="ConnectorsDune"/>

### Dune

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Dune/thumbnail.png" width="125" height="125"/>

Execute queries and retrieve blockchain data from any public query on dune.com, as well as any personal private queries your Dune account has access to

[Link to Github page](Connectors/Dune)

<div id="ConnectorsXPT-Reader"/>

### XPT Reader

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/XPT-Reader/thumbnail.png" width="125" height="125"/>

Reads a SAS Transport *xpt* file, extracting a dataset.

[Link to Github page](Connectors/XPT-Reader)

<div id="ConnectorsFlipside"/>

### Flipside

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flipside/thumbnail.png" width="125" height="125"/>

Executes a SQL query on Flipside and retrieves the blockchain data

[Link to Github page](Connectors/Flipside)

<div id="ConnectorsJira"/>

### Jira

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Jira/thumbnail.png" width="125" height="125"/>

Retrieves projects and issues from Jira

[Link to Github page](Connectors/Jira)

<div id="ConnectorsBigQueryGoogle-BigQuery-Custom-SQL"/>

### Google BigQuery Custom SQL

Executes a SQL query on Google BigQuery and imports the query results

[Link to Github page](Connectors/BigQuery/Google-BigQuery-Custom-SQL)

<div id="ConnectorsBigQueryGoogle-BigQuery-Import-Table"/>

### Google BigQuery Import Table

Allows to import a table from Google BigQuery.

[Link to Github page](Connectors/BigQuery/Google-BigQuery-Import-Table)

<div id="ConnectorsHubSpot"/>

### HubSpot

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/HubSpot/thumbnail.png" width="125" height="125"/>

Retrieves contacts, companies, deals and lists

[Link to Github page](Connectors/HubSpot)

<div id="ConnectorsEtherscan"/>

### Etherscan

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Etherscan/thumbnail.png" width="125" height="125"/>

The Ethereum Blockchain Explorer.

[Link to Github page](Connectors/Etherscan)

<div id="ConnectorsTrello"/>

### Trello

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Trello/thumbnail.png" width="125" height="125"/>

Retrieves boards, lists and cards, and allows you to search in Trello.

[Link to Github page](Connectors/Trello)

<div id="ConnectorsYahooFinance"/>

### Yahoo Finance

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/YahooFinance/thumbnail.png" width="125" height="125"/>

Fetches price data for tickers from Yahoo Finance

[Link to Github page](Connectors/YahooFinance)

<div id="AnalyticsClusteringKMeans"/>

### KMeans

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/KMeans/thumbnail.png" width="125" height="125"/>

Performs KMeans clustering on the first input data provided. The output consists of the original input with a Cluster field appended. If a second input is available, it will be used as output instead.

[Link to Github page](Analytics/Clustering/KMeans)

<div id="AnalyticsClusteringDBScan"/>

### DBScan

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/DBScan/thumbnail.png" width="125" height="125"/>

Performs DBScan clustering on the first input data provided. The output consists of the original input with a Cluster field appended. If a second input is available, it will be used as output instead.

[Link to Github page](Analytics/Clustering/DBScan)

<div id="AnalyticsClusteringGMM"/>

### Gaussian Mixture Model

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/GMM/thumbnail.png" width="125" height="125"/>

Performs GMM clustering on the first input data provided. The output consists of the original input with a Cluster field appended. If a second input is available, it will be used as output instead.

[Link to Github page](Analytics/Clustering/GMM)

<div id="AnalyticsNetwork-AnalysisAttribute-Analysis"/>

### Attribute Analysis

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Network-Analysis/Attribute-Analysis/thumbnail.png" width="125" height="125"/>

Given a dataset in which each record represents an edge between two nodes of a network, and each node has an associated categorical attribute, the block analyses connections between attributes, based on connections between associated nodes. The result of the analysis is a list of records in which each record specifies a connection from one attribute to another. The connection contains a probability field, which gives an answer to the question that if a node has the specified categorical attribute, how probable it is that it has a connection to another node with the linked categorical attribute.

[Link to Github page](Analytics/Network-Analysis/Attribute-Analysis)

<div id="AnalyticsNetwork-AnalysisTSNE"/>

### TSNE

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Network-Analysis/TSNE/thumbnail.png" width="125" height="125"/>

Given a dataset in which each record represents an edge between two nodes of a network, the block will project all the nodes onto a (e.g. 2)- dimensional plane in such a way that nodes which share many connections are close together, and nodes that do not share many connections are far apart.

[Link to Github page](Analytics/Network-Analysis/TSNE)

<div id="AnalyticsPredictionSVM"/>

### Support Vector Machine

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Prediction/SVM/thumbnail.png" width="125" height="125"/>

Predicts classes of new data from old data by drawing a boundary between two classes whereas the margin around the bondary is made as large as possible to avoid touching the points.

[Link to Github page](Analytics/Prediction/SVM)

<div id="AnalyticsPredictionKNN"/>

### K-Nearest-Neighbours

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Prediction/KNN/thumbnail.png" width="125" height="125"/>

Performs k-nearest-neighbour prediction on the data. The prediction for a new point depends on the k-nearest-neighbours around the point. The majority class is used as the prediction.

[Link to Github page](Analytics/Prediction/KNN)

<div id="AnalyticsValidationModel-Validation"/>

### Model Validation

Computes a confusion matrix as well as model validation statistics

[Link to Github page](Analytics/Validation/Model-Validation)

<div id="AnalyticsWebsitesWebsite-Analysis"/>

### Website Analysis

Extracts the structure and content of a website and its pages.

[Link to Github page](Analytics/Websites/Website-Analysis)

<div id="AnalyticsSurvival"/>

### Survival Analysis

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Survival/thumbnail.png" width="125" height="125"/>

Computes an estimate of a survival curve for truncated and/or censored data using the Kaplan-Meier or Fleming-Harrington method

[Link to Github page](Analytics/Survival)

<div id="AnalyticsData-Profiler"/>

### Data Profiler

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Data-Profiler/thumbnail.png" width="125" height="125"/>

Provides detailed statistics about a dataset

[Link to Github page](Analytics/Data-Profiler)

<div id="OutputsGoogle-BigQuery-Writer"/>

### Google BigQuery Export

Allows to write data to a Google BigQuery table. The table can be created/replaced, or records can be appended to an existing table

[Link to Github page](Outputs/Google-BigQuery-Writer)

<div id="OutputsGitHub"/>

### GitHub

Reads from and writes data to GitHub

[Link to Github page](Outputs/GitHub)

<div id="OutputsReport-tab-to-PDF"/>

### Report tab to PDF

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Report-tab-to-PDF/thumbnail.png" width="125" height="125"/>

Prints Report tabs to PDF files for each record of the input data.

[Link to Github page](Outputs/Report-tab-to-PDF)

<div id="OutputsAppend-PDF-files"/>

### Append PDF files

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Append-PDF-files/thumbnail.png" width="125" height="125"/>

Append multiple PDF files combining them into one PDF file.

[Link to Github page](Outputs/Append-PDF-files)

<div id="OutputsReport-to-PDF-batch-output"/>

### Multi-tenant Report to PDF

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Report-to-PDF-batch-output/thumbnail.png" width="125" height="125"/>

Prints Report tabs to PDF files for each record of the input data.

[Link to Github page](Outputs/Report-to-PDF-batch-output)

<div id="OutputsWeb-Image-PDF-output"/>

### Web Image-PDF output

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Web-Image-PDF-output/thumbnail.png" width="125" height="125"/>

Grabs screenshots of webpages, optionally producing a PDF document.

[Link to Github page](Outputs/Web-Image-PDF-output)

<div id="OutputsReport-to-PowerPoint"/>

### Report to PowerPoint

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Report-to-PowerPoint/thumbnail.png" width="125" height="125"/>

Export a Report to a PowerPoint pptx file

[Link to Github page](Outputs/Report-to-PowerPoint)

<div id="OutputsSlack-Bot"/>

### Slack Bot

<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Slack-Bot/thumbnail.png" width="125" height="125"/>

Posts messages on a channel.

[Link to Github page](Outputs/Slack-Bot)

