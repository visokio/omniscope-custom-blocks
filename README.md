# Omniscope Custom Blocks
Public repository for custom blocks for Omniscope Evo.

The blocks added here will be available to install in Omniscope block picker.

## List of blocks (Omniscope 2020+)

These require Omniscope 2020.1 ROCK or later.

1. Inputs
   1. [PDF Reader](Inputs/PDF%20Reader/)
   2. [SFTP Downloader](Inputs/SFTP%20Downloader/)
   3. [Sharepoint Online Downloader](Inputs/Sharepoint%20Online/)
2. Connectors
   1. [Flightstats Airlines](Connectors/Flightstats/Airlines/)
   2. [Flightstats Airports](Connectors/Flightstats/Airports/)
   3. [Flightstats Flights](Connectors/Flightstats/Flights/)
   4. [Overpass Street Coordinates](Connectors/Overpass/Street%20Coordinates/)
   5. [Azure Data Lake Storage Gen2 Blob](Connectors/Azure%20Data%20Lake%20Blob/)
   6. [Slack API WebClient](Connectors/Slack%20API%20WebClient/)
   7. [Google BigQuery Writer](Connectors/Google%20BigQuery%20Writer/)
3. Preparation
   1. [Fuzzy Join](Preparation/Join/Fuzzy%20Join/)
   2. [Inequality Join](Preparation/Join/Inequality%20Join/)
   3. [Gridsquare](Preparation/Geo/Gridsquare/)
   4. [For Each](Preparation/ForEach/ForEach/)
   5. [JSON Normalise](Preparation/JSON/Normalise/)
   6. [Execute Command](Preparation/ExecuteCommand/)
4. Analytics
   1. Clustering
       1. [DBScan](Analytics/Clustering/DBScan/)
       2. [GMM](Analytics/Network%20Analysis/Attribute%20Analysis/)
       3. [KMeans](Analytics/Clustering/KMeans/)
   2. Network analysis
       1. [Attribute Analysis](Analytics/Network%20Analysis/Attribute%20Analysis/)
       2. [Relationship Analysis](Analytics/Network%20Analysis/Relationship%20Analysis/)
   3. Prediction
       1. [K-Nearest-Neighbours](Analytics/Prediction/KNN/)
       2. [Support Vector Machine Prediction](Analytics/Prediction/SVM/)
5. Outputs
   1. [Slack Bot](Outputs/Slack%20Bot/)
   2. [Web Image-PDF output](Outputs/Web%20Image-PDF%20output/)
   3. [Multi-tenant Report to PDF](Outputs/Report%20to%20PDF%20batch%20output/)
   4. [Report tab to PDF](Outputs/Report%20tab%20to%20PDF/)
   5. [Append PDF files](Outputs/Append%20PDF%20files/)


### Inputs
<table>
    <tr valign="top">
        <td width="33%">PDF Reader<br><a href="Inputs/PDF Reader" title="PDF Reader"><img width="190" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/PDF Reader/thumbnail.png"></a>           </td>
       <td width="33%">SFTP Downloader<br><a href="Inputs/SFTP Downloader" title="SFTP Downloader"><img width="190" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/SFTP Downloader/thumbnail.png"></a>           </td>
       <td width="33%">Sharepoint Online Downloader<br><a href="Inputs/Sharepoint Online" title="Sharepoint Online Downloader"><img width="190" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Inputs/Sharepoint Online/thumbnail.png"></a>           </td>
    </tr>
</table>

### Connectors
<table>
    <tr valign="top">
        <td width="33%">Flightstats Airlines<br><a href="Connectors/Flightstats/Airlines/" title="Flightstats Airlines"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Airlines/thumbnail.png"></a></td>
        <td width="33%">Flightstats Airports<br><a href="Connectors/Flightstats/Airports/" title="Flightstats Airports"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Airports/thumbnail.png"></a></td>
        <td width="33%">Flightstats Flights<br><a href="Connectors/Flightstats/Flights/" title="Flightstats Flights"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Flights/thumbnail.png"></a></td>
    </tr>
    <tr valign="top">
        <td width="33%">Overpass Street Coordinates<br><a href="Connectors/Overpass/Street%20Coordinates/" title="Overpass Street Coordinates"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Overpass/Street%20Coordinates/thumbnail.png"></a></td>
        <td width="33%">Azure Data Lake Storage Gen2 Blob<br><a href="Connectors/Azure%20Data%20Lake%20Blob/" title="Azure Data Lake Storage Gen2 Blob"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Azure%20Data%20Lake%20Blob/thumbnail.png"></a></td>
        <td width="33%">Slack API WebClient<br><a href="Connectors/Slack%20API%20WebClient/" title="Slack API WebClient"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Slack%20API%20WebClient/thumbnail.png"></a></td>
    </tr>
</table>

