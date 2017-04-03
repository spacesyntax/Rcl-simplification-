

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
        self.edge_qflds = []
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
        self.node_attrs = {}

        self.superNodes = {}
        self.superEdges = {}

        # create spatial index object
        self.spIndex = QgsSpatialIndex()

        for f in self.edges:

            #self.progress.emit(45 * f_count / self.road_layer_count)
            #f_count += 1

            attr = f.attributes()
            attrs = dict(zip(self.edge_flds, attr))
            self.edge_attrs[f.id()] = attrs
            f_geom = f.geometry()
            vertices = [vertex for vertex in get_vertices(f_geom)]
            # TODO: some of the centroids are not correct
            self.edge_geoms[f.id()] = {'wkt': f_geom.exportToWkt(),
                                       'source': f[self.source_col],
                                       'target': f[self.target_col],
                                       'vertices': vertices,
                                       'centroid': pl_midpoint(f_geom),
                                       'angular change': pl_angle(f_geom),
                                       'ends': [vertices[0], vertices[1]]}

            self.node_attrs[f[self.source_col]] = vertices[0]
            self.node_attrs[f[self.target_col]] = vertices[-1]

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
            self.superNodes[f.id()] = {'type': 'node',
                                       'ancestors': [f.id()],
                                       'class': 'input',
                                       'wkt': f_geom.exportToWkt(),
                                       'centroid': pl_midpoint(f_geom),
                                       'attrs': attrs}

        self.nodes = list(set(self.nodes))

        # self loops are not included
        # orphans are not included
        for node, edges in self.adj_lines.items():

            #self.progress.emit(10 * f_count / feat_count)
            #f_count += 1

            for x in itertools.combinations(edges, 2):
                # TODO: parallel edges and self loops are connected at a random angle
                ends1 = self.edge_geoms[x[0]]['ends']
                ends2 = self.edge_geoms[x[0]]['ends']
                inter_point = [p for p in ends1 if p in ends2][0]
                vertex1 = self.edge_geoms[x[0]]['vertices'][-2]
                if inter_point == self.edge_geoms[x[0]]['vertices'][0]:
                    vertex1 = self.edge_geoms[x[0]]['vertices'][1]
                vertex2 = self.edge_geoms[x[1]]['vertices'][-2]
                if inter_point == self.edge_geoms[x[1]]['vertices'][0]:
                        vertex2 = self.edge_geoms[x[1]]['vertices'][1]
                angle = int(angle_3_points(inter_point, vertex1, vertex2))
                self.superEdges[(x[0], x[1])] = 180 - angle

        self.dual_edges = self.superEdges

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
        #if len(ungrouped) > 0:
        #    ungr = sGraph([f for f in self.edges if f.id() in ungrouped], self.source_col, self.target_col)
        #    ungr_comp = ungr.find_connected_comp_full()
        #    x = 1
        #    for i in ungr_comp:
        #        groups['ungrouped' + str(x)] = ungr.get_lines_from_nodes(i)
        return groups, ungrouped

    def subgraph(self, attr, value, negative=False):
        if negative:
            filtered_edges = self.make_neg_selection(attr, value)
        else:
            filtered_edges = self.make_selection(attr, value)
        return sGraph(filtered_edges, self.source_col, self.target_col)

    def subgraph2(self, nodes):
        filtered_edges = []
        set_nodes = set(nodes)
        for f in self.edges:
            ends = {f[self.source_col], f[self.target_col]}
            if len(ends.intersection(set_nodes)) == 2:
                filtered_edges.append(f)
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

    # only lines that both of their endpoints are incl. in nodes
    def get_lines_from_nodes2(self, nodes):
        lines = []
        for i in nodes:
            lines.append(self.adj_lines[i])
        lines = list(itertools.chain.from_iterable(lines))
        lines = list(set(lines))
        internal_lines = []
        external_lines = []
        for l in lines:
            b1 = False
            b2 = False
            if self.edge_geoms[l]['source'] in nodes:
                b1 = True
            if self.edge_geoms[l]['target'] in nodes:
                b2 = True
            if b1 and b2:
                internal_lines.append(l)
            else:
                external_lines.append(l)
        return internal_lines, external_lines

    def get_nodes_from_lines(self, lines):
        nodes = []
        for l in lines:
            nodes.append(self.edge_attrs[l][self.source_col])
            nodes.append(self.edge_attrs[l][self.target_col])
        return list(set(nodes))

    def simplify_dc(self):

        # subgraph from main where formofway = Dual Carriageway
        dc_w_o_bypass = self.subgraph('formofway', 'Dual Carriageway', negative=False)
        dc_nodes = dc_w_o_bypass.nodes
        # include bypass nodes (= nodes that both of their ends are connected to the dual carriageway component)
        dc = self.subgraph2(dc_nodes)

        # counter
        count = 1

        self.dl_nds_collapsed = {}

        for comp in dc.find_connected_comp_full():
            # TODO instead of bypass nodes add function to close a linestring. (e.g. Park Lane)

            dc_dl_nodes = dc.get_lines_from_nodes(comp)
            groups_by_names, ungrouped = self.group_by_name(dc_dl_nodes)

            for name, group_dl_nds in groups_by_names.items():
                if len(group_dl_nds) > 1:

                    # TODO: remove from group_dl_nds if not Dual Carriageway or if not both endpoints in dc nodes (only)
                    # the groups_by_names include non dual carriageways
                    # get dc pr nds
                    # get linesfromnodes2

                    group_pr_nds = self.get_nodes_from_lines(group_dl_nds)
                    # this includes bypass nodes
                    group_dl_nds, con_dl_nds = self.get_lines_from_nodes2(group_pr_nds)
                    group_pr_nds = self.get_nodes_from_lines(group_dl_nds)

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
                    for i in group_dl_nds:
                        # node might have already been deleted (e.g. bypass node)
                        try:
                            del self.superNodes[i]
                        except KeyError, e:
                            continue

                    # TODO: attributes will be supported as arrays/ linestring of original attributes
                    wkt = self.merge_geoms(group_dl_nds)
                    geom = QgsGeometry.fromWkt(wkt)
                    attrs = [self.edge_attrs[i] for i in group_dl_nds]
                    self.superNodes['s_' + str(count)] = {
                                                          'type': 'multiedge',
                                                          'class': 'Dual Carriageway',
                                                          'ancestors': group_dl_nds,
                                                          'wkt': wkt,
                                                          'centroid': geom.centroid().asPoint(),
                                                          'attrs':  self.merge_attrs(attrs)
                                                          }

                    # collapsed nodes
                    for i in group_dl_nds:
                        self.dl_nds_collapsed[i] = 's_' + str(count)

                    # add topological dual graph edges
                    for (dl_nd_1, dl_nd_2) in new_dl_edges:

                        dl_nd_1_end = self.edge_geoms[dl_nd_1]['source']
                        dl_nd_1_bef_end = 1
                        if dl_nd_1_end not in group_pr_nds:
                            dl_nd_1_end = self.edge_geoms[dl_nd_1]['target']
                            dl_nd_1_bef_end = len(self.edge_geoms[dl_nd_1]['vertices']) - 1
                        dl_nd_2_end = self.edge_geoms[dl_nd_2]['source']
                        dl_nd_2_bef_end = 1
                        if dl_nd_2_end not in group_pr_nds:
                            dl_nd_2_end = self.edge_geoms[dl_nd_2]['target']
                            dl_nd_2_bef_end = len(self.edge_geoms[dl_nd_2]['vertices']) - 1


                        angle1 = angle_3_points(self.node_attrs[dl_nd_1_end], self.edge_geoms[dl_nd_1]['vertices'][dl_nd_1_bef_end], self.node_attrs[dl_nd_2_end])
                        angle2 = angle_3_points(self.node_attrs[dl_nd_2_end], self.edge_geoms[dl_nd_2]['vertices'][dl_nd_2_bef_end], self.node_attrs[dl_nd_1_end])

                        # check if edge in dl edges has been collapsed
                        try:
                            dl_nd_1 = self.dl_nds_collapsed[dl_nd_1]
                        except KeyError, e:
                            pass

                        try:
                            dl_nd_2 = self.dl_nds_collapsed[dl_nd_2]
                        except KeyError, e:
                            pass
                        # TODO: check angles
                        self.superEdges[(dl_nd_1, 's_' + str(count))] = 180 - angle1
                        self.superEdges[('s_' + str(count), dl_nd_2)] = 180 - angle2

                    # counter
                    count += 1

        # del all dual graph edges that include the group_dl_nds in the end so that you loop through once
        dl_edges_to_del = []
        for dl_edge, cost in self.dual_edges.items():
            b1 = False
            try:
                dummy = self.dl_nds_collapsed[dl_edge[0]]
                b1 = True
            except KeyError, e:
                pass
            b2 = False
            try:
                dummy = self.dl_nds_collapsed[dl_edge[1]]
                b2 = True
            except KeyError, e:
                pass
            if b1 or b2:
                dl_edges_to_del.append(dl_edge)

        for i in dl_edges_to_del:
            del self.superEdges[i]

        return

    def simplify_rb(self):
        pass

    def simplify_sl(self):
        pass

    def merge_geoms(self, group):
        geoms = [self.edge_geoms[line]['wkt'] for line in group]
        line_segms = []
        for line_wkt in geoms:
            line = QgsGeometry.fromWkt(line_wkt)
            if line.wkbType() == 2:
                line_segms.append([QgsPoint(i[0], i[1]) for i in line.asPolyline()])
            elif line.wkbType() == 5:
                for segm in line.asGeometryCollection():
                    line_segms.append([QgsPoint(i[0], i[1]) for i in segm.asPolyline()])
        ml_geom = QgsGeometry.fromMultiPolyline(line_segms)
        return ml_geom.exportToWkt()

    def merge_attrs(self, attrs):
        flds = attrs[0].keys()
        mrg_attrs = {i: [] for i in flds}
        for attr in attrs:
            for k, v in attr.items():
                mrg_attrs[k].append(v)
        return mrg_attrs

    def to_primal_features(self):
        primal_features = []
        for dl_node, info in self.superNodes.items():
            new_feat = QgsFeature()
            new_feat.setGeometry(QgsGeometry.fromWkt(info['wkt']))
            # random selection of attributes
            new_feat.setAttributes(info['attrs'].values())
            primal_features.append(new_feat)
            primal_features.append(new_feat)
        return primal_features

    def to_dual_features(self):
        dual_features = []
        for edge, cost in self.superEdges.items():
            centroid1 = self.superNodes[edge[0]]['centroid']
            centroid2 = self.superNodes[edge[1]]['centroid']
            geom = QgsGeometry.fromPolyline([QgsPoint(centroid1[0], centroid1[1]), QgsPoint(centroid2[0],centroid2[1])])
            attrs = [str(edge[0]), str(edge[1]), cost]
            new_feat = QgsFeature()
            new_feat.setGeometry(geom)
            new_feat.setAttributes(attrs)
            dual_features.append(new_feat)
        return dual_features

    def createDbSublayer(self, dbname, user, host, port, password, schema, table_name, features):
        connstring = "dbname=%s user=%s host=%s port=%s password=%s" % (dbname, user, host, port, password)

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

    def to_shp(self, path, name, crs, encoding, geom_type, features, graph='primal'):
        if graph == 'primal':
            flds = self.edge_qflds
        elif graph == 'dual':
            flds = [QgsField('source', QVariant.String), QgsField('target', QVariant.String),
                           QgsField('cost', QVariant.Int)]
        if path is None:
            network = QgsVectorLayer('MultiLineString?crs=' + crs.toWkt(), name, "memory")
        else:
            file_writer = QgsVectorFileWriter(path, encoding, flds, geom_type,
                                              crs, "ESRI Shapefile")
            if file_writer.hasError() != QgsVectorFileWriter.NoError:
                print "Error when creating shapefile: ", file_writer.errorMessage()
            del file_writer
            network = QgsVectorLayer(path, name, "ogr")
        # QgsMapLayerRegistry.instance().addMapLayer(network)
        pr = network.dataProvider()
        network.startEditing()
        if path is None:
            pr.addAttributes(flds)
        pr.addFeatures(features)
        network.commitChanges()
        return network