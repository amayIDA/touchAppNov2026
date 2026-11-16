# TouchScreen Admin

Keep the TouchScreenAdmin folder beside the TouchScreen folder. Launch TouchScreenAdmin.exe, then:

1. Click a card, button label, heading line, or footer in the visual preview. The Edit heading button selects the title/subtitle group directly. Use the view selector for the standby invitation.
2. Select its text field on the right. Arabic and English fields are independently editable.
3. Change the wording, font size, bold setting or text color. The preview updates immediately.
4. Click Save to exhibit (Ctrl+S). The running exhibit reloads the saved content within one second; no rebuild or restart is required.

The content file path is displayed at the top. The admin automatically targets ../TouchScreen/content.json when available. Use Open content file to target another installation. If moved away from the exhibit, the admin edits its local content.json; choose the exhibit's file explicitly to apply changes there.

Font sizes are design pixels at the exhibit's 1600 x 703 reference resolution and scale with the screen. Text automatically shrinks to stay inside the card; Requested and Displayed sizes explain when this happens. Shorten long wording to allow a larger displayed font. Card positions, reveal/collapse interactions, TUIO calibration and animations remain controlled by the exhibit. Preview uses a still video frame and shows all cards for editing; the exhibit still begins with cards hidden.

Each save preserves the previous content file as content.json.bak. Revert selected card restores the last saved version of that card. Unsaved edits are checked when closing the admin. Invalid content is rejected, and the running exhibit keeps its last valid content if a reload fails.

Both applications share content_model.py for layout and typography. All statistic values, units, Arabic/English descriptions, system button names, header/subtitles, invitation and footer wording are editable. The old video's baked heading, button labels and footer are covered by editable replacements, so edited text never sits on top of the original wording. The title is drawn transparently over a cleaned copy of the background video; no rectangular sky mask is drawn. The original video remains unchanged.

Source: admin.py. Build: powershell -File build_admin.ps1. Integration verification: python verify_admin.py (uses a temporary content file and does not modify the installation).

Client baseline: original PDF artwork now supplies the default cards, numbers, percentages, header and labels. The client fonts are the only available weights: Bahij Black, ExtraBold and Plain. Number, raised plus sign and currency are separate fields. Saving edits replaces only that field while keeping surrounding artwork. Long replacement wording may need a smaller font or explicit line breaks. Original client layers remain the baseline until edited. The overall artboard is 1600 x 696, matching the reference image.
