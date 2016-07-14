import networkx as nx
from networkx import connected_components
import itertools
import processing
from decimal import *
import math

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

number_decimals = 6


def keep_decimals(number, number_decimals):
    integer_part = int(number)
    decimal_part = str(abs(int((number - integer_part)*(10**number_decimals))))
    if len(decimal_part) < number_decimals:
        zeros = str(0)*(number_decimals-len(decimal_part))
        decimal_part = zeros + decimal_part
    decimal = (str(integer_part) + '.' + decimal_part[0:number_decimals])
    if number < 0:
        decimal = ('-' + str(integer_part) + '.' + decimal_part[0:number_decimals])
    return decimal


def explode_shapefile(shp_path, expl_shp_path):
    shp_input = QgsVectorLayer(shp_path, "network", "ogr")
    processing.runalg("qgis:explodelines", shp_input, expl_shp_path)
    expl_shp = QgsVectorLayer(expl_shp_path, "network_exploded", "ogr")
    return expl_shp

# add_unique_feature_id column
# now it has been manually added ('feat_id')
# add parameter simplify = True so that you deal with less features
def read_shp_to_graph(shp_path):
    graph_shp = nx.read_shp(str(shp_path), simplify=True)
    shp = QgsVectorLayer(shp_path, "network", "ogr")
    # parallel edges are excluded of the graph because read_shp does not return a multi-graph, self-loops are included
    # all_ids = [i.id() for i in shp.getFeatures()]
    # ids = [i[2]['feat_id'] for i in graph.edges(data=True)]
    # parallel_ids = [fid for fid in all_ids if fid not in ids]
    graph = nx.MultiGraph(graph_shp.to_undirected(reciprocal=False))
    # while len(parallel_ids) > 0
    # create new shapefile with lines that have not been added (parallel_ids)
    # column_names = [i.name() for i in shp.pendingFields()]
    # for i in parallel_lines:
    #    graph.add_edge(i[1],i[1],dict(zip(column_names,i[2])))
    return graph


def snap_graph(graph, number_decimals):
    snapped_graph = nx.MultiGraph()
    edges = graph.edges(data=True)
    getcontext().prec = 3
    getcontext().rounding = ROUND_DOWN
    snapped_edges = [((Decimal(keep_decimals(edge[0][0], number_decimals)), Decimal(keep_decimals(edge[0][1], number_decimals))), (Decimal(keep_decimals(edge[1][0], number_decimals)), Decimal(keep_decimals(edge[1][1],number_decimals))), edge[2]) for edge in edges]
    snapped_graph.add_edges_from(snapped_edges)
    return snapped_graph


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


# convert primary graph to dual graph
# TO DO: add option for including length

# primary graph consists of nodes (points) and edges (point,point)
# TO DO: both of them are features
# TO DO: construct {feature line:[feature_point, feature_point]} from shp

# TO DO: add id column name as argument


def graph_to_dual(snapped_graph,continuously=False):
    # construct a dual graph with all connections
    dual_graph_edges = []
    dual_graph_nodes = []
    # TO DO: add nodes (some lines are not connected to others because they are pl)
    # all lines
    if not continuously:
        for i, j in snapped_graph.adjacency_iter():
            edges = []
            for k, v in j.items():
                edges.append(v[0]['feat_id'])
            dual_graph_edges += [x for x in itertools.combinations(edges, 2)]
    # only lines with connectivity 2
    if continuously:
        for i, j in snapped_graph.adjacency_iter():
            edges = []
            if len(j) == 2:
                for k, v in j.items():
                    edges.append(v[0]['feat_id'])
            dual_graph_edges += [x for x in itertools.combinations(edges, 2)]
    dual_graph = nx.MultiGraph()
    dual_graph.add_edges_from(dual_graph_edges)
    for e in snapped_graph.edges_iter(data='feat_id'):
        dual_graph.add_node(e[2]['feat_id'])
    return dual_graph


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




