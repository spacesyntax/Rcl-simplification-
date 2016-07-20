from graph_tools_1 import *
from simplify_intersections import *
from dual_graph_to_shp import *

number_decimals = 0

"""MERGE"""
# give shp path in single quotes
shp_path = 'C:/Users/I.Kolovou/Desktop/itn/os_road_selection_foreground.shp'
update_feat_id_col(shp_path)
g=read_shp_to_graph(shp_path)
snapped= snap_graph(g, number_decimals)

# merge lines from intersection to intersection
dual1= graph_to_dual(snapped, inter_to_inter=True)
sets=merge_graph(dual1,shp_path)
# TODO: when geometries are combined dangles are kept (change endpoints of geoms when geom.combine(geom))
merged_network, merged_geoms = merge_geometries(sets, shp_path)


"""BREAK"""

# write_shp
# update feat_id column
shp_path2 = 'C:/Users/I.Kolovou/Desktop/itn/os_road_selection_foreground_merged.shp'

# break lines at intersections
g2=read_shp_to_graph(shp_path2)
merged_network = QgsVectorLayer(shp_path2, 'to_be_broken', 'ogr')
snapped2 = snap_graph(g2, number_decimals)
dual2= graph_to_dual(snapped2, inter_to_inter=True)

i = break_graph(dual2, merged_network)
# TODO: check unlinks
# TODO: check why some of the lines are not broken (some indices are not included when finding the intersection of two lists) This is due to decimal issues. Use decimals with selected precision everywhere!!

broken_network, lines_ind_to_break = break_geometries(i, merged_network)

# optional – visualise dual graph
network= iface.mapCanvas().currentLayer()
dual_to_shp(network,dual1)



"""SIMPLIFY INTERSECTIONS"""


# write_shp
# update feat_id column
shp_path3 = 'C:/Users/I.Kolovou/Desktop/itn/os_road_selection_foreground_broken.shp'
update_feat_id_col(shp_path3)
g3=read_shp_to_graph(shp_path3)


# TODO: no need to snap? Only if simplify angle and simplify intersections happen consecutively

# Replaced function with integers see experiments
l=get_nodes_coord(g3)

# TODO: if you use snap it has decimals fix x,y attribute column is empty and feat ids are not correct
points = make_points_from_shp(shp_path3, l)
neighbors = find_closest_points(points)

inter_distance_threshold = 50

edge_list = find_not_connected_nodes(shp_path3, g3,points, neighbors, inter_distance_threshold)
g3.add_edges_from(edge_list)

ids_short=find_short_edges(g3, inter_distance_threshold)
broken_network = iface.mapCanvas().currentLayer()
broken_network.select(ids_short)

# TODO: parallel edges that have been added do not have any neighbours in the dual graph

dual3 = graph_to_dual(g3, inter_to_inter=False)
short_edges_dual = dual3.subgraph(ids_short)

short_lines_neighbours=find_connected_subgraphs(dual3, short_edges_dual)

# TODO: some of the values of the keys in short_lines_neighbours do not have any item

d,m,c = simplify_intersection_geoms(shp_path3, short_lines_neighbours,g3)


"""SIMPLIFY ANGLE"""
