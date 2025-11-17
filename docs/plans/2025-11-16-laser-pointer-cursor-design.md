# Laser Pointer Cursor Design

**Date:** 2025-11-16
**Platform:** Windows Desktop
**Purpose:** Permanent cursor replacement with crosshair laser pointer design

## Requirements

### Core Requirements
- Windows-only cursor replacement for main pointer
- Crosshair design with red dot center
- Medium size (32x32 pixels) for good visibility
- System-wide replacement via registry modification
- Easy installation and restoration

### Constraints
- Main pointer only (not replacing text cursor, resize handles, etc.)
- Current user scope (HKCU registry, not system-wide)
- Must be reversible without system damage
- Must work without special permissions

## Architecture

### Components

1. **Cursor Generator** (`generate-cursor.py`)
   - Python script using Pillow library
   - Programmatically draws crosshair with red dot
   - Outputs 32x32 pixel .CUR file
   - Configurable colors and dimensions

2. **Cursor File** (`laser-pointer.cur`)
   - 32x32 pixels, 32-bit color depth with alpha
   - White crosshair lines with black outline (1-2px wide)
   - Red dot center (6-8px diameter)
   - Crosshair arms extend 12-14px from center
   - Hotspot at exact center (16,16)
   - Transparent background

3. **Installation Script** (`install-cursor.ps1`)
   - PowerShell script for automated installation
   - Backs up current cursor registry settings
   - Copies cursor to AppData for persistence
   - Updates HKCU\Control Panel\Cursors registry
   - Applies changes via system refresh

4. **Restoration Script** (`restore-cursor.ps1`)
   - PowerShell script for easy revert
   - Restores from timestamped backup
   - Falls back to Windows default if no backup
   - Cleans up copied cursor file

5. **Documentation** (`README.md`)
   - Step-by-step installation instructions
   - Visual preview of cursor
   - Troubleshooting guide
   - Uninstallation instructions

## Design Details

### Visual Design
- **Crosshair:** Thin lines (1-2px) in white with black outline for visibility on any background
- **Center Dot:** Bright red (RGB: 255, 0, 0) circle, 6-8px diameter
- **Arms:** Extend symmetrically 12-14px from center in all four directions
- **Background:** Fully transparent (alpha channel)
- **Style:** Clean, minimal, professional laser pointer aesthetic

### Technical Specifications
- **Format:** Windows .CUR (cursor) file format
- **Dimensions:** 32x32 pixels
- **Color Depth:** 32-bit RGBA
- **Hotspot:** Center point (16, 16) for accurate click registration
- **Generation:** Programmatic using PIL/Pillow, not manual editing

### Installation Flow

```
User runs install-cursor.ps1
    ↓
Check permissions & file existence
    ↓
Export current cursor settings to backup .reg file
    ↓
Copy laser-pointer.cur to %APPDATA%\laser-cursor\
    ↓
Update registry: HKCU\Control Panel\Cursors\Arrow
    ↓
Refresh system cursors (SystemParametersInfo)
    ↓
Display success message with backup location
```

### Restoration Flow

```
User runs restore-cursor.ps1
    ↓
Check for backup .reg file
    ↓
If backup exists: Import .reg file
If no backup: Reset to Windows default
    ↓
Refresh system cursors
    ↓
Optionally clean up AppData cursor file
    ↓
Display success message
```

## Error Handling

### Installation Script
- Verify cursor file exists before installation
- Check registry access permissions
- Validate backup creation succeeded
- Handle file copy failures (disk space, permissions)
- Provide clear error messages with remediation steps

### Restoration Script
- Handle missing backup file gracefully
- Validate registry import success
- Catch file deletion errors
- Fall back to Windows default if restoration fails

### General Safety
- Only modify HKCU registry (current user scope)
- Never delete system files
- Timestamped backups prevent overwriting
- Clear prompts before making changes
- All operations are reversible

## Testing Strategy

### Visual Testing
- Verify cursor renders correctly at 32x32
- Check visibility on light backgrounds
- Check visibility on dark backgrounds
- Verify hotspot accuracy (clicks register at center)
- Confirm no scaling artifacts

### Functional Testing
- Test installation script creates proper backup
- Verify cursor persists after reboot
- Test restoration script reverts successfully
- Verify backup .reg file is valid
- Test with existing custom cursor (preserve in backup)

### Edge Cases
- Installation with no write permission to AppData
- Restoration with missing backup file
- Multiple installations (backup versioning)
- PowerShell execution policy restrictions

## File Structure

```
laser-pointer-cursor/
├── README.md                    # User documentation with screenshots
├── generate-cursor.py           # Cursor generation script
├── laser-pointer.cur           # Generated cursor file (checked in)
├── install-cursor.ps1          # Installation automation
├── restore-cursor.ps1          # Restoration automation
├── requirements.txt            # Python dependencies (Pillow)
└── .gitignore                  # Ignore backup .reg files
```

## Implementation Notes

### Cursor Generation (Python)
- Use PIL.Image to create 32x32 RGBA canvas
- Use PIL.ImageDraw to draw crosshair geometry
- Draw black outline first, then white line on top (for contrast)
- Draw red filled circle for center dot
- Save with cursor format specifying hotspot coordinates

### Registry Modification (PowerShell)
- Registry path: `HKCU:\Control Panel\Cursors`
- Key to modify: `Arrow` (main pointer)
- Value format: Full path to .cur file
- Backup method: `reg export` to .reg file with timestamp
- Apply method: `[System.Windows.Forms.Cursor]::Current` refresh or SystemParametersInfo

### Documentation Requirements
- Include screenshot of cursor in action
- Step-by-step installation with images
- Common troubleshooting (execution policy, permissions)
- How to verify installation worked
- How to customize colors/size by editing generate-cursor.py

## Success Criteria

- [x] Cursor is clearly visible on light and dark backgrounds
- [x] Hotspot is accurate (clicks register where dot appears)
- [x] Installation completes without errors
- [x] Restoration returns to original cursor
- [x] Backup files are created successfully
- [x] README provides clear instructions
- [x] No system files are modified or deleted
- [x] Changes persist across reboots
- [x] Scripts handle errors gracefully
- [x] Cursor displays at correct size (not scaled)

## Future Enhancements (Out of Scope)

- Multiple color schemes (green, blue laser pointers)
- Size variants (small/large)
- Cursor trail/glow effects
- Complete cursor theme with all states
- GUI application for easy toggle
- System tray icon for quick enable/disable
