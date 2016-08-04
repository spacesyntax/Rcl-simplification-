#**Rcl Simplification**

##**About**
This is a plug-in to simplify a road centre line map to a segment map in preparation for angular segment analysis using Depthmap or the Space Syntax Toolkit plug-in in QGIS.

This plug-in was developed by Space Syntax Open Digital Works (C) 2016 Space Syntax Ltd.

The plug-in takes as an input a road centre line map and produces a a segment map optimised in terms of angular change and number of nodes in its dual graph representation.
he simplification consists of two processes, which are recommended to be made in the following sequence:
1. Simplification of angle
2. Simplification of intersections

Dependencies: [networkx](https://networkx.readthedocs.io/en/stable/install.html)

##**Simplification of angle**
The simplification of angle converts a road centre line map to a segment map that has a simplified dual graph
representation with reduced number of nodes and reduced angular change between segments.

The user has to specify the following parameters:

- **snap endpoints precision**: Avoid disconnections between lines caused by different precisions in the number of decimals
of endpoint coordinates.
- **minimum segment length**: A line  is removed if its length is below the minimum segment length parameter.
- **minimum angle deviation**: Two lines become a straight line if the angle between them is below the minimum angle
deviation parameter.
- **maximum angle deviation**: This parameter is to avoid converting multiple consecutive lines into one when the cumulative
angular change is greater than the maximum angle deviation parameter.

##**Simplification of intersections**
The simplification of intersections converts complex intersections into a single node in a primal graph representation
and collapses all connected edges to that node.

The user has to specify the following parameters:
- **snap endpoints precision**: same as above
- **intersection distance**: Endpoints  of multiple lines collapse in a single point (centroid) when the distance between
them is less than the specified intersection distance parameter .
- **minimum length deviation**: The longest line of two lines that share the same endpoints is removed when its length
is less x times the length of the other line
difference is less than the minimum length deviation parameter.
- **maximum length deviation**: The longest line of a triangle of lines is removed when the length difference of it from the
 sum of the length of the two other lines is less than the maximum length deviation parameter.

##**Installation**
To use the plug-in download the zipped folder, unzip it and move the folder to the qgis plug-ins folder in your machine
(/(User)/.qgis2/pyhton/plugins).

##**Notes**
This plug-in is currently under development. Research and experimentation to define the best graph optimisation
processes and to speed up simplification processing time is currently in progress.
It has been tested with OSM and OS maps.


##**Software Requirements**
[QGIS](http://www.qgis.org/en/site/) (2.0 or above)