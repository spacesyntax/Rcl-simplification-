

# general imports
import itertools
from objc._objc import NULL
from qgis.core import QgsFeature, QgsGeometry, QgsSpatialIndex, QgsPoint, QgsVectorFileWriter, QgsField
from PyQt4.QtCore import QObject, pyqtSignal, QVariant
import psycopg2

#from sGraph.utilityFunctions import *

class sGraph(QObject):

    finished = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)
    progress = pyqtSignal(float)
    warning = pyqtSignal(str)

    def __init__(self, road_layer, road_node_layer):
        QObject.__init__(self)
        self.road_layer = road_layer
        self.road_layer_name = self.road_layer.name()
        self.road_node_layer = road_node_layer

        self.topology = {}
        self.adj_lines = {}
        self.node_attr = {f['identifier']: f['formofnode'] for f in self.road_node_layer.getFeatures()}
        self.features = []
        self.attributes = {}
        self.geometries = {}

        # get fields and feature count
        self.road_layer_fields = [QgsField(i.name(), i.type()) for i in self.road_layer.dataProvider().fields()]
        self.road_node_layer_fields = [QgsField(i.name(), i.type()) for i in self.road_node_layer.dataProvider().fields()]
        self.road_layer_count = self.road_layer.featureCount()
        self.road_node_layer_count = self.road_node_layer.featureCount()
        # create spatial index object
        self.spIndex = QgsSpatialIndex()

        for f in self.road_layer.getFeatures():

            #self.progress.emit(45 * f_count / self.road_layer_count)
            #f_count += 1

            attr = f.attributes()
            self.features.append(f)
            self.attributes[f.id()] = attr
            #self.geometries[f.id()] = f.geometryAndOwnership()
            self.geometries[f.id()] = f.geometry().exportToWkt()

            # insert features to index
            self.spIndex.insertFeature(f)

            # create topology & adjacent lines dictionary
            startnode = f['startnode']
            endnode = f['endnode']
            try:
                self.topology[startnode] += [endnode]
            except KeyError, e:
                self.topology[startnode] = [endnode]
            try:
                self.topology[endnode] += [startnode]
            except KeyError, e:
                self.topology[endnode] = [startnode]
            try:
                self.adj_lines[startnode] += [f.id()]
            except KeyError, e:
                self.adj_lines[startnode] = [f.id()]
            try:
                self.adj_lines[endnode] += [f.id()]
            except KeyError, e:
                self.adj_lines[endnode] = [f.id()]

    def make_selection(self, attr, value):
        return [f for f in self.features if f[attr] == value]

    def group_by_name(self, lines):
        groups = {'ungrouped': []}
        for l in lines:
            if self.attributes[l][5] and not self.attributes[l][5].isspace():
                try:
                    groups[self.attributes[l][5]] += [l]
                except KeyError, e:
                    groups[self.attributes[l][5]] = [l]
            else:
                if self.attributes[l][4] and not self.attributes[l][4].isspace():
                    try:
                        groups[self.attributes[l][4]] += [l]
                    except KeyError, e:
                        groups[self.attributes[l][4]] = [l]
                else:
                    groups['ungrouped'] += [l]
        return groups

    def subgraph(self, features):
        self.subtopology = {}
        self.subadj_lines = {}
        # create topology & adjacent lines dictionary
        for f in features:
            startnode = f['startnode']
            endnode = f['endnode']
            try:
                self.subtopology[startnode] += [endnode]
            except KeyError, e:
                self.subtopology[startnode] = [endnode]
            try:
                self.subtopology[endnode] += [startnode]
            except KeyError, e:
                self.subtopology[endnode] = [startnode]
            try:
                self.subadj_lines[startnode] += [f.id()]
            except KeyError, e:
                self.subadj_lines[startnode] = [f.id()]
            try:
                self.subadj_lines[endnode] += [f.id()]
            except KeyError, e:
                self.subadj_lines[endnode] = [f.id()]
        return

    def get_next_vertex(self, tree):
        last = tree[-1]
        return tree + [i for i in self.subtopology[last] if i not in tree]

    def get_next_vertices(self,tree):
        last = tree[-1]
        subtree = []
        tree_flatten = list(itertools.chain.from_iterable(tree))
        for node in last:
            subtree += [i for i in self.subtopology[node] if i not in tree_flatten]
        tree.append(subtree)
        return tree

    def find_connected_comp(self, subgraph=True):
        ndegree_1 = list(set([n for n,neigh_n in self.subtopology.items() if len(neigh_n) == 1]))
        ndegree_1_passed = []
        connected_comp = []
        for n in ndegree_1:
            if n not in ndegree_1_passed:
                tree = [[n]]
                n_iter = 0
                ndegree_1_passed.append(n)
                while n_iter < 100:
                    last = tree[-1]
                    n_iter += 1
                    tree = self.get_next_vertices(tree)
                    if tree[-1] == []:
                        n_iter = 0
                        tree.remove([])
                        # print "hit end"
                        ndegree_1_passed += [x for x in tree[-1]]
                        break
                tree_flat = list(itertools.chain.from_iterable(tree))
                connected_comp.append(tree_flat)
        return connected_comp

    def get_lines_from_nodes(self,nodes):
        lines = []
        for i in nodes:
            lines.append(self.subadj_lines[i])
        lines = list(itertools.chain.from_iterable(lines))
        return list(set(lines))

    def createDbSublayer(self, dbname, user, host, port, password, schema, table_name, features):
        connstring = "dbname=%s user=%s host=%s port=%s password=%s" %(dbname, user, host, port, password)

        try:
            con = psycopg2.connect(connstring)
            cur = con.cursor()
            query = "DROP TABLE IF EXISTS %s.%s; CREATE TABLE %s.%s( id serial, identifier text, class text, roadnumber text, street_name text, startnode text, endnode text, geom geometry(LineString, 27700), CONSTRAINT %s PRIMARY KEY(id)); ALTER TABLE %s.%s OWNER TO postgres; " % (schema, table_name, schema, table_name, table_name +'_pk', schema, table_name)
            cur.execute(query)
            con.commit()
            for f in features:
                wkt = f.geometry().exportToWkt()
                # TODO: fix NULL values
                # TODO: fix schema, table_name w-o single quotes
                query = "INSERT INTO simpl.dual_carriageways (identifier, class, roadnumber, street_name, startnode, endnode, geom) VALUES(%s, %s, %s, %s, %s, %s, ST_GeomFromText(%s,27700));"
                cur.execute(query, (f['identifier'], replace_null_w_none(f['class']), None, None, f['startnode'], f['endnode'], wkt))
                                    # schema, table_name,
                                    #f['identifier'], replace_null_w_none(f['class']), replace_null_w_none(f['roadnumber']), replace_null_w_none(f['name1']), f['startnode'], f['endnode'], wkt))
                con.commit()
            con.close()
        except psycopg2.DatabaseError, e:
            print 'Error %s' % e