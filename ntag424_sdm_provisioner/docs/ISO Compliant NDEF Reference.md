The following breakdown shows the exact binary structure required in **File 2** of the NTAG 424 DNA tag to make it a valid, scannable NDEF record on Android.

### **1\. The NDEF Packet Structure (File 2 Content)**

This is the raw data that must be written to File 2\. It consists of the **NDEF TLV Wrapper** (7 bytes) followed by your **URL Payload**.

**Total Bytes:** 7 (Header) \+ Length of URL

| Byte Index | Value (Hex) | Description |
| :---- | :---- | :---- |
| **0** | 00 | **File Length (MSB)** (Managed by the tag, usually 00\) |
| **1** | XX | **File Length (LSB)** (Total size of the NDEF message below) |
| **2** | D1 | **NDEF Header:** MB=1, ME=1, SR=1, TNF=1 (Well Known Type) |
| **3** | 01 | **Type Length:** 1 Byte |
| **4** | YY | **Payload Length:** Length of your URL \- 1 (because prefix is compressed) |
| **5** | 55 | **Type:** 'U' (URI Record) |
| **6** | 04 | **URI ID Code:** https:// (Expands to 8 chars) |
| **7+** | 73 63 ... | **The URL String:** script.google.com/a/macros... |

### **2\. The Configuration (SDM Settings)**

To make this URL dynamic (so 000000 becomes real data), you must apply these settings using the **FileSettings** command (Cmd 0xDD) on File 2\.

#### **A. Permissions**

