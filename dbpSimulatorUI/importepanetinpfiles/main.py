# (C)Marios Kyriakou 2016
# University of Cyprus, KIOS Research Center for Intelligent Systems and Networks
from qgis.PyQt.QtWidgets import (QAction, QFileDialog, QMessageBox, QWidget, QWizard, QWizardPage, QVBoxLayout)
from qgis.PyQt.QtGui import *  # QIcon
from qgis.PyQt.QtCore import *  # QVariant, Qt
from qgis.core import (QgsProject, QgsLayerTreeGroup, QgsCoordinateReferenceSystem, QgsCoordinateTransform)
from qgis.gui import QgsProjectionSelectionTreeWidget
from .Epa2GIS import epa2gis
from . import resources_rc
import sys
import os

from qgis.PyQt import QtGui, uic, QtCore
from qgis.PyQt.QtWidgets import QDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ExportEpanetInpFiles_dialog_base.ui'))


class ExportEpanetInpFilesDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        super(ExportEpanetInpFilesDialog, self).__init__(parent)
        self.setupUi(self)


class CrsSelector(QWizard):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addPage(crs_page(self))
        global import_export
        if import_export == 'Import':
            self.setWindowTitle("IMPORT EPANET INPUT FILE")
        elif import_export == 'Export':
            self.setWindowTitle("EXPORT EPANET INPUT FILE WITH SPECIFIC CRS")

        self.setOption(QWizard.NoCancelButton, True)
        self.setOption(QWizard.NoBackButtonOnLastPage, True)
        self.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)


class crs_page(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        global import_export
        if import_export == 'Import':
            self.setTitle('Project Coordinate System')
            self.setSubTitle('Choosing an appropriate projection for EPANET layers.')
        elif import_export == 'Export':
            self.setTitle('Project Coordinate System')
            self.setSubTitle('Choosing projection for EPANET coordinates.')

        self.selector = QgsProjectionSelectionTreeWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.selector)
        self.setLayout(layout)
        self.selector.crsSelected.connect(self.crs_selected)

    def crs_selected(self):
        self.completeChanged.emit()

    def isComplete(self):
        global result_crs
        result_crs = self.selector.crs()
        return self.selector.crs().isValid()


class ImpEpanet(object):
    def __init__(self, iface):
        # Save a reference to the QGIS iface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.dlg = ExportEpanetInpFilesDialog()
        self.sections = ['junctions', 'tanks', 'pipes', 'pumps', 'valves', 'reservoirs']
        #self.sections = ['junctions', 'tanks', 'pipes', 'pumps', 'reservoirs', 'valves', 'status', 'patterns', 'curves',
        #                 'controls', 'rules', 'energy', 'reactions', 'reactions_i', 'emitters', 'quality', 'sources',
        #                 'mixing', 'times', 'report', 'options']

    def initGui(self):
        # Create action
        self.action = QAction(QIcon(":/plugins/ImportEpanetInpFiles/impepanet.png"), "Import Epanet Input File",
                              self.iface.mainWindow())
        self.action.setWhatsThis("Import Epanet Input File")
        self.action.triggered.connect(self.run)
        self.sections = ['junctions', 'tanks', 'pipes', 'pumps', 'valves', 'reservoirs']

    def unload(self):
        # Remove the plugin
        self.iface.removePluginMenu("&ImportEpanetInpFiles", self.action)
        self.iface.removeToolBarIcon(self.action)

        self.iface.removePluginMenu("&ImportEpanetInpFiles", self.actionexp)
        self.iface.removeToolBarIcon(self.actionexp)

    def run(self, filePath):
        # filePath = QFileDialog.getOpenFileName(self.iface.mainWindow(), "Choose EPANET Input file",
        #                                        os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop'),
        #                                        "Epanet Inp File (*.inp)")
        # if filePath[0] == "":
        #     return

        # Get project CRS
        proj_crs = QgsProject.instance().crs().authid()

        # Call selector
        global import_export
        import_export = 'Import'
        self.crs_ui_selector = CrsSelector()
        check = self.crs_ui_selector.exec()
        if not check:
            return

        global result_crs
        self.epsg_crs = result_crs.authid()
        epa2gis(filePath[0], self.epsg_crs)
        # Clear messages
        self.iface.messageBar().clearWidgets()
        msgBox = QMessageBox()
        msgBox.setWindowTitle('Plugin: ImportEpanetInpFiles')
        msgBox.setText('Shapefiles have been created successfully in folder "_shapefiles_".')
        msgBox.exec_()

        # Restore CRS
        QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(proj_crs))

    def selectOutp(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle('Warning')
        msgBox.setText('Please define Epanet Inp File location.')
        msgBox.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        msgBox.exec_()
        return True