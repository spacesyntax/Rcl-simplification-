from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsField, QgsFeature, QgsPoint, QgsGeometry
from PyQt4.QtCore import QVariant
import math

# find midpoint between two points


def mid(pt1, pt2):
    x = (pt1.x() + pt2.x())/2
    y = (pt1.y() + pt2.y())/2
    return (x,y)

# find midpoint of a polyline geometry , input geometry type


def pl_midpoint(pl_geom):
    vertices = pl_geom.asPolyline()
    length = 0
    mid_length = pl_geom.length() / 2
    for ind, vertex in enumerate(vertices):
        start_vertex = vertices[ind]
        end_vertex = vertices[(ind +1) % len(vertices)]
        length += math.hypot(abs(start_vertex[0]-end_vertex[0]), abs(start_vertex[1]-end_vertex[1]))
        if length > mid_length:
            ind_mid_before = ind
            ind_mid_after = ind+1
            midpoint = mid(vertices[ind_mid_before], vertices[ind_mid_after])
            break
    return midpoint

def add_column(v_layer, col_name, col_type):
    pr = v_layer.dataProvider()
    v_layer.startEditing()
    pr.addAttributes([QgsField(col_name, col_type)])
    v_layer.commitChanges()


def dual_to_shp(network,dual_graph):
    centroids = {i.id(): pl_midpoint(i.geometry()) for i in network.getFeatures()}

    # new point layer with centroids
    crs = network.crs()
    points = QgsVectorLayer('Point?crs=' + crs.toWkt(), "dual_graph_nodes", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(points)
    pr = points.dataProvider()
    points.startEditing()
    pr.addAttributes([QgsField("id", QVariant.Int)])
    points.commitChanges()

    id = int(-1)
    features = []
    for i in centroids.values():
        feat = QgsFeature()
        p = QgsPoint(i[0], i[1])
        feat.setGeometry(QgsGeometry().fromPoint(p))
        feat.setAttributes([id, i[0], i[1]])
        features.append(feat)
        id += int(1)

    points.startEditing()
    pr.addFeatures(features)
    points.commitChanges()

    # new line layer with edge-edge connections
    lines = QgsVectorLayer('LineString?crs=' + crs.toWkt(), "dual_graph_edges", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(lines)
    pr = lines.dataProvider()
    lines.startEditing()
    pr.addAttributes([QgsField("id", QVariant.Int)])
    lines.commitChanges()

    id = -1
    New_feat = []
    for i in dual_graph.edges():
        id += 1
        new_feat = QgsFeature()
        new_geom = QgsGeometry.fromPolyline([QgsPoint(centroids[i[0]][0],centroids[i[0]][1]),QgsPoint(centroids[i[1]][0],centroids[i[1]][1])])
        new_feat.setGeometry(new_geom)
        new_feat.setAttributes([id])
        New_feat.append(new_feat)

    lines.startEditing()
    pr.addFeatures(New_feat)
    lines.commitChanges()