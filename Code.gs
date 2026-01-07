const SPREADSHEET_ID = '1JD-KMm3lIm7h78HJl7qKMtdipFW7pFxgKeG7zjZfV4E';
const TOTALS_SHEET = "Totals";
const LOG_SHEET = "Logs";
const KEYS_SHEET = "Keys";
const COUNTERS_SHEET = "Counters"

// --- EXTERNAL LIBRARY LOADER ---
function loadCryptoJS() {
  if (typeof CryptoJS === 'undefined') {
    const url = 'https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js';
    eval(UrlFetchApp.fetch(url).getContentText());
  }
}

function doGet(e) {
  loadCryptoJS();
  let outcome = "";
  let paramsTableRows = "";
  var params_info = {outcome: 'Invalid'}

  if (e && e.parameter) {
    for (const [param, value] of Object.entries(e.parameter)) {
      paramsTableRows += `<tr><td>${param}</td><td>${value}</td></tr>`;
      params_info[param] = value
      
      if (param === 'uid') {
        const tag_keys = getKeysForUid(String(value));
        params_info["tag_keys"] = tag_keys;
        paramsTableRows +=`<tr style="background-color: rgba(255, 255, 0, 0.1);"><td>➥ Lookup Key</td><td>${tag_keys['status']}</td></tr>`;
        outcome = tag_keys['outcome']
      }
      if (param === 'ctr') {
        params_info['ctr'] = parseInt(value, 16);
        params_info['counter_hex'] = value;
      }
    }
  }
  
  // Validate
  const validator = new SDMValidator();
    

  Logger.log("Validating with Params: " + JSON.stringify(params_info, space=2))
 
  
  
  Logger.log(`\n--- Python Log Data Test ---`);
  Logger.log(`Target CMAC: ${params_info['cmac']}`);
  Logger.log(`Keys:        ${JSON.stringify(params_info['tag_keys'], space=2)}`);

  const result = validator.validateSdmUrl(
    params_info['uid'], 
    params_info['ctr'], 
    params_info['cmac'], 
    params_info['tag_keys']['sdm_mac_key']
  );

  Logger.log(`Calculated:  ${result.cmac_calculated}`);
  Logger.log("Result: " + JSON.stringify(space=2))
  if (result.valid && (outcome === "heads" || outcome === "tails")) {
    recordOutcome(params_info['uid'], params_info['ctr'], outcome, params_info['cmac']);
  } else if (!result.valid) {
    outcome = "INVALID: " + (result.error || "CMAC Mismatch");
  }

  return renderHtml(outcome, paramsTableRows, getTotalHeads(), getTotalTails());
}

  

/**
 * TEST RUNNER - Matches Python Log Exactly
 */
function testRunner() {
  loadCryptoJS();
  const validator = new SDMValidator();
  
  Logger.log(`=== DIAGNOSTIC START ===`);
  
  // Inputs from your Python Log
              
  const uid = "048E684A2F7080";
  const counter = 28; // Decimal 28 -> Hex 1C
  const cmacReceived = "9F5430D0B4ACB13A"; 
  const sdm_mac_key = '596b8a1352e44a53db20c24b0253f8c4'; // Key from log
  
  Logger.log(`\n--- Python Log Data Test ---`);
  Logger.log(`Target CMAC: ${cmacReceived}`);
  Logger.log(`Key:         ${sdm_mac_key}`);
  Logger.log(`Counter: ${counter}`)
  
  const keys = getKeysForUid(uid);
  Logger.log(`Got key provisioned on ${keys.provisioned_date}`)

  const result = validator.validateSdmUrl(uid, counter, cmacReceived, sdm_mac_key);
  
  Logger.log(`Calculated:  ${result.cmac_calculated}`);
  
  if (result.valid) {
    Logger.log(`✅ MATCH FOUND!`);
  } else {
    Logger.log(`❌ No match found.`);
  }
  Logger.log(`=== END ===`);


  
}


class SDMValidator {
  
