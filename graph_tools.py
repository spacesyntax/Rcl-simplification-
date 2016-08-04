# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RclSimplification
                                 A QGIS plugin
 This plugin simplifies a rcl map to segment map
                              -------------------
        begin                : 2016-06-20
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Space Syntax Limited, Ioanna Kolovou
        email                : I.Kolovou@spacesyntax.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""


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
# TODO: if number_decimals is zero remove dot or work with integers
def keep_decimals(number, number_decimals):
    integer_part = int(number)
    decimal_part = str(abs(int((number - integer_part)*(10**number_decimals))))
    if len(decimal_part) < number_decimals:
        zeros = str(0)*int((number_decimals-len(decimal_part)))
        decimal_part = zeros + decimal_part
    decimal = (str(integer_part) + '.' + decimal_part[0:number_decimals])
    if number < 0:
        decimal = ('-' + str(integer_part) + '.' + decimal_part[0:number_decimals])
    return decimal


# add unique feature id column or update
def update_feat_id_col(shp, col_name, start):
    pr = shp.dataProvider()
    fieldIdx = shp.dataProvider().fields().indexFromName(col_name)
    if fieldIdx == -1:
        pr.addAttributes([QgsField(col_name, QVariant.Int)])
        fieldIdx = shp.dataProvider().fields().indexFromName(col_name)
    fid = 1
    updateMap = {}
    if start == 0:
        for f in shp.dataProvider().getFeatures():
            updateMap[f.id()] = {fieldIdx: f.id()}
    elif start == 1:
        for f in shp.dataProvider().getFeatures():
            updateMap[f.id()] = {fieldIdx: fid}
            fid+=1
    shp.dataProvider().changeAttributeValues(updateMap)

# TODO: add networkx function


# add parameter simplify = True so that you deal with less features
# issue in windows (check which versions of networkx-works with the latest)


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


def snap_graph(graph, number_decimals):
    snapped_graph = nx.MultiGraph()
    edges = graph.edges(data=True)
    snapped_edges = [((Decimal(keep_decimals(edge[0][0], number_decimals)), Decimal(keep_decimals(edge[0][1], number_decimals))), (Decimal(keep_decimals(edge[1][0], number_decimals)), Decimal(keep_decimals(edge[1][1],number_decimals))), edge[2]) for edge in edges]
    snapped_graph.add_edges_from(snapped_edges)
    return snapped_graph


# convert primary graph to dual graph
# primary graph consists of nodes (points) and edges (point,point)
def graph_to_dual(snapped_graph, id_column, inter_to_inter=False):
    # construct a dual graph with all connections
    dual_graph_edges = []
    # all lines
    if not inter_to_inter:
        for i, j in snapped_graph.adjacency_iter():
            edges = []
            for k, v in j.items():
                edges.append(v[0][id_column])
            dual_graph_edges += [x for x in itertools.combinations(edges, 2)]
    # only lines with connectivity 2
    if inter_to_inter:
        for i, j in snapped_graph.adjacency_iter():
            edges = []
            if len(j) == 2:
                for k, v in j.items():
                    edges.append(v[0][id_column])
            dual_graph_edges += [x for x in itertools.combinations(edges, 2)]
    dual_graph = nx.MultiGraph()
    dual_graph.add_edges_from(dual_graph_edges)
    # add nodes (some lines are not connected to others because they are pl)
    for e in snapped_graph.edges_iter(data=id_column):
        dual_graph.add_node(e[2])
    return dual_graph


def merge_graph(dual_graph_input):
    # 2. merge lines from intersection to intersection
    # Is there a grass function for QGIS 2.14???
    # sets of connected nodes (edges of primary graph)
    sets = []
    for j in connected_components(dual_graph_input):
        sets.append(list(j))
    sets_in_order = [set_con for set_con in sets if len(set_con) == 2 or len(set_con) == 1]
    for set in sets:
        if len(set) > 2:
            edges = []
            for n in set:
                if len(dual_graph_input.neighbors(n)) > 2 or len(dual_graph_input.neighbors(n)) == 1 :
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

    return sets_in_order


