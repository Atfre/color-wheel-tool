#===================================================================================== #
# [SFM] Color Wheel Tool v1.3.0
#
#   This script adds a Color Wheel system and more lighting properties to the "rigs" 
# section of your lights in Source Filmmaker, letting you modify light settings in a 
# more intuitive way instead of relying on SFM's default sliders.
#
# Credits:
# Script based off Fames, msu355, and an0nymooose for fixes and implementations.
# HEX code idea by Dani3D
# Sliders remapping idea by Higglemug McGiggletoot.
#
# Early testing and feedback:
# - Bone
# - Cuori
# - HyperBlender
# - Shydo
# - Trap & Hat
#
# Author: Aftre
# ===================================================================================== #

import colorsys, sfm, sfmApp, math, vs
from vs import g_pDataModel as dm
from PySide import QtGui, QtCore, shiboken

ProductName = "Color Wheel v1.3.0"
InternalName = "color_wheel"

# -- Channels names --- #
_POLL_CHANNELS = (
    "color_red",
    "color_green",
    "color_blue",
    "intensity",
    "ambientIntensity",
    "radius",
    "horizontalFOV",
    "verticalFOV",
    "shadowFilterSize",
    "shadowAtten",
    "shadowDepthBias",
    "shadowSlopeScaleDepthBias",
    "minDistance",
    "maxDistance",
    "farZAtten",
    "constantAttenuation",
    "linearAttenuation",
    "quadraticAttenuation",
    "volumetricIntensity",
    "noiseStrength",
    "width",
    "edgeWidth",
    "height",
    "edgeHeight",
)

# -- Booleans names --- #
_BOOL_NAMES = (
    "castsShadows",
    "volumetric",
    "uberlight"
)


def getSampleTime():
    try:
        return vs.DmeTime_t(float(sfmApp.GetHeadTimeInFrames()) / float(sfmApp.GetFramesPerSecond()))
    except Exception:
        return vs.DmeTime_t(0.0)


def timelineEditor():
    try:
        name = str(sfmApp.GetNameForTimelineMode(sfmApp.GetTimelineMode())).lower()
        for editor in ('Clip', 'Motion', 'Graph'):
            if editor.lower() in name:
                return editor
    except Exception:
        pass
    return None


def channelEditTarget(channel):
    if timelineEditor() not in ('Motion', 'Graph'):
        raise ValueError('Light editing is unavailable in Clip Editor.')
    return (str(channel.GetId()), str(channel.log.GetLayer(0).GetId()))


# -- Gets the channel of a property by its name --- #
def getChannel(animSet, controlName):
    try:
        if animSet is None:
            return None
        ctrl = animSet.FindControl(controlName)
        if ctrl is not None and getattr(ctrl, "channel", None):
            return ctrl.channel
        rootGroup = animSet.GetRootControlGroup()
        if rootGroup is None:
            return None
        ctrl = rootGroup.FindControlByName(controlName, True)
        return ctrl.channel if ctrl else None
    except Exception:
        return None


# -- Reads the value of a property's channel --- #
def readCurrentChannelValue(channel, sampleTime):
    for getter in ('GetToAttribute', 'GetFromAttribute'):
        try:
            attribute = getattr(channel, getter)()
            value = float(attribute.GetValue())
            if not math.isnan(value) and not math.isinf(value):
                return value
        except Exception:
            pass
    try:
        sampleTime = channel.GetCurrentTime()
    except Exception:
        pass
    return float(channel.log.GetValue(sampleTime))


def getChannelInput(channel):
    try:
        attribute = channel.GetFromAttribute()
        return attribute if attribute is not None and str(attribute.GetTypeString()).lower() == 'float' else None
    except AttributeError:
        return None


# -- Writes values on keyframes depending on which timeline-editor you are (Clip, Motion or Graph Editors) --- #
def setChannelAllKeys(channel, value, target=None):
    try:
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return False
        current = channelEditTarget(channel)
        if target is not None and current != target:
            raise ValueError('The light channel changed before the queued edit could be applied.')
        log, layer = channel.log, channel.log.GetLayer(0)
        for i in range(layer.GetKeyCount()):
            if layer.GetKeyValue(i) != value:
                layer.SetKeyValue(i, value)
        if not layer.GetKeyCount() or log.HasDefaultValue():
            log.SetDefaultValue(value)
        attribute = getChannelInput(channel)
        if attribute is not None:
            attribute.SetValue(value)
        if hasattr(channel, 'Play'):
            channel.Play()
        return True
    except Exception as error:
        print('[Color Wheel] Could not update channel: %s' % error)
        return False


# -- Reads the value of a boolean property's channel --- #
def readLightBoolean(light, name):
    try:
        if hasattr(light, 'HasAttribute') and not light.HasAttribute(name):
            return None
        value = light.GetValue(name)
        return bool(value) if isinstance(value, (bool, int)) and value in (True, False) else None
    except Exception:
        return None


