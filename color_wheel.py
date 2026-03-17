# [SFM] Color Wheel Tool
#
# This script adds a Color Wheel + lighting properties system to the rigs section of your lights
# in Source Filmmaker, allowing you to change light colors and other settings from there instead 
# of relying on SFM's default RGB sliders.
#
# Author: Aftre
#
# Script inspired by Fames, msu355, and an0nymooose (fixes & implementations)
# HEX Code idea by Dani3D
# Early testing and feedback: Bone, Cuori, HyperBlender, Shydo and Trap & Hat

import math, sfm, sfmUtils, vs, sfmApp, vsUtils
from vs import g_pDataModel as dm
from PySide import QtGui, QtCore

ProductName = "Color Wheel"
InternalName = "color_wheel"

def getChannel(animSet, controlName):
    try:
        rootGroup = animSet.GetRootControlGroup()
        if rootGroup is None:
            return None
        ctrl = rootGroup.FindControlByName(controlName, True)
        if ctrl is None:
            return None
        return ctrl.channel
    except Exception as e:
        return None

def getPlayheadTime():
    return vs.DmeTime_t(((1.0 / sfmApp.GetFramesPerSecond()) * sfmApp.GetHeadTimeInFrames()) + 5.0)

# In Graph Editor inserts or overwrites a single keyframe at the playhead position
# In Motion and Clip Editors overwrites every existing keyframe
def setChannelAllKeys(channel, value):
    try:
        layer = channel.log.GetLayer(0)
        count = layer.GetKeyCount()
        timelineMode = sfmApp.GetTimelineMode()
        inGraphEditor = timelineMode == 4
        if inGraphEditor:
            time = getPlayheadTime()
            if count == 0:
                # If there's no keys, then inserts one affecting the whole timeline
                channel.log.InsertKey(vs.DmeTime_t(0), value, 3)
                layer.values[0] = value
            existing = channel.log.FindKeyWithinTolerance(time, vs.DmeTime_t(1))
            if existing >= 0:
                layer.values[existing] = value
            else:
                channel.log.AddBookmark(time, 0)
                index = channel.log.InsertKey(time, value, 3)
                layer.values[index] = value
        elif count == 0:
            # If there's no keys, then inserts one affecting the whole timeline
            channel.log.InsertKey(vs.DmeTime_t(0), value, 3)
            layer.values[0] = value
        else:
            for i in range(count): layer.values[i] = value
        return True
    except Exception as e:
        return False

# Applies RGB values to the light color channels
def applyLightColor(animSet, r, g, b):
    if animSet is None:
        return
    chR = getChannel(animSet, "color_red")
    chG = getChannel(animSet, "color_green")
    chB = getChannel(animSet, "color_blue")
    if not chR or not chG or not chB:
        return
    dm.StartUndo("ColorWheel", "ColorWheel", 0)
    setChannelAllKeys(chR, r)
    setChannelAllKeys(chG, g)
    setChannelAllKeys(chB, b)
    dm.FinishUndo()
    sfmApp.SetHeadTimeInFrames(sfmApp.GetHeadTimeInFrames())

def applyControlValue(animSet, controlName, value):
    ch = getChannel(animSet, controlName)
    if ch is None:
        return
    dm.StartUndo("ColorWheel", "ColorWheel", 0)
    setChannelAllKeys(ch, value)
    dm.FinishUndo()
    sfmApp.SetHeadTimeInFrames(sfmApp.GetHeadTimeInFrames())

def applyBoolValue(animSet, controlName, value):
    try:
        lightElem = animSet.light
        if lightElem is None:
            return
        dm.StartUndo("ColorWheel", "ColorWheel", 0)
        lightElem.SetValue(controlName, value)
        dm.FinishUndo()
        sfmApp.SetHeadTimeInFrames(sfmApp.GetHeadTimeInFrames())
    except Exception as e:
        pass

def readChannelValue(animSet, controlName, fallback=0.0):
    try:
        ch = getChannel(animSet, controlName)
        if ch is None:
            return fallback
        layer = ch.log.GetLayer(0)
        if layer.GetKeyCount() == 0:
            return fallback
        return float(layer.values[0])
    except Exception:
        return fallback

