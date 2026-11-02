import sys
import uuid
import math
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QColor, QBrush, QPainterPath

# ==============================================================================
# 1. KONFIGURACJA I STYLE
# ==============================================================================

class Config:
    """Fizyczne parametry konfiguracyjne aplikacji."""
    SNAP_RADIUS_METERS: float = 15.0
    MIN_DRAG_DISTANCE: float = 2.0
    MIN_CURVE_DEVIATION: float = 5.0
    LANE_WIDTH_PX: float = 8.0
    NODE_RADIUS: float = 6.0


class Style:
    """Definicje kolorów i stylów graficznych interfejsu."""
    ROAD_BASE = QColor("#2E3138")
    ROAD_EDGE = QColor("#525864")
    ROAD_DIVIDER = QColor("#FFFFFF")
    
    NODE_MARKER = QColor("#FF2E8A")
    NODE_BORDER = QColor("#FFFFFF")
    
    PREVIEW_LINE = QColor("#00C2FF")
    PREVIEW_HANDLE = QColor("#FFD000")
    
    SNAP_FILL = QColor(0, 255, 102, 30)
    SNAP_BORDER = QColor("#00FF66")
    
    BG_WINDOW = "#1E1E24"
    BG_SCENE = QColor("#1A1A1E")
    GRID_LINE = QColor("#2B2E33")
    AXIS_LINE = QColor("#3F444E")


class ZLayer:
    """Wartości z-index ustalające kolejność renderowania elementów."""
    ROAD_EDGE: int = 1
    ROAD_BASE: int = 2
    ROAD_DIVIDER: int = 3
    NODE: int = 100


# ==============================================================================
# 2. MODELE DOMENOWE
# ==============================================================================

@dataclass
class Point2D:
    """Reprezentuje punkt w dwuwymiarowym układzie współrzędnych."""
    x: float
    y: float


@dataclass
class Node:
    """Węzeł reprezentujący punkt łączeniowy w sieci drogowej."""
    id: str
    position: Point2D


@dataclass
class Road:
    """Odcinek drogi zawierający informacje o pasach i geometrii."""
    id: str
    source_id: str
    target_id: str
    control_points: List[Point2D] = field(default_factory=list)
    lanes_forward: int = 1
    lanes_backward: int = 1

    @property
    def total_lanes(self) -> int:
        """Zwraca całkowitą liczbę pasów ruchu."""
        return self.lanes_forward + self.lanes_backward


class Project:
    """Główny kontener przechowujący stan symulacji i struktury danych."""
    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.roads: Dict[str, Road] = {}


# ==============================================================================
# 3. METODY POMOCNICZE
# ==============================================================================

class GeometryUtils:
    """Statyczne metody do obliczeń geometrycznych i przestrzennych."""
    
    @staticmethod
    def distance(p1: QPointF, p2: QPointF) -> float:
        """Oblicza odległość euklidesową między dwoma punktami."""
        return math.hypot(p2.x() - p1.x(), p2.y() - p1.y())

    @staticmethod
    def point_to_line_distance(point: QPointF, line_start: QPointF, line_end: QPointF) -> float:
        """Oblicza najkrótszą odległość punktu od prostej wyznaczonej przez dwa inne punkty."""
        line_length = GeometryUtils.distance(line_start, line_end)
        if line_length == 0:
            return GeometryUtils.distance(point, line_start)
        
        numerator = abs(
            (line_end.y() - line_start.y()) * point.x() - 
            (line_end.x() - line_start.x()) * point.y() + 
            line_end.x() * line_start.y() - 
            line_end.y() * line_start.x()
        )
        return numerator / line_length


# ==============================================================================
# 4. WIDOK I KONTROLER
# ==============================================================================

class DrawingState(Enum):
    """Fazy maszyny stanów określające aktualny tryb rysowania drogi."""
    IDLE = auto()
    DRAGGING_TARGET = auto()
    ADJUSTING_CURVE = auto()


