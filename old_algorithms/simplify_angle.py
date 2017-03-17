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

import math
import networkx as nx
from qgis.core import *

def simplify_angle(network, angular_threshold, length_threshold, cumulative_threshold):

    New = {}
    Copy = {}

    for f in network.getFeatures():
        f_geom = f.geometry()
        if len(f_geom.asPolyline()) > 2:
            Dual_G = nx.Graph()
            indices_to_del_angle = []
            indices_to_del_length = []
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
                    first_f = point
                    next_f = f_geom.asPolyline()[(index + 1) % len(f_geom.asPolyline())]
                    l = math.hypot(first_f[0] - next_f[0], first_f[1] - next_f[1])
                    if l < length_threshold:
                        indices_to_del_length.append(index + 1)

            cumulative = 0
            indices_to_keep_cumulative =[]

            for i in Dual_G.edges(data=True):
                angle = i[2]['angular_change']
                if angle < angular_threshold and cumulative < cumulative_threshold:
                    intersection = set(i[0]).intersection(i[1])
                    indices_to_del_angle.append(list(intersection)[0])
                    cumulative += angle
                elif angle < angular_threshold and cumulative > cumulative_threshold:
                    intersection = set(i[0]).intersection(i[1])
                    indices_to_keep_cumulative.append(list(intersection)[0])
                    cumulative = 0
                elif angle > angular_threshold and cumulative > cumulative_threshold:
                    intersection = set(i[0]).intersection(i[1])
                    indices_to_keep_cumulative.append(list(intersection)[0])
                    cumulative = 0
                elif angle > angular_threshold and cumulative < cumulative_threshold:
                    cumulative += angle

            all_indices = [x for x in range(len(f_geom.asPolyline()) - 1)]
            indices_to_keep = list(set(all_indices) - set(indices_to_del_angle) - set(indices_to_del_length))
            indices_to_keep.append(0)
            indices_to_keep.append(len(f_geom.asPolyline()) - 1)
            indices_to_keep = list(indices_to_keep) + indices_to_keep_cumulative
            indices_to_keep = list(set(indices_to_keep))
            indices_to_keep.sort()

            new_pl = []
            if len(indices_to_keep) == len(f_geom.asPolyline()):
                Copy[f.id()] = f
            else:
                for i in indices_to_keep:
                    p = QgsPoint(f_geom.asPolyline()[i])
                    new_pl.append(p)
                new_geom = QgsGeometry().fromPolyline(new_pl)
                if new_geom.isGeosValid():
                    new_feat = QgsFeature()
                    new_feat.setGeometry(new_geom)
                    new_feat.setAttributes(f.attributes())
                    New[f.id()] = new_feat
        else:
            Copy[f.id()] = f

    network.startEditing()
    network.removeSelection()
    network.select(New.keys() + Copy.keys())
    network.deleteSelectedFeatures()
    network.addFeatures(New.values() + Copy.values())
    network.commitChanges()

    return New,Copy