def readBoolValue(animSet, controlName, fallback=False):
    try:
        lightElem = animSet.light
        if lightElem is None:
            return fallback
        return bool(lightElem.GetValue(controlName))
    except Exception:
        return fallback

##  Color Wheel thing
class COLORWheel(QtGui.QWidget):
    colorChanged = QtCore.Signal(QtGui.QColor)

    def __init__(self):
        super(COLORWheel, self).__init__()
        self.setMinimumSize(220, 220)
        self.setMaximumSize(220, 220)
        self._radius = 106
        self._selectorPos = QtCore.QPoint(110, 110)
        self._cachedWheel = None
        self._generateWheel()

        # System to avoid lagging SFM and making it explode or something
        self._applyTimer = QtCore.QTimer(self)
        self._applyTimer.setSingleShot(True)
        self._applyTimer.setInterval(40)
        self._pendingColor = None
        self._applyTimer.timeout.connect(self._emitPending)

    def _generateWheel(self):
        size = self._radius * 2
        image = QtGui.QImage(size, size, QtGui.QImage.Format_RGB32)
        cx = cy = self._radius
        for y in range(size):
            for x in range(size):
                dx, dy = x - cx, y - cy
                dist = math.sqrt(dx*dx + dy*dy)
                if dist <= self._radius:
                    # Blender layout
                    angle = math.degrees(math.atan2(-dx, dy))
                    if angle < 0: angle += 360
                    sat = dist / self._radius
                    c = QtGui.QColor()
                    # 90% desaturation to make it similar to SFMs desaturated colors
                    c.setHsv(int(angle), int(sat * 255 * 0.90), 255)
                    image.setPixel(x, y, c.rgb())
                else:
                    image.setPixel(x, y, QtGui.QColor(40, 40, 40).rgb())
        self._cachedWheel = QtGui.QPixmap.fromImage(image)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        ox = (self.width() - self._radius * 2) / 2
        oy = (self.height() - self._radius * 2) / 2
        painter.drawPixmap(ox, oy, self._cachedWheel)
        sx, sy = self._selectorPos.x(), self._selectorPos.y()
        painter.setPen(QtGui.QPen(QtCore.Qt.white, 2))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(QtCore.QPoint(sx, sy), 7, 7)
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        painter.drawEllipse(QtCore.QPoint(sx, sy), 9, 9)

    def mousePressEvent(self, event): self._pick(event.pos())
    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            self._pick(event.pos())

    def _pick(self, pos):
        cx, cy = self.width() / 2, self.height() / 2
        dx, dy = pos.x() - cx, pos.y() - cy
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > self._radius:
            angle = math.atan2(dy, dx)
            dx = math.cos(angle) * self._radius
            dy = math.sin(angle) * self._radius
            dist = self._radius
        self._selectorPos = QtCore.QPoint(int(cx + dx), int(cy + dy))
        self.update()

        # Blender layout
        angle_deg = math.degrees(math.atan2(-dx, dy))
        if angle_deg < 0: angle_deg += 360
        sat = min(dist / self._radius, 1.0)
        color = QtGui.QColor()
        color.setHsv(int(angle_deg), int(sat * 255), 255)
        self._pendingColor = color
        if not self._applyTimer.isActive():
            self._applyTimer.start()

    def _emitPending(self):
        if self._pendingColor is not None:
            self.colorChanged.emit(self._pendingColor)
            self._pendingColor = None

    def setSelectorFromColor(self, color):
        h, s, v, _ = color.getHsv()
        if s == 0:
            self._selectorPos = QtCore.QPoint(self._radius, self._radius)
            self.update()
            return
        angle_rad = math.atan2(
            -math.cos(math.radians(h)),
             math.sin(math.radians(h))
        )
        sat_dist = (s / 255.0) * self._radius
        cx, cy = self.width() / 2, self.height() / 2
        dx = -math.sin(math.radians(h)) * sat_dist
        dy =  math.cos(math.radians(h)) * sat_dist
        self._selectorPos = QtCore.QPoint(int(cx + dx), int(cy + dy))
        self.update()