* **File Type:** 0x00 (Standard Data File)  
* **Comm Mode:** 0x00 (Plain) or 0x01 (MAC'd) \- *Plain is safer for testing.*  
* **Read Access:** 0xE (**Free/Public**) \<--- **CRITICAL**  
* **Write Access:** 0x0 (Key 0\) or 0x1 (Key 1\)  
* **Read/Write Access:** 0x0 (Key 0\)  
* **Change Access:** 0x0 (Key 0\)

#### **B. SDM Mirror Options**

You must enable the mirrors and tell the tag *exactly* where to overwrite the 000000 placeholders in your URL.

* **SDM Enabled:** True  
* **UID Mirror:** True  
* **Read Counter Mirror:** True  
* **Read Counter Limit:** False (Unless you want the link to expire)  
* **Encrypted File Data:** False (Set to True only if you are encrypting part of the URL)

#### **C. The Offsets**

You calculate these based on the **File 2 Byte Index** (start counting from Byte 0 in the table above).

Using your previous URL template as an example:  
https://script.google.com/.../exec?uid=00000000000000\&ctr=000000\&cmac=0000000000000000

1. **SDM Mirror UID Offset:** 135  
   * *Logic:* It points to the start of the 00... after uid=.  
   * *Tag Action:* Overwrites 14 chars (ASCII Hex of UID) at this position.  
2. **SDM Read Ctr Offset:** 154  
   * *Logic:* It points to the start of the 00... after ctr=.  
   * *Tag Action:* Overwrites 6 chars (ASCII Hex of Counter) at this position.  
3. **SDM MAC Offset:** 166  
   * *Logic:* It points to the start of the 00... after cmac=.  
   * *Tag Action:* Overwrites 16 chars (ASCII Hex of CMAC) at this position.  
4. **SDM MAC Input Offset:** 0 (or sometimes None depending on tool)  
   * *Logic:* Points to the start of the data to be signed.  
   * *Tag Action:* If set to 0, it signs "Empty Data". If set to 166, it signs the URL prefix. **Use 0 to match your current Python code.**

### **3\. Visual Packet Diagram**

Here is how the data sits in memory vs. what the phone receives.

**A. Memory on Tag (Static Template)**

Plaintext

\[Header\] \[Prefix\] \[........................URL Body.........................\] \[Placeholders\]  
00 8C    D1 01 ... script.google.com/.../exec?uid=00000000000000\&ctr=000000\&cmac=0000000000000000  
^        ^        ^                               ^              ^           ^  
Byte 0   Byte 2   Byte 7                          Offset 135     Offset 154  Offset 166

**B. Data on Wire (Phone Scan)**

Plaintext

\[Header\] \[Prefix\] \[........................URL Body.........................\] \[Live Data\]  
00 8C    D1 01 ... script.google.com/.../exec?uid=04AE664A2F7080\&ctr=00001A\&cmac=A1B2C3D4E5F67890  
                                                  ^              ^           ^  
                                                  Real UID       Real Ctr    Real CMAC

Next Step for You:  
If you want to verify your file structure without writing to a tag yet, you can use Python to build the byte array. Would you like a script that generates the exact bytes payload for File 2?

Here is the byte-level structure of **File 2** (The NDEF File) configured for your NTAG 424 DNA. This is what you must write to the tag to make it a compliant Type 4 NDEF tag.

### **File 2: Binary Breakdown**

Total Size: \~190 Bytes (depending on exact URL length)  
Structure: \[Type 4 NLEN\] \+ \[NDEF Header\] \+ https://www.merriam-webster.com/dictionary/payload

#### **1\. The Headers (Bytes 0-6)**

These first 7 bytes are critical. If any are wrong, the phone won't detect the URL.

| Byte | Hex | ASCII | Meaning |
| :---- | :---- | :---- | :---- |
| **0** | 00 | . | **NLEN (MSB):** File Size High Byte (Usually 0\) |
| **1** | BE | ¾ | **NLEN (LSB):** File Size Low Byte (Length of NDEF message below) |
| **2** | D1 | Ñ | **NDEF Header:** (MB=1, ME=1, SR=1, TNF=1) |
| **3** | 01 | . | **Type Length:** 1 byte |
| **4** | BA | º | **Payload Length:** Length of URL minus prefix compression |
| **5** | 55 | U | **Type:** 'U' (URI Record) |
| **6** | 04 | . | **URI Identifier:** https:// (Compressed to 1 byte) |

*(Note: The values BE and BA are examples based on your long URL. You must calculate the exact length of your string).*

#### **2\. The URL Body (Bytes 7-134)**

This is your standard ASCII URL data.

| Byte | Hex | ASCII | Meaning |
| :---- | :---- | :---- | :---- |
| **7** | 73 | s | Start of "script.google.com..." |
| **8** | 63 | c |  |
| **9** | 72 | r |  |
| **...** | ... | ... | *...rest of the Google Script URL...* |
| **130** | 3F | ? | Query Start |
| **131** | 75 | u | u |
| **132** | 69 | i | i |
| **133** | 64 | d | d |
| **134** | 3D | \= | \= |

#### **3\. The SDM Mirror Areas (Bytes 135+)**

These are the placeholders you write as "0"s, which the tag will dynamically overwrite when scanned.

| Byte (Offset) | Hex | ASCII | Meaning |
| :---- | :---- | :---- | :---- |
| **135** | 30 | 0 | **UID Mirror Start** (Mirror Offset 135\) |
| **...** | 30 | 0 | *(14 bytes of zeros)* |
| **148** | 30 | 0 | **UID Mirror End** |
| **149** | 26 | & | & |
| **150** | 63 | c | c |
| **151** | 74 | t | t |
| **152** | 72 | r | r |
| **153** | 3D | \= | \= |
| **154** | 30 | 0 | **Counter Mirror Start** (Mirror Offset 154\) |
| **...** | 30 | 0 | *(6 bytes of zeros)* |
| **159** | 30 | 0 | **Counter Mirror End** |
| **160** | 26 | & | & |
| **161** | 63 | c | c |
| **...** | ... | ... | mac= |
| **166** | 30 | 0 | **CMAC Mirror Start** (Mirror Offset 166\) |
| **...** | 30 | 0 | *(16 bytes of zeros)* |
| **181** | 30 | 0 | **CMAC Mirror End** |

### **Visual Diagram**

### **Python Code to Generate This File**

This function builds the exact byte array you need to write to File 2\.

Python

def generate\_file2\_payload(url\_template: str):  
    """  
    Generates the raw bytes for NTAG 424 DNA File 2 (NDEF File).  
    """  
    if not url\_template.startswith("https://"):  
        raise ValueError("URL must start with https://")  
          
    \# 1\. Strip the protocol (it gets compressed to 0x04)  
    url\_body \= url\_template.replace("https://", "", 1)  
      
    \# 2\. Calculate Lengths  
    \# URI Payload \= 1 byte (0x04) \+ len(body)  
    payload\_len \= 1 \+ len(url\_body)  
      
    \# NDEF Message \= 2 bytes (header D1 01\) \+ 1 byte (len) \+ 1 byte (type 55\) \+ payload  
    \# Note: If payload \> 255 bytes, this logic needs Short Record (SR) adjustment.   
    \# Your URL is \< 255, so standard SR=1 works.  
    ndef\_msg\_len \= payload\_len \+ 4   
      
    \# 3\. Build the NLEN (Type 4 File Header)  
    \# 2 Bytes, Big Endian  
    nlen\_bytes \= ndef\_msg\_len.to\_bytes(2, byteorder='big')  
      
    \# 4\. Build NDEF Headers  
    \# D1 \= Record Header (MB=1, ME=1, SR=1, TNF=1)  
    \# 01 \= Type Length  
    \# payload\_len \= Payload Length  
    \# 55 \= Type 'U'  
    \# 04 \= https:// identifier  
    ndef\_header \= bytes(\[0xD1, 0x01, payload\_len, 0x55, 0x04\])  
      
    \# 5\. Build Final Byte Array  
    file2\_data \= nlen\_bytes \+ ndef\_header \+ url\_body.encode('ascii')  
      
    return file2\_data

\# Example Usage  
url \= "https://script.google.com/a/macros/gutsteins.com/s/AKfycbz...exec?uid=00000000000000\&ctr=000000\&cmac=0000000000000000"  
data \= generate\_file2\_payload(url)

print(f"Total Bytes to Write: {len(data)}")  
print(f"Hex Start: {data\[:10\].hex().upper()}")   
\# Output example: 00BE D1 01 BA 55 04 73 63 72 …

## **CMAC Configuration**

The NDEF file structure I showed includes the **space** for the CMAC, but the **generation** logic must be turned on separately.

To get the CMAC into that URL, you must apply a specific **File Settings** configuration to File 2\. Without this second step, the URL will simply remain static with cmac=0000000000000000 forever.

Here is the separation of duties:

### **1\. The Container (File 2 Content)**

* **What it provides:** The cmac=0000... placeholder.  
* **Role:** Allocates 32 hex characters (16 bytes) of physical memory in the file so the tag has a place to write the signature.  
* **Status:** This is what the Python script I provided generates.

### **2\. The Engine (File 2 Settings)**

* **What it provides:** The logic to calculate the CMAC and overwrite the zeros.  
* **Role:** You must send a ChangeFileSettings (Command 0xDD) to tell the tag: *"Every time you are read, calculate a CMAC and write it to byte offset 166."*

### **How to Enable the CMAC Generation**

You need to configure the **SDM Options** in the File Settings. Here is the exact configuration required to match the NDEF file we just built:

| Setting | Value | Why? |
| :---- | :---- | :---- |
| **SDM Enabled** | **TRUE** | Turns on the dynamic mirroring engine. |
| **UID Mirror** | **TRUE** | Enables the UID replacement. |
| **ReadCounter Mirror** | **TRUE** | Enables the Counter replacement. |
| **SDM ReadCounter Limit** | **FALSE** | (Optional) Set True if you want the link to die after X scans. |
| **SDM Encrypt File Data** | **FALSE** | **Critical:** We are using **Plain** SDM (MAC only), not encryption. |
| **SDM MAC Input Offset** | **0** | **Critical:** Signs "Empty Data" to match your Python validation fix. |
| **SDM MAC Offset** | **166** | Tells the tag to put the result at byte 166 (cmac=...). |
| **SDM Access Rights** | **Key 2** | Defines *which key* is used to generate the MAC (Key 2 is standard). |

### **Python Code to Apply the Config**

If you are using a library (like ntag424-sdm-provisioner or similar), the setup command looks like this. This is the step that actually "includes CMAC generation":

Python

\# This is NOT the file content; this is the Configuration Command.  
sdm\_config \= {  
    'sdm\_meta\_read\_access\_rights': 2,  \# Use Key 2 for MAC calculation  
    'sdm\_file\_read\_access\_rights': 0xE, \# Free Read Access (Crucial for Android detection)  
      
    \# Enable Mirrors  
    'uid\_mirroring\_enabled': True,  
    'counter\_mirroring\_enabled': True,  
    'sdm\_enabled': True,

    \# The Offsets we calculated earlier  
    'uid\_offset': 135,  
    'counter\_offset': 154,  
    'sdm\_mac\_offset': 166,

    \# The Fix for your Validation (Sign Empty Data)  
    'sdm\_mac\_input\_offset': 0   
}

\# Send command 0xDD (ChangeFileSettings) with these parameters  
tag.change\_file\_settings(file\_number=2, \*\*sdm\_config)

### **Summary**

5. **Does the URL text include the CMAC?** No, it includes a *placeholder*.  
6. **Does the Tag Configuration include the CMAC?** Yes, if you apply the settings above, the tag will automatically replace that placeholder with a fresh CMAC on every tap.