  validateSdmUrl(uid, ctr, cmac_received, sdm_mac_key) {
    const result = { valid: false, error: null, cmac_calculated: '' };

    try {
      this.checkCtr(uid, ctr);
      // 1. Build System Vector (File 1)
      const vectorHex = this.buildSystemVector(uid, ctr);
      
      // 2. Build Message
      // Matches Python Log: "UID&ctr=COUNTER&cmac="
      const counter_hex = ctr.toString(16).padStart(6, '0').toUpperCase();
      const msgStr = `${uid.toUpperCase()}&ctr=${counter_hex}&cmac=`;

      // 3. Calculate CMAC
      const svData = CryptoJS.enc.Hex.parse(vectorHex);
      const sdmKey = CryptoJS.enc.Hex.parse(sdm_mac_key);
      const msgData = CryptoJS.enc.Utf8.parse(msgStr);

      Logger.log("\n[Step 1] Deriving Session Key...");
      Logger.log(`   SV Hex:      ${vectorHex}`);
      const sessionKey = this.aesCmac(svData, sdmKey, "SessionKey");
      Logger.log(`   Session Key: ${sessionKey.toString().toUpperCase()}`);
      
      Logger.log("\n[Step 2] Signing Message...");
      Logger.log(`   Msg Str:     ${msgStr}`);
      Logger.log(`   Msg Hex:     ${msgData.toString().toUpperCase()}`);
      
      const fullCmac = this.aesCmac(msgData, sessionKey, "Message");
      const fullHex = fullCmac.toString().toUpperCase();
      const truncated = this.truncate(fullHex);
      
      Logger.log(`   Full CMAC:   ${fullHex}`);
      Logger.log(`   Truncated:   ${truncated}`);
      
      result.full_cmac = fullHex;
      result.cmac_calculated = truncated;
      result.valid = (truncated === cmac_received.toUpperCase());
      
    } catch(e) {
      result.error = e.toString();
    }
    return result;
  }

  checkCtr(uid, ctr) {
    const last_ctr = getCounterFor(uid);
    if (last_ctr === undefined) {
      const msg = `First time for ${uid}: ctr=${ctr}`;
      Logger.log(msg);
      return true
    }

    if (last_ctr >= ctr)  {
      const msg = `new counter ${ctr} is invalid (last was ${last_ctr}).`
      Logger.log(msg)
      throw new Error(msg);
    }

    Logger.log(`Counter Is Valid: new ${ctr} > old ${last_ctr}`)
    return true;
  }

  calcCMAC_Raw(msgData, keyData, label) {
    const fullCmac = this.aesCmac(msgData, keyData, label);
    const fullHex = fullCmac.toString().toUpperCase();
    return { full: fullHex };
  }

  buildSystemVector(uid, ctr) {
    const svHeader = "3CC300010080"; 
    const ctrHex = ctr.toString(16).padStart(6, '0');
    const ctrHexLe = ctrHex.match(/../g).reverse().join("");
    return svHeader + uid + ctrHexLe;
  }

  truncate(fullCmacHex) {
    let truncated = "";
    for (let i = 1; i < 16; i += 2) {
      truncated += fullCmacHex.substr(i * 2, 2);
    }
    return truncated;
  }

  /**
   * AES-128 CMAC Implementation (RFC 4493)
   */
  aesCmac(message, key, label="CMAC") {
    const blockSizeBytes = 16;
    const subKeys = this.generateSubkeys(key);
    let msg = message.clone();
    
    const n = Math.ceil((msg.sigBytes === 0 ? 1 : msg.sigBytes) / blockSizeBytes);
    const isFullBlock = (msg.sigBytes > 0 && msg.sigBytes % blockSizeBytes === 0);
    
    if (!isFullBlock) {
      msg.concat(CryptoJS.lib.WordArray.create([0x80000000], 1));
      const remaining = blockSizeBytes - (msg.sigBytes % blockSizeBytes);
      if (remaining < 16) {
          msg.concat(CryptoJS.lib.WordArray.create([0,0,0,0], remaining));
          msg.sigBytes = n * blockSizeBytes;
      }
      this.xorBlock(msg, n - 1, subKeys.k2);
    } else {
      this.xorBlock(msg, n - 1, subKeys.k1);
    }

    const iv = CryptoJS.lib.WordArray.create([0,0,0,0], 16);
    const encrypted = CryptoJS.AES.encrypt(msg, key, { 
      mode: CryptoJS.mode.CBC, 
      padding: CryptoJS.pad.NoPadding, 
      iv: iv 
    });

    const words = encrypted.ciphertext.words;
    const lastBlock = words.slice(words.length - 4, words.length);
    return CryptoJS.lib.WordArray.create(lastBlock, 16);
  }

  generateSubkeys(key) {
    const zero = CryptoJS.lib.WordArray.create([0,0,0,0], 16);
    const L = CryptoJS.AES.encrypt(zero, key, { 
      mode: CryptoJS.mode.ECB, 
      padding: CryptoJS.pad.NoPadding 
    }).ciphertext;
    
    const k1 = this.rol(L);
    if ((L.words[0] & 0x80000000) !== 0) k1.words[3] ^= 0x00000087;
    
    const k2 = this.rol(k1);
    if ((k1.words[0] & 0x80000000) !== 0) k2.words[3] ^= 0x00000087;
    
    return {k1, k2};
  }

