# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RclSimplification
                                 A QGIS plugin
 This plugin simplifies a rcl map to segment map
                              -------------------
        begin                : 2016-06-20
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Space Syntax Limited, Ioanna Kolovou
        email                : I.Kolovou@spacesyntax.com
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
import os

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'rcl_simplification_dialog_base.ui'))


class RclSimplificationDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(RclSimplificationDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # GUI signals
        self.outputText1.setPlaceholderText("Save as temporary layer...")
        self.outputText2.setPlaceholderText("Save as temporary layer...")
        self.browseOutput1.clicked.connect(self.setOutput1)
        self.browseOutput2.clicked.connect(self.setOutput2)
        # self.cancelButton.clicked.connect(self.closeDialog)

        # Setups
        #self.progressBar1.setMinimum(0)
        #self.progressBar1.setMaximum(100)
        #self.progressBar2.setMinimum(0)
        #self.progressBar2.setMaximum(100)
        self.decimalsSpin1.setDecimals(0)
        self.decimalsSpin1.setRange(1,20)
        self.decimalsSpin1.setSingleStep(1)
        self.decimalsSpin1.setValue(6)
        self.decimalsSpin1.setSuffix(' decimals')
        self.decimalsSpin2.setDecimals(0)
        self.decimalsSpin2.setRange(1, 20)
        self.decimalsSpin2.setSingleStep(1)
        self.decimalsSpin2.setValue(6)
        self.decimalsSpin2.setSuffix(' decimals')
        self.minSegLenSpin.setDecimals(4)
        self.minSegLenSpin.setRange(0, 20)
        self.minSegLenSpin.setSingleStep(0.0001)
        self.minSegLenSpin.setValue(0)
        self.minAngleDevSpin.setDecimals(0)
        self.minAngleDevSpin.setRange(0, 10)
        self.minAngleDevSpin.setSingleStep(1)
        self.minAngleDevSpin.setValue(5)
        self.minAngleDevSpin.setSuffix(unichr(176))
        self.maxAngleDevSpin.setDecimals(0)
        self.maxAngleDevSpin.setRange(0, 10)
        self.maxAngleDevSpin.setSingleStep(1)
        self.maxAngleDevSpin.setValue(10)
        self.maxAngleDevSpin.setSuffix(unichr(176))
        self.interDistSpin.setDecimals(5)
        self.interDistSpin.setRange(0, 10)
        self.interDistSpin.setSingleStep(0.00001)
        self.interDistSpin.setValue(0)
        self.minLenDevSpin.setDecimals(5)
        self.minLenDevSpin.setRange(0, 20)
        self.minLenDevSpin.setSingleStep(0.00001)
        self.minLenDevSpin.setValue(0)
        self.maxLenDevSpin.setDecimals(5)
        self.maxLenDevSpin.setRange(0, 30)
        self.maxLenDevSpin.setSingleStep(0.00001)
        self.maxLenDevSpin.setValue(0)

    def getNetwork1(self):
        return self.inputCombo1.currentText()

    def getNetwork2(self):
        return self.inputCombo2.currentText()

    def getDecimals1(self):
        # TODO: find equivalent to mm for provided crs
        return self.decimalsSpin1.value()

    def getDecimals2(self):
        # TODO: find equivalent to mm for provided crs
        return self.decimalsSpin2.value()

    def getMinSegLen(self):
        return self.minSegLenSpin.value()

    def getMinAngleDev(self):
        return self.minAngleDevSpin.value()

    def getMaxAngleDev(self):
        return self.maxAngleDevSpin.value()

    def getInterDist(self):
        return self.interDistSpin.value()

    def getMinLenDev(self):
        return (self.minLenDevSpin.value()/100) + 1

    def getMaxLenDev(self):
        return (self.maxLenDevSpin.value()/100) + 1

    def setOutput1(self):
        file_name = QtGui.QFileDialog.getSaveFileName(self, "Save output file ", "simplified_angle", '*.shp')
        if file_name:
            self.outputText1.setText(file_name)

    def setOutput2(self):
        file_name = QtGui.QFileDialog.getSaveFileName(self, "Save output file ", "simplified_inter", '*.shp')
        if file_name:
            self.outputText2.setText(file_name)

    def getOutput1(self):
        return self.outputText1.text()

    def getOutput2(self):
        return self.outputText2.text()

    def closeEvent(self, QCloseEvent):
        self.closeDialog()

    def closeDialog(self):
        self.inputCombo1.clear()
        self.inputCombo2.clear()
        self.outputText1.clear()
        self.outputText2.clear()
        self.decimalsSpin1.setValue(6)
        self.decimalsSpin2.setValue(6)
        self.minSegLenSpin.setValue(0.000)
        self.minAngleDevSpin.setValue(5)
        self.maxAngleDevSpin.setValue(10)
        self.interDistSpin.setValue(0.000)
        self.minLenDevSpin.setValue(10)
        self.maxLenDevSpin.setValue(40)
        self.minSegLenSpin.setValue(5)
        self.interDistSpin.setValue(5.5)
        self.close()