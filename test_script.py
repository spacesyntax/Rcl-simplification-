
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
sg.createDbSublayer(dbname, user, host, port, password, schema, table_name, dual_cars)

dc_comp = dc.find_connected_comp()
rb_comp = rb.find_connected_comp()

lines = sg.get_lines_from_nodes(con_comp[-1])
































ndegree_1 = list(set([n for n,neigh_n in sg.subtopology.items() if len(neigh_n) == 1]))
ndegree_1_passed = []
connected_comp = []
# for n in ndegree_1:

n = ndegree_1[0]
#    if n not in ndegree_1_passed:

tree = [[n]]
n_iter = 0
ndegree_1_passed.append(n)
while n_iter < 100:
    last = tree[-1]
    n_iter += 1
    # TODO in con_1 or is self loop
    #if last[0] in ndegree_1 and n_iter == 2:
    #    ndegree_1_passed.append(last[0])
        # print "no other line connected"
    #    n_iter = 0
    #    break
    #else:
    tree = get_next_vertices(tree)
    if tree[-1] == []:
        n_iter = 0
        tree.remove([])
        # print "hit end"
        break
connected_comp.append(tree)

