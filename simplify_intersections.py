import os
import networkx as nx
from qgis.core import *
import itertools
import math
from graph_tools_1 import keep_decimals, read_shp_to_graph, snap_graph
from decimal import *
from collections import defaultdict
from PyQt4.QtCore import QVariant, QFileInfo


# save points - nodes in a temporary shp
# get list of nodes of coordinates of the graph

def get_nodes_coord(graph):
    list_coords = [i for i in graph.nodes()]
    return list_coords


def make_points_from_shp(shp_path,list_coords ):
    network = QgsVectorLayer (shp_path, "original_network", "ogr")
    crs = network.crs()
    points_shp = QgsVectorLayer('Point?crs=' + crs.toWkt(), "intersections", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(points_shp)
    pr = points_shp.dataProvider()
    points_shp.startEditing()
    pr.addAttributes([QgsField("fid", QVariant.Int),
                      QgsField("x", QVariant.Double),
                      QgsField("y", QVariant.Double)])
    points_shp.commitChanges()
    id = int(0)
    features = []
    points_ids_coord = {}
    for i in list_coords:
        id += int(1)
        feat = QgsFeature()
        p = QgsPoint(i[0], i[1])
        feat.setGeometry(QgsGeometry().fromPoint(p))
        feat.setAttributes([id, float(i[0]), float(i[1])])
        features.append(feat)
        points_ids_coord[id] = (i[0],i[1])
    points_shp.startEditing()
    pr.addFeatures(features)
    points_shp.commitChanges()

    return points_shp, points_ids_coord


# use spatial index to find n closest neighbours of a point


def find_closest_points(points_shp):
    provider = points_shp.dataProvider()
    spIndex = QgsSpatialIndex()  # create spatial index object
    feat = QgsFeature()
    fit = provider.getFeatures()  # gets all features in layer
    # insert features to index
    while fit.nextFeature(feat):
        spIndex.insertFeature(feat)
    # find lines intersecting other lines
    neighboring_points = {i.id(): spIndex.nearestNeighbor(QgsPoint(i.geometry().asPoint()), 8) for i in points_shp.getFeatures()}
    return neighboring_points


# compare with neighbouring nodes in the graph /snapped graph?

def find_not_connected_nodes(broken_network, snapped_graph,neighboring_points, inter_distance_threshold, points_ids_coord):
    not_connected_nodes = {}
    for k, v in neighboring_points.items():
        nodes = [node_id for node_id in v if points_ids_coord[node_id] not in snapped_graph.neighbors(points_ids_coord[k]) and math.hypot(abs(points_ids_coord[node_id][0]-points_ids_coord[k][0]), abs(points_ids_coord[node_id][1]-points_ids_coord[k][1])) <= inter_distance_threshold and node_id != k]
        if len(nodes) != 0:
            not_connected_nodes[k] = nodes
    edge_list = []
    feat_id = broken_network.featureCount()
    for k, v in not_connected_nodes.items():
        nodes = [k] + v
        for comb in itertools.combinations(nodes,2):
            feat_id += 1
            edge_list.append((points_ids_coord[comb[0]], points_ids_coord[comb[1]], {'feat_id_3': feat_id}))
    return edge_list


# add extra short edges to the graph
# graph.add_edges_from(edge_list)


def find_short_edges(primal_graph, inter_distance_threshold):
    ids_short =[]
    for i in primal_graph.edges(data='feat_id_3'):
        # TODO: exclude self loops or use geometry().length() function
        if math.hypot(abs(i[0][0] - i[1][0]), abs(i[0][1] - i[1][1])) <= inter_distance_threshold and not (i[0][0]==i[1][0] and i[0][1] == i[1][1]):
            ids_short.append(i[2])
    return list(set(ids_short))


# b = find_short_edges(graph, 0.0001)

# construct a dual graph with all connections
# dual = graph_to_dual(snapped_graph_broken, inter_to_inter=False)
# short_edges_dual = dual.subgraph(ids_short)


def find_connected_subgraphs(dual, short_edges_dual):
    short_lines_neighbours = {}
    connected_short_lines = [list(i) for i in nx.connected_components(short_edges_dual)]
    for i in connected_short_lines:
        neighbours = []
        for short_line in i:
            neighbours += [x for x in dual.neighbors(short_line) if x not in neighbours]
        short_lines_neighbours[tuple(i)] = neighbours
    return short_lines_neighbours


def simplify_intersection_geoms(shp_path, short_lines_neighbours, graph):

    network = QgsVectorLayer(shp_path, "network", "ogr")
    attr_dict = {i.id(): i.attributes() for i in network.getFeatures()}
    crs = network.crs()

    feat_to_modify = {}
    feat_to_del = []

    new_geoms = {}

    # new simplified shapefile layer
    simplified_network = QgsVectorLayer('LineString?crs=' + crs.toWkt(), "simplified_network", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(simplified_network)
    pr = network.dataProvider()
    pr_fields = pr.fields()
    simplified_network.startEditing()
    simplified_network.dataProvider().addAttributes([f for f in pr_fields])
    simplified_network.commitChanges()

    all_new_points = []
    geom_dict = {i.id(): i.geometry().asPolyline() for i in network.getFeatures()}
    geom_dict2 = {i.id(): i.geometryAndOwnership() for i in network.getFeatures()}
    edge_info = {edge[2]['feat_id_3']: (edge[0],edge[1]) for edge in graph.edges(data=True)}

    for k,v in short_lines_neighbours.items():
        short_endpoints = list(set([edge_info[i][0] for i in k] + [edge_info[i][1] for i in k]))
        x = [p[0] for p in short_endpoints]
        y = [p[1] for p in short_endpoints]
        new_point = (float(sum(x)) / float(len(short_endpoints)), float(sum(y)) / float(len(short_endpoints)))
        all_new_points.append(new_point)
        for i in v:
            # TODO: Fix endpoints of pl so that it snaps with connected lines
            # now a mixture of graph nodes and qgs feature nodes is used
            if i < network.featureCount():
                endpoint_0 = edge_info[i][0]
                endpoint_1 = edge_info[i][1]
                f_endpoint_0 = geom_dict[i][0]
                if endpoint_0 in short_endpoints and endpoint_1 in short_endpoints:
                    feat_to_del.append(i)
                elif (endpoint_0 in short_endpoints and not endpoint_1 in short_endpoints) or (endpoint_0 not in short_endpoints and endpoint_1 in short_endpoints):
                    # find index
                    f_geom = geom_dict2[i]
                    if i in new_geoms.keys():
                        f_geom = new_geoms[i]
                    if (Decimal(keep_decimals(f_endpoint_0[0],6)),Decimal(keep_decimals(f_endpoint_0[1],6))) in [(Decimal(keep_decimals(x[0],6)),Decimal(keep_decimals(x[1],6))) for x in short_endpoints]:
                        # TODO: fix if the geometry has already been changed
                        vertices_to_keep =[new_point]+[x for ind,x in enumerate(f_geom.asPolyline()) if ind>=1]
                    else:
                        vertices_to_keep = [x for ind, x in enumerate(f_geom.asPolyline()) if
                                            ind <= len(f_geom.asPolyline()) - 2] + [new_point]
                    new_pl = [QgsPoint(vertex[0],vertex[1]) for vertex in vertices_to_keep ]
                    new_geom = QgsGeometry().fromPolyline(new_pl)
                    new_feat = QgsFeature()
                    new_feat.setGeometry(new_geom)
                    new_feat.setAttributes(attr_dict[i])
                    new_geoms[i] = new_geom
                    feat_to_modify[i] = new_feat

    for x in short_lines_neighbours.keys():
        for j in x:
            feat_to_del.append(j)

    all_ids = [i.id() for i in network.getFeatures()]
    ids_feat_copy = [x for x in all_ids if x not in feat_to_del and x not in feat_to_modify.keys()]

    request = QgsFeatureRequest().setFilterFids(ids_feat_copy)
    feat_copy = [feat for feat in network.getFeatures(request)]

    simplified_network.startEditing()
    simplified_network.addFeatures(feat_to_modify.values() + feat_copy)
    simplified_network.commitChanges()
    simplified_network.removeSelection()

    return feat_to_del, feat_to_modify, ids_feat_copy


def clean_network(network, length_max_threshold, length_min_threshold,number_decimals):
    # make graph
    uri = network.dataProvider().dataSourceUri()
    path = os.path.dirname(uri) + "/" + QFileInfo(uri).baseName() + ".shp"

    # TODO: update column id

    graph = read_shp_to_graph(path)
    snapped = snap_graph(graph, number_decimals)

    edges = [e for e in snapped.edges(data=True)]
    edges_coord = [e for e in snapped.edges()]
    edges_coord_rev = [e[::-1]for e in snapped.edges()]

    # exclude self loops if u==v

    duplicates = defaultdict(list)
    for i, item in enumerate(edges_coord):
        duplicates[item].append(i)
    duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}

    for common_edge in list(set(edges_coord).intersection(edges_coord_rev)):
        if not common_edge in duplicates.keys():
            duplicates[common_edge]=[]
        for x in [i for i, val in enumerate(edges_coord) if val == common_edge] + [i for i, val in enumerate(edges_coord_rev) if val == (common_edge[1],common_edge[0])]:
            duplicates[common_edge].append(x)

    duplicates_w_o_self_loops = {k: list(set(v)) for k, v in duplicates.items() if k[0]!=k[1]}
    length_dict = {i.id():i.geometry().length() for i in network.getFeatures()}
    for k, v in duplicates_w_o_self_loops.items():
        ids = [edges[index][2]['feat_id'] for index in v]
        duplicates_w_o_self_loops[k] = ids

    pairs_to_check = {}
    for k, v in duplicates_w_o_self_loops.items():
        pairs_to_check[k]= []
        for comb in itertools.combinations(v,2):
            pairs_to_check[k].append(comb)

    for k, combs in pairs_to_check.items():
        common_pairs = [comb for comb in combs if (length_dict[comb[0]]>= length_dict[comb[1]]*length_min_threshold) or (length_dict[comb[0]] <= length_dict[comb[1]]*length_min_threshold)]
        common = list(set([x for comb in common_pairs for x in comb]))
        common_lengths = [length_dict[x] for x in common ]
        common_sorted = [x for (y,x) in sorted(zip(common_lengths,common))]
        pairs_to_check[k] = common_sorted[1::]

    feat_to_del = [x for k, combs in pairs_to_check.items() for x in combs]

    triangles = []
    for edge in edges:
        for node in snapped.neighbors(edge[0]) + snapped.neighbors(edge[1]):
            if (snapped.has_edge(edge[0],node) or snapped.has_edge(node,edge[0])) and (snapped.has_edge(edge[1],node) or snapped.has_edge(node, edge[1])):
                triangles.append([edge[0],edge[1],node])

    for triangle in triangles:
        # find edges
        edges = [(triangle[0],triangle[1])]

    #            ids =
    #            lengths =

    #for each edge(u, v):
    #    for each vertex w:
    #        if (v, w) is an edge and (w, u) is an edge:
    #            return true
