# Omniscope Custom Blocks
Public repository for custom blocks for Omniscope Evo.
The blocks added here will be available to install in Omniscope block picker.

## Table of blocks (Omniscope 2020+)
1. Connectors
  1. Flightstats
    1. [Flightstats Flights](#Connectors_Flightstats_Flights)
    2. [Flightstats Airlines](#Connectors/Flightstats/Airlines)
    3. [Flightstats Airports](#Connectors/Flightstats/Airports)
  2. Overpass
    1. [Overpass Street Coordinates](#Connectors/Overpass/Street%20Coordinates)
  3. Weather
    1. [OpenWeatherMap](#Connectors/Weather/OpenWeatherMap)
  4. [Azure Data Lake Storage Gen2 Blob](#Connectors/Azure%20Data%20Lake%20Blob)
  5. [Slack API WebClient](#Connectors/Slack%20API%20WebClient)
  6. [Etherscan](#Connectors/Etherscan)
2. Preparation
  1. ForEach
    1. [ForEach](#Preparation/ForEach/ForEach)
    2. [ForEach multi stage](#Preparation/ForEach/ForEachMultiStage)
  2. Geo
    1. [Shapefile](#Preparation/Geo/Shapefile)
    2. [Gridsquare](#Preparation/Geo/Gridsquare)
  3. JSON
    1. [JSON Normalise](#Preparation/JSON/Normalise)
  4. Join
    1. [Inequality Join](#Preparation/Join/Inequality%20Join)
    2. [Interval Join](#Preparation/Join/Interval%20Join)
    3. [Fuzzy Join](#Preparation/Join/Fuzzy%20Join)
  5. Standardisation
    1. [Standardise](#Preparation/Standardisation/Standardise)
  6. [Field Renamer](#Preparation/Field%20Renamer)
  7. [Split Address](#Preparation/Split%20Address)
3. Custom
  1. [Execute Command](#Preparation/ExecuteCommand)
4. Outputs
  1. [Web Image-PDF output](#Outputs/Web%20Image-PDF%20output)
  2. [Slack Bot](#Outputs/Slack%20Bot)
  3. [Append PDF files](#Outputs/Append%20PDF%20files)
  4. [Multi-tenant Report to PDF](#Outputs/Report%20to%20PDF%20batch%20output)
  5. [GitHub](#Outputs/GitHub)
  6. [Google BigQuery Export](#Outputs/Google%20BigQuery%20Writer)
  7. [Report tab to PDF](#Outputs/Report%20tab%20to%20PDF)
5. Analytics
  1. Clustering
    1. [Gaussian Mixture Model](#Analytics/Clustering/GMM)
    2. [DBScan](#Analytics/Clustering/DBScan)
    3. [KMeans](#Analytics/Clustering/KMeans)
  2. Network Analysis
    1. [Attribute Analysis](#Analytics/Network%20Analysis/Attribute%20Analysis)
    2. [Relationship Analysis](#Analytics/Network%20Analysis/Relationship%20Analysis)
  3. Prediction
    1. [K-Nearest-Neighbours](#Analytics/Prediction/KNN)
    2. [Support Vector Machine](#Analytics/Prediction/SVM)
  4. [Website Analysis](#Analytics/Websites/Website%20Analysis)
6. Inputs
  1. [Sharepoint Online Downloader](#Inputs/Sharepoint%20Online)
  2. [R Data Reader](#Inputs/Rdata)
  3. [Rds Batch Append](#Inputs/Rds%20Batch%20Append)
  4. [PDF Reader](#Inputs/PDF%20Reader)
  5. [SFTP Downloader](#Inputs/SFTP%20Downloader)
## Block Overview
<div id="Connectors_Flightstats_Flights"/>
### Flightstats Flights
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Flights/thumbnail.png"/>
Requests information about flights specified in the input data from flightstats (https://www.flightstats.com). If the flight exists the result will contain live information, otherwise it will not be part of it. The script needs your flightstats app id and key which needs to be obtained either through buying their service or signing up for a test account.
[Link to Github page](Connectors/Flightstats/Flights)
<div id="Connectors/Flightstats/Airlines"/>
### Flightstats Airlines
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Airlines/thumbnail.png"/>
Downloads a list of airlines as provided by flightstats (https://www.flightstats.com). The script needs your flightstats app id and key which needs to be obtained either through buying their service or signing up for a test account.
[Link to Github page](Connectors/Flightstats/Airlines)
<div id="Connectors/Flightstats/Airports"/>
### Flightstats Airports
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Airports/thumbnail.png"/>
Downloads a list of airports as provided by flightstats (https://www.flightstats.com). The script needs your flightstats app id and key which needs to be obtained either through buying their service or signing up for a test account.
[Link to Github page](Connectors/Flightstats/Airports)
<div id="Connectors/Overpass/Street%20Coordinates"/>
### Overpass Street Coordinates
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Overpass/Street Coordinates/thumbnail.png"/>
Finds all matching streets given a street name and requests multiple coordinates along the street using data from Overpass API. It will create a row for each point found that is part of a street that matches the given street name. The resulting rows will include the street name, the street Id and the coordinates of the point. The script needs an input with a field with the street name.
[Link to Github page](Connectors/Overpass/Street%20Coordinates)
<div id="Connectors/Weather/OpenWeatherMap"/>
### OpenWeatherMap
Retrieves current weather and forecasts from OpenWeatherMap
[Link to Github page](Connectors/Weather/OpenWeatherMap)
<div id="Connectors/Azure%20Data%20Lake%20Blob"/>
### Azure Data Lake Storage Gen2 Blob
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Azure Data Lake Blob/thumbnail.png"/>
Storage Gen2 Blob connector to load a CSV or Parquet blob/file in Omniscope.
[Link to Github page](Connectors/Azure%20Data%20Lake%20Blob)
<div id="Connectors/Slack%20API%20WebClient"/>
### Slack API WebClient
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Slack API WebClient/thumbnail.png"/>
Allows you to call public Slack endpoints.
[Link to Github page](Connectors/Slack%20API%20WebClient)
<div id="Connectors/Etherscan"/>
### Etherscan
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Etherscan/thumbnail.png"/>
The Ethereum Blockchain Explorer.
[Link to Github page](Connectors/Etherscan)
<div id="Preparation/ForEach/ForEach"/>
### ForEach
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/ForEach/ForEach/thumbnail.png"/>
Executes another Omniscope project multiple times, each time with a different set of parameter values.
[Link to Github page](Preparation/ForEach/ForEach)
<div id="Preparation/ForEach/ForEachMultiStage"/>
### ForEach multi stage
The ForEach multi stage block allows to orchestrate the execution of another Omniscope project and running the workflow multiple times, each time with a different set of parameter values. Unlike the ForEach block allows multiple stages of execution, executing/refreshing from source a different set of blocks in each stage.
[Link to Github page](Preparation/ForEach/ForEachMultiStage)
<div id="Preparation/Geo/Shapefile"/>
### Shapefile
Match regions in shapefile with geographical points having latitude and longitude
[Link to Github page](Preparation/Geo/Shapefile)
<div id="Preparation/Geo/Gridsquare"/>
### Gridsquare
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Geo/Gridsquare/thumbnail.png"/>
Converts gridsquare / Maidenhead
[Link to Github page](Preparation/Geo/Gridsquare)
<div id="Preparation/JSON/Normalise"/>
### JSON Normalise
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/JSON/Normalise/thumbnail.png"/>
Normalise semi-structured JSON strings into a flat table, appending data record by record.
[Link to Github page](Preparation/JSON/Normalise)
<div id="Preparation/Join/Inequality%20Join"/>
### Inequality Join
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Join/Inequality Join/thumbnail.png"/>
Performs a join between the first (left) and second (right) input. The join can be performed using equality/inequality comparators ==, <=, >=, <, > , which means the result will be a constraint cartesian join including all records that match the inequalities.
[Link to Github page](Preparation/Join/Inequality%20Join)
<div id="Preparation/Join/Interval%20Join"/>
### Interval Join
Performs a join between values in the first input and intervals in the second input. Rows are joined if the value is contained in an interval.
[Link to Github page](Preparation/Join/Interval%20Join)
<div id="Preparation/Join/Fuzzy%20Join"/>
### Fuzzy Join
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Join/Fuzzy Join/thumbnail.png"/>
Performs a join between the first (left) and second (right) input. The field on which the join is performed must be text containing multiple terms. The result will contain joined records based on how many terms they share, weighted by inverse document frequency.
[Link to Github page](Preparation/Join/Fuzzy%20Join)
<div id="Preparation/Standardisation/Standardise"/>
### Standardise
Standardises fields into the range [0..1]
[Link to Github page](Preparation/Standardisation/Standardise)
<div id="Preparation/Field%20Renamer"/>
### Field Renamer
Renames the fields of a data set given a list of current names and new names.
[Link to Github page](Preparation/Field%20Renamer)
<div id="Preparation/Split%20Address"/>
### Split Address
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Split Address/thumbnail.png"/>
Splits an address field into streetname, streetnumber, and suffix.
[Link to Github page](Preparation/Split%20Address)
<div id="Preparation/ExecuteCommand"/>
### Execute Command
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/ExecuteCommand/thumbnail.png"/>
Execute a system command.
[Link to Github page](Preparation/ExecuteCommand)
<div id="Outputs/Web%20Image-PDF%20output"/>
### Web Image-PDF output
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Web Image-PDF output/thumbnail.png"/>
Grabs screenshots of webpages, optionally producing a PDF document.
[Link to Github page](Outputs/Web%20Image-PDF%20output)
<div id="Outputs/Slack%20Bot"/>
### Slack Bot
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Slack Bot/thumbnail.png"/>
Posts messages on a channel.
[Link to Github page](Outputs/Slack%20Bot)
<div id="Outputs/Append%20PDF%20files"/>
### Append PDF files
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Append PDF files/thumbnail.png"/>
Append multiple PDF files combining them into one PDF file.
[Link to Github page](Outputs/Append%20PDF%20files)
<div id="Outputs/Report%20to%20PDF%20batch%20output"/>
### Multi-tenant Report to PDF
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Report to PDF batch output/thumbnail.png"/>
Prints a Report tab in batch using multi-tenant scenario configuration.
[Link to Github page](Outputs/Report%20to%20PDF%20batch%20output)
<div id="Outputs/GitHub"/>
### GitHub
Reads from and writes data to GitHub
[Link to Github page](Outputs/GitHub)
<div id="Outputs/Google%20BigQuery%20Writer"/>
### Google BigQuery Export
Allows to write data to a Google BigQuery table. The table can be created/replaced, or records can be appeneded to an existing table
[Link to Github page](Outputs/Google%20BigQuery%20Writer)
<div id="Outputs/Report%20tab%20to%20PDF"/>
### Report tab to PDF
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Report tab to PDF/thumbnail.png"/>
Prints Report tabs to PDF files for each record of the input data.
[Link to Github page](Outputs/Report%20tab%20to%20PDF)
<div id="Analytics/Clustering/GMM"/>
### Gaussian Mixture Model
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/GMM/thumbnail.png"/>
Performs GMM clustering on the first input data provided. The output consists of the original input with a Cluster field appended. If a second input is available, it will be used as output instead.
[Link to Github page](Analytics/Clustering/GMM)
<div id="Analytics/Clustering/DBScan"/>
### DBScan
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/DBScan/thumbnail.png"/>
Performs DBScan clustering on the first input data provided. The output consists of the original input with a Cluster field appended. If a second input is available, it will be used as output instead.
[Link to Github page](Analytics/Clustering/DBScan)
<div id="Analytics/Clustering/KMeans"/>
### KMeans
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/KMeans/thumbnail.png"/>
Performs KMeans clustering on the first input data provided. The output consists of the original input with a Cluster field appended. If a second input is available, it will be used as output instead.
[Link to Github page](Analytics/Clustering/KMeans)
<div id="Analytics/Network%20Analysis/Attribute%20Analysis"/>
### Attribute Analysis
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Network Analysis/Attribute Analysis/thumbnail.png"/>
Given a dataset in which each record represents an edge between two nodes of a network, and each node has an associated categorical attribute, the block analyses connections between attributes, based on connections between associated nodes. The result of the analysis is a list of records in which each record specifies a connection from one attribute to another. The connection contains a probability field, which gives an answer to the question that if a node has the specified categorical attribute, how probable it is that it has a connection to another node with the linked categorical attribute.
[Link to Github page](Analytics/Network%20Analysis/Attribute%20Analysis)
<div id="Analytics/Network%20Analysis/Relationship%20Analysis"/>
### Relationship Analysis
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Network Analysis/Relationship Analysis/thumbnail.png"/>
Given a dataset in which each record represents an edge between two nodes of a network, the block will project all the nodes onto a (e.g. 2)- dimensional plane in such a way that nodes which share many connections are close together, and nodes that do not share many connections are far apart.
[Link to Github page](Analytics/Network%20Analysis/Relationship%20Analysis)
<div id="Analytics/Prediction/KNN"/>
### K-Nearest-Neighbours
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Prediction/KNN/thumbnail.png"/>
Performs k-nearest-neighbour prediction on the data. The prediction for a new point depends on the k-nearest-neighbours around the point. The majority class is used as the prediction.
[Link to Github page](Analytics/Prediction/KNN)
<div id="Analytics/Prediction/SVM"/>
### Support Vector Machine
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Prediction/SVM/thumbnail.png"/>
Predicts classes of new data from old data by drawing a boundary between two classes whereas the margin around the bondary is made as large as possible to avoid touching the points.
[Link to Github page](Analytics/Prediction/SVM)
<div id="Analytics/Websites/Website%20Analysis"/>
### Website Analysis
Extracts the structure and content of a website and its pages.
[Link to Github page](Analytics/Websites/Website%20Analysis)
<div id="Inputs/Sharepoint%20Online"/>
### Sharepoint Online Downloader
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/Sharepoint Online/thumbnail.png"/>
Download a file from a Sharepoint Online site.
[Link to Github page](Inputs/Sharepoint%20Online)
<div id="Inputs/Rdata"/>
### R Data Reader
Joins regions defined in a shapefile with points defined as latitudes and longitudes, and gives meta information about the content of the shapefile
[Link to Github page](Inputs/Rdata)
<div id="Inputs/Rds%20Batch%20Append"/>
### Rds Batch Append
Reads multiple rds files either from an upstream block, or a folder, and appends them
[Link to Github page](Inputs/Rds%20Batch%20Append)
<div id="Inputs/PDF%20Reader"/>
### PDF Reader
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/PDF Reader/thumbnail.png"/>
Extract text from PDF files.
[Link to Github page](Inputs/PDF%20Reader)
<div id="Inputs/SFTP%20Downloader"/>
### SFTP Downloader
<img align="right" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/SFTP Downloader/thumbnail.png"/>
Download files from a SFTP server folder.
[Link to Github page](Inputs/SFTP%20Downloader)