## Brightness Slider
# Vertical color brightness slider
class BrightnessSlider(QtGui.QWidget):
    valueChanged = QtCore.Signal(float)

    def __init__(self, parent=None):
        super(BrightnessSlider, self).__init__(parent)
        self.setFixedWidth(18)
        self.setMinimumHeight(220)
        self._value = 1.0
        self._dragging = False

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        gradient = QtGui.QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QtGui.QColor(255, 255, 255))
        gradient.setColorAt(1.0, QtGui.QColor(0, 0, 0))
        painter.fillRect(self.rect(), QtGui.QBrush(gradient))
        y = int((1.0 - self._value) * self.height())
        painter.setPen(QtGui.QPen(QtCore.Qt.white, 2))
        painter.drawLine(0, y, self.width(), y)
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        painter.drawLine(0, y+2, self.width(), y+2)

    def mousePressEvent(self, event):
        self._dragging = True
        self._updateValue(event.pos().y())

    def mouseMoveEvent(self, event):
        if self._dragging: self._updateValue(event.pos().y())

    def mouseReleaseEvent(self, event): self._dragging = False

    def _updateValue(self, y):
        self._value = 1.0 - max(0.0, min(1.0, float(y) / self.height()))
        self.update()
        self.valueChanged.emit(self._value)

    def setValue(self, v):
        self._value = max(0.0, min(1.0, v))
        self.update()

    def getValue(self): return self._value

## Property Sliders
class PropertySliders(QtGui.QWidget):
    def __init__(self, label, minVal, maxVal, defaultVal, decimals=2, parent=None):
        super(PropertySliders, self).__init__(parent)
        self._min, self._max, self._decimals = minVal, maxVal, decimals
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)
        lbl = QtGui.QLabel(label)
        lbl.setFixedWidth(130)
        lbl.setStyleSheet("font-size: 11px;")
        layout.addWidget(lbl)
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.slider.setValue(self._toSlider(defaultVal))
        self.slider.valueChanged.connect(self._onSlider)
        layout.addWidget(self.slider)
        self.valLabel = QtGui.QLabel(("%%.%df" % decimals) % defaultVal)
        self.valLabel.setFixedWidth(46)
        self.valLabel.setStyleSheet("font-size: 11px;")
        self.valLabel.mouseDoubleClickEvent = lambda e: self._startEdit()
        layout.addWidget(self.valLabel)

    def _toSlider(self, val):
        return int((val - self._min) / (self._max - self._min) * 1000)

    def _fromSlider(self, tick):
        return self._min + (self._max - self._min) * tick / 1000.0

    def _onSlider(self, tick):
        self.valLabel.setText(("%%.%df" % self._decimals) % self._fromSlider(tick))

    def getValue(self): return self._fromSlider(self.slider.value())

    def setValueSilent(self, val):
        self.slider.blockSignals(True)
        self.slider.setValue(self._toSlider(max(self._min, min(self._max, val))))
        self.valLabel.setText(("%%.%df" % self._decimals) % val)
        self.slider.blockSignals(False)

    def setTip(self, text):
        self.layout().itemAt(0).widget().setToolTip(text)

    # Lets you edit the sliders value by double clicking on it
    def _startEdit(self):
        edit = QtGui.QLineEdit(self.valLabel.text(), self.valLabel.parentWidget())
        edit.setFixedWidth(46)
        edit.setFixedHeight(20)
        edit.setStyleSheet("font-size: 11px;")
        edit.move(self.valLabel.mapTo(self.valLabel.parentWidget(), QtCore.QPoint(0, 0)))
        edit.show()
        edit.setFocus()
        edit.selectAll()
        def commit():
            try:
                val = max(self._min, min(self._max, float(edit.text())))
                self.slider.blockSignals(True)
                self.slider.setValue(self._toSlider(val))
                self.valLabel.setText(("%%.%df" % self._decimals) % val)
                self.slider.blockSignals(False)
                self.slider.valueChanged.emit(self.slider.value())
            except Exception:
                pass
            edit.deleteLater()
        edit.editingFinished.connect(commit)
        edit.focusOutEvent = lambda e: (commit(), QtGui.QLineEdit.focusOutEvent(edit, e))

    def connectChanged(self, fn):
        self.slider.valueChanged.connect(lambda _: fn(self.getValue()))

