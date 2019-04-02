# omniscope-custom-blocks
Public repository for custom blocks for Omniscope 2019+.
The blocks added here will be available to install in the block picker of Omniscope.

## List of blocks

### Connectors
<table>
    <tr valign="top">
        <td width="33%">Flightstats Airports (R)<br><a href="Connectors/Flightstats/Airports/R/" title="Flightstats Airports (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Airports/R/thumbnail.png"></a></td>
        <td width="33%">Flightstats Airlines (R)<br><a href="Connectors/Flightstats/Airlines/R/" title="Flightstats Airlines (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Airlines/R/thumbnail.png"></a></td>
        <td width="33%">Flightstats Flights (R)<br><a href="Connectors/Flightstats/Flights/R/" title="Flightstats Flights (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Flights/R/thumbnail.png"></a></td>
    </tr>
    <tr valign="top">
        <td width="33%">Overpass Street Coordinates (Python)<br><a href="Connectors/Overpass/Street%20Coordinates/Python/" title="Overpass Street Coordinates (Python)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Overpass/Street%20Coordinates/Python/thumbnail.png"></a></td>
        <td width="33%"></td>
        <td width="33%"></td>
    </tr>
</table>

### Preparation
<table>
    <tr valign="top">
        <td width="33%">Fuzzy Join (R)<br><a href="Preparation/Join/Fuzzy%20Join/R/" title="Fuzzy Join (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Join/Fuzzy%20Join/R/thumbnail.png"></a></td>
        <td width="33%">Inequality Join (R)<br><a href="Preparation/Join/Inequality%20Join/R/" title="Inequality Join (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Join/Inequality%20Join/R/thumbnail.png"></a></td>
        <td width="33%"></td>
    </tr>
</table>

### Analytics
<table>
    <tr valign="top">
        <td width="33%">DBScan (R)<br><a href="Analytics/Clustering/DBScan/R/" title="DBScan (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/DBScan/R/thumbnail.png"></a></td>
        <td width="33%">KMeans (R)<br><a href="Analytics/Clustering/KMeans/R/" title="KMeans (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/KMeans/R/thumbnail.png"></a></td>    
        <td width="33%">Gaussian Mixture Model (R)<br><a href="Analytics/Clustering/GMM/R/" title="GMM (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/GMM/R/thumbnail.png"></a></td>      
    </tr>
    <tr valign="top">
        <td width="33%">Attribute Analysis (R)<br><a href="Analytics/Network%20Analysis/Attribute%20Analysis/R/" title="Attribute Analysis (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Network%20Analysis/Attribute%20Analysis/R/thumbnail.png"></a></td>
        <td width="33%">Relationship Analysis (R)<br><a href="Analytics/Network%20Analysis/Relationship%20Analysis/R/" title="Attribute Analysis (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Network%20Analysis/Relationship%20Analysis/R/thumbnail.png"></a></td>
        <td width="33%">DBScan (Python)<br><a href="Analytics/Clustering/DBScan/Python/" title="DBScan (Python)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/DBScan/Python/thumbnail.png"></a></td>
    </tr>
    <tr valign="top">
        <td width="33%">K-Nearest-Neighbours (R)<br><a href="Analytics/Prediction/KNN/R/" title="K-Nearest-Neighbours (R)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Prediction/KNN/R/thumbnail.png"></a></td>
        <td width="33%">Support Vector Machine Prediction (Python)<br><a href="Analytics/Prediction/SVM/Python/" title="Support Vector Machine Prediction (Python)"><img width="290" src="https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Prediction/SVM/Python/thumbnail.png"></a></td>
        <td width="33%"></td>     
    </tr>

</table>


1. Inputs
2. Connectors
  1. [Flightstats Airports](Connectors/Flightstats/Airports/R/)
  2. [Flightstats Airlines](Connectors/Flightstats/Airlines/R/)
  3. [Flightstats Flights](Connectors/Flightstats/Flights/R/)
  4. [Overpass Street Coordinates](Connectors/Overpass/StreetCoordinates/Python/)
3. Preparation
  1. [Fuzzy Join](Preparation/Join/Fuzzy%20Join/R/)
  2. [Inequality Join](Preparation/Join/Inequality%20Join/R/)
4. Analytics
  1. Clustering
    1. [DBScan (R)](Analytics/Clustering/DBScan/R/)
    2. [DBScan (Python)](Analytics/Clustering/DBScan/Python/)
    3. [KMeans](Analytics/Clustering/KMeans/R/)
    4. [GMM](Analytics/Network%20Analysis/Attribute%20Analysis/R/)
  2. Prediction
    1. [K-Nearest-Neighbours](Analytics/Prediction/KNN/R/)
    2. [Support Vector Machine Prediction](Analytics/Prediction/SVN/Python/)
  3. Network analysis
    1. [Attribute Analysis](Analytics/Network%20Analysis/Attribute%20Analysis/R/)
    2. [Relationship Analysis](Analytics/Network%20Analysis/Relationship%20Analysis/R/)


## How to create a new block
Create a directory under one of the main sections that specifies the general area of what the block does. Create then a subdirectory specifying the language the block works in, which is either R, Python2 or Python3. In a last step, create the directory which contains your block's data. Add three files: The source code of the block, a README.md file containing a description and a thumbnail.png visualising what the block does. The source code should be reasonably documented and potentially contain sections to describe input fields and parameters.
