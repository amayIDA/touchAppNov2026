# Dual Lidar Touch Studio — Demo SDK

Run DualLidarTouch.exe and keep its entire folder together. This version uses the native SLAMTEC SDK bridge supplied in your lidar-touch-demo archive and follows its background subtraction, hand clustering and guided calibration approach. Close FrameGrabber and other direct lidar controllers first.

## Setup

1. Connect both lidars. Defaults are 192.168.11.2 and 192.168.11.3, UDP 8089. The PC was tested at 192.168.11.10. Confirm which address belongs to each physical corner; the network cannot identify left versus right.
2. Open Calibrate and clear all hands and moving objects from the scan plane. Click Record empty background (both, 2 seconds). Both must show Background ready. Reconnecting requires recording a fresh background.
3. Select the first sensor. Watch the raw hand count: it should change from zero to one when you put a finger/hand into the scan plane. Raw detection works before any screen calibration or guessed dimensions.
4. Click Guided calibration: corners + 12 tests. Touch and hold each target with one fingertip until captured, then lift completely before touching the next target. Hold still for about one second. Keep other hands and sleeves outside the scan plane. Repeat for the other sensor.
5. Run Fullscreen touch test. Check edges, corners and overlap. A single finger should show one stable contact. Both sensors default to whole-screen coverage; coverage can be restricted if one cannot reliably see an area.
6. Enable TUIO on 127.0.0.1:3333, then launch the touchscreen exhibit. Keep the controller running behind it. This sends TUIO contacts; it does not install a Windows touchscreen driver.
7. Save the profile. Moving sensors requires calibration again. A changed scene requires a fresh empty background. Existing profiles from the previous detector are backed up as .before-demo-sdk.json and obsolete guessed mappings are cleared.

The guided flow asks for four corner targets in order: top left, top right, bottom right, bottom left. These determine rotation and perspective automatically without physical screen dimensions. Twelve random targets, spread across twelve screen regions, then validate the mapping. Only touches within 2.5% of the shorter display dimension (minimum 18 pixels) of the highlighted target advance. Lift between targets. After all twelve pass, the mapping is saved and TUIO enabled automatically. This acceptance tolerance is not a physical finger-accuracy certification. Contacts outside the mapped screen are ignored. Repeat for the other sensor. The sensors must physically see all required targets; software cannot extend their range.

## Mounting and tuning

Both sensors are at the bottom corners. Their scan planes must lie just in front of and parallel to the screen so a fingertip intersects the beams on contact. A 2D lidar cannot distinguish contact from a hovering finger in the same scan plane. Software cannot correct incorrect physical plane alignment or beam spacing wider than a fingertip.

Demo defaults: foreground separation 60 mm, minimum 3 rays, cluster gap 100 mm and maximum hand radius 160 mm. Foreground separation measures radial distance from the learned scene, not distance from the glass. If no raw hand appears, inspect the live scan, background and physical plane before calibrating. Lower minimum rays can help sparse fingertips but may admit noise. Recording a hand as background prevents it being detected there.

The controller merges observations from different sensors and maintains contact IDs. Excessive overlap merge distance can combine separate fingers; insufficient distance can create duplicate contacts. Output only uses fresh, background-ready, calibrated sensors. Changing display resolution requires calibration again.

## Files and verification

Keep lidar-profile.json and its associated background .npy files together. Third-party notices for the supplied SDK bridge are included. Source is in lidar_touch/engine.py and studio.py; build using build_lidar.ps1.

Verification covers detector parity with the supplied JavaScript demo, synthetic guided calibration, TUIO reception by the exhibit, and real SDK scans from both connected sensors. These checks establish software behavior and connectivity; physical fingertip accuracy must be checked during installation.