def merge_graph(dual_graph_input,shp_path):
    # 2. merge lines from intersection to intersection
    # Is there a grass function for QGIS 2.14???
    # sets of connected nodes (edges of primary graph)
    shp = QgsVectorLayer(shp_path, "network", 'ogr')
    attr_dict = {i.id(): i.attributes() for i in shp.getFeatures()}
    sets = []
    for j in connected_components(dual_graph_input):
        sets.append(list(j))
    sets_in_order = [set_con for set_con in sets if len(set_con) == 2 or len(set_con) == 1]
    for set in sets:
        if len(set) > 2:
            edges = []
            for n in set:
                if len(dual_graph_input.neighbors(n)) > 2 or len(dual_graph_input.neighbors(n))==1 :
                    edges.append(n)
                    # find all shortest paths and keep longest between edges
            if len(edges) == 0:
                edges = [set[0], set[0]]
            list_paths = [i for i in nx.all_simple_paths(dual_graph_input, edges[0], edges[1])]
            if len(list_paths) == 1:
                set_in_order = list_paths[0]
            else:
                set_in_order = max(enumerate(list_paths), key=lambda tup: len(tup[1]))[1]
                del set_in_order[-1]
            sets_in_order.append(set_in_order)

    # TO DO: alter dual graph
    dual_graph_output = nx.MultiGraph(dual_graph_input)
    for j in sets_in_order:
        if len(j) > 1:
            new_node = attr_dict[set[0]][8]
            all_neighbors = []
            for node in j:
                for neigh in dual_graph_input.neighbors(node):
                    all_neighbors.append(neigh)
                if node != j[0] and dual_graph_output.has_node(node):
                    dual_graph_output.remove_node(node)
            all_neighbors_unique = []
            for x in all_neighbors:
                if x not in all_neighbors_unique and x not in j:
                    all_neighbors_unique.append(x)
            new_edges = [(new_node, x) for x in all_neighbors_unique]
            dual_graph_output.add_edges_from(new_edges)


    # merge segments based on sequence of ids plus two endpoints - combine geometries (new_seq_ids)
    return sets_in_order, dual_graph_output

# TO DO: not random generation of new attributes


