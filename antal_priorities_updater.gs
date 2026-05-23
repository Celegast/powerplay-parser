/**
 * Antal Priorities Sheet Updater — Apps Script
 *
 * Setup:
 *   1. Open the Google Sheet → Extensions → Apps Script
 *   2. Paste this entire file, replacing any existing code
 *   3. Change SECRET_TOKEN to something only you know (any random string)
 *   4. Click Deploy → New deployment → Web app
 *      - Execute as: Me
 *      - Who has access: Anyone
 *   5. Copy the deployment URL into update_google_sheet.py → WEB_APP_URL
 *
 * The sheet name (e.g. "This Cycle 79") is passed by the Python script with
 * every request so no changes are needed here when a new cycle starts.
 *
 * The script exposes two endpoints:
 *   GET  ?token=...&sheet=...            → returns current system list (for --sync-input)
 *   POST (JSON body, systems=[...])      → updates UM, RF, timestamp, and CP bar images
 *   POST (JSON body, set_status="...")   → writes/clears the update-status indicator cell
 */

var SECRET_TOKEN = 'change-me-before-deploying';

// Column numbers (1-based)
var COL_SYSTEM    = 2;   // B — system name (read-only, source of truth)
var COL_TIMESTAMP = 3;   // C — Updated (UTC)
var COL_UM        = 8;   // H — Undermining
var COL_RF        = 9;   // I — Reinforcement
var COL_IMAGE     = 5;   // E — CP bar image

// Update-status indicator cell — pick any unused cell in your sheet.
// Default: A1. Change row/col to wherever you want the indicator to appear.
var STATUS_ROW = 1;
var STATUS_COL = 6;   // F


// ── GET: return system list ────────────────────────────────────────────────────

function doGet(e) {
  if ((e.parameter.token || '') !== SECRET_TOKEN) {
    return jsonResponse({error: 'Unauthorized'});
  }

  var sheetName = e.parameter.sheet || '';
  var sheet = getSheet(sheetName);
  if (!sheet) return jsonResponse({error: 'Sheet not found: ' + sheetName});

  var values = sheet.getDataRange().getValues();
  var systems = [];
  for (var i = 1; i < values.length; i++) {   // skip header row
    var name = String(values[i][COL_SYSTEM - 1]).trim();
    if (name) systems.push(name);
  }

  return jsonResponse({systems: systems});
}


// ── POST: update data + images ─────────────────────────────────────────────────

function doPost(e) {
  try {
    var payload;
    try {
      payload = JSON.parse(e.postData.contents);
    } catch (err) {
      return jsonResponse({error: 'Invalid JSON: ' + err.message});
    }

    if ((payload.token || '') !== SECRET_TOKEN) {
      return jsonResponse({error: 'Unauthorized'});
    }

    var sheet = getSheet(payload.sheet || '');
    if (!sheet) return jsonResponse({error: 'Sheet not found: ' + payload.sheet});

    // Status-only update (set_status present → write/clear indicator cell and return)
    if (payload.set_status !== undefined) {
      setStatusCell(sheet, payload.set_status);
      return jsonResponse({ok: true});
    }

    var values = sheet.getDataRange().getValues();

    // Build lowercase name → 1-based row number map from the current sheet
    var rowMap = {};
    for (var i = 1; i < values.length; i++) {
      var name = String(values[i][COL_SYSTEM - 1]).trim();
      if (name) rowMap[name.toLowerCase()] = i + 1;
    }

    var updated  = 0;
    var notFound = [];
    var imageErrors = [];

    for (var j = 0; j < payload.systems.length; j++) {
      var sys    = payload.systems[j];
      var rowNum = rowMap[sys.name.toLowerCase()];

      if (!rowNum) {
        notFound.push(sys.name);
        continue;
      }

      if (sys.timestamp !== undefined) sheet.getRange(rowNum, COL_TIMESTAMP).setValue(new Date(sys.timestamp));
      if (sys.um        !== undefined) sheet.getRange(rowNum, COL_UM).setValue(sys.um);
      if (sys.rf        !== undefined) sheet.getRange(rowNum, COL_RF).setValue(sys.rf);

      if (sys.bar_b64) {
        try {
          insertBarImage(sheet, rowNum, COL_IMAGE, sys.bar_b64,
                         sys.bar_width || 0, sys.bar_height || 0);
        } catch (imgErr) {
          imageErrors.push(sys.name + ': ' + imgErr.message);
        }
      }

      updated++;
    }

    return jsonResponse({updated: updated, notFound: notFound, imageErrors: imageErrors});

  } catch (err) {
    return jsonResponse({error: 'Unexpected error: ' + err.message + ' | Stack: ' + err.stack});
  }
}


// ── Helpers ────────────────────────────────────────────────────────────────────

function getSheet(name) {
  if (!name) return null;
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name) || null;
}

// Number of columns the bar image spans (E, F, G = 3)
var IMAGE_SPAN_COLS = 3;

function insertBarImage(sheet, row, col, base64Data, width, height) {
  // Remove any old floating images anchored to this row (left over from the
  // previous insertImage() approach). Safe to call repeatedly — no-op once gone.
  var floatingImages = sheet.getImages();
  for (var i = floatingImages.length - 1; i >= 0; i--) {
    if (floatingImages[i].getAnchorCell().getRow() === row) {
      floatingImages[i].remove();
    }
  }

  // Merge E:G so the cell image spans all three columns.
  var imageRange = sheet.getRange(row, col, 1, IMAGE_SPAN_COLS);
  imageRange.merge();

  // Explicitly clear any existing cell image before writing the new one.
  imageRange.clearContent();

  var dataUrl   = 'data:image/png;base64,' + base64Data;
  var cellImage = SpreadsheetApp.newCellImage()
      .setSourceUrl(dataUrl)
      .setAltTextTitle('CP bar')
      .build();
  imageRange.setValue(cellImage);
}

function setStatusCell(sheet, message) {
  var cell = sheet.getRange(STATUS_ROW, STATUS_COL);
  if (message) {
    cell.setValue(message);
    cell.setBackground('#fbbc04');  // Google yellow
    cell.setFontWeight('bold');
  } else {
    cell.setValue('');
    cell.setBackground(null);
    cell.setFontWeight('normal');
  }
}

function jsonResponse(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