class RoadEditorView(QGraphicsView):
    """Główny widok graficzny obsługujący renderowanie i interakcję użytkownika."""
    
    def __init__(self, scene: QGraphicsScene, project: Project, parent: Optional[QMainWindow] = None) -> None:
        super().__init__(scene, parent)
        self.project = project
        
        self.setRenderHint(self.renderHints().Antialiasing)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        self._state: DrawingState = DrawingState.IDLE
        self._start_node: Optional[Node] = None
        self._end_node: Optional[Node] = None
        self._is_start_node_temp: bool = False
        self._press_pos: Optional[Tuple[float, float]] = None

        self._preview_path_item = None
        self._preview_handle_item = None
        self._snap_highlight_item = None  
        self._rendered_items: List = []
        self._rendered_markers: Dict[str, any] = {}

    def _screen_to_world(self, screen_pos: QPointF) -> Tuple[float, float]:
        """Konwertuje współrzędne ekranowe na układ kartezjański (odwrócenie osi Y)."""
        return screen_pos.x(), -screen_pos.y()

    def _world_to_screen(self, point: Point2D) -> QPointF:
        """Konwertuje współrzędne układu kartezjańskiego na ekranowe."""
        return QPointF(point.x, -point.y)

    def _find_node_near(self, world_x: float, world_y: float) -> Optional[Node]:
        """Zwraca węzeł znajdujący się w promieniu przyciągania (snapping)."""
        for node in self.project.nodes.values():
            if math.hypot(node.position.x - world_x, node.position.y - world_y) <= Config.SNAP_RADIUS_METERS:
                return node
        return None

    def _create_temp_node(self, world_x: float, world_y: float) -> Node:
        """Tworzy i zwraca nową instancję węzła (bez zapisu do głównego stanu projektu)."""
        return Node(id=f"w_{uuid.uuid4().hex[:8]}", position=Point2D(round(world_x, 2), round(world_y, 2)))

    def _redraw_scene(self) -> None:
        """Odświeża widok poprzez usunięcie obecnych elementów i ponowne wyrenderowanie całości."""
        self._clear_rendered_items()

        for road in self.project.roads.values():
            n1 = self.project.nodes.get(road.source_id)
            n2 = self.project.nodes.get(road.target_id)
            if not n1 or not n2: 
                continue
            self._draw_road(road, n1, n2)

        self._update_node_visibility()

    def _clear_rendered_items(self) -> None:
        """Usuwa wyrenderowane obiekty z silnika Qt i pamięci."""
        for item in self._rendered_items:
            self.scene().removeItem(item)
        self._rendered_items.clear()
        self._rendered_markers.clear()

    def _draw_road(self, road: Road, source: Node, target: Node) -> None:
        """Buduje wielowarstwową reprezentację graficzną jezdni."""
        p1 = self._world_to_screen(source.position)
        p2 = self._world_to_screen(target.position)
        
        path = QPainterPath(p1)

        if road.control_points:
            ctrl_pt = self._world_to_screen(road.control_points[0])
            path.quadTo(ctrl_pt, p2)
        else:
            path.lineTo(p2)

        width_px = road.total_lanes * Config.LANE_WIDTH_PX

        edge_pen = QPen(Style.ROAD_EDGE, width_px + 4.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        edge_item = self.scene().addPath(path, edge_pen)
        edge_item.setZValue(ZLayer.ROAD_EDGE)
        self._rendered_items.append(edge_item)
        
        base_pen = QPen(Style.ROAD_BASE, width_px, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        base_item = self.scene().addPath(path, base_pen)
        base_item.setZValue(ZLayer.ROAD_BASE)
        self._rendered_items.append(base_item)

        divider_pen = QPen(Style.ROAD_DIVIDER, 1.5, Qt.DashLine, Qt.FlatCap, Qt.RoundJoin)
        divider_item = self.scene().addPath(path, divider_pen)
        divider_item.setZValue(ZLayer.ROAD_DIVIDER)
        self._rendered_items.append(divider_item)

    def _update_node_visibility(self) -> None:
        """Zarządza widocznością węzłów (ukrywa węzły wewnętrzne o liczbie połączeń >= 2)."""
        connections: Dict[str, int] = {node_id: 0 for node_id in self.project.nodes}
        for road in self.project.roads.values():
            connections[road.source_id] += 1
            connections[road.target_id] += 1
            
        for node_id, node in self.project.nodes.items():
            if connections.get(node_id, 0) < 2:
                self._draw_node_marker(node)

    def _draw_node_marker(self, node: Node) -> None:
        """Rysuje graficzną reprezentację (znacznik) węzła."""
        pt = self._world_to_screen(node.position)
        r = Config.NODE_RADIUS
        marker = self.scene().addEllipse(
            pt.x() - r, pt.y() - r, r * 2, r * 2, 
            QPen(Style.NODE_BORDER, 1.5), QBrush(Style.NODE_MARKER)
        )
        marker.setZValue(ZLayer.NODE)
        self._rendered_markers[node.id] = marker
        self._rendered_items.append(marker)

    def mousePressEvent(self, event) -> None:
        """Kieruje obsługę wciśnięcia przycisku myszy na podstawie bieżącego stanu i typu przycisku."""
        if event.button() == Qt.RightButton:
            self._cancel_drawing()
            return super().mousePressEvent(event)

        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)

        scene_pos = self.mapToScene(event.pos())
        wx, wy = self._screen_to_world(scene_pos)

        if self._state == DrawingState.IDLE:
            self._handle_press_idle(wx, wy)
        elif self._state == DrawingState.ADJUSTING_CURVE:
            self._handle_press_adjusting(scene_pos, wx, wy)
            
        super().mousePressEvent(event)

    def _handle_press_idle(self, wx: float, wy: float) -> None:
        """Inicjalizuje proces rysowania nowej drogi po kliknięciu wolnego obszaru (Faza 1)."""
        existing_node = self._find_node_near(wx, wy)
        if existing_node:
            self._start_node = existing_node
            self._is_start_node_temp = False
        else:
            self._start_node = self._create_temp_node(wx, wy)
            self._is_start_node_temp = True
        
        self._state = DrawingState.DRAGGING_TARGET
        self._press_pos = (wx, wy)
        
        self._preview_path_item = self.scene().addPath(QPainterPath(), QPen(Style.PREVIEW_LINE, 2, Qt.DashLine))
        self._preview_handle_item = self.scene().addPath(QPainterPath(), QPen(Style.PREVIEW_HANDLE, 1.5, Qt.DotLine))

    def _handle_press_adjusting(self, scene_pos: QPointF, wx: float, wy: float) -> None:
        """Finalizuje ustalanie kształtu drogi i zapisuje nową drogę do struktury projektu (Faza 3)."""
        p0 = self._world_to_screen(self._start_node.position)
        p2 = self._world_to_screen(self._end_node.position)
        
        ctrl_points: List[Point2D] = []
        deviation = GeometryUtils.point_to_line_distance(scene_pos, p0, p2)
        
        if deviation > Config.MIN_CURVE_DEVIATION:
            ctrl_points.append(Point2D(round(wx, 2), round(wy, 2)))

        new_road = Road(
            id=f"r_{uuid.uuid4().hex[:8]}",
            source_id=self._start_node.id,
            target_id=self._end_node.id,
            control_points=ctrl_points
        )
        self.project.roads[new_road.id] = new_road
        self._cancel_drawing() 

    def mouseMoveEvent(self, event) -> None:
        """Obsługuje przesuwanie wskaźnika myszy z uwzględnieniem aktualnego stanu."""
        scene_pos = self.mapToScene(event.pos())
        wx, wy = self._screen_to_world(scene_pos)

        if self._state == DrawingState.DRAGGING_TARGET and self._preview_path_item:
            self._handle_move_dragging(scene_pos, wx, wy)
        elif self._state == DrawingState.ADJUSTING_CURVE and self._preview_path_item:
            self._handle_move_adjusting(scene_pos)

        super().mouseMoveEvent(event)

    def _handle_move_dragging(self, scene_pos: QPointF, wx: float, wy: float) -> None:
        """Aktualizuje podgląd rysowanej drogi podczas jej wyznaczania (Faza 2)."""
        start_pt = self._world_to_screen(self._start_node.position)
        target_node = self._find_node_near(wx, wy)

        if target_node and target_node != self._start_node:
            end_pt = self._world_to_screen(target_node.position)
            self._show_snap_highlight(end_pt)
        else:
            end_pt = scene_pos
            self._hide_snap_highlight()

        path = QPainterPath(start_pt)
        path.lineTo(end_pt)
        self._preview_path_item.setPath(path)
        self._preview_handle_item.setPath(QPainterPath())

    def _handle_move_adjusting(self, scene_pos: QPointF) -> None:
        """Aktualizuje kształt krzywej podglądu, używając wskaźnika jako punktu kontrolnego."""
        self._hide_snap_highlight()
        
        p0 = self._world_to_screen(self._start_node.position)
        p2 = self._world_to_screen(self._end_node.position)
        
        path = QPainterPath(p0)
        path.quadTo(scene_pos, p2)
        self._preview_path_item.setPath(path)

        handle_path = QPainterPath(p0)
        handle_path.lineTo(scene_pos)
        handle_path.lineTo(p2)
        self._preview_handle_item.setPath(handle_path)

    def mouseReleaseEvent(self, event) -> None:
        """Obsługuje zwolnienie lewego przycisku myszy w stanie przyciągania węzła."""
        if event.button() == Qt.LeftButton and self._state == DrawingState.DRAGGING_TARGET:
            scene_pos = self.mapToScene(event.pos())
            wx, wy = self._screen_to_world(scene_pos)
            self._handle_release_dragging(wx, wy)

        super().mouseReleaseEvent(event)

    def _handle_release_dragging(self, wx: float, wy: float) -> None:
        """Przetwarza ustalone położenie nowego węzła lub rejestruje przejście w tryb wyginania krzywej."""
        drag_distance = math.hypot(wx - self._press_pos[0], wy - self._press_pos[1])

        if drag_distance < Config.MIN_DRAG_DISTANCE:
            if self._is_start_node_temp and self._start_node.id not in self.project.nodes:
                self.project.nodes[self._start_node.id] = self._start_node
            self._cancel_drawing()
            return

        if self._is_start_node_temp and self._start_node.id not in self.project.nodes:
            self.project.nodes[self._start_node.id] = self._start_node

        existing_node = self._find_node_near(wx, wy)
        if existing_node:
            self._end_node = existing_node
        else:
            self._end_node = self._create_temp_node(wx, wy)
            self.project.nodes[self._end_node.id] = self._end_node
        
        self._state = DrawingState.ADJUSTING_CURVE

    def _cancel_drawing(self) -> None:
        """Przerywa bieżącą akcję, czyści pomocnicze elementy interfejsu i resetuje maszynę stanów."""
        if self._preview_path_item:
            self.scene().removeItem(self._preview_path_item)
            self._preview_path_item = None
        if self._preview_handle_item:
            self.scene().removeItem(self._preview_handle_item)
            self._preview_handle_item = None
            
        self._hide_snap_highlight()
        
        self._state = DrawingState.IDLE
        self._start_node = None
        self._end_node = None
        self._press_pos = None
        
        self._redraw_scene()

    def _show_snap_highlight(self, pt: QPointF) -> None:
        """Wyświetla lub aktualizuje graficzne wyróżnienie magnetycznego przyciągania do węzła."""
        r = Config.SNAP_RADIUS_METERS
        if not self._snap_highlight_item:
            self._snap_highlight_item = self.scene().addEllipse(
                pt.x() - r, pt.y() - r, r * 2, r * 2,
                QPen(Style.SNAP_BORDER, 1.5, Qt.DashLine), QBrush(Style.SNAP_FILL)
            )
        else:
            self._snap_highlight_item.setRect(pt.x() - r, pt.y() - r, r * 2, r * 2)

    def _hide_snap_highlight(self) -> None:
        """Ukrywa obramowanie wokół aktywnego magnetycznie węzła."""
        if self._snap_highlight_item:
            self.scene().removeItem(self._snap_highlight_item)
            self._snap_highlight_item = None


# ==============================================================================
# 5. ENTRY POINT APLIKACJI
# ==============================================================================

class MainWindow(QMainWindow):
    """Główne okno aplikacji integrujące widok edytora i infrastrukturę Qt."""
    
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Intersection Simulator - Professional Road Editor")
        self.resize(1100, 750)

        self.project = Project()

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)

        self.editor_view = RoadEditorView(self.scene, self.project, self)
        self.setCentralWidget(self.editor_view)

        self._initialize_grid()

    def _initialize_grid(self) -> None:
        """Rysuje siatkę odniesienia i główne osie układu współrzędnych."""
        grid_pen = QPen(Style.GRID_LINE, 0.5, Qt.DotLine)
        for i in range(-1000, 1001, 50):
            self.scene.addLine(i, -1000, i, 1000, grid_pen)
            self.scene.addLine(-1000, i, 1000, i, grid_pen)

        axis_pen = QPen(Style.AXIS_LINE, 1.5)
        self.scene.addLine(-1000, 0, 1000, 0, axis_pen)
        self.scene.addLine(0, -1000, 0, 1000, axis_pen)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.setStyleSheet(f"QMainWindow {{ background-color: {Style.BG_WINDOW}; }}")
    window.scene.setBackgroundBrush(QBrush(Style.BG_SCENE))
    
    window.show()
    sys.exit(app.exec())