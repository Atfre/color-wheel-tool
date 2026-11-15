# Contributing to Color Wheel Tool

You can help by reporting a bug, testing the tool in SFM, improving the documentation or contributing code. Start with the [README](README.md#get-started) if you want to install and use the tool.

[Report a problem](#report-a-bug-or-suggest-a-change) · [Run locally](#run-locally) · [Code map](#find-the-code) · [Checks](#verify-a-change) · [Pull requests](#open-a-pull-request) · [AI policy](#ai-policy)

<a id="report-a-bug-or-suggest-a-change"></a>

## ◆ Report a bug or suggest a change

Check existing issues and pull requests first. For a larger feature or a change to how light values are written, discuss the idea in an issue before implementing it.

A useful bug report includes:

- The Color Wheel version shown in the window title and your SFM and Windows versions.
- The timeline editor in use: Clip, Motion or Graph.
- Steps to reproduce the problem, the expected result and what actually happened.
- Whether the light already had animated values and which control you edited.
- Relevant `[Color Wheel]` console messages, plus a screenshot or short recording when the issue is visual.

For crashes, say whether it happened during a drag, on release, during undo/redo or while closing the window or session. Remove private information from logs and captures. A minimal session or reproduction is more useful than an entire project.

<a id="run-locally"></a>

## ◆ Run locally

Use **Source Filmmaker** with its bundled **Python 2.7, PySide and Qt 4** runtime. The `sfm`, `sfmApp` and `vs` bindings require SFM's running session (launching the script with a normal Python interpreter isn't a runtime test).

1. Fork or clone the repository and create a branch for your change.
2. Edit [`scripts/sfm/animset/color_wheel.py`](scripts/sfm/animset/color_wheel.py).
3. Copy that file into your SFM installation at `game/usermod/scripts/sfm/animset/color_wheel.py`.
4. Open any SFM session with a light. Close any existing Color Wheel window and launch the updated script through **Rig > color_wheel**.

```powershell
git clone https://github.com/Atfre/color-wheel-tool.git
cd color-wheel-tool
git switch -c fix/describe-the-change
```

Keep your work in the repository and copy the script into SFM when testing. Don't commit local sessions, crash dumps, backups, generated `.pyc` files or machine-specific installation paths. Installing or testing the tool doesn't require adding packages to SFM's Python environment.

<a id="find-the-code"></a>

## ◆ Find the code

The implementation is currently contained in one file:

| Area | Entry points |
| --- | --- |
| Channel access and static writes | `getChannel`, `getChannelInput`, `readCurrentChannelValue`, `setChannelAllKeys` |
| Color selection and brightness | `ColorPicker`, `BrightnessSlider` |
| Numeric input, clipboard and sections | `_SliderBar`, `PropertySliders`, `CollapsibleSection` |
| Window layout and current light values | `ColorWheelWindow.__init__`, `_pollPlayhead`, `_syncSnapshot` |
| Queued light edits and native defaults | `_queueEdit`, `_flushPending`, `_readLightDefaults` |
| Script history and keyboard routing | `_captureHistory`, `_finishHistory`, `_replayHistory`, `ColorWheelWindow.event` |
| Rig entry point and window lifetime | `showColorWheel`, `_resolveTarget`, the show/hide/close handlers |

Light edits are batched by a timer while dragging. The window remains bound to the light used to launch it, validates the document and channel before writing and records Python values for its own undo/redo history.

### ◇ Keep changes focused

- Preserve Python 2.7 and PySide/Qt 4 compatibility. Python 3-only syntax and PySide2/PySide6 imports won't run in this runtime.
- Follow the surrounding style. Use clear names and short comments for constraints that need explaining. Preserve the author's section comments and credits. Avoid unrelated formatting or renaming passes.
- Keep native SFM and Qt access on the UI thread. Avoid heavy work in mouse handlers, paint events or polling callbacks.
- Preserve document/light lifetime checks, bounded history and edit batching. Don't retain native element proxies in undo records or open a separate native undo transaction for every mouse move.
- Keep a completed drag as one script history action. Preserve text-field undo and the distinction between script history and SFM's global history.
- Preserve static channel editing unless a separate behavior change has been discussed. Don't introduce key insertion, deletion or time-selection editing as part of an unrelated fix.
- Include the source and applicable license information when introducing third-party code or assets and retain existing attribution.

<a id="verify-a-change"></a>

## ◆ Verify a change

For documentation-only changes, check wording, local paths and links. For script changes, check whitespace and Python 2.7 syntax, then test the affected behavior inside SFM.

Run these commands from the repository root. Adjust `$sfmGame` to your installation:

```powershell
git diff --check
$sfmGame = 'C:\Program Files (x86)\Steam\steamapps\common\SourceFilmmaker\game'
& "$sfmGame\sdktools\python\2.7\win32\python.exe" -c "compile(open('scripts/sfm/animset/color_wheel.py', 'rb').read(), 'color_wheel.py', 'exec')"
```

The compile check doesn't execute the script or validate its native bindings. The repository currently has no bundled automated SFM integration suite. Report the manual checks you actually ran and say when a check couldn't be performed.

Use a disposable session: changing a property can replace existing animated values throughout its base channel layer!

| Change or area | Check inside SFM |
| --- | --- |
| Opening and targeting | Launch from a light's Rig menu. Confirm existing values load without changing the light. Selecting a different animation set must not retarget the open window. |
| Color and layout | Exercise Wheel, Ring, Square and Triangle, RGB, HSV and HSL, brightness and HEX. Only light property categories should be collapsible; color controls stay directly in the window. Check the narrow window with More tools open and closed, including expanded property sections, for clipped labels or inaccessible controls. With no pending edits, toggling More tools must not change light values or create history actions. |
| Light properties | Drag, type, copy and paste values. Reach a slider limit and reverse direction to check that it responds immediately. Check native toggles and that changes remain live while dragging. |
| History and shortcuts | Complete a long picker or slider drag. One undo must restore its starting values and one redo its final values. The evaluated light must match both. Check the buttons: Ctrl+Z, Ctrl+Y and Ctrl+Shift+Z, including empty history and focused text fields. |
| Defaults | Use Set to Default, check the light's native defaults, then undo and redo the reset as one action. |
| Timeline behavior | Check both Motion and Graph. Existing samples should receive the edited static value without inserting or removing keys or changing their times. Confirm Clip Editor blocks editing and cancels an open numeric editor without committing its pending text. |
| Window and session lifetime | Close, hide and reopen the window. Reopen from another light. Delete the target light or close the session. Check that stale targets can't receive queued writes. |

When changing a shared path such as `_flushPending` or history replay, check the other controls that use it as well. For a rendering-related report, distinguish the value stored on the native light from what a particular shader displays.

<a id="ai-policy"></a>

## ◆ AI policy

AI assistance **doesn't** replace contributor responsibility. These rules apply to code, documentation, tests and contribution messages:

- **No AI slop or unreviewed changes.** If you submit AI-generated code or text **without** human review and cleanup, you'll be blocked from contributing. Examples include overly verbose text, unnecessary comments, overcomplicated code, failure to follow project conventions and other signs of minimal human involvement.
- **Disclose all AI use.** Name the tools you used and explain what they helped produce in your issue or pull request.
- **Understand the change.** You must be able to explain every submitted change and its effect on SFM without relying on the tool to answer for you.
- **Review and verify.** Check generated output against the actual Python 2.7/PySide APIs and run the relevant checks. Don't claim tests or results you didn't observe.
- **Follow the project.** Remove unnecessary abstractions, repetitive prose and redundant comments. Preserve existing credits and the author's section comments.
- **Write your own report.** Keep issues and pull request descriptions concise, specific and based on your observations. Don't paste unreviewed generated text or automated review replies.

Unreviewed generated submissions may be closed. Any violation of this policy may result in a contribution block. Cleaning up wording doesn't remove the disclosure requirement.

<a id="open-a-pull-request"></a>

## ◆ Open a pull request

Keep each pull request about one problem or feature. Write the description and documentation in English, consistent with the project, and include:

1. **The problem and result:** what triggers the issue and how the change behaves.
2. **The scope:** which controls or shared paths changed and why.
3. **Verification:** syntax checks and the SFM scenarios you tested with the relevant versions.
4. **Visual evidence:** before/after captures for layout or interaction changes, using a simple scene.

Update the README when installation, controls or behavior change. Avoid version bumps unless they're part of an agreed release. Review your diff for unrelated edits and local files before submitting it.

For contributor acknowledgments, see the [project credits](README.md#credits-and-support). Keep those credits when redistributing or modifying the documented source.
