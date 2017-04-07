# imports
execfile(u'/Users/joe/Rcl-simplification-/sGraph/sGraph.py'.encode('utf-8'))
execfile(u'/Users/joe/Rcl-simplification-/pythonSimplAlgorithms/geometryTools.py'.encode('utf-8'))
execfile(u'/Users/joe/Rcl-simplification-/sGraph/utilityFunctions.py'.encode('utf-8'))

execfile(u'C:/Users/I.Kolovou/Documents/GitHub/Rcl-simplification-/sGraph/sGraph.py'.encode('mbcs'))
execfile(u'C:/Users/I.Kolovou/Documents/GitHub/Rcl-simplification-/pythonSimplAlgorithms/geometryTools.py'.encode('mbcs'))
execfile(u'C:/Users/I.Kolovou/Documents/GitHub/Rcl-simplification-/sGraph/utilityFunctions.py'.encode('mbcs'))

road_layer_name = 'road'
#road_node_layer_name = 'road_node'

road_layer = getLayerByName(road_layer_name)
#road_node_layer = getLayerByName(road_node_layer_name)

# get fields
edge_attrs = [QgsField(i.name(), i.type()) for i in road_layer.dataProvider().fields()]
#node_attrs = [QgsField(i.name(), i.type()) for i in road_node_layer.dataProvider().fields()]

# load os road layer and its topology
input_edges = {edge.id():edge for edge in road_layer.getFeatures()}

sg = sGraph(input_edges.values(), source_col='startnode', target_col='endnode')

closed_linestrings = sg.group_dc(input_edges)

path = None
crs = road_layer.dataProvider().crs()
encoding = road_layer.dataProvider().encoding()
geom_type = road_layer.dataProvider().geometryType()
name = 'closed_linestrings2'

clsf = closed_linestrings.to_primal_features()
cl_layer = sg.to_shp(path, name, crs, encoding, geom_type, clsf, graph='primal')
QgsMapLayerRegistry.instance().addMapLayer(cl_layer)



dc_w_o_bypass = sg.subgraph('formofway', 'Dual Carriageway', negative=False)
dc_nodes = dc_w_o_bypass.nodes
dc = sg.subgraph_n(dc_nodes)
dc_edges = [f.id() for f in dc.edges]
dc_neg_edges = list(set([f.id() for f in sg.edges]).difference(set(dc_edges)))
dc_neg = sg.subgraph_e(dc_neg_edges, input_edges)

path = None
crs = road_layer.dataProvider().crs()
encoding = road_layer.dataProvider().encoding()
geom_type = road_layer.dataProvider().geometryType()
name = 'dual_car_subgraph'
dcf = dc.to_primal_features()
dc_layer = sg.to_shp(path, name, crs, encoding, geom_type, dcf, graph='primal')
QgsMapLayerRegistry.instance().addMapLayer(dc_layer)

for dc_pr_nodes in dc.find_connected_comp_full():
    if 9063 in dc.get_lines_from_nodes(dc_pr_nodes):
        break


dc_dl_nodes = dc.get_lines_from_nodes(dc_pr_nodes)
dc_pr_nodes_con0 = [node for node in dc_pr_nodes if len(dc.topology[node]) == 1]
links = []

for node in dc_pr_nodes_con0:
    paths = [[node]]
    x = 0
    link = None
    while link is None and x < 50:
        paths = sg.make_tree(paths, dc_neg)
        for path in paths:
            last = path[-1]
            if last in dc_pr_nodes:
                print "found path to close linestring"
                link = path
                links.append(link)
        x += 1

dc_neg.get_lines_from_nodes_ordered(links[0])

















# simplify dual carriageways
sg.simplify_dc()

# simplify roundabouts

# simplify sliproads

path = None
crs = road_layer.dataProvider().crs()
encoding = road_layer.dataProvider().encoding()
geom_type = road_layer.dataProvider().geometryType()
name = 'simplified'

# simplified primal graph to shp
nf = sg.to_primal_features()
ml_layer = sg.to_shp(path, name, crs, encoding, geom_type, nf, graph='primal')
QgsMapLayerRegistry.instance().addMapLayer(ml_layer)

name = 'simplified_dual'
df = sg.to_dual_features()
md_layer = sg.to_shp(path, name, crs, encoding, geom_type, df, graph='dual')
QgsMapLayerRegistry.instance().addMapLayer(md_layer)



# simplified dual graph to shp



dbname = 'nyc'
user = 'postgres'
host = 'localhost'
port = 5432
password = 'spaces01'
schema = "simpl"
table_name = "dual_carriageways"
sg.createDbSublayer(dbname, user, host, port, password, schema, table_name, dc.edges)






























