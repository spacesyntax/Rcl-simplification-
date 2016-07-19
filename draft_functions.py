import networkx as nx
import processing

# Feature ID Filtering

request = QgsFeatureRequest().setFilterFids( fids )
list = [ feat for feat in layer.getFeatures( request ) ]


# processing.runalg('qgis:deleteduplicategeometries', input, output)

# reference: http://stackoverflow.com/questions/30770776/networkx-how-to-create-multidigraph-from-shapefile

def read_multi_shp(path):
    """
    copied from read_shp, but allowing MultiDiGraph instead.
    """
    try:
        from osgeo import ogr
    except ImportError:
        raise ImportError("read_shp requires OGR: http://www.gdal.org/")

    net = nx.MultiDiGraph() # <--- here is the main change I made

    def getfieldinfo(lyr, feature, flds):
            f = feature
            return [f.GetField(f.GetFieldIndex(x)) for x in flds]

    def addlyr(lyr, fields):
        for findex in xrange(lyr.GetFeatureCount()):
            f = lyr.GetFeature(findex)
            flddata = getfieldinfo(lyr, f, fields)
            g = f.geometry()
            attributes = dict(zip(fields, flddata))
            attributes["ShpName"] = lyr.GetName()
            if g.GetGeometryType() == 1:  # point
                net.add_node((g.GetPoint_2D(0)), attributes)
            if g.GetGeometryType() == 2:  # linestring
                attributes["Wkb"] = g.ExportToWkb()
                attributes["Wkt"] = g.ExportToWkt()
                attributes["Json"] = g.ExportToJson()
                last = g.GetPointCount() - 1
                net.add_edge(g.GetPoint_2D(0), g.GetPoint_2D(last), attr_dict=attributes) #<--- also changed this line

    if isinstance(path, str):
        shp = ogr.Open(path)
        lyrcount = shp.GetLayerCount()  # multiple layers indicate a directory
        for lyrindex in xrange(lyrcount):
            lyr = shp.GetLayerByIndex(lyrindex)
            flds = [x.GetName() for x in lyr.schema]
            addlyr(lyr, flds)
    return net


def read_shp_to_multi(shp_path):
    graph_shp = read_multi_shp(shp_path)
    graph = nx.MultiGraph(graph_shp.to_undirected(reciprocal=False))
    return graph


# make iterator

def make_iter(my_list):
    for i in range(0,len(my_list-1)):
        yield my_list[i]


def pair(list): #Iterate over pairs in a list
    for i in range(1, len(list)):
        yield list[i-1], list[i]
# for seg_start, seg_end in pair(line.asPolyline()):

snap_threshold = 0.0001


def point_equality(vertex1,vertex2, snap_threshold):
    return ((abs(vertex1[0] - vertex2[0]) < snap_threshold) and
            (abs(vertex1[1] - vertex2[1]) < snap_threshold))


def explode_shapefile(shp_path, expl_shp_path):
    shp_input = QgsVectorLayer(shp_path, "network", "ogr")
    processing.runalg("qgis:explodelines", shp_input, expl_shp_path)
    expl_shp = QgsVectorLayer(expl_shp_path, "network_exploded", "ogr")
    return expl_shp


# slower function


def parse_shp_to_graph(shp_path):
    shp = QgsVectorLayer(shp_path, "network", "ogr")
    # shapefile should be exploded first
    shp_edges = {i.id(): i.geometryAndOwnership() for i in shp.getFeatures()}
    attr_dict = {i.id(): i.attributes() for i in shp.getFeatures()}
    graph = nx.MultiGraph()
    for k, v in shp_edges.items():
        graph.add_edge(v.asPolyline()[0], v.asPolyline()[-1], attr=attr_dict[k])
    return graph



def to_graph(l):
    g = nx.Graph()
    for part in l:
        # each sub-list is a bunch of nodes
        g.add_nodes_from(part)
        # it also implies a number of edges:
        g.add_edges_from(to_edges(part))
    return g


# careful it does not give all possible combinations)
def to_edges(l):
    """
        treat `l` as a Graph and returns it's edges
        to_edges(['a','b','c','d']) -> [(a,b), (b,c),(c,d)]
    """
    it = iter(l)
    last = next(it)
    for current in it:
        yield last, current
        last = current




def subgraph_for_back(shp,dual_graph):
    # subgraph by attribute
    expr_foreground = QgsExpression(
        "type= 'primary' OR type='primary_link' OR type = 'motorway' OR type= 'motorway_link' OR type= 'secondary' OR type= 'secondary_link' OR type= 'trunk' OR type= 'trunk_link'")
    expr_background = QgsExpression(
        "type='tertiary' or type='tertiary_link' or type= 'bridge' OR type='footway' OR type = 'living_street' OR type= 'path' OR type= 'pedestrian' OR type= 'residential' OR type= 'road' OR type= 'service' OR type= 'steps' OR type= 'track' OR type= 'unclassified' OR type='abandonded' OR type='bridleway' OR type='bus_stop' OR type='construction' OR type='elevator' OR type='proposed' OR type='raceway' OR type='rest_area'")
    osm_ids_foreground = []
    osm_ids_background = []
    for elem in shp.getFeatures(QgsFeatureRequest(expr_foreground)):
        osm_ids_foreground.append(elem.attribute('osm_id'))
    for elem in shp.getFeatures(QgsFeatureRequest(expr_background)):
        osm_ids_background.append(elem.attribute('osm_id'))
    for_sub_dual = dual_graph.subgraph(osm_ids_foreground)
    back_sub_dual = dual_graph.subgraph(osm_ids_background)
    return for_sub_dual, back_sub_dual

# subgraph a graph based on specified values of an attribute
# attr argument should be a string
# eg. attr = 'type'
# values should be a list
# eg. values = ['primary', 'primary_link', 'motorway', 'motorway_link', 'secondary', 'secondary_link', 'trunk', 'trunk_link']
# eg. values = ['tertiary','tertiary_link', 'bridge', 'footway', 'living_street', 'path', 'pedestrian', 'residential', 'road', 'service', 'steps', 'track', 'unclassified', 'abandonded', 'bridleway', 'bus_stop', 'construction', 'elevator', 'proposed', 'raceway', 'rest_area']


def graphs_intersection(dual_graph_1, dual_graph_2):
    lines_inter = []
    for node in dual_graph_2.nodes():
        if dual_graph_1.degree(node) > dual_graph_2.degree(node):
            lines_inter.append(node)
    return lines_inter