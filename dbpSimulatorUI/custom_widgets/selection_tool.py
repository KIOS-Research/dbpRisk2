from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import (QgsRectangle, QgsFeatureRequest, QgsCoordinateTransform, 
                       QgsCoordinateReferenceSystem, QgsProject, QgsGeometry, QgsWkbTypes)

class SelectionTool(QgsMapTool):
    """
    Custom map tool selection for nodes in QGIS.
    
    Attributes
    ----------
    canvas : QgsMapCanvas
        The map canvas of the QGIS project instance.
    layer : QgsVectorLayer
        The layer that the map tool selects features from.
    rubber_band : QgsRubberBand
        Transparent overlay widget to indicate selected area from dragging.
    currently_acting : Boolean
        Flag indicating that the user is currently acting with the mouse.
    start_point : QPoint
        Point on map from where mouse movement started.
    end_point : QPoint
        Point on map from where mouse movement ended.
    """
    def __init__(self, canvas, layer):
        """Constructor"""
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.setCursor(Qt.ArrowCursor)

        # Initialize rubber band for drag selection
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        # Track drag state
        self.currently_acting = False
        self.start_point = None
        self.end_point = None

    def canvasPressEvent(self, event):
        """Handle mouse press - start drag selection"""
        if event.button() == Qt.LeftButton: # If mouse left click
            self.currently_acting = True
            self.start_point = event.pos()
            self.end_point = event.pos()  # Initialize end_point to start_point
            # Clear any existing rubber_band geometry 
            # and assign Polygon (rectangle)
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)

    def canvasMoveEvent(self, event):
        """Handle mouse move - update rubber band during drag"""
        if self.currently_acting and self.start_point:
            self.end_point = event.pos() # Get current position of mouse
            
            # Only show rubber band if we're actually dragging (not just a small movement)
            distance = euclidean_distance(self.start_point, self.end_point)
            
            if distance > 5:  # Only show rubber band for actual drags
                # Create rectangle from start to current position
                rect = self.get_screen_rectangle(self.start_point, self.end_point)
                
                # Update rubber band
                self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
                self.rubber_band.addPoint(self.toMapCoordinates(rect.topLeft()))
                self.rubber_band.addPoint(self.toMapCoordinates(rect.topRight()))
                self.rubber_band.addPoint(self.toMapCoordinates(rect.bottomRight()))
                self.rubber_band.addPoint(self.toMapCoordinates(rect.bottomLeft()))
                self.rubber_band.addPoint(self.toMapCoordinates(rect.topLeft()))

    def canvasReleaseEvent(self, event):
        """Handle mouse release - perform selection"""
        if event.button() != Qt.LeftButton:
            return   # If not mouse left click then return
            
        # Clear rubber band
        self.rubber_band.reset()
        
        if not self.currently_acting:
            return
        self.currently_acting = False
        
        # Determine if it's a click or drag based on movement distance
        if self.start_point and self.end_point:
            distance = euclidean_distance(self.start_point, self.end_point)
            
            if distance < 5:  # Small movement = click selection
                self.handle_click_selection(event)
            else:  # Actual drag = rectangle selection
                self.handle_drag_selection()
        else:
            # Fallback: treat as click if end_point is None
            self.handle_click_selection(event)
    
    def handle_click_selection(self, event):
        """Handle single click selection on nodes"""
        ctrl_pressed = QApplication.keyboardModifiers() & Qt.ControlModifier
        
        # Get point in canvas coordinates (EPSG:4326)
        point_4326 = self.toMapCoordinates(event.pos())
        
        # Transform to layer CRS
        point_6312 = self.transform_point(point_4326)
        point_geom = QgsGeometry.fromPointXY(point_6312)
        
        # Create search rectangle around click point
        search_radius = 2.0  # 2 meters search radius
        search_rect = QgsRectangle(
            point_6312.x() - search_radius, point_6312.y() - search_radius,
            point_6312.x() + search_radius, point_6312.y() + search_radius
        )
        
        # Find features within search area
        request = QgsFeatureRequest().setFilterRect(search_rect)
        features = list(self.layer.getFeatures(request))
        
        if features:
            # Find the closest feature to the click point
            closest_feature = min(features, 
                key=lambda f: f.geometry().distance(point_geom) if f.geometry() else float('inf'))
            
            # Handle selection logic
            if not ctrl_pressed:
                # Normal click: clear existing selection and select clicked node
                self.layer.removeSelection()
                self.layer.select(closest_feature.id())
            else:
                # Ctrl+click: toggle selection of clicked node
                if closest_feature.id() in self.layer.selectedFeatureIds():
                    self.layer.deselect(closest_feature.id())
                else:
                    self.layer.select(closest_feature.id())
            
        else:
            # No features found under click
            if not ctrl_pressed:
                # Clear selection if clicking on empty space (without Ctrl)
                self.layer.removeSelection()

    def handle_drag_selection(self):
        """Handle drag rectangle selection"""
        ctrl_pressed = QApplication.keyboardModifiers() & Qt.ControlModifier
        
        # Get screen rectangle
        screen_rect = self.get_screen_rectangle(self.start_point, self.end_point)
        
        # Convert to map coordinates
        top_left_4326 = self.toMapCoordinates(screen_rect.topLeft())
        bottom_right_4326 = self.toMapCoordinates(screen_rect.bottomRight())
        
        # Transform to layer CRS
        top_left_6312 = self.transform_point(top_left_4326)
        bottom_right_6312 = self.transform_point(bottom_right_4326)
        
        # Create selection rectangle in layer CRS
        selection_rect = QgsRectangle(
            min(top_left_6312.x(), bottom_right_6312.x()),
            min(top_left_6312.y(), bottom_right_6312.y()),
            max(top_left_6312.x(), bottom_right_6312.x()),
            max(top_left_6312.y(), bottom_right_6312.y())
        )
        
        # Find features within rectangle
        request = QgsFeatureRequest().setFilterRect(selection_rect)
        features = list(self.layer.getFeatures(request))
        
        if features:
            feature_ids = [f.id() for f in features]
            
            if not ctrl_pressed:
                # Normal drag: clear existing selection and select dragged nodes
                self.layer.removeSelection()
                self.layer.select(feature_ids)
            else:
                # Ctrl+drag: toggle selection of dragged nodes
                currently_selected = set(self.layer.selectedFeatureIds())
                new_features = set(feature_ids)
                
                # Add unselected features, remove selected features
                to_select = new_features - currently_selected
                to_deselect = new_features & currently_selected
                
                if to_select:
                    self.layer.select(list(to_select))
                if to_deselect:
                    self.layer.deselect(list(to_deselect))
        else:
            # No features in drag rectangle
            if not ctrl_pressed:
                self.layer.removeSelection()

    def transform_point(self, point_4326):
        """Transform point from EPSG:4326 to EPSG:6312"""
        crs_4326 = QgsCoordinateReferenceSystem('EPSG:4326')
        crs_6312 = QgsCoordinateReferenceSystem('EPSG:6312')
        transform = QgsCoordinateTransform(crs_4326, crs_6312, QgsProject.instance())
        return transform.transform(point_4326)

    def get_screen_rectangle(self, start_point, end_point):
        """Create QRect from two QPoint objects"""
        from qgis.PyQt.QtCore import QRect
        return QRect(start_point, end_point).normalized()
    

import math

def euclidean_distance(p1, p2):
    """Calculate Euclidean distance between two QPoint objects"""
    dx = p1.x() - p2.x()
    dy = p1.y() - p2.y()
    return math.sqrt(dx * dx + dy * dy)