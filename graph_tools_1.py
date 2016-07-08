import networkx as nx
from networkx import connected_components
import itertools
import processing

# make iterator


def make_iter(my_list):
    for i in range(0,len(my_list-1)):
        yield my_list[i]


# convert shapefile to graph
# you may need to explode the network first


snap_threshold = 0.0001


def point_equality(vertex1,vertex2, snap_threshold):
    return ((abs(vertex1[0] - vertex2[0]) < snap_threshold) and
            (abs(vertex1[1] - vertex2[1]) < snap_threshold))


def snap(graph):
    # traverse nodes and group them if distance between them small
    nodes_comb= []
    all_nodes_comb = itertools.combinations(graph.nodes(), 2)
    for comb in all_nodes_comb:
        if point_equality(comb[0],comb[1],snap_threshold):
            nodes_comb.append([comb[0],comb[1]])
    graph_comb = to_graph(nodes_comb)
    grouped_nodes = nx.connected_components(graph_comb)
    node_replacement = {}
    node_repl_comb = {}
    for i in grouped_nodes:
        node_replacement[list(i)[0]] = list(i)
    for k, v in node_replacement.items():
        for item in v:
            if item != k:
                node_repl_comb[item]= k
    graph_snapped = nx.MultiGraph(graph)
    for p0,p1,d in graph.edges(data=True):
        new_p0 = p0
        new_p1 = p1
        if p0 in node_repl_comb.keys():
            new_p0 = node_repl_comb[p0]
        if p1 in node_repl_comb.keys():
            new_p1 = node_repl_comb[p1]
        if new_p0 != p0 or new_p1 != p1:
            graph_snapped.remove_edge(p0, p1)
            graph_snapped.add_edge(new_p0, new_p1, data=d)
    return graph_snapped


def keep_2_decimals(number):
    integer_number = int(number)
    decimal_number = str(int ((number - integer_number)*(10**(len(str(number - integer_number))-2))))
    decimal_2 = int('0.'+decimal_number[0]+decimal_number[1])
    return decimal_2


def to_graph(l):
    g = networkx.Graph()
    for part in l:
        # each sublist is a bunch of nodes
        g.add_nodes_from(part)
        # it also imlies a number of edges:
        g.add_edges_from(to_edges(part))
    return g


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


def explode_shapefile(shp_path, expl_shp_path):
    shp_input = QgsVectorLayer(shp_path, "network", "ogr")
    processing.runalg("qgis:explodelines", shp_input, expl_shp_path)
    expl_shp = QgsVectorLayer(expl_shp_path, "network_exploded", "ogr")
    return expl_shp


# do you need simplify = True ??
def shp_to_graph(shp_path):
    graph_shp = nx.read_shp(str(shp_path), simplify=True)
    shp = QgsVectorLayer(shp_path, "network", "ogr")
    # parallel edges are excluded of the graph because read_shp does not return a multi-graph, self-loops are included
    #self_loops = [[feat.id(), feat.geometry().asPolyline()[0],feat.attributes()]for feat in shp.getFeatures() if feat.geometry().asPolyline()[0] == feat.geometry().asPolyline()[-1] ]
    # parallel_edges =
    graph = graph_shp.to_undirected(reciprocal=False)
    #column_names = [i.name() for i in shp.pendingFields()]
    #for i in self_loops:
    #    graph.add_edge(i[1],i[1],dict(zip(column_names,i[2])))
    return graph

# slower function


def shp_to_graph_2(shp_path):
    shp = QgsVectorLayer(shp_path, "network", "ogr")
    # shapefile should be exploded first
    shp_edges = {i.id(): [i.geometry().asPolyline()[0],i.geometry().asPolyline()[-1]] for i in shp.getFeatures()}
    graph = nx.MultiGraph()
    for k, v in shp_edges.items():
        graph.add_edge(tuple(v[0]), tuple(v[1]), id_1=k)
    return graph


def shp_to_graph_3(shp_path):
    shp = QgsVectorLayer(shp_path, "network", "ogr")
    # shapefile should be exploded first
    features = [x for x in shp.getFeatures()]
    graph = nx.MultiGraph()
    for i in features:
        graph.add_edge(i.geometry().asPolyline()[0], i.geometry().asPolyline()[-1], attr = i.attributes())
    return graph



# convert primary graph to dual graph
# TO DO: add option for including length

# primary graph consists of nodes (points) and edges (point,point)
# TO DO: both of them are features
# TO DO: construct {feature line:[feature_point, feature_point]} from shp

# TO DO: add id column name as argument


def graph_to_dual_edges(primary_graph):
    # construct a dual graph with all connections
    dual_graph_edges = []
    for i, j in primary_graph.adjacency_iter():
        edges = []
        if len(j) > 1:
            for k, v in j.items():
                edges.append(v[0]['attr'][0])
                dual_graph_edges += [x for x in itertools.combinations(edges, 2)]
    return dual_graph_edges


"""if continuous_lines:
    # construct a dual graph of features with 2 connections
    for i, j in primary_graph.adjacency_iter():
        if len(j) == 2:
            values = []
            for k, v in j.items():
                values.append(v['osm_id'])
            # print values
            dual_graph.add_edge(values[0], values[1], data=None)"""


def dual_edges_to_graph(dual_edges):
    dual_graph = nx.MultiGraph()
    dual_graph.add_edges_from(dual_edges)
    return dual_graph


def subgraph_for_back(shp,dual_graph ):
    # subgraph by attribute
    expr_foreground = QgsExpression(
        "type= 'primary' OR type='primary_link' OR type = 'motorway' OR type= 'motorway_link' OR type= 'secondary' OR type= 'secondary_link' OR type= 'trunk' OR type= 'trunk_link'")
    expr_background = QgsExpression(
        "type='tertiary' or type='tertiary_link' or type= 'bridge' OR type='footway' OR type = 'living_street' OR type= 'path' OR type= 'pedestrian' OR type= 'residential' OR type= 'road' OR type= 'service' OR type= 'steps' OR type= 'track' OR type= 'unclassified' OR type='abandonded' OR type='bridleway' OR type='bus_stop' OR type='construction' OR type='elevator' OR type='proposed' OR type='raceway' OR type='rest_area'")
    osm_ids_foreground=[]
    osm_ids_background=[]
    for elem in shp.getFeatures(QgsFeatureRequest(expr_foreground)):
        osm_ids_foreground.append(elem.attribute('osm_id'))
    for elem in shp.getFeatures(QgsFeatureRequest(expr_background)):
        osm_ids_background.append(elem.attribute('osm_id'))
    for_sub_dual=dual_graph.subgraph(osm_ids_foreground)
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


def merge_lines(dual_graph_input,dual_graph_output):

    # 2. merge lines from intersection to intersection
    # Is there a grass function for QGIS 2.14???

    # sets of connected nodes (edges of primary graph)
    sets = []
    for j in connected_components(dual_graph_input):
        sets.append(list(j))

    # store connectivity information (sequence of ids)
    # find all edges that contain the nodes of a set and order them

    # store (stars) nodes of dual that have connectivity > 2
    # retrieve endpoint lines
    # merge segments based on sequence of ids plus two endpoints - combine geometries (new_seq_ids)

    # TO DO:
    # 1. Break at intersections
    # 3. Explode multipart geometries
    return merged_graph

# TO DO:
# store features of the secondary graph that intersect the main_graph



