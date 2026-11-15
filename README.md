<h1 align="center">Color Wheel Tool v1.3.1</h1>

<p align="center">
  A color and light attributes editor for Source Filmmaker.
</p>

<p align="center">
  <strong>Python + PySide</strong>
</p>

Choose a color, adjust light properties and see the result in SFM as you drag. Color Wheel opens from a light's **Rig** menu, loads its current settings and keeps the color picker above the light controls in one narrow window. Only the light property categories are collapsible.

[Get started](#get-started) · [Features](#features) · [Controls](#controls) · [Behavior and limits](#behavior-and-limits) · [Contribute](CONTRIBUTING.md) · [Credits](#credits-and-support)

<a id="get-started"></a>

## ◆ Get started

You need the Windows version of **Source Filmmaker** (obviously). The script uses SFM's bundled Python and PySide, you don't need to install any Python packages separately.

**Steam Workshop:** [Download Color Wheel Tool](https://steamcommunity.com/sharedfiles/filedetails/?id=3685997821).

**Manual installation from GitHub:**

1. **Download the source.** Use **Code > Download ZIP** on this repository, then extract it.
2. **Install the script.** Copy the downloaded `scripts` folder into SFM's `game/usermod` folder, merging the folders if asked. The final file must be here:

   ```text
   SteamLibrary/steamapps/common/SourceFilmmaker/game/usermod/scripts/sfm/animset/color_wheel.py
   ```

3. **Open it on a light.** In an SFM session, create or select a light in the Animation Set Editor. Switch to **Motion Editor** or **Graph Editor**, right-click the light and choose **Rig > color_wheel**. Check the **Editing:** label to confirm the target.

The window stays attached to the light used to open it. To edit another light, run **Rig > color_wheel** on that light (the previous window is replaced). Selecting another animation set alone doesn't change the target.

**This is a static light editor.** Changes also replace existing animated values in the edited channels. Read [Behavior and limits](#behavior-and-limits) before using it on an animated light!

<a id="features"></a>

## ◆ Your light controls

| Feature | What it does |
| --- | --- |
| **More tools** | Use the three-dot button beside undo/redo to show or hide HEX, picker styles, color models and component fields. These tools start collapsed to save space. |
| **Color selectors** | Switch between Wheel, Ring, Square and Triangle using the icons below the picker. |
| **RGB / HSV / HSL** | Enter color components in the selected color model. Component fields display one decimal place. |
| **Brightness and HEX** | Adjust color brightness with the vertical gradient, enter a six-digit HEX color or use **Copy HEX**. |
| **Light properties** | Adjust native SFM controls in collapsible sections below the picker. Each numeric slider has copy and paste buttons. |
| **Undo / redo** | Restore a completed slider or picker drag in one step by using the arrow buttons or keyboard shortcuts. |
| **Set to Default** | Restore the light's SFM control defaults in one undo action. The button sits below the color controls and above Intensity. |

<details>
<summary><strong>▸ Available property sections</strong></summary>

| Section | Controls |
| --- | --- |
| **Intensity** | `Intensity`, `ambientIntensity` |
| **Radius** | `Radius` |
| **Field of View** | `Horizontal FOV`, `Vertical FOV` |
| **Shadows** | `Disable Shadows`, `ShadowFilterSize`, `ShadowAtten`, `shadowDepthBias`, `shadowSlopeScale` |
| **Distance** | `minDistance`, `maxDistance`, `farZAtten` |
| **Attenuation** | `Constant`, `Linear`, `Quadratic` |
| **Volumetrics** | `Enable Volumetrics`, `volumetricIntensity`, `noiseStrength` |
| **UberLights** | `UberLight`, `width`, `edgeWidth`, `height`, `edgeHeight` |

The names above match the labels in the window. Hover over a property for its tooltip. Controls unavailable on the current light are disabled.

</details>

<a id="controls"></a>

## ◆ Mouse and keyboard

| Control | Action |
| --- | --- |
| **More tools (three dots)** | Expand or collapse the extra color controls. The window adjusts its height while keeping the light properties accessible. |
| **Drag the picker** | Choose a color with live updates in SFM. |
| **Drag the vertical gradient** | Change color brightness. This is separate from the light's Intensity property. |
| **Drag a property slider** | Adjust its value and release to finish one history action. |
| **Double-click a property slider** | Type a numeric value directly. |
| **Copy / paste icons** | Copy a slider's numeric value or paste a number from the clipboard. |
| **Ctrl+Z** | Undo one script edit. |
| **Ctrl+Y / Ctrl+Shift+Z** | Redo one script edit. |

**History shortcuts work while Color Wheel has keyboard focus.** Text fields retain their own text undo. The arrow buttons are disabled when there is no available action, and holding a shortcut doesn't repeatedly replay the history.

<details>
<summary><strong>▸ Color values and HEX</strong></summary>

RGB fields use values from 0 to 1. HSV and HSL use degrees for hue and percentages for the other components. Displaying RGB with one decimal doesn't round the other stored components when you edit a single field.

HEX represents the base color before the separate brightness multiplier. Entering a HEX color keeps the current brightness, so the resulting light RGB can differ from the HEX value when brightness is below 100%.

</details>

<a id="behavior-and-limits"></a>

## ◆ Behavior and limits

**Motion Editor and Graph Editor use the same static editing behavior.** A property edit writes one value across the existing samples in that channel's base log layer. It can flatten an existing animated curve. Empty channels receive a static default; the script doesn't insert keyframes or change sample times, bookmarks or interpolation.

The window is disabled in **Clip Editor**. It doesn't follow SFM's time selection or provide frame-specific animation editing.

Undo and redo use the current window's own history with one entry per completed gesture. They refresh the light as well as restoring its stored values. Closing or reopening the window clears that history and all edits made outside the script can invalidate recorded actions. These buttons and shortcuts aren't a browser for SFM's global undo history.

<details>
<summary><strong>▸ If something is unavailable</strong></summary>

- **The script is missing from Rig:** check the installation path above. Close the old Color Wheel window after updating the file, then reopen it from Rig. Restart SFM if its menu hasn't picked up the installation.
- **The controls are disabled:** switch to Motion Editor or Graph Editor. If the light or session was closed, reopen the script from a valid light's Rig menu.
- **A property has little visible effect:** check the light's native SFM settings and the relevant shader support. The tool edits SFM's controls, it doesn't replace the renderer.
- **A change fails:** include the `[Color Wheel]` messages from SFM's console when reporting the problem.

</details>

<a id="contribute"></a>

## ◆ Contribute

Bug reports, documentation improvements, UI feedback and code contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, the code map and checks to run before opening a pull request.

The script lives at [`scripts/sfm/animset/color_wheel.py`](scripts/sfm/animset/color_wheel.py) and runs inside SFM. There isn't a separate build step or standalone app to launch.

<a id="credits-and-support"></a>

## ◆ Credits and support

- **Author:** Aftre.
- **Code credits:** Fixes and implementations in this script were based on code by Fames, msu355 and an0nymooose.
- **HEX code idea:** Dani3D.
- **Slider remapping idea:** Higglemug McGiggletoot.
- **Early testing and feedback:** Bone, Cuori, HyperBlender, Shydo and Trap & Hat.

For a bug or idea, [open an issue](https://github.com/Atfre/color-wheel-tool/issues) with your Color Wheel version, timeline editor and steps to reproduce it. See the [contribution guide](CONTRIBUTING.md#report-a-bug-or-suggest-a-change) for useful details to include.