## Collapsible sections for each propertty
class CollapsibleSection(QtGui.QWidget):
    def __init__(self, title, parent=None):
        super(CollapsibleSection, self).__init__(parent)
        self._title = title
        self._layout = QtGui.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self.setLayout(self._layout)
        self._btn = QtGui.QPushButton("[+] " + title)
        self._btn.setStyleSheet("text-align: left; font-size: 11px; font-weight: bold; padding: 2px;")
        self._btn.setFlat(True)
        self._btn.clicked.connect(self._toggle)
        self._layout.addWidget(self._btn)
        self._body = QtGui.QWidget()
        self._bodyLayout = QtGui.QVBoxLayout()
        self._bodyLayout.setContentsMargins(8, 0, 0, 4)
        self._bodyLayout.setSpacing(2)
        self._body.setLayout(self._bodyLayout)
        self._body.setVisible(False)
        self._layout.addWidget(self._body)

    def _toggle(self):
        visible = not self._body.isVisible()
        self._body.setVisible(visible)
        self._btn.setText(("[-] " if visible else "[+] ") + self._title)

    def addWidget(self, w): self._bodyLayout.addWidget(w)

    def addRow(self, *widgets):
        row = QtGui.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        for w in widgets: row.addWidget(w)
        self._bodyLayout.addLayout(row)

