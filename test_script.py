
road_layer_name = 'road'
road_node_layer_name = 'road_node'

road_layer = getLayerByName(road_layer_name)
road_node_layer = getLayerByName(road_node_layer_name)


sg = sGraph(road_layer, road_node_layer)
dual_cars = sg.make_selection('formofway', 'Dual Carriageway')
sg.subgraph(dual_cars)

dbname = 'nyc'
user = 'postgres'
host = 'localhost'
port = 5432
password = 'spaces01'
schema = "simpl"
table_name = "dual_carriageways"

sg.createDbSublayer(dbname, user, host, port, password, schema, table_name, dual_cars)

con_comp = sg.find_connected_comp()

lines = sg.get_lines_from_nodes(con_comp[-1])

groups = sg.group_by_name(lines)





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

