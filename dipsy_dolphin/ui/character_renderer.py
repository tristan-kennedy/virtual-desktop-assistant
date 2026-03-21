from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF

from .asset_manifest import CharacterAssetManifest
from .presentation_models import CharacterPresentation


class CharacterRenderer:
    def __init__(self, manifest: CharacterAssetManifest) -> None:
        self.manifest = manifest

    def paint(self, painter: QPainter, presentation: CharacterPresentation) -> None:
        painter.setRenderHint(QPainter.Antialiasing, True)
        bob = presentation.bob_offset

        self._draw_shadow(painter, bob, presentation)
        self._draw_body_layers(painter, bob, presentation)
        self._draw_face(painter, bob, presentation)
        self._draw_badge(painter, bob)
        self._draw_effects(painter, bob, presentation)

    def _draw_shadow(
        self, painter: QPainter, bob: int, presentation: CharacterPresentation
    ) -> None:
        shadow_width = 126 if presentation.pose_id == "walk" else 120
        shadow_height = 18 if presentation.pose_id == "walk" else 20
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#091014"))
        painter.drawEllipse(
            QRectF(104 - shadow_width / 2, 196 + abs(bob) * 0.3, shadow_width, shadow_height)
        )

    def _draw_body_layers(
        self, painter: QPainter, bob: int, presentation: CharacterPresentation
    ) -> None:
        facing_shift = -5 if presentation.facing == "left" else 5
        walk_shift = 3 if presentation.pose_id == "walk" and presentation.facing == "right" else 0
        walk_shift = (
            -3 if presentation.pose_id == "walk" and presentation.facing == "left" else walk_shift
        )
        lean_x = facing_shift + walk_shift

        painter.save()
        painter.translate(lean_x * 0.35, bob)

        outline_pen = QPen(QColor("#1F5874"), 3)
        painter.setPen(outline_pen)

        painter.setBrush(QColor("#5EAED1"))
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(48, 120),
                    QPointF(28, 96),
                    QPointF(44, 138),
                ]
            )
        )

        tail_points = [
            QPointF(138, 154),
            QPointF(162 + facing_shift, 182),
            QPointF(118, 170),
        ]
        painter.setBrush(QColor("#4F9BBC"))
        painter.drawPolygon(QPolygonF(tail_points))

        painter.setBrush(QColor("#5EAED1"))
        painter.drawEllipse(QRectF(42, 62, 124, 128))

        painter.setBrush(QColor("#86D4F0"))
        painter.drawEllipse(QRectF(74, 42, 76, 68))

        painter.setBrush(QColor("#9BE3FA"))
        painter.drawPolygon(QPolygonF([QPointF(106, 70), QPointF(120, 34), QPointF(132, 76)]))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#C7F3FF"))
        painter.drawEllipse(QRectF(64, 94, 74, 74))
        painter.restore()

    def _draw_face(self, painter: QPainter, bob: int, presentation: CharacterPresentation) -> None:
        face_y = bob - 1
        brow_pen = QPen(QColor("#113246"), 2)
        face_pen = QPen(QColor("#103248"), 2)
        pupil_shift = -2 if presentation.facing == "left" else 2

        painter.save()
        painter.translate(0, face_y)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#F8FBFD"))
        painter.drawEllipse(QRectF(82, 66, 15, 15))
        painter.drawEllipse(QRectF(114, 66, 15, 15))

        painter.setBrush(QColor("#17191A"))
        if presentation.eye_state == "blink":
            painter.setPen(face_pen)
            painter.drawLine(83, 74, 96, 74)
            painter.drawLine(115, 74, 128, 74)
            painter.setPen(Qt.NoPen)
        else:
            painter.drawEllipse(QRectF(87 + pupil_shift, 70, 6, 6))
            painter.drawEllipse(QRectF(119 + pupil_shift, 70, 6, 6))

        painter.setPen(brow_pen)
        if presentation.expression_id == "happy":
            painter.drawLine(82, 63, 95, 67)
            painter.drawLine(116, 67, 129, 63)
        elif presentation.expression_id == "concerned":
            painter.drawLine(82, 67, 96, 63)
            painter.drawLine(116, 63, 129, 67)
        else:
            painter.drawLine(82, 64, 95, 64)
            painter.drawLine(116, 64, 129, 64)

        self._draw_mouth(painter, presentation)
        painter.restore()

    def _draw_mouth(self, painter: QPainter, presentation: CharacterPresentation) -> None:
        mouth_pen = QPen(QColor("#102226"), 2)
        painter.setPen(mouth_pen)
        painter.setBrush(Qt.NoBrush)

        if presentation.mouth_state == "talk_open":
            painter.setBrush(QColor("#163847"))
            painter.drawEllipse(QRectF(95, 87, 22, 14))
            painter.setBrush(QColor("#F5A4B8"))
            painter.drawEllipse(QRectF(99, 95, 14, 4))
            return

        if presentation.expression_id == "happy":
            painter.drawArc(QRectF(90, 82, 30, 26), 205 * 16, -145 * 16)
        elif presentation.expression_id == "concerned":
            painter.drawArc(QRectF(92, 92, 24, 12), 25 * 16, 130 * 16)
        else:
            painter.drawArc(QRectF(92, 84, 28, 18), 195 * 16, -120 * 16)

    def _draw_badge(self, painter: QPainter, bob: int) -> None:
        painter.save()
        painter.translate(0, bob)
        painter.setPen(QColor("#103248"))
        painter.setFont(QFont("Franklin Gothic Medium", 10, QFont.Bold))
        painter.drawText(QRectF(64, 116, 80, 20), Qt.AlignCenter, "DIPSY")
        painter.restore()

    def _draw_effects(
        self, painter: QPainter, bob: int, presentation: CharacterPresentation
    ) -> None:
        if not presentation.active_effects:
            return

        painter.save()
        painter.translate(0, bob)
        for effect in presentation.active_effects:
            if effect == "question":
                painter.setPen(QPen(QColor("#163847"), 3))
                painter.setFont(QFont("Franklin Gothic Heavy", 18, QFont.Bold))
                painter.drawText(QRectF(145, 24, 24, 28), Qt.AlignCenter, "?")
                painter.setBrush(QColor("#163847"))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QRectF(153, 49, 4, 4))
            elif effect == "spark":
                painter.setPen(QPen(QColor("#FFD56A"), 3))
                painter.drawLine(148, 34, 160, 34)
                painter.drawLine(154, 28, 154, 40)
                painter.drawLine(149, 29, 159, 39)
                painter.drawLine(149, 39, 159, 29)
            elif effect == "sweat":
                painter.setPen(QPen(QColor("#8DD9F8"), 2))
                painter.setBrush(QColor("#8DD9F8"))
                painter.drawEllipse(QRectF(138, 56, 8, 12))
        painter.restore()