# == Color Wheel Widget === #
class ColorPicker(QtGui.QWidget):
    colorChanged = QtCore.Signal(QtGui.QColor)
    colorReleased = QtCore.Signal(QtGui.QColor)

    def __init__(self):
        super(ColorPicker, self).__init__()
        self.setFixedSize(180, 180)
        self.setCursor(QtCore.Qt.CrossCursor)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self._radius, self._mode = 96, 'Wheel'
        self._hue, self._sat, self._value = 0.0, 0.0, 1.0
        self._dragging, self._region = False, None
        self._color = QtGui.QColor(255, 255, 255)
        self._selectorPos = QtCore.QPointF(100, 100)
        self._triangleMasks = self._triangleTint = None
        self._square = QtCore.QRectF(14, 24, 172, 172)
        self._innerSquare = QtCore.QRectF(49, 49, 102, 102)
        self._hueStrip = QtCore.QRectF(14, 4, 172, 12)
        self._triangle = QtGui.QPolygonF([QtCore.QPointF(174, 100),
            QtCore.QPointF(63, 164.086), QtCore.QPointF(63, 35.914)])
        self._generateWheel()

    def _generateWheel(self):
        cached = getattr(ColorPicker, '_wheelImages', None)
        if cached is not None and cached[0] == self._radius:
            self._cachedWheel, self._cachedRing = cached[1:]
            return
        wheel = QtGui.QImage(200, 200, QtGui.QImage.Format_ARGB32)
        ring = QtGui.QImage(200, 200, QtGui.QImage.Format_ARGB32)
        wheel.fill(0)
        ring.fill(0)
        for y in range(200):
            for x in range(200):
                dx, dy = x - 100, y - 100
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= self._radius:
                    hue = int(math.degrees(math.atan2(-dx, dy)) % 360)
                    wheel.setPixel(x, y, QtGui.QColor.fromHsv(hue, int(dist / self._radius * 255), 255).rgb())
                    if dist >= 78:
                        ring.setPixel(x, y, QtGui.QColor.fromHsv(hue, 255, 255).rgb())
        self._cachedWheel, self._cachedRing = QtGui.QPixmap.fromImage(wheel), QtGui.QPixmap.fromImage(ring)
        ColorPicker._wheelImages = (self._radius, self._cachedWheel, self._cachedRing)

    def setMode(self, mode):
        if mode not in ('Wheel', 'Ring', 'Square', 'Triangle'):
            return
        self._mode, self._dragging, self._region = mode, False, None
        self.update()

    def _triangleWeights(self, pos):
        hue = (pos.x() - 63.0) / 111.0
        white = (1.0 - hue + (pos.y() - 100.0) / 64.086) / 2.0
        return hue, white, 1.0 - hue - white

    def _trianglePixmap(self):
        if self._triangleMasks is None:
            images = [QtGui.QImage(200, 200, QtGui.QImage.Format_ARGB32_Premultiplied) for _ in range(2)]
            for image in images:
                image.fill(0)
            for y in range(36, 165):
                for x in range(63, 175):
                    hue, white, black = self._triangleWeights(QtCore.QPointF(x, y))
                    if min(hue, white, black) >= 0.0:
                        a, b = int(hue * 255), int(white * 255)
                        images[0].setPixel(x, y, a << 24)
                        images[1].setPixel(x, y, (b << 24) | (b << 16) | (b << 8) | b)
            self._triangleMasks = [QtGui.QPixmap.fromImage(image) for image in images]
        if self._triangleTint != self._hue:
            self._triangleColor = QtGui.QPixmap(200, 200)
            self._triangleColor.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(self._triangleColor)
            painter.fillRect(self._triangleColor.rect(), QtGui.QColor.fromHsvF(self._hue, 1.0, 1.0))
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_DestinationIn)
            painter.drawPixmap(0, 0, self._triangleMasks[0])
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
            painter.drawPixmap(0, 0, self._triangleMasks[1])
            painter.end()
            self._triangleTint = self._hue
        return self._triangleColor

    def _svPosition(self):
        if self._mode == 'Triangle':
            hue, white = self._sat * self._value, (1.0 - self._sat) * self._value
            return QtCore.QPointF(63 + 111 * hue, 100 + 64.086 * (2 * white + hue - 1))
        rect = self._square if self._mode == 'Square' else self._innerSquare
        return QtCore.QPointF(rect.left() + self._sat * rect.width(), rect.bottom() - self._value * rect.height())

    def _marker(self, painter, pos):
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 3))
        painter.drawEllipse(pos, 6, 6)
        painter.setPen(QtGui.QPen(QtCore.Qt.white, 2))
        painter.drawEllipse(pos, 5, 5)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.scale(self.width() / 200.0, self.height() / 200.0)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        angle = self._hue * 2.0 * math.pi
        if self._mode == 'Wheel':
            painter.drawPixmap(0, 0, self._cachedWheel)
            distance = self._sat * self._radius
            self._selectorPos = QtCore.QPointF(100 - math.sin(angle) * distance, 100 + math.cos(angle) * distance)
            self._marker(painter, self._selectorPos)
            return
        if self._mode in ('Ring', 'Triangle'):
            painter.drawPixmap(0, 0, self._cachedRing)
            huePos = QtCore.QPointF(100 - math.sin(angle) * 87, 100 + math.cos(angle) * 87)
        else:
            gradient = QtGui.QLinearGradient(self._hueStrip.topLeft(), self._hueStrip.topRight())
            for index in range(7):
                gradient.setColorAt(index / 6.0, QtGui.QColor.fromHsv((index * 60) % 360, 255, 255))
            painter.fillRect(self._hueStrip, QtGui.QBrush(gradient))
            huePos = QtCore.QPointF(self._hueStrip.left() + self._hue * self._hueStrip.width(), self._hueStrip.center().y())
        if self._mode == 'Triangle':
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtCore.Qt.black)
            painter.drawPolygon(self._triangle)
            painter.drawPixmap(0, 0, self._trianglePixmap())
        else:
            rect = self._square if self._mode == 'Square' else self._innerSquare
            painter.fillRect(rect, QtGui.QColor.fromHsvF(self._hue, 1.0, 1.0))
            white = QtGui.QLinearGradient(rect.topLeft(), rect.topRight())
            white.setColorAt(0, QtGui.QColor(255, 255, 255))
            white.setColorAt(1, QtGui.QColor(255, 255, 255, 0))
            painter.fillRect(rect, QtGui.QBrush(white))
            black = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
            black.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
            black.setColorAt(1, QtGui.QColor(0, 0, 0))
            painter.fillRect(rect, QtGui.QBrush(black))
        self._selectorPos = self._svPosition()
        self._marker(painter, huePos)
        self._marker(painter, self._selectorPos)

    def _eventPos(self, event):
        return QtCore.QPointF(event.x() * 200.0 / self.width(), event.y() * 200.0 / self.height())

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        self.setFocus(QtCore.Qt.MouseFocusReason)
        pos = self._eventPos(event)
        distance = math.hypot(pos.x() - 100, pos.y() - 100)
        if self._mode == 'Wheel':
            self._region = 'wheel'
        elif self._mode == 'Square':
            self._region = 'hue' if self._hueStrip.contains(pos) else 'sv' if self._square.contains(pos) else None
        elif 78 <= distance <= self._radius:
            self._region = 'hue'
        elif self._mode == 'Ring' and self._innerSquare.contains(pos):
            self._region = 'sv'
        elif self._mode == 'Triangle' and min(self._triangleWeights(pos)) >= 0.0:
            self._region = 'sv'
        else:
            self._region = None
        if self._region is not None:
            self._dragging = True
            self._pick(pos)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._pick(self._eventPos(event))

    def mouseReleaseEvent(self, event):
        if self._dragging and event.button() == QtCore.Qt.LeftButton:
            self._pick(self._eventPos(event))
            self._dragging, self._region = False, None
            self.colorReleased.emit(self._color)

    def _pick(self, pos):
        previous = self._hue, self._sat, self._value
        clamp = lambda value: max(0.0, min(1.0, value))
        if self._region in ('wheel', 'hue'):
            if self._mode == 'Square':
                self._hue = min(clamp((pos.x() - self._hueStrip.left()) / self._hueStrip.width()), 0.999999)
            else:
                self._hue = (math.atan2(100 - pos.x(), pos.y() - 100) / (2 * math.pi)) % 1.0
                if self._region == 'wheel':
                    self._sat = clamp(math.hypot(pos.x() - 100, pos.y() - 100) / self._radius)
        elif self._mode == 'Triangle':
            weights = [max(0.0, weight) for weight in self._triangleWeights(pos)]
            total = sum(weights)
            self._value = (weights[0] + weights[1]) / total
            self._sat = weights[0] / (weights[0] + weights[1]) if self._value else self._sat
        else:
            rect = self._square if self._mode == 'Square' else self._innerSquare
            self._sat = clamp((pos.x() - rect.left()) / rect.width())
            self._value = clamp((rect.bottom() - pos.y()) / rect.height())
        if previous != (self._hue, self._sat, self._value):
            self._color = QtGui.QColor.fromHsvF(self._hue, self._sat, self._value)
            self.update()
            self.colorChanged.emit(self._color)

    def setSelectorFromColor(self, color):
        hue, saturation, value, alpha = color.getHsvF()
        before = self._hue, self._sat, self._value
        if hue >= 0:
            self._hue = hue
        if value > 0:
            self._sat = saturation
        self._value, self._color = value, QtGui.QColor(color)
        if before != (self._hue, self._sat, self._value):
            self.update()


# -- Brightness Slider --- #
class BrightnessSlider(QtGui.QWidget):
    valueChanged = QtCore.Signal(float)
    valueReleased = QtCore.Signal(float)

    def __init__(self, parent=None):
        super(BrightnessSlider, self).__init__(parent)
        self.setFixedSize(16, 180)
        self.setCursor(QtCore.Qt.SizeVerCursor)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self._value = 1.0
        self._dragging = False
        self._color = QtGui.QColor(255, 255, 255)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        area = self.rect().adjusted(3, 4, -3, -5)
        grad = QtGui.QLinearGradient(0, area.top(), 0, area.bottom())
        grad.setColorAt(0, self._color)
        grad.setColorAt(1, QtGui.QColor(0, 0, 0))
        p.fillRect(area, QtGui.QBrush(grad))
        y = int(area.top() + (1 - self._value) * (area.height() - 1))
        p.setPen(QtGui.QPen(QtCore.Qt.black, 4))
        p.drawLine(0, y, self.width(), y)
        p.setPen(QtGui.QPen(QtCore.Qt.white, 2))
        p.drawLine(0, y, self.width(), y)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.setFocus(QtCore.Qt.MouseFocusReason)
            self._dragging = True
            self._set(event.pos().y())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._set(event.pos().y())

    def mouseReleaseEvent(self, event):
        if self._dragging and event.button() == QtCore.Qt.LeftButton:
            self._set(event.pos().y())
            self._dragging = False
            self.valueReleased.emit(self._value)

    def _set(self, y):
        value = 1 - max(0.0, min(1.0, (float(y) - 4) / (self.height() - 9)))
        if value != self._value:
            self.setValue(value)
            self.valueChanged.emit(value)

    def setValue(self, value):
        value = max(0.0, min(1.0, value))
        if value != self._value:
            self._value = value
            self.update()

    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.update()

    def getValue(self):
        return self._value


