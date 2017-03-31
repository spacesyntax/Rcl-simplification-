

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
        # TODO: do not duplicate key if it is already in attributes e.g. 'identifier'

        self.nodes = []
        self.edge_attrs = {}
        self.edge_geoms = {}
        self.edge_qgeoms = {}
        # angular change of polyline
        self.edge_totAngle = {}

        self.superNodes = {}
        self.superEdges = {}

        # create spatial index object
        self.spIndex = QgsSpatialIndex()

        for f in self.edges:

            #self.progress.emit(45 * f_count / self.road_layer_count)
            #f_count += 1

            attr = f.attributes()
            self.edge_attrs[f.id()] = dict(zip(self.edge_flds,attr))
            self.edge_qgeoms[f.id()] = f.geometryAndOwnership()
            self.edge_geoms[f.id()] = f.geometry().exportToWkt()
            self.edge_totAngle[f.id()] = pl_angle(f.geometry())
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

            # types: node, pseudonode, multinode, multiedge, bypassnode
            self.superNodes[f.id()] = {'type': 'node', 'ancestors': [f.id()], 'class': None}

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
                angle = int(angle_3_points(inter_point, vertex1, vertex2))
                self.superEdges[(x[0], x[1])] = 180 - angle

        self.dual_edges = self.superEdges

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

    def get_nodes_from_lines(self, lines):
        nodes = []
        for l in lines:
            nodes.append(self.edge_attrs[l][self.source_col])
            nodes.append(self.edge_attrs[l][self.target_col])
        return list(set(nodes))

    def simplify_dc(self, roadnodes):
        # subgraph from main where formofway = Dual Carriageway
        dc = self.subgraph('formofway', 'Dual Carriageway', negative=False)

        # counter
        count = 1

        for comp in dc.find_connected_comp_full():
            # add bypass nodes (= nodes that both of their ends are connected to the dual carriageway component)
            # TODO instead of bypass nodes add function to close a linestring. (e.g. Park Lane)
            dc_dl_nodes = dc.get_lines_from_nodes(comp)
            groups_by_names = self.group_by_name(dc_dl_nodes)
            for name, group_dl_nds in groups_by_names.items():

                group_pr_nds = self.get_nodes_from_lines(group_dl_nds)

                bypass_dl_nds = [f.id() for f in self.edges if f[self.source_col] in group_pr_nds
                                 and f[self.target_col] in group_pr_nds
                                 and f.id() not in group_dl_nds]

                all_pr_nds = self.get_nodes_from_lines(group_dl_nds + bypass_dl_nds)

                con_dl_nds = []
                for node in all_pr_nds:
                    # get external connections
                    con = self.adj_lines[node]
                    con_dl_nds += [line for line in con if line not in group_dl_nds + bypass_dl_nds]

                new_dl_edges = [x for x in itertools.combinations(con_dl_nds, 2)]
                # exclude if two edges are already connected (this can be where linestring not closed)
                excl_dl_edges = []
                for new_edge in new_dl_edges:
                    cost = self.dual_edges.get(new_edge, None)
                    cost_rev = self.dual_edges.get((new_edge[1], new_edge[0]), None)
                    if not(cost is None and cost_rev is None):
                        excl_dl_edges.append(new_edge)
                for edge in excl_dl_edges:
                    new_dl_edges.remove(edge)

                # delete old nodes and insert new dual **multi-edge** node
                for i in group_dl_nds + bypass_dl_nds:
                    # node might have already been deleted (eg bypass node)
                    try:
                        del self.superNodes[i]
                    except KeyError, e:
                        continue
                self.superNodes['s_' + str(count)] = {'type': 'multiedge', 'class': 'Dual Carriageway', 'ancestors': group_dl_nds + bypass_dl_nds}
                # TODO: add topological dual graph edges
                for edge in new_dl_edges:
                    dl_nd_1 = edge[0]
                    dl_nd_2 = edge[1]
                    dl_nd_1_end = self.edge_attrs[dl_nd_1][self.source_col]
                    if dl_nd_1_end not in all_pr_nds:
                        dl_nd_1_end = self.edge_attrs[dl_nd_1][self.target_col]
                    dl_nd_2_end = self.edge_attrs[dl_nd_2][self.source_col]
                    if dl_nd_2_end not in all_pr_nds:
                        dl_nd_2_end = self.edge_attrs[dl_nd_2][self.target_col]
                    dl_nd_1_end_idx = (QgsGeometry.fromWkt(self.edge_geoms[dl_nd_1]).asPolyline()).index(roadnodes[dl_nd_1_end].asPoint())
                    dl_nd_2_end_idx = (QgsGeometry.fromWkt(self.edge_geoms[dl_nd_2]).asPolyline()).index(roadnodes[dl_nd_2_end].asPoint())

                    dl_nd_1_bef_end = 1
                    if dl_nd_1_end_idx != 0:
                        dl_nd_1_bef_end = dl_nd_1_end_idx - 1

                    dl_nd_2_bef_end = 1
                    if dl_nd_2_end_idx != 0:
                        dl_nd_2_bef_end = dl_nd_2_end_idx - 1

                    angle1 = angle_3_points(roadnodes[dl_nd_1_end], (QgsGeometry.fromWkt(self.edge_geoms[dl_nd_1])).asPolyline()[dl_nd_1_bef_end], roadnodes[dl_nd_2_end].asPoint())
                    angle2 = angle_3_points(roadnodes[dl_nd_2_end], (QgsGeometry.fromWkt(self.edge_geoms[dl_nd_2])).asPolyline()[dl_nd_2_bef_end], roadnodes[dl_nd_1_end].asPoint())
                    self.superEdges[(dl_nd_1, 's_' + str(count))] = 180 - angle1
                    self.superEdges[('s_' + str(count), dl_nd_2)] = 180 - angle2

                # counter
                count += 1


        # TODO: del all dual graph edges that include the group_dl_nds, bypass_dl_nds
        # this it is best to be done in the end so that you loop through once
        all_collapsed_dl_nds = [node for node, info in self.superNodes.items() if info['type'] == 'multiedge']
        dl_edges_to_del = [dl_edge for dl_edge, cost in self.dual_edges.items() if dl_edge[0] in all_collapsed_dl_nds or dl_edge[1] in all_collapsed_dl_nds]

        for i in dl_edges_to_del:
            del self.superEdges[i]

        return

    def simplify_rb(self):
        rb = self.subgraph('formofway', 'Roundabout', negative=False)
        x = 1
        for comp in rb.find_connected_comp_full():
            group = rb.get_lines_from_nodes(comp)
            con_nodes = {}
            for line in group:
                # get external connections
                for con_line, cost in self.superNodes[line]['adj_lines'].items():
                    if con_line not in group:
                        con_nodes[con_line] = cost
                        # delete old group nodes
                del self.superNodes[line]

            # insert new dual node
            self.superNodes['super' + str(x)] = {'node_type': 'multinode', 'from': group,
                                                 'class': 'Roundabout',
                                                 'edit_type': 'collapsed_edges_to_node', 'adj_lines': con_nodes}

            # update other - other
            # TODO: draw straight links between all other
            # delete old - other


    def simplify_sl(self):
        pass

    def to_primal_features(self):
        primal_features = []
        for dl_node, info in self.superNodes.items():
            if info['type'] == 'multiedge':
                group = info['ancestors']
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