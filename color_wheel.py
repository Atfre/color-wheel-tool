#===================================================================================== #
# [SFM] Color Wheel Tool v1.2.1
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

# -- Global undo/redo actions (REMOVED) --- #
# Will work on these later and implement them working on the next and final update!
# I'm so sorry for the issue the previous version has caused, but I promise the next
# update will be better <3
#
# To fix it I had to copy a working and stable version of the script, I still had to
# redo and add some extra things, but hopefully this is more stable than 1.2.0 while
# I'm working on the 1.3.0
#
# I wanted to post a version with the undo/redo options working, but I've been very
# busy lately and I haven't had time to continue working on the script, so to not
# keep you waiting and using a buggy script, I removed these latest changes to make
# them more stable later once I have time to work on them.
# - Aftre

import math, sfm, sfmUtils, vs, sfmApp, vsUtils
from vs import g_pDataModel as dm
from PySide import QtGui, QtCore

ProductName = "Color Wheel v1.2.1"
InternalName = "color_wheel"

# -- Channels names --- #
_POLL_CHANNELS = (
    "color_red",
    "color_green",
    "color_blue",
    "intensity",
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

def getPlayheadTime():
    try:
        return vs.DmeTime_t(((1.0 / sfmApp.GetFramesPerSecond()) * sfmApp.GetHeadTimeInFrames()) + 5.0)
    except Exception:
        return vs.DmeTime_t(5.0)

def getSampleTime():
    try:
        fps = float(sfmApp.GetFramesPerSecond())
        if fps <= 0:
            fps = 24.0
        frame_t = (1.0 / fps) * sfmApp.GetHeadTimeInFrames()
        if sfmApp.GetTimelineMode() == 4:
            return vs.DmeTime_t(frame_t + 5.0)
        return vs.DmeTime_t(frame_t)
    except Exception:
        return vs.DmeTime_t(0.0)

def get_working_animset(stored):
    cur = None
    try:
        cur = sfm.GetCurrentAnimationSet()
    except Exception:
        cur = None
    if cur is not None:
        return cur
    if stored is None:
        return None
    try:
        stored.GetName()
        return stored
    except Exception:
        return None

# -- Gets the channel of a property by its name --- #
def getChannel(animSet, controlName):
    try:
        animSet = get_working_animset(animSet)
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

# -- Writes values on keyframes depending on which timeline-editor you are (Clip, Motion or Graph Editors) --- #
def setChannelAllKeys(channel, value):
    try:
        layer = channel.log.GetLayer(0)
        count = layer.GetKeyCount()
        timelineMode = sfmApp.GetTimelineMode()
        inGraphEditor = timelineMode == 4
        if inGraphEditor:
            time = getPlayheadTime()
            if count == 0:
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
            channel.log.InsertKey(vs.DmeTime_t(0), value, 3)
            layer.values[0] = value
        else:
            for i in range(count):
                layer.values[i] = value
        return True
    except Exception:
        return False

# -- Applies the RGB values into their respective channels --- #
def applyLightColor(animSet, r, g, b):
    a = get_working_animset(animSet)
    if a is None:
        return
    chR = getChannel(a, "color_red")
    chG = getChannel(a, "color_green")
    chB = getChannel(a, "color_blue")
    if not chR or not chG or not chB:
        return
    try:
        dm.StartUndo("ColorWheel", "ColorWheel", 0)
        setChannelAllKeys(chR, r)
        setChannelAllKeys(chG, g)
        setChannelAllKeys(chB, b)
        dm.FinishUndo()
        sfmApp.SetHeadTimeInFrames(sfmApp.GetHeadTimeInFrames())
    except Exception:
        pass

# -- Applies other property values into their respective channels --- #
def applyControlValue(animSet, controlName, value):
    a = get_working_animset(animSet)
    if a is None:
        return
    ch = getChannel(a, controlName)
    if ch is None:
        return
    try:
        dm.StartUndo("ColorWheel", "ColorWheel", 0)
        setChannelAllKeys(ch, value)
        dm.FinishUndo()
        sfmApp.SetHeadTimeInFrames(sfmApp.GetHeadTimeInFrames())
    except Exception:
        pass

# -- Applies boolean property values into their respective channels --- #
def applyBoolValue(animSet, controlName, value):
    try:
        a = get_working_animset(animSet)
        lightElem = a.light if a else None
        if lightElem is None:
            return
        dm.StartUndo("ColorWheel", "ColorWheel", 0)
        lightElem.SetValue(controlName, value)
        dm.FinishUndo()
        sfmApp.SetHeadTimeInFrames(sfmApp.GetHeadTimeInFrames())
    except Exception:
        pass

# -- Reads the value of a property's channel --- #
def readChannelValue(animSet, controlName, fallback=0.0):
    try:
        animSet = get_working_animset(animSet)
        if animSet is None:
            return fallback
        ch = getChannel(animSet, controlName)
        if ch is None:
            return fallback
        t = getSampleTime()
        try:
            return float(ch.log.GetValue(t))
        except Exception:
            pass
        layer = ch.log.GetLayer(0)
        if layer.GetKeyCount() > 0:
            try:
                return float(layer.values[0])
            except Exception:
                pass
        return fallback
    except Exception:
        return fallback

# -- Reads the value of a boolean property's channel --- #
def readBoolValue(animSet, controlName, fallback=False):
    try:
        animSet = get_working_animset(animSet)
        if animSet is None or animSet.light is None:
            return fallback
        return bool(animSet.light.GetValue(controlName))
    except Exception:
        return fallback


# == Color Wheel Widget === #
class COLORWheel(QtGui.QWidget):
    colorChanged = QtCore.Signal(QtGui.QColor)
    colorReleased = QtCore.Signal(QtGui.QColor)

    def __init__(self):
        super(COLORWheel, self).__init__()
        self.setMinimumSize(220, 220)
        self.setMaximumSize(220, 220)
        self._radius = 106
        self._selectorPos = QtCore.QPoint(110, 110)
        self._pendingColor = None
        self._generateWheel()
        self._applyTimer = QtCore.QTimer(self)
        self._applyTimer.setSingleShot(True)
        self._applyTimer.setInterval(40)
        self._applyTimer.timeout.connect(self._emitPending)

    def _generateWheel(self):
        r = self._radius
        img = QtGui.QImage(r * 2, r * 2, QtGui.QImage.Format_RGB32)
        bg = QtGui.QColor(40, 40, 40).rgb()
        for y in range(r * 2):
            for x in range(r * 2):
                dx, dy = x - r, y - r
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= r:
                    angle = math.degrees(math.atan2(-dx, dy))
                    if angle < 0:
                        angle += 360
                    c = QtGui.QColor()
                    c.setHsv(int(angle), int(dist / r * 255), 255)
                    img.setPixel(x, y, c.rgb())
                else:
                    img.setPixel(x, y, bg)
        self._cachedWheel = QtGui.QPixmap.fromImage(img)

    def paintEvent(self, event):
        try:
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            r = self._radius
            p.drawPixmap((self.width() - r * 2) // 2, (self.height() - r * 2) // 2, self._cachedWheel)
            sp = self._selectorPos
            p.setPen(QtGui.QPen(QtCore.Qt.white, 2))
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawEllipse(sp, 7, 7)
            p.setPen(QtGui.QPen(QtCore.Qt.black, 1))
            p.drawEllipse(sp, 9, 9)
        except Exception:
            pass

    def mousePressEvent(self, event):
        self._pick(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            self._pick(event.pos())

    def mouseReleaseEvent(self, event):
        if self._pendingColor is not None:
            self.colorReleased.emit(self._pendingColor)

    def _pick(self, pos):
        try:
            cx, cy = self.width() / 2.0, self.height() / 2.0
            dx, dy = pos.x() - cx, pos.y() - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > self._radius:
                a = math.atan2(dy, dx)
                dx, dy = math.cos(a) * self._radius, math.sin(a) * self._radius
                dist = self._radius
            self._selectorPos = QtCore.QPoint(int(cx + dx), int(cy + dy))
            self.update()
            angle_deg = math.degrees(math.atan2(-dx, dy))
            if angle_deg < 0:
                angle_deg += 360
            c = QtGui.QColor()
            c.setHsv(int(angle_deg), int(min(dist / self._radius, 1.0) * 255), 255)
            self._pendingColor = c
            if not self._applyTimer.isActive():
                self._applyTimer.start()
        except Exception:
            pass

    def _emitPending(self):
        if self._pendingColor is not None:
            self.colorChanged.emit(self._pendingColor)
            self._pendingColor = None

    def setSelectorFromColor(self, color):
        try:
            h, s, v, _ = color.getHsv()
            cx, cy = self.width() / 2.0, self.height() / 2.0
            if s == 0:
                self._selectorPos = QtCore.QPoint(int(cx), int(cy))
            else:
                d = (s / 255.0) * self._radius
                self._selectorPos = QtCore.QPoint(
                    int(cx - math.sin(math.radians(h)) * d),
                    int(cy + math.cos(math.radians(h)) * d),
                )
            self.update()
        except Exception:
            pass

# -- Brightness Slider --- #
class BrightnessSlider(QtGui.QWidget):
    valueChanged = QtCore.Signal(float)
    valueReleased = QtCore.Signal(float)

    def __init__(self, parent=None):
        super(BrightnessSlider, self).__init__(parent)
        self.setFixedWidth(18)
        self.setMinimumHeight(220)
        self._value = 1.0
        self._dragging = False

    def paintEvent(self, event):
        try:
            p = QtGui.QPainter(self)
            grad = QtGui.QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0.0, QtGui.QColor(255, 255, 255))
            grad.setColorAt(1.0, QtGui.QColor(0, 0, 0))
            p.fillRect(self.rect(), QtGui.QBrush(grad))
            y = int((1.0 - self._value) * self.height())
            p.setPen(QtGui.QPen(QtCore.Qt.white, 2))
            p.drawLine(0, y, self.width(), y)
            p.setPen(QtGui.QPen(QtCore.Qt.black, 1))
            p.drawLine(0, y + 2, self.width(), y + 2)
        except Exception:
            pass

    def mousePressEvent(self, event):
        self._dragging = True
        self._set(event.pos().y())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._set(event.pos().y())

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.valueReleased.emit(self._value)

    def _set(self, y):
        self._value = 1.0 - max(0.0, min(1.0, float(y) / self.height()))
        self.update()
        self.valueChanged.emit(self._value)

    def setValue(self, v):
        self._value = max(0.0, min(1.0, v))
        self.update()

    def getValue(self):
        return self._value

# -- Blender-styled slider bar --- #
class _BlenderBar(QtGui.QWidget):
    def __init__(self, ow):
        super(_BlenderBar, self).__init__(ow)
        self._ow = ow
        self.setFixedHeight(18)
        self.setMinimumWidth(80)
        self.setCursor(QtCore.Qt.SizeHorCursor)

    def paintEvent(self, event):
        try:
            ow = self._ow
            p = QtGui.QPainter(self)
            w, h = self.width(), self.height()
            p.fillRect(0, 0, w, h, QtGui.QColor(45, 45, 45))
            frac = max(0.0, min(1.0, (ow._value - ow._min) / (ow._softMax - ow._min)))
            if frac > 0:
                p.fillRect(0, 0, int(frac * w), h, QtGui.QColor(60, 90, 120, 180))
            p.setPen(QtGui.QPen(QtGui.QColor(220, 220, 220)))
            f = p.font()
            f.setPointSize(8)
            p.setFont(f)
            p.drawText(0, 0, w, h, QtCore.Qt.AlignCenter, ("%%.%df" % ow._decimals) % ow._value)
            p.end()
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            ow = self._ow
            ow._dragging = True
            ow._dragStartX = event.x()
            ow._dragStartVal = ow._value

    def mouseMoveEvent(self, event):
        try:
            ow = self._ow
            if not ow._dragging:
                return
            dx = event.x() - ow._dragStartX
            w = float(max(self.width(), 1))
            fine = (ow._softMax - ow._min) * w
            apx = abs(dx)
            sign = 1.0 if dx >= 0 else -1.0
            if apx <= fine:
                delta = sign * (apx / w) * (ow._softMax - ow._min)
            else:
                t = (apx - fine) / w
                delta = sign * ((ow._softMax - ow._min) + t * t * (ow._max - ow._softMax))
            ow._value = max(ow._min, min(ow._max, ow._dragStartVal + delta))
            self.update()
            ow._emitChanged()
        except Exception:
            pass

    def mouseReleaseEvent(self, event):
        self._ow._dragging = False
        self._ow._emitReleased()

    def mouseDoubleClickEvent(self, event):
        try:
            ow = self._ow
            edit = QtGui.QLineEdit(("%%.%df" % ow._decimals) % ow._value, self.parentWidget())
            edit.setFixedWidth(self.width())
            edit.setFixedHeight(self.height())
            edit.setStyleSheet("font-size:11px;background:#1a1a1a;color:#ddd;border:1px solid #555;")
            edit.move(self.mapTo(self.parentWidget(), QtCore.QPoint(0, 0)))
            edit.show()
            edit.setFocus()
            edit.selectAll()

            def commit():
                try:
                    ow._value = max(ow._min, min(ow._max, float(edit.text())))
                    self.update()
                    ow._emitChanged()
                    ow._emitReleased()
                except Exception:
                    pass
                edit.deleteLater()

            edit.editingFinished.connect(commit)
            edit.focusOutEvent = lambda e: (commit(), QtGui.QLineEdit.focusOutEvent(edit, e))
        except Exception:
            pass

# -- Property slider (label + bar) --- #
class PropertySliders(QtGui.QWidget):
    valueChanged = QtCore.Signal(float)
    valueReleased = QtCore.Signal(float)

    def __init__(self, label, minVal, maxVal, defaultVal, decimals=2, parent=None):
        super(PropertySliders, self).__init__(parent)
        self._min = float(minVal)
        self._max = 250.0
        self._softMax = float(maxVal)
        self._decimals = decimals
        self._value = float(defaultVal)
        self._dragging = False
        self._dragStartX = 0
        self._dragStartVal = 0.0
        lay = QtGui.QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.setLayout(lay)
        self._lbl = QtGui.QLabel(label)
        self._lbl.setFixedWidth(130)
        self._lbl.setStyleSheet("font-size:11px;")
        lay.addWidget(self._lbl)
        self._bar = _BlenderBar(self)
        lay.addWidget(self._bar)

    def getValue(self):
        return self._value

    def setValueSilent(self, v):
        self._value = max(self._min, min(self._max, float(v)))
        self._bar.update()

    def setTip(self, t):
        self._lbl.setToolTip(t)
        self._bar.setToolTip(t)

    def connectChanged(self, fn):
        self.valueChanged.connect(fn)

    def connectReleased(self, fn):
        self.valueReleased.connect(fn)

    def _emitChanged(self):
        self.valueChanged.emit(self._value)

    def _emitReleased(self):
        self.valueReleased.emit(self._value)

# -- Collapsible sections --- #
class CollapsibleSection(QtGui.QWidget):
    def __init__(self, title, parent=None):
        super(CollapsibleSection, self).__init__(parent)
        self._title = title
        vl = QtGui.QVBoxLayout()
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(2)
        self.setLayout(vl)
        self._btn = QtGui.QPushButton("[+] " + title)
        self._btn.setStyleSheet("text-align:left;font-size:11px;font-weight:bold;padding:2px;")
        self._btn.setFlat(True)
        self._btn.clicked.connect(self._toggle)
        vl.addWidget(self._btn)
        self._body = QtGui.QWidget()
        self._bodyLayout = QtGui.QVBoxLayout()
        self._bodyLayout.setContentsMargins(8, 0, 0, 4)
        self._bodyLayout.setSpacing(2)
        self._body.setLayout(self._bodyLayout)
        self._body.setVisible(False)
        vl.addWidget(self._body)

    def _toggle(self):
        v = not self._body.isVisible()
        self._body.setVisible(v)
        self._btn.setText(("[-] " if v else "[+] ") + self._title)

    def addWidget(self, w):
        self._bodyLayout.addWidget(w)

# -- Main window --- #
class ColorWheelWindow(QtGui.QWidget):
    def __init__(self, animSet):
        super(ColorWheelWindow, self).__init__()
        self.targetAnimSet = animSet
        self.setWindowTitle(ProductName)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setFixedWidth(340)

        inner = QtGui.QWidget()
        self._ml = QtGui.QVBoxLayout()
        self._ml.setSpacing(4)
        self._ml.setContentsMargins(8, 8, 8, 8)
        inner.setLayout(self._ml)
        scroll = QtGui.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        outer = QtGui.QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.setLayout(outer)
        self.setMinimumHeight(420)
        self.setMaximumHeight(700)

        pos = QtCore.QSettings("Aftre", "ColorWheel").value("windowPos")
        if pos:
            self.move(pos)

        ml = self._ml
        a0 = get_working_animset(animSet)
        lightName = a0.GetName() if a0 else "None"

        # -- Title + undo/redo --- #
        tr = QtGui.QHBoxLayout()
        tr.setContentsMargins(0, 0, 0, 0)
        tr.setSpacing(4)
        lbl = QtGui.QLabel("Color Wheel")
        lbl.setStyleSheet("font-size:14px;font-weight:bold;")
        tr.addWidget(lbl)
        tr.addStretch()
        ml.addLayout(tr)
        self._editingLabel = QtGui.QLabel("Editing: " + lightName)
        self._editingLabel.setStyleSheet("font-size:11px;")
        ml.addWidget(self._editingLabel)
        self._trackedAnimName = None
        if a0 is not None:
            try:
                self._trackedAnimName = a0.GetName()
            except Exception:
                self._trackedAnimName = None

        wr = QtGui.QHBoxLayout()
        wr.setSpacing(6)
        self.wheel = COLORWheel()
        self.wheel.colorChanged.connect(self.onColorChanged)
        self.wheel.colorReleased.connect(self.onColorReleased)
        wr.addWidget(self.wheel)
        self.brightnessSlider = BrightnessSlider()
        self.brightnessSlider.valueChanged.connect(self.onIntensityChanged)
        self.brightnessSlider.valueReleased.connect(self.onIntensityReleased)
        wr.addWidget(self.brightnessSlider, alignment=QtCore.Qt.AlignVCenter)
        ml.addLayout(wr)

        # -- HEX code and copy button --- #
        hr = QtGui.QHBoxLayout()
        self.hexLabel = QtGui.QLabel("#FFFFFF")
        self.hexLabel.setStyleSheet("font-size:12px;")
        self.hexLabel.mouseDoubleClickEvent = lambda e: self._startHexEdit()
        self.copyHexBtn = QtGui.QPushButton("Copy HEX")
        self.copyHexBtn.clicked.connect(self.copyHex)
        hr.addWidget(self.hexLabel)
        hr.addWidget(self.copyHexBtn)
        ml.addLayout(hr)

        win = self

        def S(label, mn, mx, dv, dc=2, ctrl=None, tip=None, maxOverride=None):
            sl = PropertySliders(label, mn, mx, dv, dc)
            if maxOverride is not None:
                sl._max = maxOverride
            if tip:
                sl.setTip(tip)
            if ctrl:
                sl.connectChanged(lambda v, c=ctrl: applyControlValue(win.targetAnimSet, c, v))
                sl.connectReleased(lambda v, c=ctrl: applyControlValue(win.targetAnimSet, c, v))
            return sl

        def boolRow(section, label, attr, tip, invert=False):
            row = QtGui.QHBoxLayout()
            row.setContentsMargins(0, 2, 0, 0)
            lb = QtGui.QLabel(label)
            lb.setStyleSheet("font-size:11px;")
            chk = QtGui.QCheckBox()
            chk.setChecked(False)
            chk.setToolTip(tip)

            fn = (
                (lambda s, a=attr: applyBoolValue(win.targetAnimSet, a, not bool(s)))
                if invert
                else (lambda s, a=attr: applyBoolValue(win.targetAnimSet, a, bool(s)))
            )
            chk.stateChanged.connect(fn)
            row.addWidget(lb)
            row.addStretch()
            row.addWidget(chk)
            section._bodyLayout.addLayout(row)
            return chk

        def sec(title, sliders, boolRows=None):
            section = CollapsibleSection(title)
            for sl in sliders:
                section.addWidget(sl)
            checks = [boolRow(section, *args) for args in (boolRows or [])]
            ml.addWidget(section)
            return checks

        # -- Properties Sections --- #
        # -- Intensity --- #
        self.s_intensity = S("Intensity", 0, 1, 1, 2, "intensity", "Controls how bright the light is.")
        sec("Intensity", [self.s_intensity])

        # -- Radius --- #
        self.s_radius = S("Radius", 0, 1, 1, 2, "radius", "Mimics a larger light source, softens shadows.")
        sec("Radius", [self.s_radius])

        # -- Field of View --- #
        self.s_hFov = S("Horizontal FOV", 0, 1, 1, 2, "horizontalFOV", "The horizontal width of the light cone.")
        self.s_vFov = S("Vertical FOV", 0, 1, 1, 2, "verticalFOV", "The vertical width of the light cone.")
        sec("Field of View", [self.s_hFov, self.s_vFov])

        # -- Shadows --- #
        self.s_shadowFilter = S("ShadowFilterSize", 0, 1, 1, 2, "shadowFilterSize", "Softens shadow edges.")
        self.s_shadowAtten = S("ShadowAtten", 0, 1, 0, 2, "shadowAtten", "Controls shadow darkness.")
        self.s_shadowDepth = S("shadowDepthBias", 0, 1, 0, 2, "shadowDepthBias", "Offsets shadow rendering.")
        self.s_shadowSlope = S("shadowSlopeScale", 0, 1, 1, 2, "shadowSlopeScaleDepthBias", "Narrows shadows at base.")
        (self.shadowsCheck,) = sec(
            "Shadows",
            [self.s_shadowFilter, self.s_shadowAtten, self.s_shadowDepth, self.s_shadowSlope],
            [("Disable Shadows", "castsShadows", "Toggles shadow casting on this light.", True)],
        )

        # -- Distance --- #
        self.s_minDist = S("minDistance", 0, 1, 0, 2, "minDistance", "Distance at which the light starts.")
        self.s_maxDist = S("maxDistance", 0, 1, 1, 2, "maxDistance", "Distance at which the light ends.")
        self.s_farZAtten = S("farZAtten", 0, 1, 1, 2, "farZAtten", "Far distance attenuation falloff.")
        sec("Distance", [self.s_minDist, self.s_maxDist, self.s_farZAtten])

        # -- Attenuation --- #
        self.s_constAtten = S("Constant", 0, 1, 0, 2, "constantAttenuation", "Brightness is constant across range.")
        self.s_linearAtten = S("Linear", 0, 1, 0, 2, "linearAttenuation", "Brightness drops steadily with distance.")
        self.s_quadAtten = S("Quadratic", 0, 1, 1, 2, "quadraticAttenuation", "Brightness drops faster with distance.")
        sec("Attenuation", [self.s_constAtten, self.s_linearAtten, self.s_quadAtten])
        
        # -- Volumetrics --- #
        self.s_volIntensity = S("volumetricIntensity", 0, 1, 1, 2, "volumetricIntensity", "Intensity of the volumetric effect.")
        self.s_noiseStr = S("noiseStrength", 0, 1, 0, 2, "noiseStrength", "Volumetric noise strength.", maxOverride=1.0)
        (self.volumetricsCheck,) = sec(
            "Volumetrics",
            [self.s_volIntensity, self.s_noiseStr],
            [("Enable Volumetrics", "volumetric", "Enables volumetric lighting (god rays).", False)],
        )

        # -- UberLights --- #
        self.s_width = S("width", 0, 1, 1, 2, "width", "Width of the uberlight shape.")
        self.s_edgeWidth = S("edgeWidth", 0, 1, 1, 2, "edgeWidth", "Softness of the uberlight width edges.")
        self.s_height = S("height", 0, 1, 1, 2, "height", "Height of the uberlight shape.")
        self.s_edgeHeight = S("edgeHeight", 0, 1, 1, 2, "edgeHeight", "Softness of the uberlight height edges.")
        (self.uberCheck,) = sec(
            "UberLights",
            [self.s_width, self.s_edgeWidth, self.s_height, self.s_edgeHeight],
            [("UberLight", "uberlight", "Enables UberLight on this light.", False)],
        )

        # -- Credits --- #
        ml.addStretch()
        credit = QtGui.QLabel("by Aftre")
        credit.setStyleSheet("color:#555;font-size:10px;")
        credit.setAlignment(QtCore.Qt.AlignRight)
        ml.addWidget(credit)

        self.currentR = self.currentG = self.currentB = 1.0
        self.brightnessScale = 1.0
        self._lastHeadFrame = -1
        self._lastSnapshot = {}
        self._loading = False

        self._playheadTimer = QtCore.QTimer(self)
        self._playheadTimer.setInterval(5)
        self._playheadTimer.timeout.connect(self._pollPlayhead)
        self._playheadTimer.start()
        self._loadFromLight()

    def closeEvent(self, event):
        try:
            QtCore.QSettings("Aftre", "ColorWheel").setValue("windowPos", self.pos())
        except Exception:
            pass
        super(ColorWheelWindow, self).closeEvent(event)

    def _resolveTarget(self):
        self.targetAnimSet = get_working_animset(self.targetAnimSet)
        return self.targetAnimSet

    def _pollPlayhead(self):
        try:
            if self._loading:
                return

            cur = None
            try:
                cur = sfm.GetCurrentAnimationSet()
            except Exception:
                cur = None

            if cur is not None:
                try:
                    new_name = cur.GetName()
                except Exception:
                    new_name = None
                if new_name != getattr(self, "_trackedAnimName", None):
                    self._trackedAnimName = new_name
                    self.targetAnimSet = cur
                    self._editingLabel.setText("Editing: " + (new_name or "None"))
                    self._lastHeadFrame = -1
                    self._lastSnapshot = {}
                    self._loadFromLight()
                    return

            self._resolveTarget()
            a = self.targetAnimSet
            if a is None:
                return

            frame = sfmApp.GetHeadTimeInFrames()
            t = getSampleTime()
            snap = {}
            for name in _POLL_CHANNELS:
                ch = getChannel(a, name)
                if ch:
                    try:
                        snap[name] = float(ch.log.GetValue(t))
                    except Exception:
                        pass
            if a.light:
                for b in _BOOL_NAMES:
                    try:
                        snap["__b_" + b] = bool(a.light.GetValue(b))
                    except Exception:
                        pass

            if frame == self._lastHeadFrame and snap == self._lastSnapshot:
                return
            self._lastHeadFrame = frame
            self._lastSnapshot = snap

            chR = getChannel(a, "color_red")
            chG = getChannel(a, "color_green")
            chB = getChannel(a, "color_blue")
            if chR and chG and chB:
                try:
                    r = float(chR.log.GetValue(t))
                    g = float(chG.log.GetValue(t))
                    b = float(chB.log.GetValue(t))
                    bright = max(r, g, b, 0.001)
                    nr = min(r / bright, 1.0)
                    ng = min(g / bright, 1.0)
                    nb = min(b / bright, 1.0)
                    self.currentR, self.currentG, self.currentB = nr, ng, nb
                    self.brightnessScale = min(bright, 1.0)
                    color = QtGui.QColor(int(nr * 255), int(ng * 255), int(nb * 255))
                    self.hexLabel.setText("#%02X%02X%02X" % (color.red(), color.green(), color.blue()))
                    self.wheel.blockSignals(True)
                    self.wheel.setSelectorFromColor(color)
                    self.wheel.blockSignals(False)
                    self.brightnessSlider.blockSignals(True)
                    self.brightnessSlider.setValue(self.brightnessScale)
                    self.brightnessSlider.blockSignals(False)
                except Exception:
                    pass

            for sl, ctrl in (
                (self.s_intensity, "intensity"),
                (self.s_radius, "radius"),
                (self.s_hFov, "horizontalFOV"),
                (self.s_vFov, "verticalFOV"),
                (self.s_shadowFilter, "shadowFilterSize"),
                (self.s_shadowAtten, "shadowAtten"),
                (self.s_shadowDepth, "shadowDepthBias"),
                (self.s_shadowSlope, "shadowSlopeScaleDepthBias"),
                (self.s_minDist, "minDistance"),
                (self.s_maxDist, "maxDistance"),
                (self.s_farZAtten, "farZAtten"),
                (self.s_constAtten, "constantAttenuation"),
                (self.s_linearAtten, "linearAttenuation"),
                (self.s_quadAtten, "quadraticAttenuation"),
                (self.s_volIntensity, "volumetricIntensity"),
                (self.s_noiseStr, "noiseStrength"),
                (self.s_width, "width"),
                (self.s_edgeWidth, "edgeWidth"),
                (self.s_height, "height"),
                (self.s_edgeHeight, "edgeHeight"),
            ):
                try:
                    ch = getChannel(a, ctrl)
                    if ch:
                        sl.setValueSilent(float(ch.log.GetValue(t)))
                except Exception:
                    pass

            def _sync_bool_chk(chk, key, invert):
                if key not in snap:
                    return
                try:
                    val = snap[key]
                    chk.blockSignals(True)
                    chk.setChecked((not val) if invert else val)
                    chk.blockSignals(False)
                except Exception:
                    try:
                        chk.blockSignals(False)
                    except Exception:
                        pass

            _sync_bool_chk(self.uberCheck, "__b_uberlight", False)
            _sync_bool_chk(self.volumetricsCheck, "__b_volumetric", False)
            _sync_bool_chk(self.shadowsCheck, "__b_castsShadows", True)
        except Exception:
            pass

    # -- Load values from current light --- #
    def _loadFromLight(self):
        try:
            self._loading = True
            self._lastHeadFrame = -1
            self._lastSnapshot = {}
            self._resolveTarget()
            a = self.targetAnimSet
            if a is None:
                return

            r = readChannelValue(a, "color_red", 1.0)
            g = readChannelValue(a, "color_green", 1.0)
            b = readChannelValue(a, "color_blue", 1.0)
            bright = max(r, g, b, 0.001)
            nr, ng, nb = r / bright, g / bright, b / bright
            self.currentR, self.currentG, self.currentB = nr, ng, nb
            self.brightnessScale = min(bright, 1.0)
            color = QtGui.QColor(int(nr * 255), int(ng * 255), int(nb * 255))
            self.hexLabel.setText("#%02X%02X%02X" % (color.red(), color.green(), color.blue()))
            self.wheel.blockSignals(True)
            self.wheel.setSelectorFromColor(color)
            self.wheel.blockSignals(False)
            self.brightnessSlider.blockSignals(True)
            self.brightnessSlider.setValue(self.brightnessScale)
            self.brightnessSlider.blockSignals(False)

            for sl, ctrl, fb in (
                (self.s_intensity, "intensity", 1.0),
                (self.s_radius, "radius", 1.0),
                (self.s_hFov, "horizontalFOV", 1.0),
                (self.s_vFov, "verticalFOV", 1.0),
                (self.s_shadowFilter, "shadowFilterSize", 1.0),
                (self.s_shadowAtten, "shadowAtten", 0.0),
                (self.s_shadowDepth, "shadowDepthBias", 0.0),
                (self.s_shadowSlope, "shadowSlopeScaleDepthBias", 1.0),
                (self.s_minDist, "minDistance", 0.0),
                (self.s_maxDist, "maxDistance", 1.0),
                (self.s_farZAtten, "farZAtten", 1.0),
                (self.s_constAtten, "constantAttenuation", 0.0),
                (self.s_linearAtten, "linearAttenuation", 0.0),
                (self.s_quadAtten, "quadraticAttenuation", 1.0),
                (self.s_volIntensity, "volumetricIntensity", 1.0),
                (self.s_noiseStr, "noiseStrength", 0.0),
                (self.s_width, "width", 1.0),
                (self.s_edgeWidth, "edgeWidth", 1.0),
                (self.s_height, "height", 1.0),
                (self.s_edgeHeight, "edgeHeight", 1.0),
            ):
                try:
                    sl.setValueSilent(readChannelValue(a, ctrl, fb))
                except Exception:
                    pass

            for chk, ctrl, fb, invert in (
                (self.uberCheck, "uberlight", False, False),
                (self.volumetricsCheck, "volumetric", False, False),
                (self.shadowsCheck, "castsShadows", True, True),
            ):
                try:
                    chk.blockSignals(True)
                    val = readBoolValue(a, ctrl, fb)
                    chk.setChecked(not val if invert else val)
                    chk.blockSignals(False)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self._loading = False

    def onColorChanged(self, color):
        try:
            if self._loading:
                return
            self._resolveTarget()
            self.currentR = color.red() / 255.0
            self.currentG = color.green() / 255.0
            self.currentB = color.blue() / 255.0
            self.hexLabel.setText("#%02X%02X%02X" % (color.red(), color.green(), color.blue()))
            self._applyToLight()
        except Exception:
            pass

    def onColorReleased(self, color):
        try:
            if self._loading:
                return
            self._resolveTarget()
            self._applyToLight()
        except Exception:
            pass

    def onIntensityChanged(self, v):
        try:
            if self._loading:
                return
            self._resolveTarget()
            self.brightnessScale = v
            self._applyToLight()
        except Exception:
            pass

    def onIntensityReleased(self, v):
        try:
            if self._loading:
                return
            self._resolveTarget()
            self._applyToLight()
        except Exception:
            pass

    def _applyToLight(self):
        try:
            s = self.brightnessScale
            applyLightColor(
                self.targetAnimSet,
                min(self.currentR * s, 1.0),
                min(self.currentG * s, 1.0),
                min(self.currentB * s, 1.0),
            )
        except Exception:
            pass

    # -- HEX value/copying --- #
    def _startHexEdit(self):
        try:
            edit = QtGui.QLineEdit(self.hexLabel.text(), self.hexLabel.parentWidget())
            edit.setFixedWidth(self.hexLabel.width())
            edit.setFixedHeight(22)
            edit.setStyleSheet("font-size:11px;")
            edit.move(self.hexLabel.mapTo(self.hexLabel.parentWidget(), QtCore.QPoint(0, 0)))
            edit.show()
            edit.setFocus()
            edit.selectAll()

            def commit():
                try:
                    txt = edit.text().strip()
                    if not txt.startswith("#"):
                        txt = "#" + txt
                    c = QtGui.QColor(txt)
                    if c.isValid():
                        self.wheel.blockSignals(True)
                        self.wheel.setSelectorFromColor(c)
                        self.wheel.blockSignals(False)
                        self.currentR = c.red() / 255.0
                        self.currentG = c.green() / 255.0
                        self.currentB = c.blue() / 255.0
                        self.hexLabel.setText("#%02X%02X%02X" % (c.red(), c.green(), c.blue()))
                        self._resolveTarget()
                        self._applyToLight()
                except Exception:
                    pass
                edit.deleteLater()

            edit.editingFinished.connect(commit)
            edit.focusOutEvent = lambda e: (commit(), QtGui.QLineEdit.focusOutEvent(edit, e))
        except Exception:
            pass

    def copyHex(self):
        try:
            QtGui.QApplication.clipboard().setText(self.hexLabel.text())
        except Exception:
            pass

try:
    currentAnimSet = sfm.GetCurrentAnimationSet()
    existing = globals().get(InternalName)
    if existing is not None:
        try:
            existing.close()
        except Exception:
            pass
    tool = ColorWheelWindow(currentAnimSet)
    globals()[InternalName] = tool
    tool.show()

except Exception as e:
    print("[Color Wheel] Failed to launch: %s" % e)