# -- Blender-styled slider bar --- #
class _SliderBar(QtGui.QWidget):
    def __init__(self, owner):
        super(_SliderBar, self).__init__(owner)
        self._slider = owner
        self._editor = None
        self.setFixedHeight(20)
        self.setMinimumWidth(90)
        self.setCursor(QtCore.Qt.SizeHorCursor)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    def paintEvent(self, event):
        slider = self._slider
        painter = QtGui.QPainter(self)
        width, height = self.width(), self.height()
        painter.fillRect(self.rect(), QtGui.QColor(45, 45, 45))
        span = max(slider._softMax - slider._min, 0.001)
        fraction = max(0.0, min(1.0, (slider._value - slider._min) / span))
        if fraction:
            painter.fillRect(0, 0, int(fraction * width), height, QtGui.QColor(60, 90, 120, 180))
        painter.setPen(QtGui.QColor(80, 80, 80))
        painter.drawRect(0, 0, width - 1, height - 1)
        painter.setPen(QtGui.QColor(220, 220, 220))
        painter.drawText(self.rect(), QtCore.Qt.AlignCenter, slider._format % slider._value)

    def mousePressEvent(self, event):
        if not self.isEnabled() or not getattr(self._slider, '_editAllowed', lambda: True)():
            event.ignore()
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.setFocus(QtCore.Qt.MouseFocusReason)
            self._slider._dragging = True
            self._slider._dragStartX = event.globalX()
            self._slider._dragStartVal = self._slider._value

    def mouseMoveEvent(self, event):
        slider = self._slider
        if not self.isEnabled() or not slider._dragging:
            return
        dx = event.globalX() - slider._dragStartX
        width = float(max(self.width(), 160))
        span = slider._softMax - slider._min
        distance = abs(dx)
        if distance <= span * width:
            delta = distance / width * span
        else:
            delta = span + ((distance - span * width) / width) ** 2 * (slider._max - slider._softMax)
        raw = slider._dragStartVal + (delta if dx >= 0 else -delta)
        value = max(slider._min, min(slider._max, raw))
        if raw != value:
            slider._dragStartX = event.globalX()
            slider._dragStartVal = value
        if value != slider._value:
            slider._value = value
            self.update()
            slider.valueChanged.emit(value)

    def mouseReleaseEvent(self, event):
        if self._slider._dragging and event.button() == QtCore.Qt.LeftButton:
            self._slider._dragging = False
            self._slider.valueReleased.emit(self._slider._value)

    def mouseDoubleClickEvent(self, event):
        if not self.isEnabled() or not getattr(self._slider, '_editAllowed', lambda: True)():
            event.ignore()
            return
        if event.button() != QtCore.Qt.LeftButton or self._editor is not None:
            return
        slider = self._slider
        slider._dragging = False
        slider._editing = True
        edit = self._editor = QtGui.QLineEdit(slider._format % slider._value, self)
        edit.setAlignment(QtCore.Qt.AlignCenter)
        edit.setGeometry(self.rect())
        edit.show()
        edit.setFocus()
        edit.selectAll()

        def commit():
            if self._editor is not edit:
                return
            self._editor = None
            slider._editing = False
            try:
                if not self.isEnabled() or not getattr(slider, '_editAllowed', lambda: True)():
                    return
                value = float(edit.text())
                if not math.isnan(value) and not math.isinf(value):
                    slider._value = max(slider._min, min(slider._max, value))
                    self.update()
                    slider.valueChanged.emit(slider._value)
                    slider.valueReleased.emit(slider._value)
            except ValueError:
                pass
            finally:
                edit.deleteLater()

        edit.editingFinished.connect(commit)


_historyIcons = None


def historyIcons():
    global _historyIcons
    if _historyIcons is None:
        _historyIcons = []
        for redo in (False, True):
            pixmap = QtGui.QPixmap(18, 18)
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            if redo:
                painter.translate(18, 0)
                painter.scale(-1, 1)
            painter.setPen(QtGui.QPen(QtGui.QColor('#dddddd'), 1.7))
            painter.drawLine(4, 9, 14, 9)
            painter.drawLine(4, 9, 8, 5)
            painter.drawLine(4, 9, 8, 13)
            painter.end()
            _historyIcons.append(QtGui.QIcon(pixmap))
    return _historyIcons


_clipboardIcons = None


def clipboardIcons():
    global _clipboardIcons
    if _clipboardIcons is None:
        icons = []
        for paste in (False, True):
            pixmap = QtGui.QPixmap(16, 16)
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            painter.setPen(QtGui.QPen(QtGui.QColor('#dddddd'), 1))
            painter.setBrush(QtGui.QColor('#303030'))
            if paste:
                painter.drawRect(3, 3, 10, 11)
                painter.drawRect(5, 1, 6, 4)
                painter.drawLine(6, 8, 10, 8)
                painter.drawLine(6, 11, 10, 11)
            else:
                painter.drawRect(6, 1, 8, 10)
                painter.drawRect(2, 5, 8, 10)
            painter.end()
            icons.append(QtGui.QIcon(pixmap))
        _clipboardIcons = icons
    return _clipboardIcons


_selectorIcons = None


def selectorIcons(wheel):
    global _selectorIcons
    if _selectorIcons is None:
        _selectorIcons = dict((name, QtGui.QIcon(pixmap.scaled(20, 20,
            QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))) for name, pixmap in
            (('Wheel', wheel._cachedWheel), ('Ring', wheel._cachedRing)))
        for name in ('Square', 'Triangle'):
            pixmap = QtGui.QPixmap(20, 20)
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            gradient = QtGui.QLinearGradient(2, 2, 18, 18)
            for position, color in ((0, '#ffffff'), (0.5, '#408cff'), (1, '#111111')):
                gradient.setColorAt(position, QtGui.QColor(color))
            painter.setBrush(QtGui.QBrush(gradient))
            painter.setPen(QtGui.QPen(QtGui.QColor('#dddddd'), 1))
            if name == 'Square':
                painter.drawRect(QtCore.QRectF(2, 2, 16, 16))
            else:
                painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(10, 1),
                    QtCore.QPointF(1, 18), QtCore.QPointF(19, 18)]))
            painter.end()
            _selectorIcons[name] = QtGui.QIcon(pixmap)
    return _selectorIcons


# -- Property slider (label + bar) --- #
class PropertySliders(QtGui.QWidget):
    valueChanged = QtCore.Signal(float)
    valueReleased = QtCore.Signal(float)

    def __init__(self, label, minVal, maxVal, defaultVal, decimals=2, parent=None):
        super(PropertySliders, self).__init__(parent)
        self._min, self._max, self._softMax = float(minVal), 250.0, float(maxVal)
        self._value = float(defaultVal)
        self._format = '%%.%df' % decimals
        self._dragging = self._editing = False
        self._dragStartX = self._dragStartVal = 0
        lay = QtGui.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self._lbl = QtGui.QLabel(label)
        self._lbl.setMinimumWidth(110)
        self._bar = _SliderBar(self)
        lay.addWidget(self._lbl, 1)
        lay.addWidget(self._bar, 1)
        self._copyButton, self._pasteButton = QtGui.QToolButton(), QtGui.QToolButton()
        for button, icon, tip, callback in zip(
                (self._copyButton, self._pasteButton), clipboardIcons(),
                ('Copy value', 'Paste value'), (self._copyValue, self._pasteValue)):
            button.setObjectName('ClipboardButton')
            button.setFixedSize(20, 20)
            button.setIcon(icon)
            button.setIconSize(QtCore.QSize(16, 16))
            button.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
            button.setToolTip(tip)
            button.setAccessibleName(tip + ': ' + label)
            button.setCursor(QtCore.Qt.PointingHandCursor)
            button.clicked.connect(callback)
            lay.addWidget(button)

    def _copyValue(self):
        QtGui.QApplication.clipboard().setText(repr(self._value))

    def _pasteValue(self):
        if self._dragging or self._editing:
            return
        try:
            value = float(QtGui.QApplication.clipboard().text().strip())
            if math.isnan(value) or math.isinf(value):
                raise ValueError
        except (ValueError, TypeError):
            QtGui.QToolTip.showText(self._pasteButton.mapToGlobal(QtCore.QPoint(0, 20)),
                                   'Copy a numeric value first.', self._pasteButton)
            return
        value = max(self._min, min(self._max, value))
        if value != self._value:
            self.setValueSilent(value)
            self.valueChanged.emit(self._value)
            self.valueReleased.emit(self._value)

    def getValue(self):
        return self._value

    def setValueSilent(self, value):
        if self._dragging or self._editing:
            return
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return
        self._min, self._max = min(self._min, value), max(self._max, value)
        if value != self._value:
            self._value = value
            self._bar.update()

    def setTip(self, text):
        self._lbl.setToolTip(text)
        self._bar.setToolTip(text)


# -- Collapsible sections --- #
class CollapsibleSection(QtGui.QFrame):
    def __init__(self, title, parent=None, expanded=False):
        super(CollapsibleSection, self).__init__(parent)
        self.setObjectName('Section')
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 4)
        layout.setSpacing(3)
        self._btn = QtGui.QToolButton()
        self._btn.setText(title)
        self._btn.setCheckable(True)
        self._btn.setChecked(expanded)
        self._btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._btn.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        self._body = QtGui.QWidget()
        self._bodyLayout = QtGui.QVBoxLayout(self._body)
        self._bodyLayout.setContentsMargins(0, 0, 0, 0)
        self._bodyLayout.setSpacing(3)
        layout.addWidget(self._btn)
        layout.addWidget(self._body)
        self._btn.toggled.connect(self._toggle)
        self._toggle(expanded)

    def _toggle(self, expanded):
        self._body.setVisible(expanded)
        self._btn.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)

    def addWidget(self, widget):
        self._bodyLayout.addWidget(widget)


def readSfmControlDefault(target, name):
    control = target.FindControl(name)
    if control is None:
        group = target.GetRootControlGroup()
        control = group.FindControlByName(name, True) if group is not None else None
    if control is None:
        return None
    try:
        value = float(control.GetValue('defaultValue'))
        if not math.isnan(value) and not math.isinf(value):
            return value
    except Exception:
        pass
    try:
        channel = getattr(control, 'channel', None)
        log = channel.log if channel is not None else None
        if log is not None and log.HasDefaultValue():
            value = float(log.GetDefaultValue())
            if not math.isnan(value) and not math.isinf(value):
                return value
    except Exception:
        pass
    return None


