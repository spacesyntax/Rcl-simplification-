

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
        self.edge_qflds = QgsFields()
        for field in self.edges[0].fields():
            self.edge_qflds.append(QgsField(field.name(), field.type()))
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

        self.superNodes = {}

        # create spatial index object
        self.spIndex = QgsSpatialIndex()

        for f in self.edges:

            #self.progress.emit(45 * f_count / self.road_layer_count)
            #f_count += 1

            attr = f.attributes()
            self.edge_attrs[f.id()] = dict(zip(self.edge_flds,attr))
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

            # TODO: decide if geometries and attributes and adj.lines can be stored here
            # a dictionary to match simplified nodes with the input network nodes
            # types: single, pseudonode, multinode, multiedge, bypassnode
            # transformation: raw (None), updated, disregarded, collapsed, inserted
            self.superNodes[f.id()] = {'node_type': 'single',
                                       'from': None, 'class': None, 'edit_type': None, 'adj_lines': {}}

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
                self.superNodes[x[0]]['adj_lines'][x[1]] = angle
                self.superNodes[x[1]]['adj_lines'][x[0]] = angle

    # TODO: some of the centroids are not correct
    def get_centroids_dict(self):
        return {edge: pl_midpoint(edge_geom) for edge, edge_geom in self.edge_qgeoms.items()}

    def make_selection(self, attr, value):
        return [f for f in self.edges if f[attr] == value]

    def make_neg_selection(self, attr, value):
        return [f for f in self.edges if f[attr] != value]

    def group_by_name(self, lines):
        groups = {}
        ungrouped = []
        for l in lines:
            if self.edge_attrs[l]['name1'] and not self.edge_attrs[l]['name1'].isspace():
                try:
                    groups[self.edge_attrs[l]['name1']] += [l]
                except KeyError, e:
                    groups[self.edge_attrs[l]['name1']] = [l]
            else:
                if self.edge_attrs[l]['roadnumber'] and not self.edge_attrs[l]['roadnumber'].isspace():
                    try:
                        groups[self.edge_attrs[l]['roadnumber']] += [l]
                    except KeyError, e:
                        groups[self.edge_attrs[l]['roadnumber']] = [l]
                else:
                    ungrouped += [l]
        if len(ungrouped) > 0:
            ungr = sGraph([f for f in self.edges if f.id() in ungrouped], self.source_col, self.target_col)
            ungr_comp = ungr.find_connected_comp_full()
            x = 1
            for i in ungr_comp:
                groups['ungrouped' + str(x)] = ungr.get_lines_from_nodes(i)
        return groups

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

    def simplify_dc(self):
        # TODO: after sub-graphing & before finding the con_comp add lines that both of their endpoints are on dc.nodes
        dc = self.subgraph('formofway', 'Dual Carriageway', negative=False)
        x = 1
        for comp in dc.find_connected_comp_full():
            groups_by_names = dc.group_by_name(dc.get_lines_from_nodes(comp))
            for name, group in groups_by_names.items():
                # TODO: filter from the other_con if a line connects to all lines in a group
                # TODO: if yes then line becomes a bypass node
                other_con = {}
                for line in group:
                    # get external connections
                    for con_line, cost in self.superNodes[line]['adj_lines'].items():
                        if con_line not in group:
                            other_con[con_line] = cost
                    # delete old group nodes
                    del self.superNodes[line]

                # insert new dual node
                self.superNodes['super'+str(x)] = {'node_type': 'multiedge', 'from': group, 'class': 'Dual Carriageway',
                                                   'edit_type': 'collapsed_edges_to_line', 'adj_lines': other_con}

                # update old - other to new other
                for line in other_con.keys():
                    old_nodes = [i for i in self.superNodes[line]['adj_lines'].keys() if i in group]
                    for node in old_nodes:
                        angle = self.superNodes[line]['adj_lines'][node]
                        del self.superNodes[line]['adj_lines'][node]
                        self.superNodes[line]['adj_lines']['super'+str(x)] = angle

                # counter
                x += 1

        return

    def simplify_rb(self):
        rb = self.subgraph('formofway', 'Roundabout', negative=False)
        x = 1
        for comp in rb.find_connected_comp_full():
            group = rb.get_lines_from_nodes(comp)
            other_con = {}
            for line in group:
                # get external connections
                for con_line, cost in self.superNodes[line]['adj_lines'].items():
                    if con_line not in group:
                        other_con[con_line] = cost
                        # delete old group nodes
                del self.superNodes[line]

            # insert new dual node
            self.superNodes['super' + str(x)] = {'node_type': 'multinode', 'from': group,
                                                 'class': 'Roundabout',
                                                 'edit_type': 'collapsed_edges_to_node', 'adj_lines': other_con}

            # update other - other
            # TODO: draw straight links between all other
            # delete old - other


    def simplify_sl(self):
        pass

    def to_primal_features(self):
        primal_features = []
        for dl_node, info in self.superNodes.items():
            if info['node_type'] == 'multiedge':
                group = info['from']
                geoms = [self.edge_geoms[line] for line in group]
                line_segms = []
                for line_wkt in geoms:
                    line = QgsGeometry.fromWkt(line_wkt)
                    # TODO: test if geom is valid in the new OS Open Road format
                    if line.wkbType() == 2:
                        line_segms.append([QgsPoint(i[0], i[1]) for i in line.asPolyline()])
                    elif line.wkbType() == 5:
                        for segm in line.asGeometryCollection():
                            line_segms.append([QgsPoint(i[0], i[1]) for i in segm.asPolyline()])
                ml_geom = QgsGeometry.fromMultiPolyline(line_segms)
                new_feat = QgsFeature()
                new_feat.setGeometry(ml_geom)
                # TODO: attributes should be array of original attributes
                # random selection of attributes
                new_feat.setAttributes(self.edge_attrs[group[0]].values())
                primal_features.append(new_feat)
            else:
                new_feat = QgsFeature()
                new_feat.setGeometry(QgsGeometry.fromWkt(self.edge_geoms[dl_node]))
                new_feat.setAttributes(self.edge_attrs[dl_node].values())
                primal_features.append(new_feat)
        return primal_features

    def to_dual_features(self):
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

    def to_shp(self, path, name, crs, encoding, geom_type, features):
        if path is None:
            network = QgsVectorLayer('LineString?crs=' + crs.toWkt(), name, "memory")
        else:
            file_writer = QgsVectorFileWriter(path, encoding, self.edge_qflds, geom_type,
                                              crs, "ESRI Shapefile")
            if file_writer.hasError() != QgsVectorFileWriter.NoError:
                print "Error when creating shapefile: ", file_writer.errorMessage()
            del file_writer
            network = QgsVectorLayer(path, name, "ogr")
        # QgsMapLayerRegistry.instance().addMapLayer(network)
        pr = network.dataProvider()
        network.startEditing()
        if path is None:
            pr.addAttributes(self.edge_qflds)
        pr.addFeatures(features)
        network.commitChanges()
        return network