def merge_geometries(sets_in_order, shp_path):
    shp = QgsVectorLayer(shp_path, "network", 'ogr')
    geom_dict = {i.id(): i.geometryAndOwnership() for i in shp.getFeatures()}
    attr_dict = {i.id(): i.attributes() for i in shp.getFeatures()}
    merged_geoms = []
    for set_to_merge in sets_in_order:
        if len(set_to_merge) == 1:
            new_geom = geom_dict[set_to_merge[0]]
            new_attr = attr_dict[set_to_merge[0]]
        elif len(set_to_merge) == 2:
            line1_geom = geom_dict[set_to_merge[0]]
            line2_geom = geom_dict[set_to_merge[1]]
            new_geom = line1_geom.combine(line2_geom)
            new_attr = attr_dict[set_to_merge[0]]
        else:
            new_attr = attr_dict[set_to_merge[0]]
            new_geom = geom_dict[set_to_merge[0]]
            geom_to_merge = [geom_dict[i] for i in set_to_merge]
            for i, line in enumerate(geom_to_merge):
                ind = i
                if ind == (len(set_to_merge) - 1):
                    pass
                else:
                    l_geom = geom_to_merge[ind]
                    next_line = set_to_merge[(ind + 1) % len(set_to_merge)]
                    # print set_to_merge[ind], next_line
                    next_l_geom = geom_dict[next_line]
                    new_geom = l_geom.combine(next_l_geom)
                    geom_to_merge[(ind + 1) % len(geom_to_merge)] = new_geom
        merged_geoms.append([new_geom, new_attr])
    crs = shp.crs()
    merged_network = QgsVectorLayer('LineString?crs=' + crs.toWkt(), "merged_network", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(merged_network)
    merged_network.dataProvider().addAttributes([y for y in shp.dataProvider().fields()])
    merged_network.updateFields()
    new_features = []
    for i in merged_geoms:
        feature = QgsFeature()
        feature.setGeometry(i[0])
        feature.setAttributes(i[1])
        new_features.append(feature)
    merged_network.startEditing()
    merged_network.addFeatures(new_features)
    merged_network.commitChanges()
    merged_network.removeSelection()
    return merged_network, merged_geoms


def break_multiparts(shp):
    feat_to_del = []
    for f in shp.getFeatures():
        f_geom_type = f.geometry().wkbType()
        if f_geom_type == 5:
            f_id = f.id()
            attr = f.attributes()
            new_geoms = f.geometry().asGeometryCollection()
            for i in new_geoms:
                new_feat = QgsFeature()
                new_feat.setGeometry(i)
                new_feat.setAttributes(attr)
                shp.startEditing()
                shp.addFeature(new_feat, True)
                shp.commitChanges()
            feat_to_del.append(f_id)
    shp.removeSelection()
    shp.select(feat_to_del)
    shp.startEditing()
    shp.deleteSelectedFeatures()
    shp.commitChanges()
    shp.removeSelection()


def break_graph(dual_graph_output, merged_network):
    # TO DO:
    # 1. Break at intersections
    # create spatial index for features in line layer
    provider = merged_network.dataProvider()
    spIndex = QgsSpatialIndex()  # create spatial index object
    feat = QgsFeature()
    fit = provider.getFeatures()  # gets all features in layer
    # insert features to index
    while fit.nextFeature(feat):
        spIndex.insertFeature(feat)
    # find lines intersecting other lines
    inter_lines = {i.id(): spIndex.intersects(QgsRectangle(QgsPoint(i.geometry().asPolyline()[0]), QgsPoint(i.geometry().asPolyline()[-1]))) for i in merged_network.getFeatures()}

    intersections = []
    for k, v in inter_lines.items():
        for i in v:
            intersections.append([i,k])

    for i in intersections:
        if i[1] not in inter_lines[i[0]]:
            inter_lines[i[0]].append(i[1])

    # find nodes of dual graph connected to other nodes
    con_nodes = {k: v.keys() for k, v in dual_graph_output.adjacency_iter()}
    for k, v in con_nodes.items():
        for item in v:
            inter_lines[k].remove(item)

    for k, v in inter_lines.items():
        if k in con_nodes.keys():
            if k not in con_nodes[k]:
                v.remove(k)

    return inter_lines


def break_geometries(inter_lines, merged_network):

    geom_dict_indices = {i.id(): i.geometry().asPolyline() for i in merged_network.getFeatures()}
    inter_lines_to_break = {k: v for k, v in inter_lines.items() if len(v) != 0}
    inter_lines_to_copy = [k for k, v in inter_lines.items() if len(v) == 0]
    lines_ind_to_break = {}

    for k, v in inter_lines_to_break.items():
        # add the number of indices that a line is going to break
        # add index 0 and index -1 and sort
        break_indices = []
        for item in v:
            inter_points = set(geom_dict_indices[k]).intersection(geom_dict_indices[item])
            for point in inter_points:
                break_indices.append(geom_dict_indices[k].index(point))
        break_indices.append(0)
        break_indices.append(len(geom_dict_indices[k])-1)
        break_indices_unique = list(set(break_indices))
        break_indices_unique.sort()
        lines_ind_to_break[k] = break_indices_unique

    for i in inter_lines_to_copy:
        break_indices = []
        break_indices.append(0)
        break_indices.append(len(geom_dict_indices[k]) - 1)
        lines_ind_to_break[k] = break_indices

    new_broken_feat = []
    attr_dict = {i.id(): i.attributes() for i in merged_network.getFeatures()}

    for k, v in lines_ind_to_break.items():
        for ind, index in enumerate(v):
            if len(v) > 0 and ind != len(v)-1:
                points = []
                for i in range(index, v[ind+1]+1):
                    points.append(QgsGeometry.fromPoint(geom_dict_indices[k][i]).asPoint())
                new_geom = QgsGeometry().fromPolyline(points)
                new_feat = QgsFeature()
                new_feat.setGeometry(new_geom)
                new_feat.setAttributes(attr_dict[k])
                new_broken_feat.append(new_feat)

    crs = merged_network.crs()
    broken_network = QgsVectorLayer('LineString?crs=' + crs.toWkt(), "broken_network", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(broken_network)
    broken_network.dataProvider().addAttributes([y for y in merged_network.dataProvider().fields()])
    broken_network.updateFields()
    broken_network.startEditing()
    broken_network.addFeatures(new_broken_feat)
    broken_network.commitChanges()
    broken_network.removeSelection()
    return broken_network, lines_ind_to_break
