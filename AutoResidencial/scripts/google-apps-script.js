function doPost(e) {
  const data = JSON.parse(e.postData.contents);

  SpreadsheetApp
    .getActiveSpreadsheet()
    .getSheetByName("Sheet1")
    .appendRow([
      data.Temperatura,
      data.Umidade,
      data.Gas,
      data.Luminosidade,
      data.Movimento
    ]);

  return ContentService.createTextOutput("OK");
}