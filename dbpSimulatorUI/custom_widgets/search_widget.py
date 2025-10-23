import pandas as pd
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QSizePolicy, QLineEdit, QPushButton, QCompleter
from qgis.core import QgsProject, QgsFeatureRequest


class CompleterLineEdit(QLineEdit):
    """
    Custom QLineEdit that shows completer popup on focus/click.
    """

    def __init__(self, *args, **kwargs):
        """Constructor"""
        super().__init__(*args, **kwargs)
        # Set white background
        self.setStyleSheet("QLineEdit { background-color: white; border: none; }")

    def focusInEvent(self, event):
        """Handler for event if user starts interacting with keyboard"""
        super().focusInEvent(event)
        if self.completer() and self.text() == "":
            self.completer().complete()

    def mousePressEvent(self, event):
        """Handler for event if user clicked inside the widget"""
        super().mousePressEvent(event)
        if self.completer():
            self.completer().complete()

    def keyPressEvent(self, event):
        comp = self.completer()
        if comp and event.key() in (Qt.Key_Down, Qt.Key_Up):
            if not comp.popup().isVisible():
                comp.complete()  # open pop up completion
                return
        super().keyPressEvent(event)


class SearchWidget(QWidget):
    """
    Custom widget for searching features in QGIS.

    Attributes
    ----------
    canvas : QgsMapCanvas
        The map canvas of the QGIS project instance.
    layer : QgsVectorLayer
        Layer the widget listens to:
    df : pandas.DataFrame
        Dataframe containing all features of the layer.
    subset : pandas.DataFrame
        Dataframe containing a subset of df.
    completer : QCompleter
        Class that provides completions based on the subset dataframe.
    """

    def __init__(self, layer_name, canvas):
        """Constructor"""
        super().__init__()
        self.canvas = canvas
        self.layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        self.df = None
        self.subset = None
        self.completer = None
        self._freeze_subset = False
        self._all_ids_set = set()
        # First set the UI
        self.setup_ui()
        # Then connect listeners for events
        self.connect_signals()
        # Load layer data
        self.load_layer_data()

    def connect_signals(self):
        """Initialize event listeners in the widget"""
        # When layer selection changes update the completer
        self.layer.selectionChanged.connect(lambda: (self.change_subset()))
        # Connect text change events
        self.search_input.textChanged.connect(self.on_text_changed)
        # Pressing enter in input
        self.search_input.returnPressed.connect(self._on_enter)

    def load_layer_data(self, dma=None):
        """Data loading with optional filtering"""

        if dma is not None:
            # Filter features by DMA using QgsFeatureRequest
            request = QgsFeatureRequest().setFilterExpression(f'"DMA" = \'{dma}\'')
            features = list(self.layer.getFeatures(request))
        else:
            # Get all features if no DMA specified
            features = list(self.layer.getFeatures())

        # Vectorized extraction
        self.df = pd.DataFrame({
            'id': [str(feat['id']) for feat in features],
            'fid': [feat.id() for feat in features]
        })

        # Set the subset to have all the features
        self.subset = self.df

        self._all_ids_set = set(self.df['id'].astype(str))

        # Update the completer
        self.update_completer()

    def update_completer(self):
        """Update the completer with current subset DataFrame data"""
        if hasattr(self, 'search_input'):
            # Create new completer with current data
            items = self.subset['id'].astype(str).tolist()
            self.completer = QCompleter(items, self)
            self.completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.completer.setFilterMode(Qt.MatchContains)
            self.completer.setMaxVisibleItems(4)
            self.completer.activated[str].connect(self._select_by_text)
            self.search_input.setCompleter(self.completer)

    def setup_ui(self):
        """Sets the UI of the widget"""
        layout = QHBoxLayout()

        # Search input with instant autocomplete
        self.search_input = CompleterLineEdit()
        self.search_input.setPlaceholderText("Enter node id...")

        # Set size policy to prevent excessive expansion
        self.search_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # Install event filter to handle mouse clicks
        self.search_input.installEventFilter(self)

        # Selection tool button
        self.selection_tool_button = QPushButton()
        self.selection_tool_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.selection_tool_button.setMaximumWidth(35)
        self.selection_tool_button.setMaximumHeight(35)
        self.selection_tool_button.setToolTip("Enable Selection Tool")

        # Set icon and styling for selection tool button
        from qgis.PyQt.QtGui import QIcon
        from qgis.core import QgsApplication



        self.selection_tool_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #cccccc;
                border-radius: 10px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border: 1px solid #0078d4;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)

        layout.addWidget(self.search_input)
        # Add stretch to prevent widgets from expanding to fill entire space
        layout.addStretch()

        # Set layout margins and spacing for better control
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(10)

        self.setLayout(layout)

    def change_subset(self):
        """Changes the subset dataframe to filter completions"""

        if self._freeze_subset:
            return
        # If no selection on map
        if self.layer.selectedFeatureCount() == 0:
            self.search_input.setText("")
            self.on_text_changed()  # Trigger listener

        # Get features of layer
        fids = list(self.layer.selectedFeatureIds())
        matches = self.df['fid'].isin(fids)  # Find matches

        if not self.df[matches].empty:
            # Filter the dataframe to keep only selected features
            self.subset = self.df[matches]
            # Assign the first id in the list to the QLineEdit
            self.search_input.setText(self.subset.iloc[0]['id'])
            # Update the completer
            self.update_completer()

    def on_text_changed(self):
        """Handle text changes - show appropriate items when cleared"""
        text = self.search_input.text().strip()

        if text == "":
            # When text is cleared, show the appropriate subset
            if self.layer.selectedFeatureCount() == 0:
                # No features selected - show all data
                self.subset = self.df
            else:
                # Features are selected - show only selected features
                fids = list(self.layer.selectedFeatureIds())
                matches = self.df['fid'].isin(fids)
                self.subset = self.df[matches]

            self.update_completer()

    def _select_by_text(self, text: str):
        text = text.strip()
        if not text:
            return
        matches = self.df[self.df['id'] == text]
        if matches.empty:
            return
        fid = int(matches.iloc[0]['fid'])
        self._freeze_subset = True
        try:
            self.layer.selectByIds([fid])
        finally:
            self._freeze_subset = False
        self.canvas.refresh()

    def select_node(self):
        """Function to handle when pressing the select_button"""

        self._select_by_text(self.search_input.text())
        # Get current text
        text = self.search_input.text().strip()
        if not text:
            return

        # Find matches in the global dataframe
        matches = self.df[self.df['id'] == text]

        if not matches.empty:
            # Get first feature
            fid = matches.iloc[0]['fid']
            # Select on map
            self.layer.selectByIds([fid])
            if self.layer.selectedFeatures():
                self.canvas.refresh()

    def _on_enter(self):
        text = self.search_input.text().strip()
        if not text:
            return

        comp = self.search_input.completer()
        # block temporary completer for not interfering
        if comp:
            comp.blockSignals(True)
        try:
            if text in self._all_ids_set:
                # Protection for not changing the subset from change_subset()
                self._freeze_subset = True
                try:
                    self._select_by_text(text)
                finally:
                    self._freeze_subset = False

        finally:
            if comp:
                comp.blockSignals(False)
                if comp.popup() and comp.popup().isVisible():
                    comp.popup().hide()