# TODO: not random generation of new attributes


def merge_geometries(sets_in_order, shp_path, number_decimals):
    shp = QgsVectorLayer(shp_path, "network", 'ogr')
    feat_count = shp.featureCount() - 1
    geom_dict = {i.id(): i.geometryAndOwnership() for i in shp.getFeatures()}
    attr_dict = {i.id(): i.attributes() for i in shp.getFeatures()}
    merged_geoms = {}

    for set_to_merge in sets_in_order:
        if len(set_to_merge) == 1:
            merged_geoms[tuple([set_to_merge[0]])] = {'id': set_to_merge[0], 'geom': geom_dict[set_to_merge[0]], 'attr': attr_dict[set_to_merge[0]]}
        else:
            new_geom = geom_dict[set_to_merge[0]]
            geom_to_merge = [geom_dict[i] for i in set_to_merge]
            for ind, line in enumerate(geom_to_merge[1:], start=1):
                second_geom = geom_dict[set_to_merge[ind]]
                first_geom = geom_to_merge[(ind - 1) % len(set_to_merge)]
                new_geom = second_geom.combine(first_geom)
                geom_to_merge[ind] = new_geom
            merged_geoms[tuple(set_to_merge)] = {'geom': new_geom, 'attr': attr_dict[set_to_merge[0]]}

    crs = shp.crs()
    merged_network = QgsVectorLayer('LineString?crs=' + crs.toWkt(), "merged_network", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(merged_network)
    merged_network.dataProvider().addAttributes([y for y in shp.dataProvider().fields()] + [QgsField('merged_id',QVariant.Int)] +[QgsField('feat_id_2',QVariant.Int)])
    merged_network.updateFields()
    column_names = [i.name() for i in shp.dataProvider().fields()] + ['merged_id']+['feat_id_2']
    feat_id_index = column_names.index('feat_id')
    count = 1
    merged_features = []
    for i,j in merged_geoms.items():
        f_geom = j['geom']
        f_geom_type = f_geom.wkbType()
        if f_geom_type == 5:
            attr = j['attr']
            new_geoms = f_geom.asGeometryCollection()
            for geom in new_geoms:
                new_feat = QgsFeature()
                new_feat.setGeometry(geom)
                new_feat.setAttributes(attr+[feat_count]+[count])
                feat_count += 1
                count += 1
                merged_features.append(new_feat)
        else:
            feature = QgsFeature()
            feature.setGeometry(j['geom'])
            if len(i) == 1:
                feature.setAttributes(j['attr'] + [j['attr'][feat_id_index]]+[count])
            else:
                feature.setAttributes(j['attr'] + [feat_count]+[count])
                feat_count += 1
            merged_features.append(feature)
            count += 1

    merged_network.startEditing()
    merged_network.addFeatures(merged_features)
    merged_network.commitChanges()
    merged_network.removeSelection()

    snapped_graph_merged = nx.MultiGraph()
    edges_to_add = [[(Decimal(keep_decimals(feat.geometry().asPolyline()[0][0], number_decimals)),
                      Decimal(keep_decimals(feat.geometry().asPolyline()[0][1], number_decimals))),
                     (Decimal(keep_decimals(feat.geometry().asPolyline()[-1][0], number_decimals)),
                      Decimal(keep_decimals(feat.geometry().asPolyline()[-1][1], number_decimals))), feat.attributes()]
                    for feat in merged_network.getFeatures()]

    for i in edges_to_add:
        snapped_graph_merged.add_edge(i[0], i[1], attr_dict=dict(zip(column_names, i[2])))

    return merged_network, merged_geoms, snapped_graph_merged


def break_graph(snapped_graph_merged, merged_network):
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
    inter_lines = {i.id(): spIndex.intersects(QgsRectangle(QgsPoint(i.geometry().asPolyline()[0]), QgsPoint(i.geometry().asPolyline()[-1]))) for i in merged_network.getFeatures() if not i.geometry().isMultipart()}

    intersections = []
    for k, v in inter_lines.items():
        for i in v:
            intersections.append([i,k])

    for i in intersections:
        if i[1] not in inter_lines[i[0]]:
            inter_lines[i[0]].append(i[1])


    snap_dual_merged = graph_to_dual(snapped_graph_merged, 'feat_id_2', inter_to_inter=False)
    #find nodes of dual graph connected to other nodes
    con_nodes = {k: v.keys() for k, v in snap_dual_merged.adjacency_iter()}
    for k, v in con_nodes.items():
        for item in v:
            if item not in inter_lines[k]:
                print item, inter_lines[k]
            else:
                inter_lines[k].remove(item)

    for k, v in inter_lines.items():
        if k in con_nodes.keys():
            if k not in con_nodes[k]:
                v.remove(k)

    return inter_lines, snap_dual_merged


def break_geometries(inter_lines, merged_network, snapped_graph_merged, number_decimals):

    geom_dict_indices = {i.id(): i.geometry().asPolyline() for i in merged_network.getFeatures()}
    inter_lines_to_break = {k: v for k, v in inter_lines.items() if len(v) != 0}
    inter_lines_to_copy = [k for k, v in inter_lines.items() if len(v) == 0]
    lines_ind_to_break = {}
    feat_count = merged_network.featureCount()-1

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

    request = QgsFeatureRequest().setFilterFids(inter_lines_to_copy)
    feat_to_copy = [f for f in merged_network.getFeatures(request)]
    count=0
    for f in feat_to_copy:
        f.setAttributes(f.attributes()+[f.attributes()[-1]]+[count])
        count+=1

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
                new_feat.setAttributes(attr_dict[k]+ [feat_count]+[count])
                feat_count += 1
                count += 1
                new_broken_feat.append(new_feat)

    crs = merged_network.crs()
    broken_network = QgsVectorLayer('LineString?crs=' + crs.toWkt(), "simplified_network", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(broken_network)
    broken_network.dataProvider().addAttributes([y for y in merged_network.dataProvider().fields()]+[QgsField('broken_id',QVariant.Int)]+[QgsField('feat_id_3',QVariant.Int)])
    broken_network.updateFields()
    broken_network.startEditing()
    broken_network.addFeatures(new_broken_feat)
    broken_network.addFeatures(feat_to_copy)
    broken_network.commitChanges()
    broken_network.removeSelection()


    # convert snapped graph
    snapped_graph_broken = nx.MultiGraph()

    edges_to_add = [[(Decimal(keep_decimals(feat.geometry().asPolyline()[0][0], number_decimals)), Decimal(keep_decimals(feat.geometry().asPolyline()[0][1], number_decimals))),
                     (Decimal(keep_decimals(feat.geometry().asPolyline()[-1][0], number_decimals)), Decimal(keep_decimals(feat.geometry().asPolyline()[-1][1], number_decimals))), feat.attributes()] for feat in broken_network.getFeatures()]

    column_names = [i.name() for i in merged_network.dataProvider().fields()] + ['broken_f_id'] + ['feat_id_3']

    for i in edges_to_add:
        snapped_graph_broken.add_edge(i[0], i[1], attr_dict=dict(zip(column_names, i[2])))

    return broken_network, lines_ind_to_break, snapped_graph_broken

# TODO: to be tested, issue with speed


def get_invalid_duplicate_geoms_ids(shp,graph):
    invalid_geoms_ids = [i.id() for i in shp.getFeatures() if not i.geometry().isGeosValid()]

    dupl_geoms_ids = []

    list_lengths = [keep_decimals(i.geometry().length(), 6) for i in shp.getFeatures()]
    dupl_lengths = list(set([k for k, v in Counter(list_lengths).items() if v > 1]))
    for item in dupl_lengths:
        dupl_geoms_ids.append([i[0] for i in zip(count(), list_lengths) if i[1] == item])

    for i in dupl_geoms_ids:
        i.remove(i[0])

    dupl_geoms_ids_to_rem = [x[0] for x in dupl_geoms_ids]

    #for i in graph.edges(data=True):
    #   if i[2]['feat_id_3'] in invalid_geoms_ids + dupl_geoms_ids_to_rem:
    #       graph.remove_edge(i[0], i[1])

    return invalid_geoms_ids + dupl_geoms_ids_to_rem, dupl_lengths


# this changes the raw data
def break_multiparts(shp, snapped_graph, number_decimals):
    feat_to_del = []
    New_feat = []
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
                New_feat.append(new_feat)
            feat_to_del.append(f_id)
    shp.startEditing()
    shp.addFeatures(New_feat)
    shp.removeSelection()
    shp.select(feat_to_del)
    shp.deleteSelectedFeatures()
    shp.commitChanges()
    shp.removeSelection()

    request = QgsFeatureRequest().setFilterFids(feat_to_del)
    edges_to_remove = [((Decimal(keep_decimals(feat.geometry().asPolyline()[0][0], number_decimals)),
                         Decimal(keep_decimals(feat.geometry().asPolyline()[0][1], number_decimals))),
                        (Decimal(keep_decimals(feat.geometry().asPolyline()[-1][0],number_decimals)),
                         Decimal(keep_decimals(feat.geometry().asPolyline()[-1][1], number_decimals)))) for feat in
                       shp.getFeatures(request)]
    snapped_graph.remove_edges_from(edges_to_remove)

    edges_to_add = [[(Decimal(keep_decimals(feat.geometry().asPolyline()[0][0], number_decimals)),
                      Decimal(keep_decimals(feat.geometry().asPolyline()[0][1], number_decimals))),
                     (Decimal(keep_decimals(feat.geometry().asPolyline()[-1][0], number_decimals)),
                      Decimal(keep_decimals(feat.geometry().asPolyline()[-1][1], number_decimals))), feat.attributes()]
                    for feat in New_feat]

    column_names = [i.name() for i in shp.dataProvider().fields()]

    for i in edges_to_add:
        snapped_graph.add_edge(i[0], i[1], attr_dict=dict(zip(column_names, i[2])))

    return snapped_graph


#TODO: add name suffix
def write_shp(broken_network, shp_path):
    shp_path_to_write = os.path.dirname(shp_path) + "/" + QFileInfo(shp_path).baseName() + "_merged.shp"
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
    network_to_break.dataProvider().addFeatures([x for x in broken_network.getFeatures()])
    return shp_path_to_write

def save_shp(shp, path):
    # add a writer
    provider = shp.dataProvider()
    shp_writer = QgsVectorFileWriter(path, provider.encoding(), provider.fields(),
                                                   provider.geometryType(), provider.crs(), "ESRI Shapefile")
    if shp_writer.hasError() != QgsVectorFileWriter.NoError:
        print "Error when creating shapefile: ", shp_writer.errorMessage()
    del shp_writer
    saved_shp = QgsVectorLayer(path, "simplified_network", "ogr")
    saved_shp.updateFields()
    saved_shp.dataProvider().addFeatures([x for x in shp.getFeatures()])
    return saved_shp


#TODO: clean columns

def clean_cols(shp):
    col_to_del = ['feat_id','merged_id','feat_id_2','broken_id','feat_id_3']
    col_update = 'feat_id'
    col_to_del_ind = [ shp.fieldNameIndex(col_name) for col_name in col_to_del]
    shp.dataProvider().deleteAttributes(col_to_del_ind)
    shp.dataProvider().addAttributes([QgsField(col_update, QVariant.Int)])
    fieldIdx = shp.dataProvider().fields().indexFromName(col_update)
    updateMap = {}
    for f in shp.dataProvider().getFeatures():
        updateMap[f.id()] = {fieldIdx: f.id()}
    shp.dataProvider().changeAttributeValues(updateMap)


#TODO: update layer on mapcanvas
def updateLayer(shp_vector, shp_name):
    ind = [id for id, layer in QgsMapLayerRegistry.instance().mapLayers().items() if layer.name() == shp_name]
    QgsMapLayerRegistry.instance().removeMapLayer([ind])
    QgsMapLayerRegistry.instance().addMapLayer(shp_vector)



# what if it is a temp layer