## Main Window
# Window Code meow
class ColorWheelWindow(QtGui.QWidget):
    def __init__(self, animSet):
        super(ColorWheelWindow, self).__init__()
        self.targetAnimSet = animSet
        self.setWindowTitle(ProductName)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setFixedWidth(340)
        scroll = QtGui.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        inner = QtGui.QWidget()
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setSpacing(4)
        mainLayout.setContentsMargins(8, 8, 8, 8)
        inner.setLayout(mainLayout)
        scroll.setWidget(inner)
        outerLayout = QtGui.QVBoxLayout()
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(scroll)
        self.setLayout(outerLayout)
        self.setMinimumHeight(420)
        self.setMaximumHeight(700)

        # Window Title
        title = QtGui.QLabel("Color Wheel")
        title.setStyleSheet("font-size:15px; font-weight:bold;")
        mainLayout.addWidget(title)

        # Show which light is selected or affected by the script
        lightName = animSet.GetName() if animSet else "None"
        self.targetLabel = QtGui.QLabel("Editing: %s" % lightName)
        self.targetLabel.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        mainLayout.addWidget(self.targetLabel)

        # Color wheel + colors intensity slider (brightness)
        wheelRow = QtGui.QHBoxLayout()
        wheelRow.setSpacing(6)
        self.wheel = COLORWheel()
        self.wheel.colorChanged.connect(self.onColorChanged)
        wheelRow.addWidget(self.wheel)
        self.brightnessSlider = BrightnessSlider()
        self.brightnessSlider.valueChanged.connect(self.onIntensityChanged)
        wheelRow.addWidget(self.brightnessSlider, alignment=QtCore.Qt.AlignVCenter)
        mainLayout.addLayout(wheelRow)

        # HEX code and copy button
        hexRow = QtGui.QHBoxLayout()
        self.hexLabel = QtGui.QLabel("#FFFFFF")
        self.hexLabel.setStyleSheet("font-size: 12px;")
        self.hexLabel.mouseDoubleClickEvent = lambda e: self._startHexEdit()
        self.copyHexBtn = QtGui.QPushButton("Copy HEX")
        self.copyHexBtn.clicked.connect(self.copyHex)
        hexRow.addWidget(self.hexLabel)
        hexRow.addWidget(self.copyHexBtn)
        mainLayout.addLayout(hexRow)

        ## Other Properties
        # Intensity
        secInt = CollapsibleSection("Intensity")
        self.s_intensity = PropertySliders("Intensity", 0.0, 1.0, 1.0)
        self.s_intensity.setTip("Controls how bright the light is. Higher = brighter, lower = dimmer.")
        self.s_intensity.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "intensity", v))
        secInt.addWidget(self.s_intensity)
        mainLayout.addWidget(secInt)

        # Radius
        secRad = CollapsibleSection("Radius")
        self.s_radius = PropertySliders("Radius", 0.0, 1.0, 1.0, 2)
        self.s_radius.setTip("Mimics a larger light source, softens shadows and causes light to wrap around objects.")
        self.s_radius.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "radius", v))
        secRad.addWidget(self.s_radius)
        mainLayout.addWidget(secRad)

        # FOV
        secFOV = CollapsibleSection("Field of View")
        self.s_hFov = PropertySliders("Horizontal FOV", 0.0, 1.0, 1.0, 2)
        self.s_hFov.setTip("The horizontal width of the light cone.")
        self.s_vFov = PropertySliders("Vertical FOV", 0.0, 1.0, 1.0, 2)
        self.s_vFov.setTip("The vertical width of the light cone.")
        self.s_hFov.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "horizontalFOV", v))
        self.s_vFov.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "verticalFOV", v))
        secFOV.addWidget(self.s_hFov)
        secFOV.addWidget(self.s_vFov)
        mainLayout.addWidget(secFOV)

        # Shadows
        secShad = CollapsibleSection("Shadows")
        self.s_shadowFilter = PropertySliders("ShadowFilterSize", 0.0, 1.0, 1.0)
        self.s_shadowFilter.setTip("Softens the edges of shadows without changing how light wraps around objects.")
        self.s_shadowAtten = PropertySliders("ShadowAtten", 0.0, 1.0, 0.0)
        self.s_shadowAtten.setTip("Controls shadow darkness. Higher = more transparent, lower = darker.")
        self.s_shadowDepth = PropertySliders("shadowDepthBias", 0.0, 1.0, 0.0)
        self.s_shadowDepth.setTip("Offsets the point at which SFM starts rendering shadows from a surface.")
        self.s_shadowSlope = PropertySliders("shadowSlopeScale", 0.0, 1.0, 1.0)
        self.s_shadowSlope.setTip("Narrows shadows at their base.")
        self.s_shadowFilter.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "shadowFilterSize", v))
        self.s_shadowAtten.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "shadowAtten", v))
        self.s_shadowDepth.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "shadowDepthBias", v))
        self.s_shadowSlope.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "shadowSlopeScaleDepthBias", v))
        secShad.addWidget(self.s_shadowFilter)
        secShad.addWidget(self.s_shadowAtten)
        secShad.addWidget(self.s_shadowDepth)
        secShad.addWidget(self.s_shadowSlope)
        mainLayout.addWidget(secShad)

        # Distance
        secDist = CollapsibleSection("Distance")
        self.s_minDist = PropertySliders("minDistance", 0.0, 1.0, 0.0, 2)
        self.s_minDist.setTip("Distance at which the light starts.")
        self.s_maxDist = PropertySliders("maxDistance", 0.0, 1.0, 1.0, 2)
        self.s_maxDist.setTip("Distance at which the light ends.")
        self.s_farZAtten = PropertySliders("farZAtten", 0.0, 1.0, 1.0, 2)
        self.s_farZAtten.setTip("Far distance attenuation falloff.")
        self.s_minDist.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "minDistance", v))
        self.s_maxDist.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "maxDistance", v))
        self.s_farZAtten.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "farZAtten", v))
        secDist.addWidget(self.s_minDist)
        secDist.addWidget(self.s_maxDist)
        secDist.addWidget(self.s_farZAtten)
        mainLayout.addWidget(secDist)

        # Attenuation
        secAtten = CollapsibleSection("Attenuation")
        self.s_constAtten = PropertySliders("Constant", 0.0, 1.0, 0.0)
        self.s_constAtten.setTip("Brightness is constant across the whole light range.")
        self.s_linearAtten = PropertySliders("Linear", 0.0, 1.0, 0.0)
        self.s_linearAtten.setTip("Brightness drops at a steady rate with distance.")
        self.s_quadAtten = PropertySliders("Quadratic", 0.0, 1.0, 1.0)
        self.s_quadAtten.setTip("Brightness drops increasingly faster with distance.")
        self.s_constAtten.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "constantAttenuation", v))
        self.s_linearAtten.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "linearAttenuation", v))
        self.s_quadAtten.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "quadraticAttenuation", v))
        secAtten.addWidget(self.s_constAtten)
        secAtten.addWidget(self.s_linearAtten)
        secAtten.addWidget(self.s_quadAtten)
        mainLayout.addWidget(secAtten)

        # Volumetric
        secVol = CollapsibleSection("Volumetrics")
        self.s_volIntensity = PropertySliders("volumetricIntensity", 0.0, 1.0, 1.0)
        self.s_volIntensity.setTip("Intensity of the volumetric effect.")
        self.s_noiseStr = PropertySliders("noiseStrength", 0.0, 1.0, 0.0)
        self.s_noiseStr.setTip("Strength of the volumetric noise/cloudy texture.")
        self.s_volIntensity.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "volumetricIntensity", v))
        self.s_noiseStr.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "noiseStrength", v))
        secVol.addWidget(self.s_volIntensity)
        secVol.addWidget(self.s_noiseStr)
        mainLayout.addWidget(secVol)

        # UberLight
        secUber = CollapsibleSection("UberLights")
        self.s_width = PropertySliders("width", 0.0, 1.0, 1.0, 2)
        self.s_width.setTip("Width of the uberlight shape.")
        self.s_edgeWidth = PropertySliders("edgeWidth", 0.0, 1.0, 1.0, 2)
        self.s_edgeWidth.setTip("Softness of the uberlight width edges.")
        self.s_height = PropertySliders("height", 0.0, 1.0, 1.0, 2)
        self.s_height.setTip("Height of the uberlight shape.")
        self.s_edgeHeight = PropertySliders("edgeHeight", 0.0, 1.0, 1.0, 2)
        self.s_edgeHeight.setTip("Softness of the uberlight height edges.")
        self.s_width.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "width", v))
        self.s_edgeWidth.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "edgeWidth", v))
        self.s_height.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "height", v))
        self.s_edgeHeight.connectChanged(lambda v: applyControlValue(self.targetAnimSet, "edgeHeight", v))
        secUber.addWidget(self.s_width)
        secUber.addWidget(self.s_edgeWidth)
        secUber.addWidget(self.s_height)
        secUber.addWidget(self.s_edgeHeight)
        uberRow = QtGui.QHBoxLayout()
        uberRow.setContentsMargins(0, 2, 0, 0)
        uberLbl = QtGui.QLabel("UberLight")
        uberLbl.setStyleSheet("font-size: 11px;")
        self.uberCheck = QtGui.QCheckBox()
        self.uberCheck.setChecked(False)
        self.uberCheck.stateChanged.connect(lambda s: applyBoolValue(self.targetAnimSet, "uberlight", bool(s)))
        uberRow.addWidget(uberLbl)
        uberRow.addStretch()
        uberRow.addWidget(self.uberCheck)
        secUber._bodyLayout.addLayout(uberRow)
        mainLayout.addWidget(secUber)
        mainLayout.addStretch()

        credit = QtGui.QLabel("by Aftre")
        credit.setStyleSheet("color: #555555; font-size: 10px;")
        credit.setAlignment(QtCore.Qt.AlignRight)
        mainLayout.addWidget(credit)

        self.currentColor = QtGui.QColor(255, 255, 255)
        self.currentR = 1.0
        self.currentG = 1.0
        self.currentB = 1.0
        self.brightnessScale = 1.0
        self._lastHeadFrame = -1

        # Auto-updates every 5ms to keep the script synced with the current playhead position
        self._playheadTimer = QtCore.QTimer(self)
        self._playheadTimer.setInterval(5)
        self._playheadTimer.timeout.connect(self._pollPlayhead)
        self._playheadTimer.start()

        # Loads the current light values into the window
        self._loadFromLight()

    # Every 5ms, reads the current values of the light depending where the playhead is at in the Graph Editor and sends it to
    # the window (auto-update/detection)
    def _pollPlayhead(self):
        frame = sfmApp.GetHeadTimeInFrames()
        if frame == self._lastHeadFrame:
            return
        self._lastHeadFrame = frame
        a = self.targetAnimSet
        if a is None:
            return
        time = getPlayheadTime()
        try:
            chR = getChannel(a, "color_red")
            chG = getChannel(a, "color_green")
            chB = getChannel(a, "color_blue")
            if chR and chG and chB:
                r = float(chR.log.GetValue(time))
                g = float(chG.log.GetValue(time))
                b = float(chB.log.GetValue(time))
                brightness = max(r, g, b, 0.001)
                nr = min(r / brightness, 1.0)
                ng = min(g / brightness, 1.0)
                nb = min(b / brightness, 1.0)
                self.currentR, self.currentG, self.currentB = nr, ng, nb
                self.brightnessScale = min(brightness, 1.0)
                color = QtGui.QColor(int(nr * 255), int(ng * 255), int(nb * 255))
                self.currentColor = color
                self.hexLabel.setText("#%02X%02X%02X" % (color.red(), color.green(), color.blue()))
                self.wheel.setSelectorFromColor(color)
                self.brightnessSlider.setValue(self.brightnessScale)
        except Exception:
            pass
        def sv(slider, ctrl, fb):
            try:
                ch = getChannel(a, ctrl)
                if ch: slider.setValueSilent(float(ch.log.GetValue(time)))
            except Exception:
                pass
        sv(self.s_intensity, "intensity", 1.0)
        sv(self.s_radius, "radius", 1.0)
        sv(self.s_hFov, "horizontalFOV", 1.0)
        sv(self.s_vFov, "verticalFOV", 1.0)
        sv(self.s_shadowFilter,"shadowFilterSize", 1.0)
        sv(self.s_shadowAtten, "shadowAtten", 0.0)
        sv(self.s_shadowDepth, "shadowDepthBias", 0.0)
        sv(self.s_shadowSlope, "shadowSlopeScaleDepthBias", 1.0)
        sv(self.s_minDist, "minDistance", 0.0)
        sv(self.s_maxDist, "maxDistance", 1.0)
        sv(self.s_farZAtten, "farZAtten", 1.0)
        sv(self.s_constAtten, "constantAttenuation", 0.0)
        sv(self.s_linearAtten, "linearAttenuation", 0.0)
        sv(self.s_quadAtten, "quadraticAttenuation", 1.0)
        sv(self.s_volIntensity,"volumetricIntensity", 1.0)
        sv(self.s_noiseStr, "noiseStrength", 0.0)
        sv(self.s_width, "width", 1.0)
        sv(self.s_edgeWidth, "edgeWidth", 1.0)
        sv(self.s_height, "height", 1.0)
        sv(self.s_edgeHeight, "edgeHeight", 1.0)

    # Reads the light values and sends it to the window
    def _loadFromLight(self):
        self._lastHeadFrame = -1
        a = self.targetAnimSet
        if a is None:
            return

        # Reads RGB from light and sends it to the Color Wheel and brightness slider
        r = readChannelValue(a, "color_red", 1.0)
        g = readChannelValue(a, "color_green", 1.0)
        b = readChannelValue(a, "color_blue", 1.0)
        brightness = max(r, g, b, 0.001)
        nr = r / brightness
        ng = g / brightness
        nb = b / brightness

        self.currentR, self.currentG, self.currentB = nr, ng, nb
        self.brightnessScale = min(brightness, 1.0)

        color = QtGui.QColor(int(nr * 255), int(ng * 255), int(nb * 255))
        self.currentColor = color
        self.hexLabel.setText("#%02X%02X%02X" % (color.red(), color.green(), color.blue()))

        # Move the color wheel selector to the right coords
        self.wheel.setSelectorFromColor(color)

        # Set brightness value to the slider
        self.brightnessSlider.setValue(self.brightnessScale)

        # Loads all property sliders
        self.s_intensity.setValueSilent(readChannelValue(a, "intensity", 1.0))
        self.s_radius.setValueSilent(readChannelValue(a, "radius", 1.0))
        self.s_hFov.setValueSilent(readChannelValue(a, "horizontalFOV", 1.0))
        self.s_vFov.setValueSilent(readChannelValue(a, "verticalFOV", 1.0))
        self.s_shadowFilter.setValueSilent(readChannelValue(a, "shadowFilterSize", 1.0))
        self.s_shadowAtten.setValueSilent(readChannelValue(a, "shadowAtten", 0.0))
        self.s_shadowDepth.setValueSilent(readChannelValue(a, "shadowDepthBias", 0.0))
        self.s_shadowSlope.setValueSilent(readChannelValue(a, "shadowSlopeScaleDepthBias", 1.0))
        self.s_minDist.setValueSilent(readChannelValue(a, "minDistance", 0.0))
        self.s_maxDist.setValueSilent(readChannelValue(a, "maxDistance", 1.0))
        self.s_farZAtten.setValueSilent(readChannelValue(a, "farZAtten", 1.0))
        self.s_constAtten.setValueSilent(readChannelValue(a, "constantAttenuation", 0.0))
        self.s_linearAtten.setValueSilent(readChannelValue(a, "linearAttenuation", 0.0))
        self.s_quadAtten.setValueSilent(readChannelValue(a, "quadraticAttenuation", 1.0))
        self.s_volIntensity.setValueSilent(readChannelValue(a, "volumetricIntensity", 1.0))
        self.s_noiseStr.setValueSilent(readChannelValue(a, "noiseStrength", 0.0))
        self.s_width.setValueSilent(readChannelValue(a, "width", 1.0))
        self.s_edgeWidth.setValueSilent(readChannelValue(a, "edgeWidth", 1.0))
        self.s_height.setValueSilent(readChannelValue(a, "height", 1.0))
        self.s_edgeHeight.setValueSilent(readChannelValue(a, "edgeHeight", 1.0))

        # UberLight checkbox
        self.uberCheck.blockSignals(True)
        self.uberCheck.setChecked(readBoolValue(a, "uberlight", False))
        self.uberCheck.blockSignals(False)

    # Applies Color Wheel color to the light
    def onColorChanged(self, color):
        self.currentColor = color
        self.currentR = color.red() / 255.0
        self.currentG = color.green() / 255.0
        self.currentB = color.blue() / 255.0
        self.hexLabel.setText("#%02X%02X%02X" % (color.red(), color.green(), color.blue()))
        self._applyToLight()

    # When the brightness slider is used, updates the light
    def onIntensityChanged(self, value):
        self.brightnessScale = value
        self._applyToLight()

    # Color value * brightness and sends value to the light
    def _applyToLight(self):
        r = min(self.currentR * self.brightnessScale, 1.0)
        g = min(self.currentG * self.brightnessScale, 1.0)
        b = min(self.currentB * self.brightnessScale, 1.0)
        applyLightColor(self.targetAnimSet, r, g, b)

    # Double-click selection and edit for the HEX values
    def _startHexEdit(self):
        edit = QtGui.QLineEdit(self.hexLabel.text(), self.hexLabel.parentWidget())
        edit.setFixedWidth(self.hexLabel.width())
        edit.setFixedHeight(22)
        edit.setStyleSheet("font-size: 11px;")
        edit.move(self.hexLabel.mapTo(self.hexLabel.parentWidget(), QtCore.QPoint(0, 0)))
        edit.show()
        edit.setFocus()
        edit.selectAll()
        def commit():
            txt = edit.text().strip()
            if not txt.startswith("#"): txt = "#" + txt
            try:
                color = QtGui.QColor(txt)
                if color.isValid():
                    self.wheel.setSelectorFromColor(color)
                    self.currentR = color.red() / 255.0
                    self.currentG = color.green() / 255.0
                    self.currentB = color.blue() / 255.0
                    self.hexLabel.setText("#%02X%02X%02X" % (color.red(), color.green(), color.blue()))
                    self._applyToLight()
            except Exception:
                pass
            edit.deleteLater()
        edit.editingFinished.connect(commit)
        edit.focusOutEvent = lambda e: (commit(), QtGui.QLineEdit.focusOutEvent(edit, e))

    def copyHex(self):
        QtGui.QApplication.clipboard().setText(self.hexLabel.text())

try:
    currentAnimSet = sfm.GetCurrentAnimationSet()
    existing = globals().get(InternalName)
    if existing is not None:
        existing.close()

    tool = ColorWheelWindow(currentAnimSet)
    globals()[InternalName] = tool
    tool.show()

except Exception as e:
    print("[Color Wheel] Failed to launch: %s" % e)
