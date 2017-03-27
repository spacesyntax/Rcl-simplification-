
road_layer_name = 'road'
road_node_layer_name = 'road_node'

road_layer = getLayerByName(road_layer_name)
road_node_layer = getLayerByName(road_node_layer_name)

# get fields
edge_attrs = [QgsField(i.name(), i.type()) for i in road_layer.dataProvider().fields()]
node_attrs = [QgsField(i.name(), i.type()) for i in road_node_layer.dataProvider().fields()]

# load os road layer and its topology
edges = [edge for edge in road_layer.getFeatures()]
sg = sGraph(edges, source_col='startnode', target_col='endnode')

# subgraph dual carriageways
dc = sg.subgraph('formofway', 'Dual Carriageway', negative=False)
# subgraph roundabouts
rb = sg.subgraph('formofway', 'Roundabout', negative=False)
# subgraph sliproads
sl = sg.subgraph('formofway', 'Slip Road', negative=False)

dbname = 'nyc'
user = 'postgres'
host = 'localhost'
port = 5432
password = 'spaces01'
schema = "simpl"
table_name = "dual_carriageways"
sg.createDbSublayer(dbname, user, host, port, password, schema, table_name, dc.edges)

dc_comp = dc.find_connected_comp_full()

rb_comp = rb.find_connected_comp()

lines = sg.get_lines_from_nodes(con_comp[-1])




























