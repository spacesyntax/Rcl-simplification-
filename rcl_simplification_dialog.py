# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RclSimplificationDialog
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

        # Setup the progress bar
        self.progressBar1.setMinimum(0)
        self.progressBar1.setMaximum(100)
        self.progressBar2.setMinimum(0)
        self.progressBar2.setMaximum(100)


    def getNetwork1(self):
        return self.inputCombo1.currentText()

    def getNetwork2(self):
        return self.inputCombo2.currentText()

    def getNetwork2(self):
        return self.inputCombo2.currentText()

    def setDecimals(self):
        if self.snapTickBox1.isChecked():
            self.costCombo.setEnabled(True)

    def getDecimals1(self):
        # TODO: find equivalent to mm for provided crs
        if self.snapTickBox1.isChecked():
            return self.decimalsSpin1.value()
        else:
            return 0

    def getDecimals2(self):
        # TODO: find equivalent to mm for provided crs
        if self.snapTickBox2.isChecked():
            return self.decimalsSpin2.value()
        else:
            return 0

    def getMinSegLen(self):
        return self.minSegLenSpin.value()

    def getMinAngleDev(self):
        return self.minAngleDevSpin.value()

    def getMaxAngleDev(self):
        return self.maxAngleDevSpin.value()

    def getInterDist(self):
        return self.interDistSpin.value()

    def getMinLenDev(self):
        return self.minLenDevSpin.value()

    def getMaxLenDev(self):
        return self.maxLenDevSpin.value()

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

    def closeDialog(self):
        self.inputCombo1.clear()
        self.inputCombo1.setEnabled(False)
        self.snapTickBox1.setCheckState(False)

        self.inputCombo2.clear()
        self.inputCombo2.setEnabled(False)
        self.snapTickBox2.setCheckState(False)

        self.decimalsSpin1.setValue(1)
        self.minSegLenSpin.setValue(50)
        self.minAngleDevSpin.setValue(50)
        self.maxAngleDevSpin.setValue(50)

        self.decimalsSpin2.setValue(1)
        self.minSegLenSpin.setValue(50)
        self.minAngleDevSpin.setValue(50)
        self.maxAngleDevSpin.setValue(50)

        self.outputText1.clear()
        self.outputText2.clear()

        self.progressBar1.reset()
        self.progressBar2.reset()
        self.close()









