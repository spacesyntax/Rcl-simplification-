
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