from PyQt4.QtCore import QVariant, QFileInfo
import os
import processing
import networkx as nx
from qgis.core import *
import itertools
import csv

# construct graph
# snap graph

# save points - nodes in a temporary shp

shp_to_graph
snap_graph

# get list of nodes of coordinates of the graph


def get_nodes_coord(graph):
    list_coords = []
    for i in graph.nodes():
        list_coords.append(i)

    return list_coords



def make_points_from_shp(shp_original,list_coords ):
    network = QgsVectorLayer (shp_original, "original_network", "ogr")
    crs = network.crs()
    points = QgsVectorLayer('Point?crs=' + crs.toWkt(), "temporary_points", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(points)
    pr = points.dataProvider()
    points.startEditing()
    pr.addAttributes([QgsField("fid", QVariant.Int),
                      QgsField("x", QVariant.Double),
                      QgsField("y", QVariant.Double)])
    points.commitChanges()

    id = int(-1)
    features = []
    for i in list_coords:
        feat = QgsFeature()
        p = QgsPoint(i[0], i[1])
        feat.setGeometry(QgsGeometry().fromPoint(p))
        feat.setAttributes([id, i[0], i[1]])
        features.append(feat)
        id += int(1)

    points.startEditing()
    pr.addFeatures(features)
    points.commitChanges()

    return points


# use spatial index to find n closest neighbours of a point


def find_closest_points(points):
    provider = points.dataProvider()
    spIndex = QgsSpatialIndex()  # create spatial index object
    feat = QgsFeature()
    fit = provider.getFeatures()  # gets all features in layer
    # insert features to index
    while fit.nextFeature(feat):
        spIndex.insertFeature(feat)
    # find lines intersecting other lines
    neighboring_points = {i.id(): spIndex.nearestNeighbor(QgsPoint(i.geometry().asPoint()), 10) for i in points.getFeatures()}


# compare with connected nodes for every point








def simplify_intersections(network,threshold_inter):
    #create a copy of the input network as a memory layer
    crs=network.crs()
    temp_network=QgsVectorLayer('LineString?crs='+crs.toWkt(), "temporary_network", "memory")
    QgsMapLayerRegistry.instance().addMapLayer(temp_network)
    temp_network.dataProvider().addAttributes([y for y in network.dataProvider().fields()])
    temp_network.updateFields()
    temp_network.startEditing()
    temp_network.addFeatures([x for x in network.getFeatures()])
    temp_network.commitChanges()
    temp_network.removeSelection()

    #make a new temporary point layer at intersections
    Points=QgsVectorLayer('Point?crs='+crs.toWkt(),"temporary_points","memory")
    QgsMapLayerRegistry.instance().addMapLayer(Points)
    pr=Points.dataProvider()
    Points.startEditing()
    pr.addAttributes([QgsField("fid", QVariant.Int),
                          QgsField("x", QVariant.Double),
                          QgsField("y", QVariant.Double)])
    Points.commitChanges()

    #add point features at intersections of the network
    nodes_passed=[]
    features=[]
    id=1
    for i in temp_network.getFeatures():
        g=[i.geometry().asPolyline()[0],i.geometry().asPolyline()[-1]]
        for i in g:
            if i not in nodes_passed:
                feat=QgsFeature()
                p=QgsPoint(i[0],i[1])
                feat.setGeometry(QgsGeometry().fromPoint(p))
                feat.setAttributes ([id,i[0],i[1]])
                features.append(feat)
                nodes_passed.append(i)
                id+=1

    Points.startEditing()
    pr.addFeatures(features)
    Points.commitChanges()

    #make a distance matrix of all points for the 10 closest neighbours
    #get the path of the Points layer and make the path of th csv matrix
    network_filepath= network.dataProvider().dataSourceUri()
    (myDirectory,nameFile) = os.path.split(network_filepath)
    csv_path=myDirectory+"/Matrix.csv"

    processing.runalg("qgis:distancematrix", Points, "fid", Points,"fid",0, 10, csv_path)

    #specify new short lines as new edges
    New_edges=[]

    with open(csv_path,'rb') as f:
        reader = csv.reader(f)
        your_list = list(reader)

    #remove header
    your_list.remove(['InputID', 'TargetID', 'Distance'])

    for i in your_list:
        if float(i[2])<=threshold_inter and float(i[2])>0:
            if i[0]>=i[1]:
                New_edges.append([int(i[0]),int(i[1])])

    #make a dictionary of point id and x,y coordinates
    P_D={}
    for i in Points.getFeatures():
        fid=i.id()
        x=i.attribute('x')
        y=i.attribute('y')
        P_D[fid]=(x,y)

    #make a dictionary with x,y coordinates of lines of the network layer and their id
    Id_D={}
    for f in temp_network.getFeatures():
        Id_D[(f.geometry().asPolyline()[0],f.geometry().asPolyline()[-1])]=f.id()

    feat_count=int(temp_network.featureCount())
    feat_count_init=int(temp_network.featureCount())

    new_attr=[]
    for i in range(0,len(temp_network.dataProvider().fields())):
        new_attr.append(NULL)

    New_feat_l=[]
    for t in New_edges:
        p1=P_D[t[0]]
        p2=P_D[t[1]]
        qp_1=QgsPoint(p1[0],p1[1])
        qp_2=QgsPoint(p2[0],p2[1])
        feat=QgsFeature()
        geom=QgsGeometry().fromPolyline([qp_1,qp_2])
        feat.setGeometry(geom)
        feat.setAttributes(new_attr)
        New_feat_l.append(feat)

    temp_network.startEditing()
    temp_network.addFeatures(New_feat_l)
    temp_network.commitChanges()

    #construct a normal graph from the merged netwrok
    G=nx.MultiGraph()
    for f in temp_network.getFeatures():
        f_geom=f.geometry()
        id=f.id()
        p0=f_geom.asPolyline()[0]
        p1=f_geom.asPolyline()[-1]
        G.add_edge(p0,p1,fid=id)

    #construct a dual graph with all connections
    Dual_G=nx.MultiGraph()
    for e in G.edges_iter(data='fid'):
        Dual_G.add_node(e[2])

    Dual_G_edges=[]
    for i,j in G.adjacency_iter():
        edges=[]
        if len(j)>1:
            for k,v in j.items():
                edges.append(v[0]['fid'])
            for elem in range(0,len(edges)+1):
                for subset in itertools.combinations(edges,elem):
                    if len(subset)==2:
                        Dual_G_edges.append(subset)

    for i in Dual_G_edges:
        Dual_G.add_edge(i[0],i[1],data=None)

    ids_short=[]
    for f in temp_network.getFeatures():
        l=f.geometry().length()
        id=f.id()
        if l<threshold_inter:
            ids_short.append(id)

    Short_G=Dual_G.subgraph(ids_short)

    Neighbours=[]
    all_new_points=[]
    lines_modified=[]
    for i in nx.connected_components(Short_G):
        comp=list(i)
        temp_network.removeSelection()
        temp_network.select(comp)
        short_endpoints=[]
        for f in temp_network.selectedFeatures():
            p0=f.geometry().asPolyline()[0]
            p_1=f.geometry().asPolyline()[-1]
            short_endpoints.append(p0)
            short_endpoints.append(p_1)
        x=[p[0] for p in short_endpoints]
        y=[p[1] for p in short_endpoints]
        new_point=(float(sum(x))/float(len(short_endpoints)),float(sum(y))/float(len(short_endpoints)))
        all_new_points.append(new_point)
        neighbours=[]
        for i in comp:
            for j in Dual_G.neighbors_iter(i):
                if j not in neighbours and j not in ids_short:
                    neighbours.append(j)
        for i in neighbours:
            Neighbours.append(i)
        neighbours_to_rem=[]
        for i in neighbours:
            if i<=feat_count_init:
                temp_network.removeSelection()
                temp_network.select(i)
                f=temp_network.selectedFeatures()[0]
                if f.geometry().asPolyline()[0] in short_endpoints and f.geometry().asPolyline()[-1] in short_endpoints:
                    neighbours_to_rem.append(i)
                elif f.geometry().asPolyline()[0] in short_endpoints and not f.geometry().asPolyline()[-1] in short_endpoints:
                    lines_modified.append(f.id())
                    if len(f.geometry().asPolyline())<=2:
                        point_index=0
                        vertices_to_keep =[new_point]+[f.geometry().asPolyline()[-1]]
                    else:
                        vertices_to_keep =[new_point]+[x for ind,x in enumerate(f.geometry().asPolyline()) if ind>=1]
                    new_pl=[]
                    for vertex in vertices_to_keep:
                        p=QgsPoint(vertex[0],vertex[1])
                        new_pl.append(p)
                    new_geom=QgsGeometry().fromPolyline(new_pl)
                    temp_network.startEditing()
                    temp_network.changeGeometry(f.id(),new_geom)
                    temp_network.commitChanges()
                elif f.geometry().asPolyline()[0] not in short_endpoints and f.geometry().asPolyline()[-1] in short_endpoints:
                    lines_modified.append(f.id())
                    if len(f.geometry().asPolyline())<=2:
                        point_index=len(f.geometry().asPolyline())-1
                        vertices_to_keep=[f.geometry().asPolyline()[0]]+[new_point]
                    else:
                        vertices_to_keep= [x for ind,x in enumerate(f.geometry().asPolyline()) if ind<=len(f.geometry().asPolyline())-2] +[new_point]
                    new_pl=[]
                    for vertex in vertices_to_keep:
                        p=QgsPoint(vertex[0],vertex[1])
                        new_pl.append(p)
                    new_geom=QgsGeometry().fromPolyline(new_pl)
                    temp_network.startEditing()
                    temp_network.changeGeometry(f.id(),new_geom)
                    temp_network.commitChanges()
                for l in neighbours_to_rem:
                    ids_short.append(l)

    ids_unique=[]
    for i in ids_short:
        if i not in ids_unique:
            ids_unique.append(i)

    temp_network.startEditing()
    temp_network.dataProvider().deleteFeatures(ids_unique)
    temp_network.commitChanges()

    name_points=None
    for i, j in QgsMapLayerRegistry.instance().mapLayers().items():
        if Points==j:
            name_points=i

    #QgsMapLayerRegistry.instance().removeMapLayer(name_points)

    return temp_network,all_new_points