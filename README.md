# 🎨 [SFM] Color Wheel Tool

A Color Wheel tool for Source Filmmaker built using **Python**.

This script adds a Color Wheel + light properties system to the rigs section of your lights in Source Filmmaker, allowing you to change light colors and other settings from there instead of relying on SFM’s default RGB sliders.

The color wheel and sliders are inspired by Blender system. This tool introduces a more intuitive and efficient way to modify your lights.

## ✨ Features

- Interactive color wheel
- Vertical RGB brightness slider
- Colors on the wheel that compensates SFM's light desaturation
- Real-time color update
- HEX code display and copy button (idea by: Dani3D)
- Editable values by double-clicking
- Tooltips for each property when hovering
- Property sliders now work like in Blender, reaching values beyond the usual 0-1 range, with a maximum of 250
- Organized sections for each light property
  - Intensity
  - Radius
  - Field of View
  - Shadows
  - Distance
  - Attenuation
  - Volumetrics
  - UberLights
- No more switching between multiple SFM sliders, everything is in a single clean interface.

---

## 📂 Structure

```
color_wheel.py
```

---

## 📦 Installation

- **(1) Locate your SFM usermod scripts folder**
```
SteamLibrary/steamapps/common/SourceFilmmaker/game/usermod/scripts/sfm/animset/
```
- **(2) Place the script**
```
color_wheel.py
```
- **(3) Run the script in SFM**
  - Open Source Filmmaker
  - Spawn a light
  - Right click on the light
  - Go to the "rig" section
  - Run the "color_wheel" script

 ---

 ## 📝 Credits

- Script inspired by Fames, msu355, and an0nymooose (fixes & implementations)
- HEX code idea by Dani3D
- Early testing & feedback: Bone, Cuori, HyperBlender, Shydo, Trap & Hat

If you have any bugs or suggestions, feel free to reach out.
