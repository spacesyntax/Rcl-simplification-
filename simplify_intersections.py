from PyQt4.QtCore import QVariant
import networkx as nx
from qgis.core import *
import itertools
import math
# from graph_tools_1 import keep_decimals
from decimal import *

# construct graph
# snap graph

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
    id = int(-1)
    features = []
    for i in list_coords:
        id += int(1)
        feat = QgsFeature()
        p = QgsPoint(i[0], i[1])
        feat.setGeometry(QgsGeometry().fromPoint(p))
        feat.setAttributes([id, i[0], i[1]])
        features.append(feat)
        id += int(1)
    points_shp.startEditing()
    pr.addFeatures(features)
    points_shp.commitChanges()
    return points_shp


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

def find_not_connected_nodes(shp_path, graph,points_shp,neighboring_points, inter_distance_threshold):
    network = QgsVectorLayer(shp_path, "original_network", "ogr")
    point_ids_coords = { p.id(): (p.attributes()[1],p.attributes()[2]) for p in points_shp.getFeatures() }
    not_connected_nodes = {}
    for k, v in neighboring_points.items():
        nodes = [node_id for node_id in v if point_ids_coords[node_id] not in graph.neighbors(point_ids_coords[k]) and math.hypot(abs(point_ids_coords[node_id][0]-point_ids_coords[k][0]), abs(point_ids_coords[node_id][1]-point_ids_coords[k][1])) <= inter_distance_threshold and node_id != k]
        if len(nodes) != 0:
            not_connected_nodes[k] = nodes
    edge_list = []
    feat_id = network.featureCount()
    for k, v in not_connected_nodes.items():
        nodes = [k] + v
        for comb in itertools.combinations(nodes,2):
            feat_id += 1
            edge_list.append((point_ids_coords[comb[0]], point_ids_coords[comb[1]], {'feat_id': feat_id}))
    return edge_list

# a = find_not_connected_nodes(shp_path, graph,points_shp,neighboring_points, 0.0001)

# add extra short edges to the graph



# graph.add_edges_from(edge_list)


def find_short_edges(primal_graph, inter_distance_threshold):
    ids_short =[]
    for i in primal_graph.edges(data='feat_id'):
        if math.hypot(abs(i[0][0] - i[1][0]), abs(i[0][1] - i[1][1])) <= inter_distance_threshold:
            ids_short.append(i[2])
    return list(set(ids_short))


# b = find_short_edges(graph, 0.0001)

# construct a dual graph with all connections
# dual = graph_to_dual(graph, inter_to_inter=False)
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

    new_geoms ={}

    # new simplified shapefile layer
    simplified_network = QgsVectorLayer('LineString?crs=' + crs.toWkt(), "simplified_network", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(simplified_network)
    pr = network.dataProvider()
    simplified_network.startEditing()
    simplified_network.dataProvider().addAttributes(pr.fields())
    simplified_network.commitChanges()

    all_new_points = []
    for k,v in short_lines_neighbours.items():
        short_endpoints_all = [edge[0] for edge in graph.edges(data=True) if edge[2]['feat_id'] in list(k)]
        short_endpoints_all += [edge[1] for edge in graph.edges(data=True) if edge[2]['feat_id'] in list(k)]
        short_endpoints =[]
        for x in short_endpoints_all:
            if x not in short_endpoints:
                short_endpoints.append(x)
        x = [p[0] for p in short_endpoints]
        y = [p[1] for p in short_endpoints]
        new_point = (float(sum(x)) / float(len(short_endpoints)), float(sum(y)) / float(len(short_endpoints)))
        all_new_points.append(new_point)
        for i in v:
            # TODO: Fix endpoints of pl so that it snaps with connected lines
            # now a mixture of graph nodes and qgs feature nodes is used
            if i < network.featureCount():
                request = QgsFeatureRequest().setFilterFid(i)
                f = next(network.getFeatures(request))
                endpoint_0 = [edge[0] for edge in graph.edges(data=True) if edge[2]['feat_id'] == i][0]
                endpoint_1 = [edge[1] for edge in graph.edges(data=True) if edge[2]['feat_id'] == i][0]
                f_endpoint_0 = f.geometry().asPolyline()[0]
                if endpoint_0 in short_endpoints and endpoint_1 in short_endpoints:
                    feat_to_del.append(i)
                elif (endpoint_0 in short_endpoints and not endpoint_1 in short_endpoints) or (endpoint_0 not in short_endpoints and endpoint_1 in short_endpoints):
                    # find index
                    if (Decimal(keep_decimals(f_endpoint_0[0],6)),Decimal(keep_decimals(f_endpoint_0[1],6))) in [(Decimal(keep_decimals(x[0],6)),Decimal(keep_decimals(x[1],6))) for x in short_endpoints]:
                        # TODO: fix if the geometry has already been changed
                        f_geom = f.geometry()
                        if i in new_geoms.keys():
                            f_geom = new_geoms[i]
                        if len(f_geom.asPolyline())<=2:
                            vertices_to_keep =[new_point]+[f_geom.asPolyline()[-1]]
                        else:
                            vertices_to_keep =[new_point]+[x for ind,x in enumerate(f_geom.asPolyline()) if ind>=1]
                        new_pl=[]
                        for vertex in vertices_to_keep:
                            p=QgsPoint(vertex[0],vertex[1])
                            new_pl.append(p)
                        new_geom = QgsGeometry().fromPolyline(new_pl)
                        new_feat = QgsFeature()
                        new_feat.setGeometry(new_geom)
                        new_feat.setAttributes(attr_dict[i])
                        new_geoms[i] = new_geom
                        feat_to_modify[i] = new_feat
                    else:
                        f_geom = f.geometry()
                        if i in new_geoms.keys():
                            f_geom = new_geoms[i]
                        if len(f_geom.asPolyline())<=2:
                            vertices_to_keep=[f_geom.asPolyline()[0]]+[new_point]
                        else:
                            vertices_to_keep= [x for ind,x in enumerate(f_geom.asPolyline()) if ind<=len(f_geom.asPolyline())-2] +[new_point]
                        new_pl=[]
                        for vertex in vertices_to_keep:
                            p=QgsPoint(vertex[0],vertex[1])
                            new_pl.append(p)
                        new_geom=QgsGeometry().fromPolyline(new_pl)
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


def clean_network(length_max_threshold, length_min_threshold):
    pass