import networkx as nx
from networkx import connected_components
import itertools
from decimal import *
from qgis.core import *
from collections import Counter
from itertools import izip as zip, count  # izip for maximum efficiency
from PyQt4.QtCore import QVariant, QFileInfo
import os.path

# depthmap uses a precision of 6 decimals
# find equivalent to mm precision or use depthmap default precision
# number_decimals = 6


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

# add unique feature id column
# now it has been manually added ('feat_id')


# TODO: error when col_name already exists

def update_feat_id_col(shp_path):
    shp = QgsVectorLayer( shp_path, "network", "ogr")
    pr = shp.dataProvider()
    fieldIdx = shp.dataProvider().fields().indexFromName('feat_id')
    if fieldIdx == -1:
        shp.startEditing()
        pr.addAttributes([QgsField('feat_id', QVariant.Int)])
        shp.commitChanges()
        shp.updateFields()
        fieldIdx = shp.dataProvider().fields().indexFromName('feat_id')

    updateMap = {}
    for f in shp.getFeatures():
        updateMap[f.id()] = {fieldIdx: f.id()}

    shp.dataProvider().changeAttributeValues(updateMap)


# TODO: break edges at the graph, avoid changing raw data
# this changes the raw data


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

# TODO: add networkx function


# add parameter simplify = True so that you deal with less features
# issue in windows (different versions of networkx?)

# TODO: if the input layer is a memory layer then write the shp to local drive and after the process delete it

def read_shp_to_graph(shp_path):
    
    graph_shp = nx.read_shp(str(shp_path), simplify=True)
    shp = QgsVectorLayer(shp_path, "network", "ogr")
    graph = nx.MultiGraph(graph_shp.to_undirected(reciprocal=False))
    # parallel edges are excluded of the graph because read_shp does not return a multi-graph, self-loops are included
    all_ids = [i.id() for i in shp.getFeatures()]
    ids_incl = [i[2]['feat_id'] for i in graph.edges(data=True)]
    ids_excl = set(all_ids) - set(ids_incl)

    request = QgsFeatureRequest().setFilterFids(list(ids_excl))
    excl_features = [feat for feat in shp.getFeatures(request)]

    ids_excl_attr = [[i.geometry().asPolyline()[0], i.geometry().asPolyline()[-1], i.attributes()] for i in
                     excl_features]
    column_names = [i.name() for i in shp.dataProvider().fields()]

    for i in ids_excl_attr:
        graph.add_edge(i[0], i[1], attr_dict=dict(zip(column_names,i[2])))

    return graph


# TODO: to be tested
def get_invalid_duplicate_geoms_ids(shp_path,graph):
    shp = QgsVectorLayer(shp_path, "network", "ogr")
    invalid_geoms_ids = [i.id() for i in shp.getFeatures() if not i.geometry().isGeosValid()]

    dupl_geoms_ids = []

    list_lengths =[i.geometry().length() for i in shp.getFeatures()]
    dupl_lengths = list(set([k for k, v in Counter(list_lengths) if v>1 ]))
    for item in dupl_lengths:
        dupl_geoms_ids.append([i for i, j in zip(count(), [list_lengths]) if j == item])

    for i in graph.edges(data=True):
        if i['feat_id'] in invalid_geoms_ids + dupl_geoms_ids:
            graph.remove_edge(i[0], i[1])


def snap_graph(graph, number_decimals):
    snapped_graph = nx.MultiGraph()
    edges = graph.edges(data=True)
    # maybe not needed
    getcontext().rounding = ROUND_DOWN
    snapped_edges = [((Decimal(keep_decimals(edge[0][0], number_decimals)), Decimal(keep_decimals(edge[0][1], number_decimals))), (Decimal(keep_decimals(edge[1][0], number_decimals)), Decimal(keep_decimals(edge[1][1],number_decimals))), edge[2]) for edge in edges]
    snapped_graph.add_edges_from(snapped_edges)
    return snapped_graph


# convert primary graph to dual graph
# primary graph consists of nodes (points) and edges (point,point)


def graph_to_dual(snapped_graph, inter_to_inter=False):
    # construct a dual graph with all connections
    dual_graph_edges = []
    dual_graph_nodes = []
    # all lines
    if not inter_to_inter:
        for i, j in snapped_graph.adjacency_iter():
            edges = []
            for k, v in j.items():
                edges.append(v[0]['feat_id'])
            dual_graph_edges += [x for x in itertools.combinations(edges, 2)]
    # only lines with connectivity 2
    if inter_to_inter:
        for i, j in snapped_graph.adjacency_iter():
            edges = []
            if len(j) == 2:
                for k, v in j.items():
                    edges.append(v[0]['feat_id'])
            dual_graph_edges += [x for x in itertools.combinations(edges, 2)]
    dual_graph = nx.MultiGraph()
    dual_graph.add_edges_from(dual_graph_edges)
    # add nodes (some lines are not connected to others because they are pl)
    for e in snapped_graph.edges_iter(data='feat_id'):
        dual_graph.add_node(e[2])
    return dual_graph


def merge_graph(dual_graph_input,shp_path):
    # 2. merge lines from intersection to intersection
    # Is there a grass function for QGIS 2.14???
    # sets of connected nodes (edges of primary graph)
    shp = QgsVectorLayer(shp_path, "network", 'ogr')
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

    # TODO: alter dual graph
    dual_graph_output = nx.MultiGraph(dual_graph_input)

    # merge segments based on sequence of ids plus two endpoints - combine geometries (new_seq_ids)
    return sets_in_order

# TODO: not random generation of new attributes

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


def write_shp(merged_network,shp_path):
    shp_path_to_write = os.path.dirname(shp_path) +"/"+ QFileInfo(shp_path).baseName() + "_merged.shp"
    # add a writer
    shp = QgsVectorLayer(shp_path, "network","ogr")
    provider = shp.dataProvider()
    shp_writer = QgsVectorFileWriter(shp_path_to_write, provider.encoding(), provider.fields(),
                                                   provider.geometryType(), provider.crs(), "ESRI Shapefile")
    if shp_writer.hasError() != QgsVectorFileWriter.NoError:
        print "Error when creating shapefile: ", shp_writer.errorMessage()
    del shp_writer
    network_to_break = QgsVectorLayer(shp_path_to_write, "network_to_break", "ogr")
    network_to_break.updateFields()
    network_to_break.dataProvider().addFeatures([x for x in merged_network.getFeatures()])
    QgsMapLayerRegistry.instance().addMapLayer(network_to_break)
    return shp_path_to_write




def break_graph(dual_graph_output, merged_network):
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
