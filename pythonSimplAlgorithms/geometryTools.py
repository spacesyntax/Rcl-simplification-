
import math


def angle_3_points(inter_point, vertex1, vertex2):
    inter_vertex1 = math.hypot(abs(inter_point.asPoint()[0] - vertex1[0]),
                               abs(inter_point.asPoint()[1] - vertex1[1]))
    inter_vertex2 = math.hypot(abs(inter_point.asPoint()[0] - vertex2[0]),
                               abs(inter_point.asPoint()[1] - vertex2[1]))
    vertex1_2 = math.hypot(abs(vertex1[0] - vertex2[0]), abs(vertex1[1] - vertex2[1]))
    A = ((inter_vertex1 ** 2) + (inter_vertex2 ** 2) - (vertex1_2 ** 2))
    B = (2 * inter_vertex1 * inter_vertex2)
    if B != 0:
        cos_angle = A / B
    else:
        cos_angle = NULL
    if cos_angle < -1:
        cos_angle = int(-1)
    if cos_angle > 1:
        cos_angle = int(1)
    return math.degrees(math.acos(cos_angle))


# TODO
def angle_4_points(line1, line2):
    pass


# TODO test
def pl_angle(pl_geom):
    pl = pl_geom.asPolyline()
    totAngle = 0
    for indx, vertex in enumerate(pl_geom.asPolyline()[2:]):
        vertex1 = pl[indx]
        inter_point = QgsGeometry.fromPoint(QgsPoint(pl[indx + 1][0], pl[indx + 1][1]))
        vertex2 = pl[indx + 2]
        totAngle += angle_3_points(inter_point, vertex1, vertex2)
    return totAngle


def mid(pt1, pt2):
    x = (pt1.x() + pt2.x()) / 2
    y = (pt1.y() + pt2.y()) / 2
    return x, y


def pl_midpoint(pl_geom):
    vertices = pl_geom.asPolyline()
    length = 0
    mid_length = pl_geom.length() / 2
    for ind, vertex in enumerate(vertices):
        start_vertex = vertices[ind]
        end_vertex = vertices[(ind + 1) % len(vertices)]
        length += math.hypot(abs(start_vertex[0] - end_vertex[0]), abs(start_vertex[1] - end_vertex[1]))
        ind_mid_before = ind
        ind_mid_after = ind + 1
        if length > mid_length:
            midpoint = mid(vertices[ind_mid_before], vertices[ind_mid_after])
            break
        elif length == mid_length:
            midpoint = vertices[ind_mid_after]
            break
    return midpoint