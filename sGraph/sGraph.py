

# general imports
import itertools
from qgis.core import QgsFeature, QgsGeometry, QgsSpatialIndex, QgsPoint, QgsVectorFileWriter, QgsField
from PyQt4.QtCore import QObject, pyqtSignal, QVariant
import psycopg2

#from sGraph.utilityFunctions import *

class sGraph(QObject):

    finished = pyqtSignal(object)
    error = pyqtSignal(Exception, basestring)
    progress = pyqtSignal(float)
    warning = pyqtSignal(str)

    # TODO: check if nodes need to be added (nodes, node_key)
    # self.nodes = nodes
    # self.node_key = node_key
    # self.n_nodes = len(self.nodes)
    # self.node_flds = [i.name() for i in self.nodes[0]]
    # self.node_attrs = {f[node_key]: f.attributes() for f in self.nodes}

    def __init__(self, edges, source_col='default', target_col='default'):
        QObject.__init__(self)
        self.edges = edges
        self.edge_flds = [i.name() for i in self.edges[0].fields()]
        self.n_edges = len(self.edges)
        self.source_col = source_col
        self.target_col = target_col

        self.topology = {}
        self.adj_lines = {}
        self.dual_edges = {}
        # TODO: do not duplicate key if it already in attributes e.g. 'identifier'

        self.nodes = []
        self.edge_attrs = {}
        self.edge_geoms = {}
        self.edge_qgeoms = {}

        # a dictionary to match simplified nodes with the input network nodes
        # types: single, pseudonode, multinode, multiedge, bypassnode
        # transformation: raw (None), updated, disregarded, collapsed, inserted
        self.superNodes = {}

        # create spatial index object
        self.spIndex = QgsSpatialIndex()

        for f in self.edges:

            #self.progress.emit(45 * f_count / self.road_layer_count)
            #f_count += 1

            attr = f.attributes()
            self.edge_attrs[f.id()] = attr
            self.edge_qgeoms[f.id()] = f.geometryAndOwnership()
            self.edge_geoms[f.id()] = f.geometry().exportToWkt()

            # insert features to index
            self.spIndex.insertFeature(f)

            # create topology & adjacent lines dictionary
            if self.source_col == 'default':
                startnode = f.geometry().asPolyline()[0]
            else:
                startnode = f[self.source_col]
            if self.target_col == 'default':
                endnode = f.geometry().asPolyline()[-1]
            else:
                endnode = f[self.target_col]

            try:
                self.topology[startnode] += [endnode]
            except KeyError, e:
                self.topology[startnode] = [endnode]
            try:
                self.topology[endnode] += [startnode]
            except KeyError, e:
                self.topology[endnode] = [startnode]
            self.nodes.append(startnode)
            self.nodes.append(endnode)
            try:
                self.adj_lines[startnode] += [f.id()]
            except KeyError, e:
                self.adj_lines[startnode] = [f.id()]
            try:
                self.adj_lines[endnode] += [f.id()]
            except KeyError, e:
                self.adj_lines[endnode] = [f.id()]

        self.nodes = list(set(self.nodes))

        # self loops are not included
        # orphans are not included
        for node, edges in self.adj_lines.items():

            #self.progress.emit(10 * f_count / feat_count)
            #f_count += 1

            for x in itertools.combinations(edges, 2):
                inter_point = self.edge_qgeoms[x[0]].intersection(self.edge_qgeoms[x[1]])
                vertex1 = self.edge_qgeoms[x[0]].asPolyline()[-2]
                if inter_point.asPoint() == self.edge_qgeoms[x[0]].asPolyline()[0]:
                    vertex1 = self.edge_qgeoms[x[0]].asPolyline()[1]
                vertex2 = self.edge_qgeoms[x[1]].asPolyline()[-2]
                if inter_point.asPoint() == self.edge_qgeoms[x[1]].asPolyline()[0]:
                        vertex2 = self.edge_qgeoms[x[1]].asPolyline()[1]
                angle = angle_3_points(inter_point, vertex1, vertex2)
                try:
                    self.dual_edges[x[0]][x[1]] = angle
                except KeyError, e:
                    self.dual_edges[x[0]] = {x[1]: angle}
                try:
                    self.dual_edges[x[1]][x[0]] = angle
                except KeyError, e:
                    self.dual_edges[x[1]] = {x[0]: angle}


    def collapse_to_edge(self, groups):
        x = 1
        self.collapsed_dual_nodes = {type:'to_node'/'to_edge', }
        for i in groups:
            new_edge = 'dual' + str(x)
            geom_collection = []



            x += 1

    def collapse_to_node(self, groups):
        x = 1
        self.collapsed_dual_nodes = {type:'to_node'/'to_edge'}
        for i in groups:
            new_edge = 'dual' + str(x)
            geom_collection = []

            x += 1

    def insert_dual_edge(self, edge, angle):
        try:
            self.dual_edges[edge[0]][edge[1]] = angle
        except KeyError, e:
            self.dual_edges[edge[0]] = {edge[1]: angle}
        return

    def delete_dual_edge(self, edge):
        del self.dual_edges[edge[0]]
        self.updated_dual_edges
        pass

    def update_dual_edge(self):
        # remove item from dictionary
        self.delete_dual_edge()
        self.insert_dual_edge()
        pass

    def delete_dual_node(self):
        pass

    def make_selection(self, attr, value):
        return [f for f in self.edges if f[attr] == value]

    def make_neg_selection(self, attr, value):
        return [f for f in self.edges if f[attr] != value]

    def group_by_name(self, lines):
        groups = {}
        ungrouped = []
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
                    ungrouped += [l]
        return groups, ungrouped

    def subgraph(self, attr, value, negative=False):
        if negative:
            filtered_edges = self.make_neg_selection(attr, value)
        else:
            filtered_edges = self.make_selection(attr, value)
        return sGraph(filtered_edges, self.source_col, self.target_col)

    def get_next_vertex(self, tree):
        last = tree[-1]
        return tree + [i for i in self.topology[last] if i not in tree]

    def get_next_vertices(self,tree):
        last = tree[-1]
        subtree = []
        tree_flatten = list(itertools.chain.from_iterable(tree))
        for node in last:
            subtree += [i for i in self.topology[node] if i not in tree_flatten]
        tree.append(subtree)
        return tree

    def find_connected_comp_full(self):
        # using degree 1 nodes does not get all connected components
        # ndegree_1 = list(set([n for n,neigh_n in self.topology.items() if len(neigh_n) == 1]))
        # ndegree_1_passed = []
        nodes_passed = []
        connected_comp = []
        for n in self.nodes:
            if n not in nodes_passed:
                tree = [[n]]
                n_iter = 0
                nodes_passed.append(n)
                while n_iter < 100:
                    last = tree[-1]
                    n_iter += 1
                    tree = self.get_next_vertices(tree)
                    if last == []:
                        n_iter = 0
                        tree.remove([])
                        # print "hit end"
                        break
                    else:
                        nodes_passed += [x for x in tree[-1]]
                tree_flat = list(itertools.chain.from_iterable(tree))
                connected_comp.append(tree_flat)
        return connected_comp

    def get_lines_from_nodes(self, nodes):
        lines = []
        for i in nodes:
            lines.append(self.adj_lines[i])
        lines = list(itertools.chain.from_iterable(lines))
        return list(set(lines))

    def get_internal_conn(self,lines):
        pass

    def get_external_conn(self,lines):
        pass


    def simplify_dc(self):
        dc = self.subgraph('formofway', 'Dual Carriageway', negative=False)
        for comp in dc.find_connected_comp_full():
            groups_by_names, ungrouped = self.group_by_name(self.get_lines_from_nodes(comp))
            for name, group in groups_by_names.items():
                self.superNodes[group] = {'class': 'dual carriageway', 'from': group, 'type': 'multiedge'}

                self.superEdges
                # change dual graph
                # delete old nodes
                # delete old edges connections
                # insert new dual node
                # update old - other to new other


                pass


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