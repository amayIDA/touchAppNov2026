# S3 Touch Studio

## Windows application and touch slideshow

Run **release/S3-Touch-Studio.exe** for the standalone Windows app. It includes its own runtime and opens in full screen without a browser address bar. Node.js and a separate browser are not required. **Esc** returns to a normal app window, **F11** toggles full screen, and **Controls** opens sensor and content settings. Close the app with the window close button or Alt+F4.

**Touch slideshow / Stories** opens a gallery of the same three sample images. Tap a thumbnail to open its large picture with information alongside it. **Swap sides** moves the picture between left and right; tap the large picture to hide/reveal its information; **All pictures** returns to thumbnails. **Slideshow** automatically advances every eight seconds; Previous, Next and Pause also work by touch. LiDAR selection uses a short hold and requires lifting the hand before the next selection.

Edit the title and description under **Edit slide information** on the control screen. Adding your own picture also adds it to the gallery. Content is stored locally in the app's profile. Key **5** opens Stories; keys **1–4** retain the existing experiences.

The Windows package seeds its first launch with the current local sensor calibration. Later changes are saved in the app's user-data folder. If the local web demo is already running, the app uses that existing connection and calibration. Otherwise it starts its own local sensor service. Keep Frame Grabber scanning with Multitouch → TUIO enabled when using TUIO input.

To build the executable from source: `npm ci`, then `npm run package:windows`. The portable executable is generated under `release/`, which is excluded from Git. The packaged app contains the native LiDAR bridge; build tools, SDK sources, logs and development dependencies are excluded.

A local LED touch demonstration for SLAMTEC RPLIDAR S3. Double-click **Start Touch Demo.bat**, or run `npm start`, and open http://localhost:4173.

## Ready-to-test full-screen demo

Double-click **Start Full Screen Demo.bat** to open the dedicated LED view in an Edge app window with full-screen startup. The launcher starts the local server if needed and reconnects using the saved sensor settings. If the browser keeps its window border, click **Enter full screen** or press **F11**. Move this window to the LED output before calibrating; Windows+Shift+Arrow can move a window between monitors.

On 13 November 2026 the physical S3 was successfully connected directly over **UDP, 192.168.11.3:8089**, with approximately **2,964 valid scan points per revolution at 10 Hz**. These settings are saved in the local configuration. A background was recorded with no foreground clusters present. The physical on-surface target calibration still requires the operator to touch the targets on the final LED output.

The control screen also has **Start full screen**, which expands the current view without opening another tab. The bottom display controls let you switch experiences, calibrate, or return to the controls. Keys **1–4** choose Ripple, Light trails, LED tiles and Picture reveal; **F** toggles full screen; **C** opens controls; **Esc** exits browser full screen.

**Picture reveal:** touch to reveal a full-screen landscape, lift your hand and touch again to cycle through three original sample artworks. The picture remains visible while touching and for a few seconds afterwards. Use **Add your own picture** to select a JPG, PNG or WebP from this PC; it is saved in this browser and shared with display windows in the same browser profile. **Use sample pictures** restores the included artwork. Native touchscreen input works directly; mouse input requires the labelled Pointer preview switch. LiDAR input stays active in the normal display mode.

## Use with your existing Frame Grabber

1. Keep SLAMTEC Frame Grabber scanning your S3.
2. Enable **Multitouch → TUIO** in Frame Grabber. Its current TUIO port is **3333**.
3. In this app choose **Frame Grabber · TUIO** and click **Connect sensor**. The status changes to live only when actual TUIO frames arrive.
4. Click **Open LED display**, move the new browser window to the LED screen, and enter full screen using its top-right button.
5. Run **Guided self-calibration** from the control window. With one hand in the laser plane, touch each target and hold still until captured. Remove your hand between targets. The fifth target checks the centre before saving.

This path receives real S3 touches through Frame Grabber. It does not show raw scans or report a raw scan rate; the displayed frequency is the received TUIO frame rate. Upstream Frame Grabber detection settings, range and screen crop still apply. Ensure the entire physical screen is included in its input region. Its mouse emulation can be disabled to prevent unintended desktop clicks.

## Connect directly to the S3

Stop scanning in Frame Grabber before using a direct connection. Choose network TCP, network UDP, or USB/serial. Use the IP, port and protocol configured for your network adapter. Frame Grabber currently shows **192.168.11.3:8089**; confirm its selected TCP/UDP protocol. These are observed settings, not an assumption about every S3. USB S3 connections use **1,000,000 baud**.

Direct connections use the official SLAMTEC C++ SDK and its typical scan mode. The compiled Windows bridge is included at `bin/lidar-bridge.exe`.

For direct mode:

1. Connect and wait for live scans.
2. Clear all hands and objects from the touch area and click **Record**. Empty scans are learned over at least two seconds.
3. Open the LED display and run guided calibration.
4. Try Ripple, Light trails, or LED tiles. Changes also apply to an open LED display window.

**Physical alignment:** the scan plane must pass just in front of and approximately parallel to the surface, covering every target. Calibration corrects in-plane position, rotation, flips and projective skew. It cannot correct a scan plane that misses part of the screen. Recalibrate and record a new background after moving the LiDAR. A 2D LiDAR detects intersections with its scan plane, not physical contact or pressure.

Calibration captures stable single-hand clusters, requires hand release between targets, and checks the centre against an 8% screen-distance tolerance. The app rejects crossed, repeated or degenerate corner captures. Calibration and connection preferences are saved locally in `data/config.json`; the background is learned again after every direct reconnect. This is a client demo, not a precision touch certification.

Manual calibration is available: record the background, then capture or click the physical screen corners in the scan view, in the stated order. TUIO mode displays normalized coordinates scaled to a 0–1000 grid, rather than millimetres.

Pointer preview is an explicitly labelled visual preview and pauses sensor rendering in that particular window. It is off by default, and does not broadcast simulated touches or save calibration.

## Development

Requires Node.js 20 or later. No npm dependencies or install step is required. Run `npm test` for geometry, foreground detection, tracking and TUIO protocol checks.

To rebuild the native bridge, use `npm run build:bridge`. The build script uses the portable Zig 0.13.0 compiler at `.tools/zig-windows-x86_64-0.13.0/zig.exe` and the official SDK checkout at `vendor/rplidar_sdk`. Both were downloaded from their official sources. SDK source is licensed under BSD-2-Clause; see `vendor/rplidar_sdk/LICENSE` and `THIRD-PARTY-NOTICES.txt`. Application adapter code is original; vendor demo code was not copied.

The server listens on this PC only (127.0.0.1:4173). Its TUIO listener also binds locally. No sensor data is uploaded. External font loading is optional and has local fallbacks. Stop the launcher with Ctrl+C to close the sensor connection.

References: [SLAMTEC official SDK](https://github.com/Slamtec/rplidar_sdk), [TUIO 1.1 protocol](https://www.tuio.org/?specification).