  rol(wordArray) {
    const w = wordArray.words;
    const msb1 = (w[1] >>> 31) & 1;
    const msb2 = (w[2] >>> 31) & 1;
    const msb3 = (w[3] >>> 31) & 1;
    
    const newWords = [
      (w[0] << 1) | msb1,
      (w[1] << 1) | msb2,
      (w[2] << 1) | msb3,
      (w[3] << 1)
    ];
    return CryptoJS.lib.WordArray.create(newWords, 16);
  }

  xorBlock(msg, blockIndex, key) {
    const words = msg.words;
    const keyWords = key.words;
    const start = blockIndex * 4;
    for (let i = 0; i < 4; i++) {
      words[start + i] = (words[start + i] || 0) ^ keyWords[i];
    }
  }
}

// --- Sheet Helpers ---
function getTotalHeads() {
  return getSheetValueFor("A2");
}

function getTotalTails() {
  return getSheetValueFor("B2");
}

function getCounterFor(uid) {
  Logger.log("Looking up counter for: " + uid);
  const row = getRowForUid(uid, COUNTERS_SHEET);
  const ctr =  parseInt(row["MAX of counter"]); 
  Logger.log(`got ctr=${ctr}`)
  return ctr;
}

function getValuesAsDict(sheet_name) {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(sheet_name);
  const data = sheet.getDataRange().getValues();
  const headers = [];
  for (let i = 0; i < data[0].length; i++) {
    headers.push(String(data[0][i]));
  }
  var items = [];
  for (let row = 1; row < data.length; row++) {
    var item = {}
    for (let col = 0; col < headers.length; col++) {
      item[headers[col]] = String(data[row][col]);
    }
    items.push(item);
  }
  return items;
}

function getRowForUid(uid, sheet_name) {
  Logger.log(`Lookup up for ${uid} in ${sheet_name}`);
  const data = getValuesAsDict(sheet_name);
  Logger.log(`Got ${data.length} rows`)
  for (let i = 0; i < data.length; i++) {
    if (data[i]["uid"] === String(uid)) {
      Logger.log(`found: ${data[i]["uid"]} on row ${i}`);
      return data[i];
    }
  }
  Logger.log("Error no keys found for: " + uid);
  return { uid: uid, status: "Not Found" };

}

function getKeysForUid(uid) {
  return getRowForUid(uid, KEYS_SHEET);
}

function recordOutcome(uid, ctr, side, cmac) {
  SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(LOG_SHEET).appendRow([new Date(), uid, ctr, side.toLowerCase(), cmac]);
}

function getSheetValueFor(cell) {
  return SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(TOTALS_SHEET).getRange(cell).getDisplayValue();
}

function renderHtml(outcome, paramsTableRows, heads, tails) {
  const htmlTemplate = `
  <!DOCTYPE html>
  <html>
  <head>
    <base target="_top">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
      body { font-family: 'Courier New', monospace; background: #f0f2f5; color: #333; padding: 20px; display: flex; flex-direction: column; align-items: center; }
      .header { background: linear-gradient(135deg, #007BFF 0%, #00BFFF 100%); color: white; padding: 20px 40px; border-radius: 12px; text-align: center; width: 100%; max-width: 500px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 30px; display: flex; flex-direction: column; align-items: center; }
      .header h1 { margin: 0 0 15px 0; font-size: 2.2em; font-weight: 600; }
      .params-table { margin-top: 15px; border-collapse: collapse; width: 100%; font-size: 0.9rem; border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; background: rgba(255,255,255,0.1); }
      .params-table td { padding: 8px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.2); color: #fff; }
      .results-table { border-collapse: collapse; width: 100%; max-width: 500px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 12px; overflow: hidden; background: white; }
      .results-table td { padding: 18px; font-size: 2.0rem; font-weight: bold; border-bottom: 1px solid #e0e0e0; }
      .fancy-text { padding: 10px; font-family: monospace; font-size: 4rem; font-weight: bold; color: #ff6347; text-shadow: 2px 2px 0 #fff; }
    </style>
  </head>
  <body>
    <div class="header">
      <h1>Heads vs. Tails</h1>
      ${outcome ? `<div><span class="fancy-text">${outcome}</span></div>` : ''}
      ${paramsTableRows ? `<table class="params-table"><tbody>${paramsTableRows}</tbody></table>` : ''}
    </div>
    <table class="results-table">
      <tbody>
        <tr><td>Heads:</td><td>${heads}</td></tr>
        <tr><td>Tails:</td><td>${tails}</td></tr>
      </tbody>
    </table>
  </body>
  </html>`;
  return HtmlService.createHtmlOutput(htmlTemplate).setTitle('Heads vs Tails').setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
