#from graph_tools_1 import *
#from simplify_intersections import *
#from dual_graph_to_shp import *


# test script

shp_path = '/Users/joe/Documents/Model Simplificator/Athens/Rcl-simplification-test/Rcl-simplification-test2/network_small.shp'
shapefile = QgsVectorLayer(shp_path, "network", "ogr")

""" MEGRE """

# does it alter the feature id?
update_feat_id_col(shapefile, 'feat_id',start=0)

QgsMapLayerRegistry.instance().addMapLayer(shapefile)

# threshold: number decimals
graph = read_shp_to_graph(shp_path)
snapped = snap_graph(graph, 6)

# get_invalid_duplicate_geoms_ids(shp_path, snapped)
dual_t = graph_to_dual(snapped, 'feat_id',inter_to_inter=True)

# optional: create dual graph
# shp = iface.mapCanvas().currentLayer()
# dual_to_shp(shp,dual_t)

sets = merge_graph(dual_t,shp_path)
merged_network, mg, snapped_merged = merge_geometries(sets, shp_path,6)


""" BREAK """

i = break_graph(snapped_merged,merged_network)
broken_network, lines_ind_to_break, snapped_graph_broken = break_geometries(i, merged_network,snapped_merged,6)

# TODO: some geometries not merged
# TODO: clean duplicate geoms


# TODO: correct snapped_graph_broken

""" SIMPLIFY INTERSECTIONS """

shp_path1='/Users/joe/Documents/Model Simplificator/Athens/Rcl-simplification-test/Rcl-simplification-test2/broken_network.shp'

broken_network = QgsVectorLayer(shp_path1,"broken_network","ogr")
update_feat_id_col(broken_network, 'feat_id_3',start=0)
QgsMapLayerRegistry.instance().addMapLayer(broken_network)
graph = read_shp_to_graph(shp_path1)
snapped_graph_broken = snap_graph(graph, 6)

l=get_nodes_coord(snapped_graph_broken)
points,point_ids_coords = make_points_from_shp(shp_path1, l)
neighbors = find_closest_points(points)

inter_distance_threshold = 0.0002

edge_list = find_not_connected_nodes(broken_network, snapped_graph_broken,neighbors, inter_distance_threshold, point_ids_coords)
snapped_graph_broken.add_edges_from(edge_list)

ids_short = find_short_edges(snapped_graph_broken, inter_distance_threshold)

# broken_network = iface.mapCanvas().currentLayer()
# broken_network.select(ids_short)

dual3 = graph_to_dual(snapped_graph_broken, 'feat_id_3', inter_to_inter=False)#short_edges_dual = dual3.subgraph(ids_short)
short_edges_dual = dual3.subgraph(ids_short)
short_lines_neighbours = find_connected_subgraphs(dual3, short_edges_dual)

h = short_lines_neighbours
short_lines_neighbours = {k:v for k, v in h.items() if len(v) != 0}



#d, m, c = simplify_intersection_geoms(shp_path1, short_lines_neighbours,snapped_graph_broken)

# TODO: some of the values of the keys in short_lines_neighbours do not have any item


""" SIMPLIFY ANGLE """

#broken_network=iface.mapCanvas().currentLayer()
#new,copy=simplify_angle(broken_network, 10, 0.00025)





