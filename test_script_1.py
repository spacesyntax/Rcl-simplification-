from graph_tools_1 import *
from simplify_intersections import *
from dual_graph_to_shp import *


# test script

shp_path = '/Users/joe/Documents/Model Simplificator/Athens/Raw_Data/Network.shp'

# does it alter the feature id?
break_multiparts(shp_path)
update_feat_id_col(shp_path)

# threshold: number decimals
number_decimals = 6
graph=read_shp_to_graph(shp_path)
snapped=snap_graph(graph, number_decimals)

# get_invalid_duplicate_geoms_ids(shp_path, snapped)
dual_t=graph_to_dual(snapped, inter_to_inter=True)

# optional: create dual graph
# shp=iface.mapCanvas().currentLayer()
# dual_to_shp(shp,dual_t)

sets = merge_graph(dual_t,shp_path)
a,b = merge_geometries(sets, shp_path)
shp_path2 = write_shp(a,shp_path)



update_feat_id_col(shp_path2)

merged_network = iface.mapCanvas().currentLayer()


merged_graph=read_shp_to_graph(shp_path2)
dual_f=graph_to_dual(merged_graph,inter_to_inter=False)
i= break_graph(dual_f,merged_network)
c,d=break_geometries(i, merged_network)




broken_network=iface.mapCanvas().currentLayer()
new,copy=simplify_angle(broken_network, 10, 0.00025)





