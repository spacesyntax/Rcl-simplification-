# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RclSimplification
                                 A QGIS plugin
 This plugin simplifies a rcl map to segment map
                              -------------------
        begin                : 2016-06-20
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Ioanna Kolovou
        email                : ioanna.kolovou@gmail.com 
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from rcl_simplification_dialog import RclSimplificationDialog
import os.path
import graph_tools_1 as gt
import simplify_angle as sa
import simplify_intersections as si
from qgis.utils import *
from PyQt4.QtCore import QVariant, QFileInfo
from qgis.core import *

# Import the debug library
# set is_debug to False in release version
is_debug = False
try:
    import pydevd
    has_pydevd = False
except ImportError, e:
    has_pydevd = False
    is_debug = False


class RclSimplification:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'RclSimplification_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = RclSimplificationDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&RcL Simplification')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'RclSimplification')
        self.toolbar.setObjectName(u'RclSimplification')

        # Setup debugger
        if has_pydevd and is_debug:
            pydevd.settrace('localhost', port=53100, stdoutToServer=True, stderrToServer=True, suspend=True)


        # setup GUI signals
        self.dlg.run1.clicked.connect(self.simplifyAngle)
        self.dlg.run2.clicked.connect(self.simplifyInter)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('RclSimplification', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/RclSimplification/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Rcl simplification'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def getInput1(self):
        name = self.dlg.getNetwork1()
        layer = None
        for i in self.iface.legendInterface().layers():
            if i.name() == name:
                layer = i
        return layer

    def getInput2(self):
        name = self.dlg.getNetwork2()
        layer = None
        for i in self.iface.legendInterface().layers():
            if i.name() == name:
                layer = i
        return layer

    def getSimplifyAngleSettings(self):

        settings_angle = {}
        settings_angle['network'] = self.getInput1()
        # settings_angle['snapped'] = self.dlg.snapTickBox1.isChecked()
        settings_angle['decimal precision'] = self.dlg.getDecimals1()
        settings_angle['min seg length'] = self.dlg.getMinSegLen()
        settings_angle['min angle dev'] = self.dlg.getMinAngleDev()
        settings_angle['max angle dev'] = self.dlg.getMaxAngleDev()
        settings_angle['output1'] = self.dlg.getOutput1()

        return settings_angle

    def getSimplifyInterSettings(self):

        settings_inter= {}
        settings_inter['network'] = self.getInput2()
        # settings_angle['snapped'] = self.dlg.snapTickBox1.isChecked()
        settings_inter['decimal precision'] = self.dlg.getDecimals2()
        settings_inter['intersection distance'] = self.dlg.getInterDist()
        settings_inter['min length dev'] = self.dlg.getMinLenDev()
        settings_inter['max length dev'] = self.dlg.getMaxLenDev()
        settings_inter['output1'] = self.dlg.getOutput2()

        return settings_inter


    def simplifyAngle(self):

        settings_angle = self.getSimplifyAngleSettings()
        input1_uri = settings_angle['network'].dataProvider().dataSourceUri()
        input1_path = os.path.dirname(input1_uri) + "/" + QFileInfo(input1_uri).baseName() + ".shp"

        n_decimals = int(settings_angle['decimal precision'])
        graph = gt.read_shp_to_graph(input1_path)
        snapped = gt.snap_graph(graph, n_decimals)

        dual_t = gt.graph_to_dual(snapped, 'feat_id', inter_to_inter=True)
        sets = gt.merge_graph(dual_t)
        merged_network, mg, snapped_merged = gt.merge_geometries(sets, input1_path, n_decimals)

        inter_lines, f = gt.break_graph(snapped_merged, merged_network)
        broken_network, lines_ind_to_break, snapped_graph_broken = gt.break_geometries(inter_lines, merged_network, snapped_merged,n_decimals)

        sa.simplify_angle(broken_network, settings_angle['min angle dev'], settings_angle['min seg length'])

    def simplifyInter(self):
        settings_inter = self.getSimplifyInterSettings()
        input2_uri = settings_inter['network'].dataProvider().dataSourceUri()
        input2_path = os.path.dirname(input2_uri) + "/" + QFileInfo(input2_uri).baseName() + ".shp"

        n_decimals = int(settings_inter['decimal precision'])
        graph = gt.read_shp_to_graph(input2_path)
        snapped = gt.snap_graph(graph, n_decimals)

        dual_t = gt.graph_to_dual(snapped, 'feat_id', inter_to_inter=True)
        sets = gt.merge_graph(dual_t)
        merged_network, mg, snapped_merged = gt.merge_geometries(sets, input2_path, n_decimals)

        inter_lines, f = gt.break_graph(snapped_merged, merged_network)
        broken_network, lines_ind_to_break, snapped_graph_broken = gt.break_geometries(inter_lines, merged_network,
                                                                                       snapped_merged, n_decimals)

        shp_path = gt.write_shp(broken_network, input2_path)
        print shp_path

        broken_network = QgsVectorLayer(shp_path, "broken_network", "ogr")
        gt.update_feat_id_col(broken_network, 'feat_id_3', start=0)
        broken_network = QgsVectorLayer(shp_path, "broken_network", "ogr")

        QgsMapLayerRegistry.instance().addMapLayer(broken_network)

        graph = gt.read_shp_to_graph(shp_path)
        snapped_graph_broken = gt.snap_graph(graph, 6)
        l = si.get_nodes_coord(snapped_graph_broken)
        points, point_ids_coords = si.make_points_from_shp(shp_path, l)
        neighbors = si.find_closest_points(points)

        inter_distance_threshold = settings_inter['intersection distance']

        edge_list = si.find_not_connected_nodes(broken_network, snapped_graph_broken, neighbors, inter_distance_threshold,point_ids_coords)
        snapped_graph_broken.add_edges_from(edge_list)

        ids_short = si.find_short_edges(snapped_graph_broken, inter_distance_threshold)

        dual3 = gt.graph_to_dual(snapped_graph_broken, 'feat_id_3',inter_to_inter=False)  # short_edges_dual = dual3.subgraph(ids_short)
        short_edges_dual = dual3.subgraph(ids_short)
        short_lines_neighbours = si.find_connected_subgraphs(dual3, short_edges_dual)
        h = short_lines_neighbours
        short_lines_neighbours = {k: v for k, v in h.items() if len(v) != 0}

        d, m, c = si.simplify_intersection_geoms(shp_path, short_lines_neighbours,snapped_graph_broken)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&RcL Simplification'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def getActiveLayers(self):
        layers_list = []
        for layer in self.iface.legendInterface().layers():
            if layer.isValid() and (layer.wkbType() == 2 or layer.wkbType() == 5):
                layers_list.append(layer.name())
        self.dlg.inputCombo1.clear()
        self.dlg.inputCombo2.clear()
        self.dlg.inputCombo1.addItems(layers_list)
        self.dlg.inputCombo2.addItems(layers_list)


    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        self.getActiveLayers()

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass


