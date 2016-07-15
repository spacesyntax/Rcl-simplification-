import math
import networkx as nx


def simplify_angle(network, angular_threshold, length_threshold):

    New = {}
    Copy = {}
    for feature in network.getFeatures():
        f = feature
        f_geom = f.geometry()
        if len(f_geom.asPolyline()) > 2:
            Dual_G = nx.Graph()
            indices_to_del_angle = []
            indices_to_del_length = []
            l=length_threshold
            for index, point in enumerate(f_geom.asPolyline()):
                if index < len(f_geom.asPolyline()) - 2:
                    first_x = point[0]
                    first_y = point[1]
                    second = f_geom.asPolyline()[(index + 1) % len(f_geom.asPolyline())]
                    second_x = second[0]
                    second_y = second[1]
                    third = f_geom.asPolyline()[(index + 2) % len(f_geom.asPolyline())]
                    third_x = third[0]
                    third_y = third[1]
                    fi = math.degrees(
                        math.asin((third_x - second_x) / math.hypot(third_x - second_x, third_y - second_y)))
                    omega = math.degrees(
                        math.asin((second_x - first_x) / math.hypot(second_x - first_x, second_y - first_y)))
                    angle = 180 + fi - omega
                    if angle > 180:
                        angle = 360 - angle
                    angle = 180 - angle
                    Dual_G.add_edge((index, index + 1), (index + 1, index + 2), angular_change=angle)
                if index < len(f_geom.asPolyline()) - 1:
                    first = point
                    next = f_geom.asPolyline()[(index + 1) % len(f_geom.asPolyline())]
                    l = math.hypot(first[0] - next[0], first[1] - next[1])
                    if l < length_threshold:
                        indices_to_del_length.append(index + 1)
            cumulative_angle = 0
            for i in Dual_G.edges(data=True):
                angle = i[2]['angular_change']
                if angle < angular_threshold:
                    cumulative_angle += angle
                    if cumulative_angle < 90:
                        intersection = set(i[0]).intersection(i[1])
                        indices_to_del_angle.append(list(intersection)[0])
                    else:
                         cumulative_angle = 0
            indices_to_keep = [x for x in range(len(f_geom.asPolyline()) - 1)]
            for i in indices_to_del_angle:
                indices_to_keep.remove(i)
            for i in indices_to_del_length:
                if i in indices_to_keep:
                    indices_to_keep.remove(i)
            if 0 not in indices_to_keep:
                indices_to_keep.append(0)
            if len(f_geom.asPolyline()) - 1 not in indices_to_keep:
                indices_to_keep.append(len(f_geom.asPolyline()) - 1)
            indices_to_keep.sort()
            new_pl = []
            if len(indices_to_keep) == len(f_geom.asPolyline()):
                Copy[feature.id()] = feature
            else:
                for i in indices_to_keep:
                    p = QgsPoint(f_geom.asPolyline()[i])
                    new_pl.append(p)
                new_geom = QgsGeometry().fromPolyline(new_pl)
                if new_geom isGeosValid():
                    new_feat = QgsFeature()
                    new_feat.setGeometry(new_geom)
                    new_feat.setAttributes(feature.attributes())
                    New[feature.id()] = new_feat
        else:
            Copy[feature.id()] = feature

    network.startEditing()
    network.removeSelection()
    network.select(New.keys() + Copy.keys())
    network.deleteSelectedFeatures()
    network.addFeatures(New.values() + Copy.values())
    network.commitChanges()

    return New,Copy