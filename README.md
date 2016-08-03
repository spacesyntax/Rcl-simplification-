{\rtf1\ansi\ansicpg1252\cocoartf1404\cocoasubrtf340
{\fonttbl\f0\fnil\fcharset0 HelveticaNeue;\f1\fswiss\fcharset0 Helvetica;\f2\fnil\fcharset0 Consolas;
}
{\colortbl;\red255\green255\blue255;\red38\green38\blue38;\red50\green98\blue178;}
{\*\listtable{\list\listtemplateid1\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat1\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid1\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid1}
{\list\listtemplateid2\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat1\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid101\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid2}
{\list\listtemplateid3\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat1\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid201\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid3}
{\list\listtemplateid4\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat1\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid301\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid4}}
{\*\listoverridetable{\listoverride\listid1\listoverridecount0\ls1}{\listoverride\listid2\listoverridecount0\ls2}{\listoverride\listid3\listoverridecount0\ls3}{\listoverride\listid4\listoverridecount0\ls4}}
\paperw11900\paperh16840\margl1440\margr1440\vieww21180\viewh14980\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\b\fs72 \cf0 Rcl Simplification \

\f1\b0\fs24 \
\

\f0\b\fs48 About
\b0\fs24 \cf2 \expnd0\expndtw0\kerning0
\

\fs32 \cf2 This is a plug-in to simplify a road centre line map to a segment map in preparation for angular segment analysis using Depthmap or the Space Syntax Toolkit plug-in in QGIS.\
\pard\pardeftab720\partightenfactor0
\cf2 \
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0
\cf2 This plug-in was developed by Space Syntax Open Digital Works (C) 2016 Space Syntax Ltd.\
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\partightenfactor0
\cf2 The plug-in takes as an input a road centre line map and produces a a segment map optimised in terms of angular change and number of nodes in its dual graph representation.\
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\partightenfactor0
\cf2 The simplification consists of two processes, which are recommended to be made in the following sequence: \
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\partightenfactor0
\cf2     1. Simplification of angle\
    2. Simplification of intersections\
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\partightenfactor0
\cf2 Dependencies: networkx (installation: https://networkx.readthedocs.io/en/stable/install.html)\
\
\pard\pardeftab720\partightenfactor0

\b\fs48 \cf2 Simplification of angle \
\pard\pardeftab720\partightenfactor0

\b0\fs32 \cf2 The simplification of angle converts a road centre line map to a segment map that has a simplified dual graph representation with reduced number of nodes and reduced angular change between segments. \
\
The user has to specify the following parameters:\
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls1\ilvl0\cf2 \kerning1\expnd0\expndtw0 {\listtext	\'95	}
\b \expnd0\expndtw0\kerning0
snap endpoints precision:
\b0  avoid disconnections between lines caused by different precisions in the number of decimals of endpoint coordinates\
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls2\ilvl0\cf2 \kerning1\expnd0\expndtw0 {\listtext	\'95	}
\b \expnd0\expndtw0\kerning0
minimum segment length:
\b0  A line  is removed if its length is below the minimum segment length parameter.\
\ls2\ilvl0\kerning1\expnd0\expndtw0 {\listtext	\'95	}
\b \expnd0\expndtw0\kerning0
minimum angle deviation: 
\b0 Two lines become a straight line if the angle between them is below the minimum angle deviation parameter .\
\ls2\ilvl0\kerning1\expnd0\expndtw0 {\listtext	\'95	}
\b \expnd0\expndtw0\kerning0
maximum angle deviation :
\b0  This parameter is to avoid converting multiple consecutive lines into one when the cumulative angular change is greater than the maximum angle deviation parameter.\
\pard\tx566\pardeftab720\partightenfactor0

\b\fs48 \cf2 \
\pard\pardeftab720\partightenfactor0
\cf2 Simplification of intersections \
\pard\pardeftab720\partightenfactor0

\b0\fs32 \cf2 The simplification of intersections converts complex intersections into a single node in a primal graph representation and collapses all connected edges to that node. \
\
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls3\ilvl0\cf2 \kerning1\expnd0\expndtw0 {\listtext	\'95	}
\b \expnd0\expndtw0\kerning0
snap endpoints precision:
\b0  same as above \
\ls3\ilvl0\kerning1\expnd0\expndtw0 {\listtext	\'95	}
\b \expnd0\expndtw0\kerning0
intersection distance: 
\b0 Endpoints  of multiple lines collapse in a single point (centroid) when the distance between them is less than the specified intersection distance parameter \
\ls3\ilvl0\kerning1\expnd0\expndtw0 {\listtext	\'95	}
\b \expnd0\expndtw0\kerning0
minimum length deviation: 
\b0 The longest line of two lines that share the same endpoints is removed when their length difference is less than the minimum length deviation parameter\
\ls3\ilvl0\kerning1\expnd0\expndtw0 {\listtext	\'95	}
\b \expnd0\expndtw0\kerning0
maximum length deviation: 
\b0 The longest line of a triangle of lines is removed when the length difference of it from the sum of the length of the two other lines is less than the maximum length deviation parameter \
\pard\pardeftab720\partightenfactor0

\f2\fs24 \cf2 \
\pard\pardeftab720\partightenfactor0

\f0\b\fs48 \cf2 Installation\
\pard\pardeftab720\partightenfactor0

\b0\fs32 \cf2 To use the plug-in download the zipped folder, unzip it and move the folder to the qgis plug-ins folder in your machine (/(User)/.qgis2/pyhton/plugins).\
\
\pard\pardeftab720\partightenfactor0

\b\fs48 \cf2 Notes\
\pard\pardeftab720\partightenfactor0

\b0\fs32 \cf2 This plug-in is currently under development. Research and experimentation to define the best graph optimisation processes and to speed up simplification processing time is currently in progress. \
It has been tested with OSM and OS maps. \cf2 \
\
\pard\pardeftab720\partightenfactor0

\b\fs48 \cf2 Software Requirements\
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls4\ilvl0
\b0\fs32 \cf2 \kerning1\expnd0\expndtw0 {\listtext	\'95	}\expnd0\expndtw0\kerning0
QGIS (2.0 or above) - {\field{\*\fldinst{HYPERLINK "http://www.qgis.org/en/site/"}}{\fldrslt \cf3 http://www.qgis.org/en/site/}}}