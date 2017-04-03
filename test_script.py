# imports
execfile(u'/Users/joe/Rcl-simplification-/sGraph/sGraph.py'.encode('utf-8'))
execfile(u'/Users/joe/Rcl-simplification-/pythonSimplAlgorithms/geometryTools.py'.encode('utf-8'))
execfile(u'/Users/joe/Rcl-simplification-/sGraph/utilityFunctions.py'.encode('utf-8'))

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






