# -- Main window --- #
class ColorWheelWindow(QtGui.QWidget):
    def __init__(self, animSet):
        super(ColorWheelWindow, self).__init__()
        self.targetAnimSet = animSet
        self._fixedTargetWindow = True
        self._targetHandle = animSet.GetHandle()
        self._targetId = str(animSet.GetId())
        self._documentId = str(sfmApp.GetDocumentRoot().GetId())
        self._targetLost = self._closing = self._engineBusy = False
        self.setObjectName(InternalName + '_editor')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self._channels, self._sliders, self._checks = {}, {}, {}
        self._lastSnapshot, self._pending, self._pendingTargets = {}, {}, {}
        self._undoHistory, self._redoHistory = [], []
        self._historyBefore = None
        self._timelineEditor, self._editorBlocked = None, False
        self._historyReplaying = self._historySkipped = False
        self._cacheTicks = 0
        self._loading = False
        self.currentR = self.currentG = self.currentB = self.brightnessScale = 1.0
        self.setWindowTitle(ProductName)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setMinimumSize(290, 560)
        self.resize(300, 680)
        self.setStyleSheet('''
            QWidget { color: #dddddd; font-size: 11px; }
            ColorWheelWindow, QScrollArea, QWidget#Content { background: #282828; }
            QScrollArea { border: none; }
            QFrame#Section { background: #303030; border: 1px solid #484848; border-radius: 2px; }
            QFrame#Separator { border: none; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #303030, stop:0.2 #5b5b5b, stop:0.8 #5b5b5b, stop:1 #303030); }
            QToolButton { border: none; font-weight: bold; padding: 1px 0; text-align: left; }
            QToolButton:hover { color: #ffffff; }
            QToolButton#ClipboardButton { background: #383838; border: 1px solid #555555; border-radius: 2px; padding: 0; }
            QToolButton#ClipboardButton:hover { background: #494949; border-color: #888888; }
            QToolButton#HistoryButton { background: #383838; border: 1px solid #555555; border-radius: 3px; padding: 0; }
            QToolButton#HistoryButton:hover:enabled { background: #494949; border-color: #888888; }
            QToolButton#HistoryButton:disabled { background: #2e2e2e; border-color: #3c3c3c; }
            QLineEdit { background: #202020; border: 1px solid #555555; border-radius: 3px; padding: 2px; }
            QLineEdit:focus { border-color: #888888; }
            QDoubleSpinBox { background: #202020; border: 1px solid #555555; border-radius: 3px; padding: 2px; }
            QDoubleSpinBox QLineEdit { border: none; padding: 0; }
            QLineEdit[invalid="true"] { border-color: #de8686; }
            QPushButton { background: #3c3c3c; border: 1px solid #606060; border-radius: 3px; padding: 3px 7px; }
            QPushButton:hover { background: #494949; border-color: #888888; color: #ffffff; }
            QPushButton:checked { background: #3c4650; border-color: #718095; color: #dddddd; }
            QLabel#Muted { color: #aaaaaa; font-size: 11px; }
            QScrollBar:vertical { background: #282828; width: 10px; margin: 2px; }
            QScrollBar::handle:vertical { background: #666666; min-height: 24px; border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            QCheckBox:hover { color: #ffffff; }
            QWidget:disabled { color: #777777; }
        ''')
        outer = QtGui.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        # -- Title + undo/redo --- #
        title = QtGui.QLabel('Color Wheel')
        title.setStyleSheet('font-size: 14px; font-weight: bold;')
        header = QtGui.QHBoxLayout()
        header.setContentsMargins(8, 6, 8, 0)
        header.addWidget(title, 1)
        self.undoButton, self.redoButton = QtGui.QToolButton(), QtGui.QToolButton()
        for button, icon, tip, callback in zip(
                (self.undoButton, self.redoButton), historyIcons(),
                ('Undo script edit', 'Redo script edit'), (self._undoScript, self._redoScript)):
            button.setObjectName('HistoryButton')
            button.setFixedSize(26, 24)
            button.setIcon(icon)
            button.setIconSize(QtCore.QSize(18, 18))
            button.setToolTip(tip)
            button.setAccessibleName(tip)
            button.clicked.connect(callback)
            header.addWidget(button)
        self._updateHistoryButtons()
        outer.addLayout(header)
        self._editingLabel = QtGui.QLabel()
        self._editingLabel.setObjectName('Muted')
        self._editingLabel.setContentsMargins(8, 0, 8, 3)
        outer.addWidget(self._editingLabel)
        self._content = QtGui.QWidget()
        self._content.setObjectName('Content')
        contentLayout = QtGui.QVBoxLayout(self._content)
        contentLayout.setContentsMargins(8, 0, 8, 0)
        contentLayout.setSpacing(8)
        outer.addWidget(self._content, 1)
        attributes = QtGui.QWidget()
        attributes.setObjectName('Content')
        layout = QtGui.QVBoxLayout(attributes)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        scroll = self._attributeScroll = QtGui.QScrollArea()
        scroll.setMinimumSize(260, 140)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setWidget(attributes)

        colorSection = self._colorSection = CollapsibleSection('Color', expanded=True)
        colorSection.setMinimumWidth(250)
        colorSection.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
        contentLayout.addWidget(colorSection)
        self.wheel = ColorPicker()
        self.brightnessSlider = BrightnessSlider()
        self.wheel.colorChanged.connect(self._onPickerColorChanged)
        self.wheel.colorReleased.connect(self.onColorReleased)
        self.brightnessSlider.valueChanged.connect(self.onIntensityChanged)
        self.brightnessSlider.valueReleased.connect(self._flushPending)
        wheelRow = QtGui.QHBoxLayout()
        wheelRow.addStretch()
        wheelRow.addWidget(self.wheel)
        wheelRow.addSpacing(6)
        wheelRow.addWidget(self.brightnessSlider)
        wheelRow.addStretch()
        colorSection._bodyLayout.addLayout(wheelRow)
        controls = QtGui.QWidget()
        controls.setFixedWidth(234)
        controlsLayout = QtGui.QVBoxLayout(controls)
        controlsLayout.setContentsMargins(0, 0, 0, 0)
        controlsLayout.setSpacing(4)
        colorSection._bodyLayout.addWidget(controls, 0, QtCore.Qt.AlignHCenter)
        brightnessRow = QtGui.QHBoxLayout()
        brightnessRow.addWidget(self._separator(), 1)
        self._brightnessLabel = QtGui.QLabel('100%')
        brightnessRow.addWidget(self._brightnessLabel, 0, QtCore.Qt.AlignRight)
        controlsLayout.addLayout(brightnessRow)
        # -- HEX code and copy button --- #
        hexRow = QtGui.QHBoxLayout()
        hexRow.setSpacing(4)
        self._swatch = QtGui.QLabel()
        self._swatch.setFixedSize(18, 18)
        self.hexEdit = QtGui.QLineEdit('#FFFFFF')
        self.hexEdit.setMaxLength(7)
        self.hexEdit.setFixedHeight(22)
        self.hexEdit.editingFinished.connect(self._commitHex)
        self.hexEdit.textEdited.connect(self._clearHexError)
        self.copyHexBtn = QtGui.QPushButton('Copy HEX')
        self.copyHexBtn.setFixedHeight(22)
        self.copyHexBtn.clicked.connect(self.copyHex)
        hexRow.addWidget(self._swatch)
        hexRow.addWidget(self.hexEdit, 1)
        hexRow.addWidget(self.copyHexBtn)
        controlsLayout.addLayout(hexRow)
        controlsLayout.addSpacing(4)
        shapeRow, self._shapeButtons = self._optionRow(('Wheel', 'Ring', 'Square', 'Triangle'),
            self._setPickerShape, selectorIcons(self.wheel))
        controlsLayout.addLayout(shapeRow)
        modelRow, self._spaceButtons = self._optionRow(('RGB', 'HSV', 'HSL'), self._setColorSpace)
        controlsLayout.addLayout(modelRow)
        controlsLayout.addWidget(self._separator())
        self._componentLabels, self._componentEdits = [], []
        componentRow = QtGui.QHBoxLayout()
        componentRow.setSpacing(6)
        componentRow.addStretch()
        for index in range(3):
            column = QtGui.QVBoxLayout()
            column.setSpacing(2)
            label = QtGui.QLabel()
            label.setObjectName('Muted')
            label.setFixedHeight(12)
            label.setAlignment(QtCore.Qt.AlignCenter)
            edit = QtGui.QDoubleSpinBox()
            edit.setFixedSize(74, 22)
            edit.setAlignment(QtCore.Qt.AlignCenter)
            edit.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
            edit.setKeyboardTracking(False)
            edit.valueChanged.connect(self._commitColorComponents)
            self._componentLabels.append(label)
            self._componentEdits.append(edit)
            column.addWidget(label)
            column.addWidget(edit)
            componentRow.addLayout(column)
        componentRow.addStretch()
        controlsLayout.addLayout(componentRow)
        self._setColorSpace('RGB')
        self._addDefaultButton(contentLayout)
        contentLayout.addWidget(scroll, 1)

        # -- Properties Sections --- #
        groups = (
            # -- Intensity --- #
            ('Intensity', (
                ('intensity', 'Intensity', 1, 'Controls how bright the light is.'),
                ('ambientIntensity', 'ambientIntensity', 0.25, 'Native ambient-fill control. Visible effect depends on shader support in classic SFM.'),)),
            # -- Radius --- #
            ('Radius', (
                ('radius', 'Radius', 1, 'Mimics a larger light source, softens shadows.'),)),
            # -- Field of View --- #
            ('Field of View', (
                ('horizontalFOV', 'Horizontal FOV', 1, 'The horizontal width of the light cone.'),
                ('verticalFOV', 'Vertical FOV', 1, 'The vertical width of the light cone.'),)),
            # -- Shadows --- #
            ('Shadows', (
                ('shadowFilterSize', 'ShadowFilterSize', 1, 'Softens shadow edges.'),
                ('shadowAtten', 'ShadowAtten', 0, 'Controls shadow darkness.'),
                ('shadowDepthBias', 'shadowDepthBias', 0, 'Offsets shadow rendering.'),
                ('shadowSlopeScaleDepthBias', 'shadowSlopeScale', 1, 'Narrows shadows at base.'),)),
            # -- Distance --- #
            ('Distance', (
                ('minDistance', 'minDistance', 0, 'Distance at which the light starts.'),
                ('maxDistance', 'maxDistance', 1, 'Distance at which the light ends.'),
                ('farZAtten', 'farZAtten', 1, 'Far distance attenuation falloff.'),)),
            # -- Attenuation --- #
            ('Attenuation', (
                ('constantAttenuation', 'Constant', 0, 'Brightness is constant across range.'),
                ('linearAttenuation', 'Linear', 0, 'Brightness drops steadily with distance.'),
                ('quadraticAttenuation', 'Quadratic', 1, 'Brightness drops faster with distance.'),)),
            # -- Volumetrics --- #
            ('Volumetrics', (
                ('volumetricIntensity', 'volumetricIntensity', 1, 'Intensity of the volumetric effect.'),
                ('noiseStrength', 'noiseStrength', 0, 'Volumetric noise strength.'),)),
            # -- UberLights --- #
            ('UberLights', (
                ('width', 'width', 1, 'Width of the uberlight shape.'),
                ('edgeWidth', 'edgeWidth', 1, 'Softness of the uberlight width edges.'),
                ('height', 'height', 1, 'Height of the uberlight shape.'),
                ('edgeHeight', 'edgeHeight', 1, 'Softness of the uberlight height edges.'),)))
        toggles = {
            'Shadows': ('castsShadows', 'Disable Shadows', 'Toggles shadow casting on this light.', True),
            'Volumetrics': ('volumetric', 'Enable Volumetrics', 'Enables volumetric lighting (god rays).', False),
            'UberLights': ('uberlight', 'UberLight', 'Enables UberLight on this light.', False),
        }
        for title, properties in groups:
            section = CollapsibleSection(title, expanded=title in ('Intensity', 'Radius', 'Field of View'))
            if title in toggles:
                name, label, tip, invert = toggles[title]
                check = QtGui.QCheckBox(label)
                check.setToolTip(tip)
                check.stateChanged.connect(lambda state, n=name, i=invert:
                    self._queueEdit('__b_' + n, not bool(state) if i else bool(state), True))
                self._checks[name] = check
                section.addWidget(check)
            for name, label, default, tip in properties:
                slider = PropertySliders(label, 0, 1, default)
                if name in ('noiseStrength', 'ambientIntensity'):
                    slider._max = 1.0
                slider._editAllowed = self._editingAllowed
                slider.setTip(tip)
                slider.valueChanged.connect(lambda value, n=name: self._queueEdit(n, value))
                slider.valueReleased.connect(self._flushPending)
                self._sliders[name] = slider
                section.addWidget(slider)
            layout.addWidget(section)
        # -- Credits --- #
        hint = QtGui.QLabel('by Aftre')
        hint.setStyleSheet('color: #777777;')
        hint.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        hint.setContentsMargins(8, 0, 8, 4)
        outer.addWidget(hint)
        layout.addStretch()
        self._applyTimer = QtCore.QTimer(self)
        self._applyTimer.setSingleShot(True)
        self._applyTimer.setInterval(33)
        self._applyTimer.timeout.connect(self._flushPending)
        self._playheadTimer = QtCore.QTimer(self)
        self._playheadTimer.setInterval(100)
        self._playheadTimer.timeout.connect(self._pollPlayhead)
        pos = QtCore.QSettings('Aftre', 'ColorWheel').value('windowPos')
        if isinstance(pos, QtCore.QPoint):
            self.move(pos)
        for widget in self.findChildren(QtGui.QAbstractButton):
            widget.setCursor(QtCore.Qt.PointingHandCursor)
            widget.setAttribute(QtCore.Qt.WA_Hover, True)
        self._updateColorUi()
        self._pollPlayhead()

    def _addDefaultButton(self, layout):
        button = QtGui.QPushButton('Set to Default')
        button.setMinimumHeight(24)
        button.setToolTip('Restore this light to its SFM default values. One undo action.')
        button.clicked.connect(lambda: self._queueEdit('__defaults', True, True))
        self._defaultButton = button
        layout.addWidget(button)

    def _readLightDefaults(self, target):
        edits, missing = {}, []
        for name in _POLL_CHANNELS:
            if name not in self._channels:
                continue
            value = readSfmControlDefault(target, name)
            if value is None:
                missing.append(name)
            else:
                edits[name] = value
        if missing:
            raise ValueError('SFM defaultValue is unavailable for: ' + ', '.join(missing))
        for name, fallback in zip(_BOOL_NAMES, (True, False, False)):
            if readLightBoolean(target.light, name) is not None:
                value = readSfmControlDefault(target, name)
                edits['__b_' + name] = bool(value) if value is not None else fallback
        return edits

    def _separator(self):
        line = QtGui.QFrame()
        line.setObjectName('Separator')
        line.setFixedHeight(1)
        return line

    def _optionRow(self, names, callback, icons=None):
        row, buttons = QtGui.QHBoxLayout(), {}
        row.setSpacing(6)
        row.addStretch()
        group = QtGui.QButtonGroup(self)
        group.setExclusive(True)
        for name in names:
            button = QtGui.QPushButton('' if icons else name)
            button.setFixedSize(54 if icons else 74, 24)
            button.setToolTip(name)
            button.setAccessibleName(name)
            if icons:
                button.setIcon(icons[name])
                button.setIconSize(QtCore.QSize(18, 18))
            button.setCheckable(True)
            group.addButton(button)
            button.clicked.connect(lambda checked=False, n=name: callback(n))
            buttons[name] = button
            row.addWidget(button)
        row.addStretch()
        buttons[names[0]].setChecked(True)
        return row, buttons

    def _setPickerShape(self, shape):
        self.wheel.setMode(shape)

    def _setColorSpace(self, space):
        self._colorSpace = space
        self._syncColorFields()

    def _syncColorFields(self):
        rgb = tuple(max(0.0, min(value * self.brightnessScale, 1.0))
                    for value in (self.currentR, self.currentG, self.currentB))
        if self._colorSpace == 'RGB':
            values, names = rgb, ('R', 'G', 'B')
        else:
            if self._colorSpace == 'HSV':
                hue, saturation, value = colorsys.rgb_to_hsv(*rgb)
                names = ('H', 'S', 'V')
            else:
                hue, value, saturation = colorsys.rgb_to_hls(*rgb)
                names = ('H', 'S', 'L')
            if saturation == 0.0:
                hue = self.wheel._hue
            if self._colorSpace == 'HSV' and value == 0.0:
                saturation = self.wheel._sat
            values = (hue * 360.0, saturation * 100.0, value * 100.0)
        for index, (label, edit, name, value) in enumerate(zip(
                self._componentLabels, self._componentEdits, names, values)):
            edit.blockSignals(True)
            try:
                if getattr(edit, '_colorFieldSpace', None) != self._colorSpace:
                    label.setText(name)
                    edit.setDecimals(1)
                    edit.setRange(0.0, 1.0 if self._colorSpace == 'RGB' else 359.9 if index == 0 else 100.0)
                    edit.setSingleStep(0.1 if self._colorSpace == 'RGB' else 1.0)
                    edit.setSuffix('' if self._colorSpace == 'RGB' else ' deg' if index == 0 else '%')
                    edit.setToolTip('%s (%s)' % (name, self._colorSpace))
                    edit._colorFieldSpace = self._colorSpace
                if not edit.hasFocus():
                    edit.setValue(value)
            finally:
                edit.blockSignals(False)

    def _commitColorComponents(self, *args):
        if self._loading or self._resolveTarget() is None:
            return
        values = [edit.value() for edit in self._componentEdits]
        if self._colorSpace != 'RGB':
            self.wheel._hue = values[0] / 360.0
            if self._colorSpace == 'HSV':
                self.wheel._sat = values[1] / 100.0
            self.wheel.update()
        if self._colorSpace == 'HSV':
            rgb = colorsys.hsv_to_rgb(values[0] / 360.0, values[1] / 100.0, values[2] / 100.0)
        elif self._colorSpace == 'HSL':
            rgb = colorsys.hls_to_rgb(values[0] / 360.0, values[2] / 100.0, values[1] / 100.0)
        else:
            sender = self.sender()
            if sender in self._componentEdits:
                rgb = [v * self.brightnessScale for v in (self.currentR, self.currentG, self.currentB)]
                index = self._componentEdits.index(sender)
                rgb[index] = values[index]
            else:
                rgb = values
        self._applyRgbComponents(rgb)
        self._flushPending()

    def _onPickerColorChanged(self, color):
        if self._loading or self._resolveTarget() is None:
            return
        self._applyRgbComponents((color.redF(), color.greenF(), color.blueF()))

    def _applyRgbComponents(self, rgb):
        bright = max(rgb)
        self.brightnessScale = bright
        if bright > 0:
            self.currentR, self.currentG, self.currentB = (value / bright for value in rgb)
        else:
            color = QtGui.QColor.fromHsvF(self.wheel._hue, self.wheel._sat, 1.0)
            self.currentR, self.currentG, self.currentB = color.redF(), color.greenF(), color.blueF()
        self._updateColorUi()
        self._applyToLight()

    def present(self):
        self._closing = False
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if self.isVisible() and not self._targetLost:
            self._pollPlayhead()
            if not self._targetLost:
                self._playheadTimer.start()
        else:
            self._playheadTimer.stop()

    def event(self, event):
        if event.type() in (QtCore.QEvent.ShortcutOverride, QtCore.QEvent.KeyPress) and self.isVisible():
            key, modifiers = event.key(), event.modifiers()
            undo = key == QtCore.Qt.Key_Z and modifiers == QtCore.Qt.ControlModifier
            redo = ((key == QtCore.Qt.Key_Y and modifiers == QtCore.Qt.ControlModifier)
                    or (key == QtCore.Qt.Key_Z and modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier)))
            if undo or redo:
                focus = self.focusWidget()
                while isinstance(focus, QtGui.QWidget) and focus is not self:
                    if isinstance(focus, (QtGui.QLineEdit, QtGui.QTextEdit, QtGui.QPlainTextEdit, QtGui.QAbstractSpinBox)):
                        return QtGui.QWidget.event(self, event)
                    focus = focus.parentWidget()
                event.accept()
                if event.type() == QtCore.QEvent.KeyPress and not event.isAutoRepeat():
                    (self.undoButton if undo else self.redoButton).click()
                return True
        return QtGui.QWidget.event(self, event)

    def showEvent(self, event):
        QtGui.QWidget.showEvent(self, event)
        if hasattr(self, '_playheadTimer') and not self._targetLost:
            self._closing = False
            self._pollPlayhead()
            if not self._targetLost:
                self._playheadTimer.start()

    def hideEvent(self, event):
        if hasattr(self, '_playheadTimer'):
            self._cancelPending()
            self._playheadTimer.stop()
        QtGui.QWidget.hideEvent(self, event)

    def closeEvent(self, event):
        self._closing = True
        self._cancelPending()
        self._playheadTimer.stop()
        QtCore.QSettings('Aftre', 'ColorWheel').setValue('windowPos', self.pos())
        QtGui.QWidget.closeEvent(self, event)

    def _stopInteractions(self):
        self.wheel._dragging = False
        self.brightnessSlider._dragging = False
        for slider in self._sliders.values():
            slider._dragging = slider._editing = False
            editor, slider._bar._editor = slider._bar._editor, None
            if editor is not None and shiboken.isValid(editor):
                editor.blockSignals(True)
                editor.hide()
                editor.deleteLater()

    def _cancelPending(self):
        self._stopInteractions()
        self._clearHistory()
        self._pending.clear()
        self._pendingTargets.clear()
        self._applyTimer.stop()

    def _disableTarget(self):
        self._targetLost = True
        self.targetAnimSet = None
        self._cancelPending()
        self._channels.clear()
        self._playheadTimer.stop()
        self._content.setEnabled(False)
        self._editingLabel.setText('Light unavailable - reopen from Rig')

    def _syncEditorAccess(self, editor):
        blocked = editor not in ('Motion', 'Graph')
        changed = editor != self._timelineEditor or blocked != self._editorBlocked
        self._timelineEditor, self._editorBlocked = editor, blocked
        if not changed:
            return
        self._pending.clear()
        self._pendingTargets.clear()
        self._applyTimer.stop()
        self._stopInteractions()
        self._finishHistory()
        self._content.setEnabled(not blocked)
        self._lastSnapshot = {}
        self._updateHistoryButtons()

    def _editingAllowed(self):
        if self._closing or self._targetLost:
            return False
        editor = timelineEditor()
        self._syncEditorAccess(editor)
        return not self._editorBlocked and not self._targetLost and not self._closing

    def _resolveTarget(self):
        if self._targetLost or self._closing:
            return None
        if self._engineBusy:
            return self.targetAnimSet
        try:
            if not sfmApp.HasDocument():
                self._disableTarget()
                return None
            root = sfmApp.GetDocumentRoot()
            if root is None or str(root.GetId()) != self._documentId:
                self._disableTarget()
                return None
            element = dm.GetElement(self._targetHandle)
            if element is None or str(element.GetId()) != self._targetId:
                self._disableTarget()
                return None
            target = self.targetAnimSet
            if target is None or getattr(target, 'light', None) is None:
                self._disableTarget()
                return None
            name = target.GetName()
            if isinstance(name, str):
                name = name.decode('utf-8', 'replace')
            editor = timelineEditor()
            self._syncEditorAccess(editor)
            label = 'Editing: ' + name
            if self._editorBlocked:
                label += ' (not editable in Clip Editor)' if editor == 'Clip' else ' (timeline editor unavailable)'
            if label != self._editingLabel.text():
                self._editingLabel.setText(label)
            return target
        except Exception as error:
            print('[Color Wheel] Light is no longer available: %s' % error)
            self._disableTarget()
            return None

    def _channel(self, name):
        channel = getChannel(self.targetAnimSet, name)
        if channel is None:
            self._channels.pop(name, None)
            self._cacheTicks = 0
            if name in self._sliders:
                self._sliders[name].setEnabled(False)
        return channel

    def _refreshChannels(self, target):
        root = target.GetRootControlGroup()
        for name in _POLL_CHANNELS:
            try:
                control = target.FindControl(name)
                if control is None and root is not None:
                    control = root.FindControlByName(name, True)
                channel = getattr(control, 'channel', None) if control is not None else None
                if channel is not None:
                    self._channels[name] = True
                else:
                    self._channels.pop(name, None)
            except Exception:
                self._channels.pop(name, None)
            if name in self._sliders:
                self._sliders[name].setEnabled(name in self._channels)

    # -- Load values from current light --- #
    def _pollPlayhead(self):
        if self._loading or self._engineBusy or self._closing or self.window().isMinimized():
            return
        target = self._resolveTarget()
        if target is None:
            return
        dragging = self._historyDragging()
        interval = 33 if dragging else 100
        if self._playheadTimer.interval() != interval:
            self._playheadTimer.setInterval(interval)
        if dragging:
            return
        self._engineBusy = True
        try:
            if self._cacheTicks == 0:
                self._refreshChannels(target)
            self._cacheTicks = (self._cacheTicks + 1) % 30
            time = getSampleTime()
            snapshot = {}
            for name in list(self._channels):
                channel = self._channel(name)
                if channel is not None:
                    try:
                        value = readCurrentChannelValue(channel, time)
                        if not math.isnan(value) and not math.isinf(value):
                            snapshot[name] = value
                    except Exception:
                        self._cacheTicks = 0
            for name in _BOOL_NAMES:
                try:
                    snapshot['__b_' + name] = bool(target.light.GetValue(name))
                except Exception:
                    pass
            self._syncSnapshot(snapshot)
        except Exception as error:
            print('[Color Wheel] Could not read light: %s' % error)
            self._cacheTicks = 0
        finally:
            self._engineBusy = False

    def _syncSnapshot(self, snapshot):
        previous = self._lastSnapshot
        self._loading = True
        try:
            rgb = tuple(snapshot.get(name) for name in _POLL_CHANNELS[:3])
            oldRgb = tuple(previous.get(name) for name in _POLL_CHANNELS[:3])
            if (None not in rgb and rgb != oldRgb and '__color' not in self._pending
                    and not self.wheel._dragging and not self.brightnessSlider._dragging):
                bright = max(max(rgb), 0.0)
                self.currentR, self.currentG, self.currentB = (max(0.0, min(v / max(bright, 0.001), 1.0)) for v in rgb)
                self.brightnessScale = min(bright, 1.0)
                self._updateColorUi()
            for name, slider in self._sliders.items():
                if name in snapshot and name not in self._pending and snapshot[name] != slider.getValue():
                    slider.setValueSilent(snapshot[name])
                if name in self._pending or slider._dragging or slider._editing:
                    if name in previous:
                        snapshot[name] = previous[name]
                    else:
                        snapshot.pop(name, None)
            if '__color' in self._pending or self.wheel._dragging or self.brightnessSlider._dragging:
                for name in _POLL_CHANNELS[:3]:
                    if name in previous:
                        snapshot[name] = previous[name]
                    else:
                        snapshot.pop(name, None)
            for name, check in self._checks.items():
                key = '__b_' + name
                if key in snapshot and check.isChecked() != (not snapshot[key] if name == 'castsShadows' else snapshot[key]):
                    check.blockSignals(True)
                    try:
                        check.setChecked(not snapshot[key] if name == 'castsShadows' else snapshot[key])
                    finally:
                        check.blockSignals(False)
            self._lastSnapshot = snapshot
        finally:
            self._loading = False

    def _historyDragging(self):
        return (self.wheel._dragging or self.brightnessSlider._dragging
                or any(slider._dragging or slider._editing for slider in self._sliders.values()))

    def _updateHistoryButtons(self):
        ready = not (self._closing or self._targetLost or self._editorBlocked or self._engineBusy or self._historyBefore is not None)
        self.undoButton.setEnabled(ready and bool(self._undoHistory))
        self.redoButton.setEnabled(ready and bool(self._redoHistory))

    def _clearHistory(self):
        self._historyBefore = None
        self._historySkipped = False
        self._undoHistory[:] = []
        self._redoHistory[:] = []
        self._updateHistoryButtons()

    def _historyRead(self, target, name):
        # Store Python scalars only; never retain native element or time proxies.
        if name.startswith('__b_'):
            return bool(target.light.GetValue(name[4:]))
        channel = self._channel(name)
        if channel is None:
            raise ValueError('A recorded light control is unavailable.')
        log, layer = channel.log, channel.log.GetLayer(0)
        if layer.GetKeyCount() > 25000:
            raise ValueError('This channel exceeds the script history memory limit.')
        keys = tuple((layer.GetKeyTime(i).GetTenthsOfMS(), float(layer.GetKeyValue(i)))
                     for i in range(layer.GetKeyCount()))
        default = float(log.GetDefaultValue()) if log.HasDefaultValue() else None
        attribute = getChannelInput(channel)
        inputValue = float(attribute.GetValue()) if attribute is not None else None
        return (str(channel.GetId()), str(layer.GetId()), keys, default, inputValue)

    def _captureHistory(self, target, edits):
        if self._historyReplaying or self._historySkipped:
            return
        names = set(edits)
        if '__color' in names:
            names.remove('__color')
            names.update(_POLL_CHANNELS[:3])
        if self._historyBefore is None:
            self._historyBefore = {}
        for name in names:
            if name not in self._historyBefore:
                self._historyBefore[name] = self._historyRead(target, name)
        self._updateHistoryButtons()

    def _finishHistory(self):
        self._historySkipped = False
        if self._historyBefore is None or self._historyReplaying:
            return
        before, self._historyBefore = self._historyBefore, None
        target = self._resolveTarget()
        if target is None:
            return
        try:
            after = dict((name, self._historyRead(target, name)) for name in before)
            if any(not name.startswith('__') and value[:2] != after[name][:2] for name, value in before.items()):
                self._clearHistory()
                print('[Color Wheel] Script history cleared: a channel was replaced during the edit.')
                return
            before = dict((name, value) for name, value in before.items() if value != after[name])
            if before:
                after = dict((name, after[name]) for name in before)
                self._undoHistory.append((before, after))
                self._redoHistory[:] = []
                # Bound memory for long editing sessions and densely animated lights.
                def cost(entry):
                    return sum(len(v[2]) for side in entry for n, v in side.items() if not n.startswith('__'))
                total = sum(cost(entry) for entry in self._undoHistory)
                while self._undoHistory and (len(self._undoHistory) > 100 or total > 50000):
                    total -= cost(self._undoHistory.pop(0))
        except Exception as error:
            self._clearHistory()
            print('[Color Wheel] Script history cleared: %s' % error)
        self._updateHistoryButtons()

    def _validateWriteTarget(self):
        if timelineEditor() not in ('Motion', 'Graph'):
            raise ValueError('Light editing is unavailable in Clip Editor.')
        root = sfmApp.GetDocumentRoot() if sfmApp.HasDocument() else None
        element = dm.GetElement(self._targetHandle) if root is not None else None
        if (self._closing or root is None or str(root.GetId()) != self._documentId
                or element is None or str(element.GetId()) != self._targetId):
            self._disableTarget()
            raise ValueError('The Rig light or document closed during the edit.')

    def _historyWrite(self, target, name, state):
        if name.startswith('__b_'):
            target.light.SetValue(name[4:], state)
            return
        channel = self._channel(name)
        log, layer = channel.log, channel.log.GetLayer(0)
        keys, default = state[2:4]
        if (layer.GetKeyCount() != len(keys) or any(
                layer.GetKeyTime(i).GetTenthsOfMS() != ticks for i, (ticks, value) in enumerate(keys))):
            raise ValueError('The light samples changed before history could be restored.')
        for i, (ticks, value) in enumerate(keys):
            if layer.GetKeyValue(i) != value:
                layer.SetKeyValue(i, value)
        if default is not None:
            log.SetDefaultValue(default)
        elif log.HasDefaultValue():
            log.ClearDefaultValue()
        if state[4] is not None:
            attribute = getChannelInput(channel)
            if attribute is None:
                raise ValueError('The recorded light input is unavailable.')
            attribute.SetValue(state[4])
        if hasattr(channel, 'Play'):
            channel.Play()

    def _undoScript(self):
        self._replayHistory(False)

    def _redoScript(self):
        self._replayHistory(True)

    def _replayHistory(self, redo):
        if not self._engineBusy and not self._editingAllowed():
            return
        if self._engineBusy or self._closing or self._targetLost or self._historyDragging():
            return
        self._flushPending()
        stack, opposite = (self._redoHistory, self._undoHistory) if redo else (self._undoHistory, self._redoHistory)
        target = self._resolveTarget()
        if not stack or target is None:
            return
        entry = stack[-1]
        wanted, expected = (entry[1], entry[0]) if redo else entry
        started, written = False, []
        self._engineBusy = self._historyReplaying = True
        self._playheadTimer.stop()
        try:
            self._validateWriteTarget()
            if any(self._historyRead(target, name) != value for name, value in expected.items()):
                self._clearHistory()
                print('[Color Wheel] Script history cleared: a recorded control was edited outside this history.')
                return
            dm.StartUndo('ColorWheel', 'ColorWheel', 0)
            started = True
            self._validateWriteTarget()
            if any(self._historyRead(target, name) != value for name, value in expected.items()):
                raise ValueError('The light changed before history could be restored.')
            for name, value in wanted.items():
                written.append(name)
                self._historyWrite(target, name, value)
            if any(self._historyRead(target, name) != value for name, value in wanted.items()):
                raise ValueError('SFM did not restore every recorded value.')
            stack.pop()
            opposite.append(entry)
        except Exception as error:
            try:
                self._validateWriteTarget()
                for name in reversed(written):
                    self._historyWrite(target, name, expected[name])
            except Exception:
                self._clearHistory()
            print('[Color Wheel] Could not restore script history: %s' % error)
        finally:
            if started:
                try:
                    dm.FinishUndo()
                except Exception as error:
                    print('[Color Wheel] Could not finish undo: %s' % error)
            try:
                if written and not self._targetLost and not self._closing:
                    sfmApp.SetHeadTimeInFrames(sfmApp.GetHeadTimeInFrames())
            except Exception as error:
                print('[Color Wheel] Could not refresh light: %s' % error)
            finally:
                self._engineBusy = self._historyReplaying = False
                if not self._closing and self.isVisible() and self._resolveTarget() is not None:
                    self._lastSnapshot, self._cacheTicks = {}, 0
                    self._pollPlayhead()
                    self._playheadTimer.start()
                self._updateHistoryButtons()

    def _captureEditTargets(self, names, existing=()):
        targets = {}
        for name in names:
            if name == '__color':
                targets.update(self._captureEditTargets(_POLL_CHANNELS[:3], existing))
            elif not name.startswith('__') and name not in existing:
                channel = self._channel(name)
                if channel is None:
                    raise ValueError('A light control is unavailable: ' + name)
                targets[name] = channelEditTarget(channel)
        return targets

    def _queueEdit(self, name, value, immediate=False):
        if not self._engineBusy and not self._editingAllowed():
            return
        if self._historyReplaying:
            return
        if self._loading or self._closing or self._targetLost or not self.isVisible():
            return
        values = value if name == '__color' else (value,)
        if any(math.isnan(float(v)) or math.isinf(float(v)) for v in values):
            return
        if not self._engineBusy and self._resolveTarget() is None:
            return
        if not self._engineBusy:
            try:
                names = self._channels if name == '__defaults' else (name,)
                self._pendingTargets.update(self._captureEditTargets(names))
            except Exception as error:
                print('[Color Wheel] Edit not applied: %s' % error)
                return
        self._pending[name] = value
        if immediate and not self._engineBusy:
            self._flushPending()
        elif not self._applyTimer.isActive():
            self._applyTimer.start()

    def _flushPending(self, *args):
        if not self._engineBusy and not self._editingAllowed():
            return
        if self._engineBusy or self._closing or self._targetLost:
            return
        self._applyTimer.stop()
        if not self._pending:
            if not self._historyDragging():
                self._finishHistory()
            return
        target = self._resolveTarget()
        if target is None:
            return
        edits = self._pending.copy()
        editTargets = self._pendingTargets.copy()
        self._pending.clear()
        self._pendingTargets.clear()
        self._engineBusy = True
        self._playheadTimer.stop()
        resetDefaults = edits.pop('__defaults', False)
        resetComplete = False
        started, changed, completed = False, False, True
        try:
            if resetDefaults or self._cacheTicks == 0:
                self._refreshChannels(target)
            if resetDefaults:
                try:
                    defaults = self._readLightDefaults(target)
                except Exception as error:
                    self._pending.update(edits)
                    self._pendingTargets.update(editTargets)
                    button = self._defaultButton
                    if button.isVisible():
                        QtGui.QToolTip.showText(button.mapToGlobal(QtCore.QPoint(0, button.height())), str(error), button)
                    print('[Color Wheel] Defaults were not applied: %s' % error)
                    return
                edits = defaults
                if not edits:
                    return
            editTargets.update(self._captureEditTargets(edits, editTargets))
            try:
                self._captureHistory(target, edits)
            except Exception as error:
                self._clearHistory()
                self._historySkipped = True
                print('[Color Wheel] This edit could not be recorded: %s' % error)
            dm.StartUndo('ColorWheel', 'ColorWheel', 0)
            started = True
            self._validateWriteTarget()
            for name, context in editTargets.items():
                channel = self._channel(name)
                if channel is None or channelEditTarget(channel) != context:
                    raise ValueError('A light channel changed before the queued edit could be applied.')
            for name, value in edits.items():
                if name == '__color':
                    channels = [self._channel(n) for n in _POLL_CHANNELS[:3]]
                    if all(channel is not None for channel in channels):
                        for name, channel, component in zip(_POLL_CHANNELS[:3], channels, value):
                            written = setChannelAllKeys(channel, component, editTargets[name])
                            changed, completed = written or changed, written and completed
                # -- Applies boolean property values into their respective channels --- #
                elif name.startswith('__b_'):
                    target.light.SetValue(name[4:], value)
                    changed = True
                # -- Applies other property values into their respective channels --- #
                else:
                    channel = self._channel(name)
                    if channel is not None:
                        written = setChannelAllKeys(channel, value, editTargets[name])
                        changed, completed = written or changed, written and completed
            if resetDefaults and completed:
                self._lastSnapshot = {}
                resetComplete = True
            elif resetDefaults:
                print('[Color Wheel] Incomplete default reset: SFM could not write a light control; use Undo to restore the previous state.')
                button = self._defaultButton
                if button.isVisible():
                    QtGui.QToolTip.showText(button.mapToGlobal(QtCore.QPoint(0, button.height())),
                                           'Incomplete reset: SFM could not update a control. Use Undo to restore the previous state.', button)
        except Exception as error:
            print('[Color Wheel] Could not apply light changes: %s' % error)
            self._cacheTicks = 0
        finally:
            if started:
                try:
                    dm.FinishUndo()
                except Exception as error:
                    print('[Color Wheel] Could not finish undo: %s' % error)
            try:
                if changed and not self._closing:
                    sfmApp.SetHeadTimeInFrames(sfmApp.GetHeadTimeInFrames())
            except Exception as error:
                print('[Color Wheel] Could not refresh light: %s' % error)
            finally:
                self._engineBusy = False
                if not self._historyDragging():
                    self._finishHistory()
                self._updateHistoryButtons()
                if not self._closing and self.isVisible() and self._resolveTarget() is not None:
                    self._playheadTimer.start()
                    if resetComplete:
                        self._pollPlayhead()
                    if self._pending:
                        self._applyTimer.start()

    def _updateColorUi(self):
        color = QtGui.QColor(int(self.currentR * 255), int(self.currentG * 255), int(self.currentB * 255))
        text = '#%02X%02X%02X' % (color.red(), color.green(), color.blue())
        if text != getattr(self, '_hexText', None):
            self._swatch.setStyleSheet('background: %s; border: 1px solid #666666; border-radius: 3px;' % text)
        self._hexText = text
        if not self.hexEdit.hasFocus():
            self.hexEdit.setText(self._hexText)
        if not self.wheel._dragging:
            self.wheel.setSelectorFromColor(QtGui.QColor.fromRgbF(
                max(0.0, min(self.currentR * self.brightnessScale, 1.0)),
                max(0.0, min(self.currentG * self.brightnessScale, 1.0)),
                max(0.0, min(self.currentB * self.brightnessScale, 1.0))))
        self.brightnessSlider.setColor(color)
        if not self.brightnessSlider._dragging:
            self.brightnessSlider.setValue(self.brightnessScale)
        self._brightnessLabel.setText('%d%%' % int(round(self.brightnessScale * 100)))
        self._syncColorFields()

    def onColorChanged(self, color):
        if self._loading or self._resolveTarget() is None:
            return
        self.currentR, self.currentG, self.currentB = (v / 255.0 for v in (color.red(), color.green(), color.blue()))
        self._updateColorUi()
        self._applyToLight()

    def onColorReleased(self, color):
        self._flushPending()

    def onIntensityChanged(self, value):
        if self._loading or self._resolveTarget() is None:
            return
        self.brightnessScale = value
        self._updateColorUi()
        self._applyToLight()

    # -- Applies the RGB values into their respective channels --- #
    def _applyToLight(self):
        scale = self.brightnessScale
        rgb = tuple(max(0.0, min(value * scale, 1.0)) for value in (self.currentR, self.currentG, self.currentB))
        self._queueEdit('__color', rgb)

    # -- HEX value/copying --- #
    def _clearHexError(self, *args):
        self.hexEdit.setProperty('invalid', False)
        self.hexEdit.style().unpolish(self.hexEdit)
        self.hexEdit.style().polish(self.hexEdit)

    def _commitHex(self):
        text = self.hexEdit.text().strip().lstrip('#')
        color = QtGui.QColor('#' + text)
        if len(text) != 6 or not color.isValid():
            self.hexEdit.setProperty('invalid', True)
            self.hexEdit.style().unpolish(self.hexEdit)
            self.hexEdit.style().polish(self.hexEdit)
            return
        self._clearHexError()
        if '#' + text.upper() == self._hexText:
            self.hexEdit.setText(self._hexText)
            return
        self.onColorChanged(color)
        self.hexEdit.setText(self._hexText)
        self._flushPending()

    def copyHex(self):
        QtGui.QApplication.clipboard().setText(self._hexText)


def showColorWheel():
    target = sfm.GetCurrentAnimationSet()
    if target is None or getattr(target, 'light', None) is None or not sfmApp.HasDocument():
        print('[Color Wheel] Open this script from a light in the Rig menu.')
        return None
    existing = getattr(sfmApp, InternalName + '_instance', None)
    if existing is None:
        existing = globals().get(InternalName)
    if existing is not None and shiboken.isValid(existing):
        if not getattr(existing, '_fixedTargetWindow', False):
            print('[Color Wheel] Restart SFM once before using this version.')
            return None
        existing.close()
        existing.deleteLater()
    window = ColorWheelWindow(target)
    setattr(sfmApp, InternalName + '_instance', window)
    globals()[InternalName] = window
    window.present()
    return window

try:
    tool = showColorWheel()
except Exception as error:
    print('[Color Wheel] Failed to launch: %s' % error)