### Preparation
<table>
    <tr valign="top">
        <td width="33%">Fuzzy Join<br><a href="Preparation/Join/Fuzzy%20Join/" title="Fuzzy Join"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Join/Fuzzy%20Join/thumbnail.png"></a></td>
        <td width="33%">Inequality Join<br><a href="Preparation/Join/Inequality%20Join/" title="Inequality Join"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Join/Inequality%20Join/thumbnail.png"></a></td>
        <td width="33%">Gridsquare<br><a href="Preparation/Geo/Gridsquare/" title="Gridsquare"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Geo/Gridsquare/thumbnail.png"></a></td>
    </tr>
   <tr valign="top">
        <td width="33%">For Each<br><a href="Preparation/ForEach/ForEach/" title="For Each"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/ForEach/ForEach/thumbnail.png"></a></td>
      <td width="33%">JSON Normalise<br><a href="Preparation/JSON/Normalise/" title="JSON Normalise"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/JSON/Normalise/thumbnail.png"></a></td>
      <td width="33%">Execute Command<br><a href="Preparation/ExecuteCommand/" title="Execute Command"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/ExecuteCommand/thumbnail.png"></a></td>
   </tr>
</table>

### Analytics
<table>
    <tr valign="top">
        <td width="33%">DBScan<br><a href="Analytics/Clustering/DBScan/" title="DBScan"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/DBScan/thumbnail.png"></a></td>
        <td width="33%">Gaussian Mixture Model<br><a href="Analytics/Clustering/GMM/" title="GMM"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/GMM/thumbnail.png"></a></td>      
        <td width="33%">KMeans<br><a href="Analytics/Clustering/KMeans/" title="KMeans"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/KMeans/thumbnail.png"></a></td>    
    </tr>
    <tr valign="top">
        <td width="33%">Attribute Analysis<br><a href="Analytics/Network%20Analysis/Attribute%20Analysis/" title="Attribute Analysis"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Network%20Analysis/Attribute%20Analysis/thumbnail.png"></a></td>
        <td width="33%">Relationship Analysis<br><a href="Analytics/Network%20Analysis/Relationship%20Analysis/" title="Attribute Analysis"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Network%20Analysis/Relationship%20Analysis/thumbnail.png"></a></td>
        <td width="33%">K-Nearest-Neighbours<br><a href="Analytics/Prediction/KNN/" title="K-Nearest-Neighbours"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Prediction/KNN/thumbnail.png"></a></td>
    </tr>
    <tr valign="top">
        <td width="33%">Support Vector Machine Prediction<br><a href="Analytics/Prediction/SVM/" title="Support Vector Machine Prediction"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Prediction/SVM/thumbnail.png"></a></td>
        <td width="33%"></td>     
        <td width="33%"></td>     
    </tr>
</table>

### Outputs
<table>
    <tr valign="top">
        <td width="25%">Slack Bot<br><a href="Outputs/Slack Bot" title="Slack Bot"><img width="190" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Slack Bot/thumbnail.png"></a>           </td>
        <td width="25%">Web Image-PDF output<br><a href="Outputs/Web Image-PDF output" title="Web Image-PDF output"><img width="190" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Web Image-PDF output/thumbnail.png"></a>           </td>
        <td width="25%">Multi-tenant Report to PDF<br><a href="Outputs/Report to PDF batch output" title="Report to PDF batch output"><img width="190" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Report to PDF batch output/thumbnail.png"></a>           </td>
        <td width="25%">Report tab to PDF<br><a href="Outputs/Report tab to PDF" title="Report tab to PDF"><img width="190" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Report tab to PDF/thumbnail.png"></a>           </td>
    </tr>
   <tr valign="top">
        <td width="25%">Append PDF files<br><a href="Outputs/Append PDF files" title="Append PDF files"><img width="190" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Outputs/Append PDF files/thumbnail.png"></a>           </td>
    </tr>
</table>


## How to create a new block
1. Design your custom block in Omniscope Evo 2020.1 or later.
   The source code should be reasonably documented and potentially contains sections to describe input fields and parameters.
2. Export as a ZIP file from the block dialog.
3. Create a directory in this repository under one of the main sections that specifies the general area of what the block does. 
4. Extract the ZIP file into this directory.
5. Consider adding a README.md for convenience, and a thumbnail.png.
6. Update the root index.json with an entry corresponding to this new block.
7. Update the root README.md (this readme itself) with the new block.


## List of blocks (for previous Omniscope version, 2019.x)

These conform to an older specification of custom blocks supported by Omniscope 2019.3, and will be removed mid-2020.

1. Connectors
   1. [Flightstats Airlines](Connectors/Flightstats/Airlines/R/)
   2. [Flightstats Airports](Connectors/Flightstats/Airports/R/)
   3. [Flightstats Flights](Connectors/Flightstats/Flights/R/)
   4. [Overpass Street Coordinates](Connectors/Overpass/Street%20Coordinates/Python/)
2. Preparation
   1. [Fuzzy Join](Preparation/Join/Fuzzy%20Join/R/)
   2. [Inequality Join](Preparation/Join/Inequality%20Join/R/)
3. Analytics
   1. Clustering
       1. [DBScan (R)](Analytics/Clustering/DBScan/R/)
       2. [DBScan (Python)](Analytics/Clustering/DBScan/Python/)
       3. [GMM](Analytics/Network%20Analysis/Attribute%20Analysis/R/)
       4. [KMeans](Analytics/Clustering/KMeans/R/)
   2. Prediction
       1. [K-Nearest-Neighbours](Analytics/Prediction/KNN/R/)
       2. [Support Vector Machine Prediction](Analytics/Prediction/SVM/Python/)
   3. Network analysis
       1. [Attribute Analysis](Analytics/Network%20Analysis/Attribute%20Analysis/R/)
       2. [Relationship Analysis](Analytics/Network%20Analysis/Relationship%20Analysis/R/)

