// Trova e rimuove il record in tutti i fogli secondari
function findAndRemoveRecordInAllSheets(id, easySheetId, veryEasySheetId, intermediateSheetId, moderateSheetId, difficultSheetId) {
  var sheetIds = [easySheetId, veryEasySheetId, intermediateSheetId, moderateSheetId, difficultSheetId];
  
  for (var i = 0; i < sheetIds.length; i++) {
    try {
      var sheet = SpreadsheetApp.openById(sheetIds[i]).getSheetByName('Tracks');
      if (!sheet) {
        Logger.log('Sheet not found with ID: ' + sheetIds[i]);
        continue;
      }
      
      var lastRow = sheet.getLastRow();
      
      if (lastRow <= 1) {
        Logger.log('Sheet with ID ' + sheetIds[i] + ' is empty or only contains header.');
        continue;
      }
      
      var range = sheet.getRange(2, 1, lastRow - 1, 1); // Skip header
      var values = range.getValues();
      
      for (var j = 0; j < values.length; j++) {
        if (values[j][0] == id) {
          sheet.deleteRow(j + 2);
          Logger.log('Removed row with ID ' + id + ' from sheet with ID ' + sheetIds[i]);
          return sheet;
        }
      }
    } catch (error) {
      Logger.log("Error opening sheet with ID: " + sheetIds[i] + " - " + error.message);
    }
  }
  
  return null; // Nessun record trovato nei fogli secondari
}

// Capitalizza la prima lettera della stringa
function capitalizeFirstLetter(string) {
  return string.charAt(0).toUpperCase() + string.slice(1).toLowerCase();
}

// Aggiorna o inserisce una riga nel foglio specificato
function updateOrInsertRow(sheet, id, trailName, lat, lon, difficulty, length_, timing, distance, websiteLink, maxPart, notes) {
  var lastRow = sheet.getLastRow();
  difficulty = capitalizeFirstLetter(difficulty);

  if (lastRow <= 1) { // Se il foglio è vuoto o contiene solo intestazione
    sheet.appendRow([id, trailName, lat, lon, difficulty, length_, timing, distance, websiteLink, maxPart, notes]);
    Logger.log('Inserted new row into empty sheet.');
    sheet.getRange(2, 3).setNumberFormat('@STRING@'); // Imposta il formato per latitudine e longitudine
    sheet.getRange(2, 4).setNumberFormat('@STRING@');
    return;
  }
  
  var range = sheet.getRange(2, 1, lastRow - 1, 1); // Presupponendo che i dati inizino dalla riga 2
  var values = range.getValues();
  
  var foundRow = null;
  for (var i = 0; i < values.length; i++) {
    if (values[i][0] == id) {
      foundRow = i + 2; // Aggiungi 2 perché la ricerca parte dalla riga 2
      break;
    }
  }
  
  if (foundRow) {
    sheet.getRange(foundRow, 2).setValue(trailName);
    sheet.getRange(foundRow, 3).setValue(lat).setNumberFormat('@STRING@'); // Imposta il formato come testo
    sheet.getRange(foundRow, 4).setValue(lon).setNumberFormat('@STRING@'); // Imposta il formato come testo
    sheet.getRange(foundRow, 5).setValue(difficulty);
    sheet.getRange(foundRow, 6).setValue(length_);
    sheet.getRange(foundRow, 7).setValue(timing);
    sheet.getRange(foundRow, 8).setValue(distance);
    sheet.getRange(foundRow, 9).setValue(websiteLink);
    sheet.getRange(foundRow, 10).setValue(maxPart);
    sheet.getRange(foundRow, 11).setValue(notes);
    Logger.log('Updated existing row with ID ' + id);
  } else {
    sheet.appendRow([id, trailName, lat, lon, difficulty, length_, timing, distance, websiteLink, maxPart, notes]);
    Logger.log('Inserted new row into non-empty sheet.');
    sheet.getRange(lastRow + 1, 3).setNumberFormat('@STRING@'); // Imposta il formato per latitudine e longitudine
    sheet.getRange(lastRow + 1, 4).setNumberFormat('@STRING@');
  }
}

// Elenco dei fogli e gestione delle modifiche
function processRow(row, editedColumn) {
  var masterSheet = SpreadsheetApp.openById('[GOOGLE SHEET ID]').getSheetByName('General Info');
  if (!masterSheet) {
    Logger.log('Master sheet not found');
    return;
  }

  var id = masterSheet.getRange(row, 1).getValue();
  var trailName = masterSheet.getRange(row, 2).getValue();
  var lat = masterSheet.getRange(row, 3).getValue();
  var lon = masterSheet.getRange(row, 4).getValue();
  var newDifficulty = masterSheet.getRange(row, 5).getValue().toLowerCase();
  var length_ = masterSheet.getRange(row, 6).getValue();
  var timing = masterSheet.getRange(row, 7).getValue();
  var distance = masterSheet.getRange(row, 8).getValue();
  var websiteLink = masterSheet.getRange(row, 9).getValue();
  var maxPart = masterSheet.getRange(row, 10).getValue();
  var notes = masterSheet.getRange(row, 11).getValue();
  
  Logger.log('Processing row ' + row + ' with ID: ' + id + ' and new difficulty: ' + newDifficulty);
  
  var veryEasySheetId = '[GOOGLE SHEET ID]';
  var easySheetId = '[GOOGLE SHEET ID]';
  var intermediateSheetId = '[GOOGLE SHEET ID]';
  var moderateSheetId = '[GOOGLE SHEET ID]';
  var difficultSheetId = '[GOOGLE SHEET ID]';
  
  var oldSheet = findAndRemoveRecordInAllSheets(id, easySheetId, veryEasySheetId, intermediateSheetId, moderateSheetId, difficultSheetId);
  
  if (oldSheet != null || editedColumn == 5) { // attivazione automatica
    var targetSheet;
    if (newDifficulty === 'easy') {
      targetSheet = SpreadsheetApp.openById(easySheetId).getSheetByName('Tracks');
    } else if (newDifficulty === 'very easy') {
      targetSheet = SpreadsheetApp.openById(veryEasySheetId).getSheetByName('Tracks');
    } else if (newDifficulty === 'intermediate') {
      targetSheet = SpreadsheetApp.openById(intermediateSheetId).getSheetByName('Tracks');
    } else if (newDifficulty === 'moderate') {
      targetSheet = SpreadsheetApp.openById(moderateSheetId).getSheetByName('Tracks');
    } else if (newDifficulty === 'difficult') {
      targetSheet = SpreadsheetApp.openById(difficultSheetId).getSheetByName('Tracks');
    } else {
      Logger.log("Unsupported difficulty: " + newDifficulty);
      return;
    }
    
    updateOrInsertRow(targetSheet, id, trailName, lat, lon, newDifficulty, length_, timing, distance, websiteLink, maxPart, notes);
  }
}

// Gestisce l'evento di modifica nella Google Sheet
function onEdit(e) {
  var sheet = e.source.getActiveSheet();
  var range = e.range;

  if (sheet.getName() === 'General Info') {
    var row = range.getRow();
    var col = range.getColumn();
    
    Logger.log('Edit detected in row ' + row + ', column ' + col);
    
    // Processa la riga modificata o aggiunta e passa la colonna modificata
    processRow(row, col);
  }
}
