# NXP NT4H2421Gx NTAG 424 DNA - Section 10: Command Set

**Source:** NT4H2421Gx Datasheet Rev. 3.0, 31 January 2019
**Copyright:** NXP B.V. 2019 - Extracted for technical reference

---

**10 Command set** 

**10.1 Introduction** 

This section contains the full command set of NTAG 424 DNA. 

**Remark**: In the figures and tables, always CommMode.Plain is presented and the field length is valid for the plain data length. For the CommMode.MAC and CommMode.Full, the cryptogram needs to be calculated according to the secure messaging Section 9, then data field needs to fill with the cryptogram (Plain; CMAC; encrypted data with 

CMAC). Communication mode and condition are mentioned in the command description. **10.2 Supported commands and APDUs**   
**Table 22. APDUs**

![Table 22](images/nxp-datasheet/table_22_page_013.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

| Command  | C-APDU (hex)  |  |  |  |  |  |  | R-APDU (hex)  |  | Communication mode |
| ----- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---- |
| **INS**  | **CLA**  | **INS**  | **P1**  | **P2**  | **Lc**  | **Data**  | **Le**  | **Data**  | **SW1SW2** Succ  essful |  |
| AuthenticateEV2First \- Part1  | 90  | 71  | 00  | 00  | XX  | Data  | 00  | Data  | 91AF  | N/A (command specific) |
| AuthenticateEV2First \- Part2  | 90  | AF  | 00  | 00  | 20  | Data  | 00  | Data  | 9100 |  |
| AuthenticateEV2NonFirst \- Part1 | 90  | 77  | 00  | 00  | XX  | Data  | 00  | Data  | 91AF  | N/A (command specific) |
| AuthenticateEV2NonFirst \- Part2 | 90  | AF  | 00  | 00  | 20  | Data  | 00  | Data  | 9100 |  |
| AuthenticateLRPFirst \- Part1  | 90  | 71  | 00  | 00  | XX  | Data  | 00  | Data  | 91AF  | N/A (command specific) |
| AuthenticateLRPFirst \- Part2  | 90  | AF  | 00  | 00  | 20  | Data  | 00  | Data  | 9100 |  |
| AuthenticateLRPNonFirst \- Part1 | 90  | 77  | 00  | 00  | XX  | Data  | 00  | Data  | 91AF  | N/A (command specific) |
| AuthenticateLRPNonFirst \- Part2 | 90  | AF  | 00  | 00  | 20  | Data  | 00  | Data  | 9100 |  |
| ChangeFileSettings  | 90  | 5F  | 00  | 00  | XX  | Data  | 00  | \-  | 9100  | CommMode.Full |
| ChangeKey  | 90  | C4  | 00  | 00  | XX  | Data  | 00  | \-  | 9100  | CommMode.Full |
| GetCardUID  | 90  | 51  | 00  | 00  | \-  | \-  | 00  | Data  | 9100  | CommMode.Full |
| GetFileCounters  | 90  | F6  | 00  | 00  | \-  | File ID  | 00  | Data  | 9100  | CommMode.Full |
| GetFileSettings  | 90  | F5  | 00  | 00  | 01  | File number  | 00  | Data  | 9100  | CommMode.MAC |
| GetKeyVersion  | 90  | 64  | 00  | 00  | 01  | Key number  | 00  | Data  | 9100  | CommMode.MAC |
| GetVersion \- Part1  | 90  | 60  | 00  | 00  | \-  | \-  | 00  | Data  | 91AF  | CommMode.MAC\[1\] |
| GetVersion \- Part2  | 90  | AF  | 00  | 00  | \-  | \-  | 00  | Data  | 91AF  | CommMode.MAC |
| GetVersion \- Part3  | 90  | AF  | 00  | 00  | \-  | \-  | 00  | Data  | 9100  | CommMode.MAC |
| ISOReadBinary  | 00  | B0  | XX  | XX  | \-  | \-  | XX  | Data  | 9000  | CommMode.Plain |
| ReadData  | 90  | AD  | 00  | 00  | XX  | Reference  | 00  | Data  | 9100  | Comm. mode of targeted file |
| Read\_Sig  | 90  | 3C  | 00  | 00  | 01  | 00  | 00  | Data  | 9100  | CommMode.Full |
| ISOSelectFile  | 00  | A4  | XX  | XX  | XX  | Data to send  | XX  | FCI  | 9000  | CommMode.Plain |
| SetConfiguration  | 90  | 5C  | 00  | 00  | XX  | Data  | 00  | \-  | 9100  | CommMode.Full |
| ISOUpdateBinary  | 00  | D6  | XX  | XX  | XX  | Data to write  | \-  | \-  | 9000  | CommMode.Plain |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 44 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Command  | C-APDU (hex)  |  |  |  |  |  |  | R-APDU (hex)  |  | Communication mode |
| :---- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---- |
| WriteData  | 90  | 8D  | 00  | 00  | XX  | Data  | 00  | \-  | 9100  | Comm. mode of targeted file |

\[1\] MAC on command and returned with the last response, calculated over all 3 responses 

**10.3 Status word** 

**Table 23. SW1 SW2 for CLA byte 0x90** 

![Table 23](images/nxp-datasheet/table_23_page_045.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

| SW1 SW2  | Name  | Description |
| :---: | ----- | ----- |
| 0x9100  | OPERATION\_OK  | Successful operation. |
| 0x911C  | ILLEGAL\_COMMAND\_CODE  | Command code not supported. |
| 0x911E  | INTEGRITY\_ERROR  | CRC or MAC does not match data. Padding bytes not valid. |
| 0x9140  | NO\_SUCH\_KEY  | Invalid key number specified. |
| 0x917E  | LENGTH\_ERROR  | Length of command string invalid. |
| 0x919D  | PERMISSION\_DENIED  | Current configuration / status does not allow the re- quested command. |
| 0x919E  | PARAMETER\_ERROR  | Value of the parameter(s) invalid. |
| 0x91AD  | AUTHENTICATION\_DELAY  | Currently not allowed to authenticate. Keep trying until full delay is spent. |
| 0x91AE  | AUTHENTICATION\_ERROR  | Current authentication status does not allow the re- quested command. |
| 0x91AF  | ADDITIONAL\_FRAME  | Additionaldata frame is expected to be sent. |
| 0x91BE  | BOUNDARY\_ERROR  | Attempt toread/write data from/to beyond the file’s/record’s limits. Attempt to exceed the limits of a value file. |
| 0x91CA  | COMMAND\_ABORTED  | Previous Command was not fully completed. Not all Frames were requested or provided by the PCD. |
| 0x91F0  | FILE\_NOT\_FOUND  | Specified file number does not exist. |

**Table 24.  SW1 SW2 for CLA byte 0x00**

![Table 24](images/nxp-datasheet/table_24_page_045.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

| SW1 SW2  | Description |
| :---: | ----- |
| 0x6700  | Wrong length; no further indication |
| 0x6982  | Security status not satisfied |
| 0x6985  | Conditions of use not satisfied |
| 0x6A80  | Incorrect parameters in the command data field |
| 0x6A82  | File or application not found |
| 0x6A86  | Incorrect parameters P1-P2 |
| 0x6A87  | Lc inconsistent with parameters P1-P2 |
| 0x6C00  | Wrong Le field |
| 0x6CXX  | Wrong Le field; SW2 encodes the exact number of avail- able data bytes. |
| 0x6D00  | Instruction code not supported or invalid |
| 0x6E00  | Class not supported |
| 0x9000  | Normal processing (no further qualification) |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 45 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.4 Authentication commands** 

Authentication with the defined key is required to access the protected file according to access rights. Based on successful authentication session keys are generated, which are used for secure messaging between the terminal and NT4H2421Gx. 

**Remark:**Default FWI settings for authentication and secure messaging are set according to GSMA specification v2.0 to the value 7h. This value is stored in the User ATS. 

**10.4.1 AuthenticateEV2First** 

This command initiates an authentication based on standard AES. After this 

authentication, AES secure messaging is applied. This authentication command is 

used to authenticate for the first time in a transaction and can always be used within 

a transaction. AuthenticateEV2First starts a transaction with a Transaction Identifier 

(TI) and AuthenticateEV2NonFirst continues the transaction with that TI. This 3-pass challenge-response-based mutual authentication command is completed in two parts: 

| 1st Part 1  1 1 1 1 1 1 \[1...6\]  1  CLA  CMD  P1  P2  Lc  Le  KeyNo LenCap PCDcap2  PCD to PICC  90  71  00  00  XX  00  16  1  1  status  Response data  PICC to PCD  E(Kx, RndB)  SW1  SW2  2nd Part  1  1 1 1 1  1  32  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  E(Kx, RndA || RndB')  90  AF  00  00  20  00  32  1  1  status  Response data  PICC to PCD  E(Kx, TI || RndA' || PDcap2 || PCDcap2)  SW1  SW2  *aaa-032196*  Figure 13.  AuthenticateEV2First command protocol |

![Figure 13](images/nxp-datasheet/figureigure_13_page_046.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)
| ----- |

**Table 25.  Command parameters description \- AuthenticateEV2First \- Part1**

![Table 25](images/nxp-datasheet/table_25_page_046.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| CMD  | 1  | 71h  | Command code. |
| KeyNo | 1  |  | Targeted authentication key |
|  | Bit 7-6  | 00b  | RFU |
|  | Bit 5-0  | 0h to 4h  | Key number |
| LenCap  | 1  | 00h to 06h  | Length of the PCD Capabilities.  \[This value should be set to 00h\]. |
| PCDcap2.1 | \[1\]  | \-  | Capability vector of the PCD. |
|  | Bit 7-2  | Full range  | RFU, can hold any value |
|  | Bit 1  | 0b  | EV2 secure messaging |
|  | Bit 0  | Full range  | RFU, can hold any value |
| PCDcap2.2-6  | \[1..5\]  | Full range  | Capability vector of the PCD.  All other bytes but PCDcap2.1 are optional, RFU and can hold any value.  \[If LenCap set to 00h, no PCDcap2 present\] |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 46 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Data Parameters** |  |  |  |
| \-  | \-  | \-  | No data parameters |

**Table 26.  Response data parameters description \- AuthenticateEV2First \- Part1** 

![Table 26](images/nxp-datasheet/table_26_page_047.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| E(Kx, RndB)  | 16  | Full range  | Encrypted PICC challenge  The following data, encrypted with the key Kx referenced by KeyNo:  \- RndB: 16 byte random from PICC |
| SW1SW2  | 2  | 91AFh  91XXh | successful execution  Refer to Table 26 |

![Table 26](images/nxp-datasheet/table_26_page_047.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

**Table 27.  Return code description \- AuthenticateEV2First \- Part1** 

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed. |
| NO\_SUCH\_KEY  | 40h  | Targeted key does not exist |
| PERMISSION\_DENIED  | 9Dh | Targeted key not available for authentication. |
|  |  | Targeted key not enabled. |
|  |  | Targeting EV2 authentication and secure messaging, while not allowed by configuration (PDCap2.1.Bit1 is ’1’). |
| AUTHENTICATION\_DELAY  | ADh  | Currently not allowed to authenticate. Keep trying until full delay is spent. |

**Table 28.  Command parameters description \- AuthenticateEV2First \- Part2**

![Table 28](images/nxp-datasheet/table_28_page_047.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| CMD  | 1  | AFh  | Additional frame |
| E(Kx, RndA || RndB') | 32  | Full range | Encrypted PCD challenge and response |
|  |  |  | The following data, encrypted with the key Kx referenced by KeyNo:  \- RndA: 16 byte random from PCD.  \- RndB': 16 byte RndB rotated left by 1 byte |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 47 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**Table 29.  Response data parameters description \- AuthenticateEV2First \- Part2** 

![Table 29](images/nxp-datasheet/table_29_page_048.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| E(Kx, TI  || RndA' ||  PDcap2 ||  PCDcap2) | 32  | Full range  | Encrypted PICC response  The following data encrypted with the key referenced by KeyNo:  \- TI: 4 byte Transaction Identifier  \- RndA’: 16 byte RndA rotated left by 1 byte. \- PDcap2: 6 byte PD capabilities  \- PCDcap2: 6 byte PCD capabilities |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 30 |

![Table 30](images/nxp-datasheet/table_30_page_048.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

**Table 30.  Return code description \- AuthenticateEV2First \- Part2**

![Table 30](images/nxp-datasheet/table_30_page_048.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| AUTHENTICATION\_ERROR  | AEh  | Wrong RndB' |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 48 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.4.2 AuthenticateEV2NonFirst** 

The AuthenticateEV2NonFirst command can be used only if there is a valid 

authentication with AuthenticateEV2First. It continues the transaction with the transaction started by previous AuthenticateEV2First command. It starts a new session. The scheme of transaction and sessions within the transaction have been designed to protect any possible sophisticated replay attacks 

| 1st Part  1  1 1 1 1 1  1  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  KeyNo  90  77  00  00  01  00  16  1  1  status  Response data  PICC to PCD  E(Kx, RndB)  SW1  SW2  2nd Part  1  1 1 1 1  1  32  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  E(Kx, RndA || RndB')  90  AF  00  00  20  00  32  1  1  status  Response data  PICC to PCD  E(Kx, RndA')  SW1  SW2  *aaa-032197*  Figure 14.  AuthenticateEV2NonFirst command protocol |

![Figure 14](images/nxp-datasheet/figureigure_14_page_049.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)
| ----- |

**Table 31.  Command parameters description \- AuthenticateEV2NonFirst \- Part1** 

![Table 31](images/nxp-datasheet/table_31_page_049.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| CMD  | 1  | 77h  | Command code. |
| KeyNo | 1  |  | Targeted authentication key |
|  | Bit 7-6  | 0  | RFU |
|  | Bit 5-0  | 0h to 04h  | Key number |
| **Command Data Parameters** |  |  |  |
| \-  | \-  | \-  | No data parameters |

**Table 32.  Response data parameters description \- AuthenticateEV2NonFirst \- Part1**

![Table 32](images/nxp-datasheet/table_32_page_049.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| E(Kx, RndB)  | 16  | Full range  | Encrypted PICC challenge  The following data, encrypted with the key Kx referenced by KeyNo:  \- RndB (16 byte): Random number from the PICC. |
| SW1SW2  | 2  | 91AFh  91XXh | successful execution  Refer to Table 33 |

![Table 33](images/nxp-datasheet/table_33_page_049.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 49 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**Table 33.  Return code description \- AuthenticateEV2NonFirst \- Part1** 

![Table 33](images/nxp-datasheet/table_33_page_049.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed. |
| NO\_SUCH\_KEY  | 40h  | Targeted key does not exist |
| PERMISSION\_DENIED  | 9Dh | In not authenticated state and not targeting OriginalityKey |
|  |  | Targeted key not available for authentication. |
|  |  | Targeted key not enabled. |
| AUTHENTICATION\_DELAY  | ADh  | Currently not allowed to authenticate. Keep trying until full delay is spent. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

**Table 34.  Command parameters description \- AuthenticateEV2NonFirst \- Part2** 

![Table 34](images/nxp-datasheet/table_34_page_050.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| CMD  | 1  | AFh  | Additional frame |
| E(Kx, RndA || RndB') | 32  | Full range | Encrypted PCD challenge and response |
|  |  |  | The following data, encrypted with the key Kx referenced by KeyNo:  \- RndA: 16 byte random from PCD.  \- RndB': 16 byte RndB rotated left over 1 byte. |

**Table 35.  Response data parameters description \- AuthenticateEV2NonFirst \- Part2** 

![Table 35](images/nxp-datasheet/table_35_page_050.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| E(Kx, RndA')  | 16  | Full range  | Encrypted PICC challenge and response The following data, encrypted with the key Kx referenced by KeyNo:  \- RndA: 16 byte random from PCD.  \- RndB’: 16 byte RndB rotated left over 1 byte. |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 36 |

![Table 36](images/nxp-datasheet/table_36_page_050.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

**Table 36.  Return code description \- AuthenticateEV2NonFirst \- Part2**

![Table 36](images/nxp-datasheet/table_36_page_050.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| AUTHENTICATION\_ERROR  | AEh  | Wrong RndB' |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 50 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.4.3 AuthenticateLRPFirst** 

Authentication for LRP secure messaging. The AuthenticationLRPFirst is intended to be the first in a transaction and recommended. LRP secure messaging allows side-channel resistant implementations. 

| 1st Part  1  1 1 1 1  1  1  CLA  CMD  P1  P2  Lc  Le  KeyNo  PCD to PICC  90  71  00  00  01  00  1 16  1  1  status  Auth  Response data  PICC to PCD  Mode  RndB  SW1  SW2  2nd Part  1  1 1 1 1 16 16  1  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  RndA PCDResponse  90  AF  00  00  20  00  16 16  1  1  Data status  PICC to PCD  PICCData PICCResponse  SW1  SW2  *aaa-032199*  Figure 15.  AuthenticateLRPFirst command protocol |

![Figure 15](images/nxp-datasheet/figureigure_15_page_051.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)
| ----- |

**Table 37. Command parameters description \- AuthenticateLRPFirst \- Part1** 

![Table 37](images/nxp-datasheet/table_37_page_051.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| CMD  | 1  | 71h  | Command code. |
| KeyNo | 1  |  | Targeted authentication key |
|  | Bit 7-6  | 00b  | RFU |
|  | Bit 5-0  | 0h..4h  | Key number |
| LenCap  | 1  | 1h..6h  | Length of the PCD Capabilities. |
| PCDcap2.1 | 1  | \-  | Capability vector of the PCD. |
|  | Bit 7-2  | Full range  | RFU, can hold any value |
|  | Bit 1  | 1b  | LRP secure messaging |
|  | Bit 0  | Full range  | RFU, can hold any value |
| PCDcap2.2-6  | \[1..5\]  | Full range  | Capability vector of the PCD.  All other bytes but PCDcap2.1 are optional, RFU and can hold any value. |
| **Command Data Parameters** |  |  |  |
| \-  | \-  | \-  | No data parameters |

**Table 38. Response data parameters description \- AuthenticateLRPFirst \- Part1**

![Table 38](images/nxp-datasheet/table_38_page_051.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| AuthMode  | 1  | 01h  | LRP Mode |
| RndB  | 16  | Full range  | PICC challenge  RndB |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 51 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| SW1SW2  | 2  | 91AFh  91XXh | successful execution  Refer to Table 39 |

![Table 39](images/nxp-datasheet/table_39_page_052.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

**Table 39.  Return code description \- AuthenticateLRPFirst \- Part1** 

![Table 39](images/nxp-datasheet/table_39_page_052.svg)

![Table 3](images/nxp-datasheet/table_3_page_007.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed. |
| NO\_SUCH\_KEY  | 40h  | Targeted key does not exist. |
| PERMISSION\_DENIED  | 9Dh  | Targeted key is locked as related TotFailCtr is equal to or bigger than the TotFailCtrLimit. |
| AUTHENTICATION\_DELAY  | ADh  | Currently not allowed to authenticate. Keep trying until full delay is spent. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

**Table 40. Command parameters description \- AuthenticateLRPFirst \- Part2** 

![Table 40](images/nxp-datasheet/table_40_page_052.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| CMD  | 1  | AFh  | Additional frame |
| RndA  | 16  | Full range  | PCD challenge |
| PCDResponse  | 16  | Full range  | PCD response  *MACLRP (SesAuthMACKey;RndA || RndB)* |

**Table 41. Response data parameters description \- AuthenticateLRPFirst \- Part2** 

![Table 41](images/nxp-datasheet/table_41_page_052.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| PICCData  | 16  | Full range  | Encrypted PICC data,  ELRP (SesAuthENCKey; TI; PDCap2;  PCDCap2) |
| PICCRespons e | 16  | Full range  | PICC response to the challenge  *MACLRP (SesAuthMACKey; RndB || RndA || PICCData)* |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 42 |

![Table 42](images/nxp-datasheet/table_42_page_052.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

**Table 42.  Return code description \- AuthenticateLRPFirstPart2**

![Table 42](images/nxp-datasheet/table_42_page_052.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| AUTHENTICATION\_ERROR  | AEh  | Wrong PCDResp |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 52 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.4.4 AuthenticateLRPNonFirst** 

Consecutive authentication for LRP secure messaging. After this authentication, 

LRP secure messaging is used. This authentication is intended to be the following 

authentication in a transaction. 

| 1st Part  1 1 1 1 1  1 1 \[1...6\] 1  CLA  CMD  P1  P2  Lc  Le  KeyNo LenCap PCDcap2  PCD to PICC  90  71  00  00  XX  00  1 16  1  1  status  Auth  Response data  PICC to PCD  Mode  RndB  SW1  SW2  2nd Part  1  1 1 1 1 16 16  1  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  RndA PCDResponse  90  AF  00  00  20  00  32  1  1  status  Response data  PICC to PCD  PICCResponse  SW1  SW2  *aaa-032198*  Figure 16.  AuthenticationLRPNonFirst command protocol |

![Figure 16](images/nxp-datasheet/figureigure_16_page_053.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)
| ----- |

**Table 43. Command parameters description \- AuthenticateLRPNonFirst \- Part1** 

![Table 43](images/nxp-datasheet/table_43_page_053.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| CMD  | 1  | 71h  | Command code. |
| KeyNo | 1  |  | Targeted authentication key |
|  | Bit 7-6  | 00b  | RFU |
|  | Bit 5-0  | 00h to 04h  | Key Number |
| **Command Data Parameters** |  |  |  |
| \-  | \-  | \-  | No data parameters |

**Table 44. Response data parameters description \- AuthenticateLRPNonFirst \- Part1** 

![Table 44](images/nxp-datasheet/table_44_page_053.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| AuthMode  | 1  | 01h  | LRP |
| RndB  | 16  | Full range  | PICC random RndB |
| SW1SW2  | 2  | 91AFh  91XXh | successful execution  Refer to Table 45 |

![Table 45](images/nxp-datasheet/table_45_page_053.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

**Table 45.  Return code description \- AuthenticateLRPNonFirst \- Part1**

![Table 45](images/nxp-datasheet/table_45_page_053.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 53 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Status  | Value  | Description |
| :---- | :---- | ----- |
| NO\_SUCH\_KEY  | 40h  | Targeted key does not exist |
| PERMISSION\_DENIED  | 9Dh | In not authenticated state and not targeting OriginalityKeys |
|  |  | Targeted key not available for authentication. |
|  |  | Targeted key not enabled. |
| AUTHENTICATION\_DELAY  | ADh  | Currently not allowed to authenticate.  Keep trying until full delay is spent. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

**Table 46.  Command parameters description \- AuthenticateLRPNonFirst \- Part2** 

![Table 46](images/nxp-datasheet/table_46_page_054.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| CMD  | 1  | AFh  | Additional frame |
| RndA  | 16  | Full range  | PCD challenge  RndA |
| PCDResp  | 16  | Full range  | PCD response to the challenge  *MACLRP (SesAuthMACKey;RndA || RndB)* |

**Table 47. Response data parameters description \- AuthenticateLRPNonFirst \- Part2** 

![Table 47](images/nxp-datasheet/table_47_page_054.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| PICCResp  | 16  | Full range  | PICC response to the challenge  *MACLRP (SesAuthMACKey;RndB || RndA)* |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 48 |

![Table 48](images/nxp-datasheet/table_48_page_054.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

**Table 48.  Return code description \- AuthenticateLRPNonFirst \- Part2**

![Table 48](images/nxp-datasheet/table_48_page_054.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| AUTHENTICATION\_ERROR  | AEh  | Wrong PCDResp |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 54 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.5 Memory and configuration commands** 

**10.5.1 SetConfiguration** 

With the SetConfiguration command, the application attributes can be configured. It 

requires an authentication with the AppMasterKey and CommMode.Full. 

The command consists of an option byte and a data field with a size depending on the option. The option byte specifies the nature of the data field content. 

In the below table “No change” references are used with configurations that are 

persistent. This means that the associated configuration is left as it is already in the card and its value is not changed. 

| 1 1 1 1 1  1 up to 40 bytes 1  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  Option  Data Parameters  90  5C  00  00  XX  00  0  1  1  status  Response data  PICC to PCD  \-  SW1  SW2  *aaa-032200*  Figure 17.  SetConfiguration command protocol |

![Figure 17](images/nxp-datasheet/figureigure_17_page_055.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)
| ----- |

**Table 49. Command parameters description \- SetConfiguration** 

![Table 49](images/nxp-datasheet/table_49_page_055.svg)

![Table 4](images/nxp-datasheet/table_4_page_008.svg)

| Name  | Length  | Value  | Description |
| ----- | ----- | :---- | :---- |
| Command Header Parameters |  |  |  |
| Cmd  | 1  | 5Ch  | Command code. |
| Option  | 1 | \-  | Configuration Option. It defines the length and content of the Data parameter. The Option byte is transmitted in plain text, whereas the Data is always transmitted in CommMode.Full. |
|  |  | 00h  | PICC configuration. |
|  |  | 04h  | Secure Messaging Configuration. |
|  |  | 05h  | Capability data. |
|  |  | 0Ah  | Failed authentication counter setting |
|  |  | 0Bh  | HW configuration |
|  |  | Other values  | RFU |
| Command Data Parameters |  |  |  |
| Data  | Up to 10 bytes  | \-  | Data content depends on option values. |
|  |  | Full range  | Data content depends on option value as defined in setConfigOptionsList Table. |

**Table 50.  SetConfigOptionList**

![Table 50](images/nxp-datasheet/table_50_page_055.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

| Option  | Data  Length | Field  | Length/bitin dex | Description |
| :---- | :---- | :---- | :---- | :---- |
| 00h  | 1 byte  | PICC Configuration |  |  |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 55 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Option  | Data  Length | Field  | Length/bitin dex | Description |
| :---- | :---- | :---- | :---- | :---- |
|  |  | PICCConfig | Bit 7-2  | RFU |
|  |  |  | Bit 1  | UseRID configuration for Random. Random ID is disabled at delivery time.  1b: Enable Random UID  0b: No change |
|  |  |  | Bit 0  | RFU |
| 04h  | 2 bytes | Secure Messaging Configuration |  |  |
|  |  | SMConfig  | Bit 15 to 3  | RFU |
|  |  |  | Bit 2  | Secure messaging configuration for StandardData file  0b: No Change  1b: disable chained writing with WriteData command in CommMod e.MAC and CommMode.Full |
|  |  |  | Bit 1-0  | RFU |
| 05h  | 10 bytes | Capability data, consisting of PDCap2 |  |  |
|  |  |  | 4 bytes  | RFU |
|  |  |  | 1 byte  | User configured PDCap2.1  Bit 7 to 2: RFU  Bit 1: 1b means enable LRP mode. This change is permanent, LRP mode cannot be disabled afterwards.  Bit 1: 0b means no change |
|  |  |  | 3 bytes  | RFU |
|  |  |  | 1 byte  | User configured PDCap2.5 |
|  |  |  | 1 byte  | User configured PDCap2.6 |
| 0Ah  | 5 bytes | Failed authentication counter configuration |  |  |
|  |  | FailedCtrOption  | 1 byte  | Bit 7 to 1: RFU  Bit 0: Set to 0b for disabling Bit 0: Set to 1b for enabling  \[default\] |
|  |  | TotFailCtrLimit  | 2 bytes  | configurable limit, encoded as 2-byte unsigned integer (LSB first), must be bigger than 0000h. Default value: 1000\. When  disabling, this value is ignored |
|  |  | TotFailCtrDecr  | 2 bytes  | configurable decrement value, encoded as 2-byte unsigned integer (LSB first). Default value: 10\. When disabling, this value is ignored. |
| 0Bh  | 1 byte  | HW configuration |  |  |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 56 / 97**  
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Option  | Data  Length | Field  | Length/bitin dex | Description |
| :---- | :---- | :---- | :---- | :---- |
|  |  | HW Option  | 1 byte  | Bit 7 to 1: RFU  Bit 0: Set to 0b for Standard back modulation  Bit 0: Set to 1b for Strong back modulation (default)\[1\] |

\[1\] note that it is strongly recommended to leave the default setting, specifically for antennas smaller than Class1 

**Table 51. Response data parameters description \- SetConfiguration** 

![Table 51](images/nxp-datasheet/table_51_page_057.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| Response  data | 0  | \-  | No response data |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 52 |

![Table 52](images/nxp-datasheet/table_52_page_057.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

**Table 52. Return code description \- SetConfiguration**

![Table 52](images/nxp-datasheet/table_52_page_057.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

| Status  | Value  | Description |
| ----- | ----- | :---- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| INTEGRITY\_ERROR  | 1Eh  | Invalid cryptogram (padding or CRC). Invalid secure messaging MAC. |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed.  Option 00h: Data length is not 1  Option 04h: Data length is not 2  Option 05h: Data length is not 10  Option 0Ah: Data length is not 5  Option 0Bh: Data length is not 1 |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed.  Option 00h: Data bit 7-2 or bit 0 not set to 0b.  Unsupported option (i.e. Reserved). |
| PERMISSION\_DENIED  | 9Dh  | Option 00h, 04h, 05h, 0Ah, 0Bh: not supported / allowed at PICC level |
| AUTHENTICATION\_ERROR  | AEh  | Option 00h, 04h, 05h, 0Ah, 0Bh: No active authentication with AppMasterKey. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 57 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.5.2 GetVersion** 

The GetVersion command returns manufacturing related data of NTAG 424 DNA 

(NT4H2421Gx). No parameters are required for this command. 

**Remark:** This command is only available after ISO/IEC 14443-4 activation. 

The version data is return over three frames. Part1 returns the hardware-related 

information, Part2 returns the software-related information and Part3 and last frame 

returns the production-related information. This command is freely accessible without secure messaging as soon as the PD is selected and there is no active authentication. 

| 1 1 1 1 1 1 Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  \-  90  60  00  00  \-  00  1 1 1  1  1  1  1  1  1  PICC to PCDSW1status VendorID  HWType  HWSubType HWMajorVersion  HWMinorVersion  HWStorageSize  HWProtocol  SW2  0  1 1 1 1 1  1  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  \-  90  AF  00  00  \-  00  1 1 1  1  1  1  1  1  1  PICC to PCDSW1status VendorID  SWType  SWSubType SWMajorVersion  SWMinorVersion  SWStorageSize  SWProtocol  SW2  1 1 1 1 1  0  1  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  \-  90  AF  00  00  \-  00  7 1 1  1  4  1  1  \[1\]  PICC to PCDSW1status UID  BatchNo  BatchNo/FabKey FabKey/CWProd  YearProd  FabKeyID  SW2  *aaa-032201*  Figure 18. GetVersion command protocol |

![Figure 18](images/nxp-datasheet/figureigure_18_page_058.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)
| ----- |

**Part 1** 

**Table 53.  Command parameters description \- GetVersion \- Part1** 

![Table 53](images/nxp-datasheet/table_53_page_058.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| Cmd  | 1  | 60h  | Command code. |
| **Command Data Parameters** |  |  |  |
| \-  | \-  | \-  | No data parameters |

**Table 54.  Response data parameters description \- GetVersion \- Part1**

![Table 54](images/nxp-datasheet/table_54_page_058.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| VendorID  | 1  | 04h  | Vendor ID |
| HWType  | 1  | 04h  | HW type for NTAG |
| HWSubType  | 1 | \-  | HW subtype |
|  |  | X2h  | 50 pF |
|  |  | 0Xh  | Strong back modulation |
|  |  | 8Xh  | Standard back modulation |
| HWMajorVersion  | 1  | 30h  | HW major version number |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 58 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| HWMinorVersion  | 1  | 00h  | HW minor version number |
| HWStorageSize  | 1 | \-  | HW storage size |
|  |  | 11h  | 256 B\<storage size\< 512 B |
|  |  | other  values | RFU |
| HWProtocol  | 1  | 05h  | HW communication protocol type |
| SW1SW2  | 2  | 91AFh  91XXh | successful execution  Refer to Table 59 |

![Table 59](images/nxp-datasheet/table_59_page_059.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

**Part 2** 

**Table 55.  Command parameters description \- GetVersion \- Part2** 

![Table 55](images/nxp-datasheet/table_55_page_059.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| CMD  | 1  | AFh  | Additional frame request. |
| Data  | 0  | \-  | No data parameters: |

**Table 56.  Response data parameters description \- GetVersion \- Part2** 

![Table 56](images/nxp-datasheet/table_56_page_059.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| VendorID  | 1  | 04h  | Vendor ID |
| SWType  | 1  | 04h  | SW type for NTAG |
| SWSubType  | 1  | 02h  | SW subtype |
| SWMajorVersion  | 1  | 01h  | SW major version number |
| SWMinorVersion  | 1  | 02h  | SW minor version number |
| SWStorageSize  | 1 | \-  | SW storage size |
|  |  | 11h  | 256 B\<storage size\< 512 B |
|  |  | other  values | RFU |
| SWProtocol  | 1  | 05h  | SW communication protocol type |
| SW1SW2  | 2  | 91AFh  91XXh | successful execution  Refer to Table 59 |

![Table 59](images/nxp-datasheet/table_59_page_059.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

**Part 3** 

**Table 57.  Command parameters description \- GetVersion \- Part3**

![Table 57](images/nxp-datasheet/table_57_page_059.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| CMD  | 1  | AFh  | Additional frame request. |
| Data  | 0  | \-  | No data parameters: |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 59 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**Table 58.  Response data parameters description \- GetVersion \- Part3** 

![Table 58](images/nxp-datasheet/table_58_page_060.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | ----- | :---- |
| UID  | 7 | \-  | UID |
|  |  | All zero  | if configured for RandomID |
|  |  | Full range  | UID if not configured for RandomID |
| BatchNo  | 4  | Full range  | Production batch number |
| BatchNo/FabKey | 1 |  |  |
|  | Bit 7-4  | Full range  | Production batch number |
|  | Bit 3-0  | 0h  | Default FabKey, other values RFU |
| FabKey/CWProd | 1 |  |  |
|  | Bit 7  | 0b  | Default FabKey, other values RFU |
|  | Bit 6-0  | 01h..52h  | Calendar week of production |
| YearProd  | 1  | Full range  | Year of production |
| FabKeyID  | \[1\]  | 1Fh..FFh  | Optional, present for customized configurations when FabKey \= 1Fh |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 59 |

![Table 59](images/nxp-datasheet/table_59_page_059.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

**Table 59.  Return code description \- GetVersion**

![Table 59](images/nxp-datasheet/table_59_page_059.svg)

![Table 5](images/nxp-datasheet/table_5_page_010.svg)

| Status  | Value  | Description |
| :---- | :---- | :---- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| INTEGRITY\_ERROR  | 1Eh  | Invalid secure messaging MAC (only). |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 60 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.5.3 GetCardUID** 

GetCardUID command is required to get the 7-byte UID from the card. In case "Random ID" at activation is configured, encrypted secure messaging is applied for this command and response. An authentication with any key needs to be performed prior to the 

command GetCardUID. This command returns the UID and gives the opportunity to 

retrieve the UID, even if the Random ID is used. 

| 1 1 1 1 1  1  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  \-  90  51  00  00  \-  00  7  1  1  status  Response data  PICC to PCD  UID  SW1  SW2  *aaa-032202*  Figure 19. GetCardUID command protocol |

![Figure 19](images/nxp-datasheet/figureigure_19_page_061.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)
| ----- |

**Table 60.  Command parameters description \- GetCardUID** 

![Table 60](images/nxp-datasheet/table_60_page_061.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| Cmd  | 1  | 51h  | Command code. |
| **Command Data Parameters** |  |  |  |
| \-  | \-  | \-  | No data parameters |

**Table 61.  Response data parameters description \- GetCardUID** 

![Table 61](images/nxp-datasheet/table_61_page_061.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| UID  | 7  | Full range  | UID of the NT4H2421Gx |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 62 |

![Table 62](images/nxp-datasheet/table_62_page_061.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

**Table 62.  Return code description \- GetCardUID**

![Table 62](images/nxp-datasheet/table_62_page_061.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| INTEGRITY\_ERROR  | 1Eh  | Invalid secure messaging MAC (only). |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| AUTHENTICATION\_ERROR  | AEh  | No active authentication |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 61 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.6 Key management commands** 

NT4H2421Gx provides the following command set for Key Management. 

**10.6.1 ChangeKey** 

The ChangeKey command is used to change the application keys. Authentication with application key number 0 is required to change the key. CommMode.Full is applied for this command. Note that the cryptogram calculations for changing key number 0 and other keys are different. 

| 1 1 1 1 1  1  1 17 or 21  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  KeyNo  KeyData  90  C4  00  00  XX  00  0  1  1  status  Response data  PICC to PCD  \-  SW1  SW2  *aaa-032203*  Figure 20.  ChangeKey command protocol |

![Figure 20](images/nxp-datasheet/figureigure_20_page_062.svg)

![Figure 2](images/nxp-datasheet/figureigure_2_page_007.svg)
| ----- |

**Table 63.  Command parameters description \- ChangeKey** 

![Table 63](images/nxp-datasheet/table_63_page_062.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| Cmd  | 1  | C4h  | Command code. |
| KeyNo | 1  | \-  | Key number of the key to be changed. |
|  | Bit 7-6  | 00b  | RFU |
|  | Bit 5-0 |  | Key Number |
|  |  | 0h..4h  | The application key number |
| **Command Data Parameters** |  |  |  |
| KeyData  | 17 or 21 |  | New key data. |
|  |  | full range  (17-byte  length) | if key 0 is to be changed  NewKey || KeyVer |
|  |  | full range  (21-byte  length) | if key 1 to 4 are to be changed  (NewKey XOR OldKey) || KeyVer ||  CRC32NK\[1\] |

\[1\] The CRC32NK is the 4-byte CRC value computed according to IEEE Std 802.3-2008 (FCS Field) over NewKey \[9\] 

**Table 64.  Response data parameters description \- ChangeKey**

![Table 64](images/nxp-datasheet/table_64_page_062.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| Response data  | 0  | \-  | No response data |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 65 |

![Table 65](images/nxp-datasheet/table_65_page_062.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 62 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**Table 65.  Return code description \- ChangeKey**

![Table 65](images/nxp-datasheet/table_65_page_062.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| INTEGRITY\_ERROR  | 1Eh  | Integrity error in cryptogram or invalid secure messaging MAC ( Secure Messaging). |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed. |
| NO\_SUCH\_KEY  | 40h  | Targeted key does not exist |
| PERMISSION\_DENIED  | 9Dh  | At PICC level, targeting any OriginalityKey which cannot be changed |
| AUTHENTICATION\_ERROR  | AEh  | At application level, missing active authentication with AppMasterKey while targeting any AppKey. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 63 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.6.2 GetKeyVersion** 

The GetKeyVersion command retrieves the current key version of any key. Key version can be changed with the ChangeKey command together with the key. 

| 1 1 1 1 1 1  1  CLA  CMD  P1  P2  Lc  Le  KeyNo  PCD to PICC  90  64  00  00  01  00  1  1  1  status  Response data  PICC to PCD  KeyVer  SW1  SW2  *aaa-032204*  Figure 21.  GetKeyVersion command protocol |

![Figure 21](images/nxp-datasheet/figureigure_21_page_064.svg)

![Figure 2](images/nxp-datasheet/figureigure_2_page_007.svg)
| ----- |

**Table 66.  Command parameters description \- GetKeyVersion** 

![Table 66](images/nxp-datasheet/table_66_page_064.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| Cmd  | 1  | 64h  | Command code. |
| KeyNo | 1  | \-  | Key number of the targeted key |
|  | Bit 7-4  | 00h  | RFU |
|  | 3 to 0  | 00h to 04h  | Application key number |
| **Command Data Parameters** |  |  |  |
| \-  | \-  | \-  | No data parameters |

**Table 67.  Response data parameters description \- GetKeyVersion** 

![Table 67](images/nxp-datasheet/table_67_page_064.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| KeyVer  | 1 | \-  | Key version of the targeted key |
|  |  | 00h  | \[if targeting disabled keys\] |
|  |  | 00h  | \[if targeting OriginalityKey\] |
|  |  | Full range  | \[else\] |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 68 |

![Table 68](images/nxp-datasheet/table_68_page_064.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

**Table 68.  Return code description \- GetKeyVersion**

![Table 68](images/nxp-datasheet/table_68_page_064.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| INTEGRITY\_ERROR  | 1Eh  | Invalid secure messaging MAC (only). |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed. |
| NO\_SUCH\_KEY  | 40h  | Targeted key does not exist. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 64 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.7 File management commands** 

The NT4H2421Gx provides the following command set for File Management functions. 

**10.7.1 ChangeFileSettings** 

The ChangeFileSettings command changes the access parameters of an existing file. The communication mode can be either CommMode.Plain or CommMode.Full based on current access right of the file. 

| 1 1 1 1 1 1Data  CLA  CMD  P1  P2  Lc  Le  FileNo FileOption AccessRights \[SDMOptions SMDAccessRights UIDOffset SDMReadCtrOffset  PCD to PICC  90  5F  00  00  XX  00  PICCDataOffset SDMMACInputOFFset SDMENCOffset SDMENCLength SDMMACOffset SDMReadCtrLimit\]  0 1 1  Response data  \- SW1statusSW2  PICC to PCD  *aaa-032576*  Figure 22.  ChangeFileSettings command protocol |

![Figure 22](images/nxp-datasheet/figureigure_22_page_065.svg)

![Figure 2](images/nxp-datasheet/figureigure_2_page_007.svg)
| ----- |

**Table 69.  Command parameters description \- ChangeFileSettings**

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| Command Header Parameters |  |  |  |
| Cmd  | 1  | 5Fh  | Command code. |
| FileNo | 1  | \-  | File number of the targeted file. |
|  | Bit 7-5  |  | RFU |
|  | Bit 4-0  |  | File number |
| Command Data Parameters |  |  |  |
| FileOption | 1  | \-  | Options for the targeted file. |
|  | Bit 7  | 0b  | RFU |
|  | Bit 6 |  | Secure Dynamic Messaging and Mirroring |
|  |  | 0b  | disabled |
|  |  | 1b  | enabled |
|  | Bit 5-2  | 0000b  | RFU |
|  | Bit 1-0  |  | CommMode (see Table  CommunicationModes) |
| AccessRights  | 2  | \-  | Set of access conditions for the first set in the file (see Section 8.2.3.3). |
| SDMOptions  | \[1\]  | \-  | \[Optional, present if FileOption\[Bit 6\] set\]  SDM Options |
|  | Bit 7  | \-  | UID (only for mirroring) |
|  |  | 0b  | disabled |
|  |  | 1b  | enabled |
|  | Bit 6  | \-  | SDMReadCtr |
|  |  | 0b  | disabled |
|  |  | 1b  | enabled |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 65 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
|  | Bit 5  | \-  | SDMReadCtrLimit |
|  |  | 0b  | disabled |
|  |  | 1b  | enabled |
|  | Bit 4  | \-  | SDMENCFileData |
|  |  | 0b  | disabled |
|  |  | 1b  | enabled |
|  | Bit 3-1  | 000b  | RFU |
|  | Bit 0  | \-  | Encoding mode |
|  |  | 1b  | ASCII |
| SDMAccessRights  | \[2\]  | \-  | \[Optional, present if FileOption\[Bit 6\] set\]  SDM Access Rights |
|  | Bit 15- 12  | \-  | SDMMetaRead access right |
|  |  | 0h..4h  | Encrypted PICCData mirroring using the targeted AppKey |
|  |  | Eh  | Plain PICCData mirroring |
|  |  | Fh  | No PICCData mirroring |
|  | Bit 11- 8  | \-  | SDMFileRead access right |
|  |  | 0h..4h  | Targeted AppKey |
|  |  | Fh  | No SDM for Reading |
|  | Bit 7-4  | Fh  | RFU |
|  | Bit 3-0  | \-  | SDMCtrRet access right |
|  |  | 0h..4h  | Targeted AppKey |
|  |  | Eh  | Free |
|  |  | Fh  | No Access |
| UIDOffset | \[3\]  | \-  | \[Optional, present if  ((SDMOptions\[Bit 7\] \= 1b) AND (SDMMetaRead access right \= Eh)\] Mirror position (LSB first) for UID |
|  |  | 0h .. (FileSize \-  UIDLength) | Offset within the file |
| SDMReadCtrOffset | \[3\]  | \-  | \[Optional, present if  ((SDMOptions\[Bit 6\] \= 1b) AND (SDMMetaRead access right \= Eh)\] Mirror position (LSB first) for SDMReadCtr |
|  |  | 0h .. (FileSize \-  SDMReadCtrLength) | Offset within the file |
|  |  | FFFFFFh  | No SDMReadCtr mirroring |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 66 / 97**  
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Name  | Length  | Value  | Description |
| :---- | :---- | ----- | ----- |
| PICCDataOffset | \[3\]  | \-  | \[Optional, present if SDMMetaRead access right \=0h..4h\]  Mirror position (LSB first) for encrypted PICCData |
|  |  | 0h .. (FileSize \-  PICCDataLength) | Offset within the file |
| SDMMACInputOffset | \[3\]  | \-  | \[Optional, present if SDMFileRead access right \!= Fh\]  Offset in the file where the SDM MAC computation starts (LSB first) |
|  |  | 0h .. (SDMMACOffset)  | Offset within the file |
| SDMENCOffset | \[3\]  | \-  | \[Optional, present if ((SDMFileRead access right \!= Fh) AND  (SDMOptions\[Bit 4\] \= 1b))\]  SDMENCFileData mirror position (LSB first) |
|  |  | SDMMACInputOffset .. (SDMMACOffset \- 32\) | Offset within the file |
| SDMENCLength | \[3\]  | \-  | \[Optional, present if ((SDMFileRead access right \!= Fh) AND  (SDMOptions\[Bit 4\] \= 1b))\]  Length of the SDMENCFileData (LSB first) |
|  |  | 32 .. (SDMMACOffset \- SDMENCOffset) | Offset within the file, must be multiple of 32 |
| SDMMACOffset | \[3\]  | \-  | \[Optional, present if SDMFileRead access right \!= Fh\]  SDMMAC mirror position (LSB first) |
|  |  | SDMMACInputOffset .. (FileSize \- 16\) | \[if (SDMFileRead access right \!= Fh) AND (SDMOptions\[Bit 4\] \= 0b)\] Offset within the file |
|  |  | (SDMENCOffset \+  SDMENCLength) .. (FileSize- 16\) | \[if (SDMFileRead access right \!= Fh) AND (SDMOptions\[Bit 4\] \= 1b)\] Offset within the file |
| SDMReadCtrLimit  | \[3\]  | Full range  | \[Optional, present if  SDMOptions\[Bit 5\] \= 1b\]  SDMReadCtrLimit value (LSB first) |

**Table 70.  Response data parameters description \- ChangeFileSettings**

![Table 70](images/nxp-datasheet/table_70_page_067.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| Response  data | 0  | \-  | No response data |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 71 |

![Table 71](images/nxp-datasheet/table_71_page_067.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 67 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**Table 71.  Return code description \- ChangeFileSettings**

![Table 71](images/nxp-datasheet/table_71_page_067.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| INTEGRITY\_ERROR  | 1Eh  | Integrity error in cryptogram. Invalid Secure Messaging MAC (only). |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| PARAMETER\_ERROR  | 9Eh | Parameter value not allowed. |
|  |  | Targeted key for one of the access conditions in AccessRights or SDMAccessRights does not exist. |
|  |  | Trying to set access right SDMMetaRead to a value different than Fh, while both UID and SDMReadCtr mirroring are disabled. |
|  |  | Trying to set access right SDMMetaRead to Fh, while enabling UID mirroring. |
|  |  | Trying to set access right SDMCtrRet to a value different from Fh, while SDMReadCtr is disabled. |
|  |  | SDMMAC and UID mirroring are overlapping, i.e. the following condition is not satisfied: (SDMMACOffset ≥ UIDOffset \+ UIDLength) OR (UIDOffset ≥ SDMMACOffset \+ SDMMACLength) |
|  |  | SDMMAC and SDMReadCtr mirroring are  overlapping, i.e. the following condition is not satisfied: (SDMMACOffset ≥ SDMReadCtrOffset \+ SDMReadCtrLength) OR (SDMReadCtrOffset ≥ SDMMACOffset \+ SDMMACLength) |
|  |  | SDMMAC and PICCData mirroring are  overlapping, i.e. the following condition is not satisfied: (SDMMACOffset ≥ PICCDataOffset \+ PICCDataLength) OR (PICCDataOffset ≥ SDMMACOffset \+ SDMMACLength) |
|  |  | SDMENCFileData and UID mirroring are overlapping, i.e. the following condition is not satisfied:  (SDMENCOffset ≥ UIDOffset \+ UIDLength) OR (UIDOffset ≥ SDMENCOffset \+ SDMENCLength) |
|  |  | SDMENCFileData and SDMReadCtr mirroring are overlapping, i.e. the following condition is not satisfied: (SDMENCOffset ≥ SDMReadCtrOffset \+ SDMReadCtrLength) OR (SDMReadCtrOffset ≥ SDMENCOffset \+ SDMENCLength) |
|  |  | SDMENCFileData and PICCData mirroring are overlapping, i.e. the following condition is not satisfied: (SDMENCOffset ≥ PICCDataOffset \+ PICCDataLength) OR (PICCDataOffset ≥ SDMENCOffset \+ SDMENCLength) |
|  |  | UID and SDMReadCtr mirroring are overlapping, i.e. the following condition is not satisfied: (UIDOffset ≥ SDMReadCtrOffset \+ SDMReadCtrLength) OR (SDMReadCtrOffset ≥ UIDOffset \+ UIDLength) |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 68 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Status  | Value  | Description |
| :---- | :---- | ----- |
|  |  | Enabling Secure Dynamic Messaging encryption (SDMOptions\[Bit 4\] set to 1b) is not possible if access right SDMFileRead \= Fh. |
|  |  | Enabling Secure Dynamic Messaging encryption (SDMOptions\[Bit 4\] set to 1b) is not allowed if not both SDMReadCtr and UID are mirrored (i.e. SDMOptions\[Bit 7\] and SDMOptions\[Bit 6\] must be set to 1b) |
|  |  | Trying to set a SDMReadCtrLimit while not enabling SDMReadCtr. |
|  |  | Trying to set a SDMReadCtrLimit which is smaller or equal to the current SDMReadCtr. |
| PERMISSION\_DENIED  | 9Dh | PICC level (MF) is selected. |
|  |  | access right Change of targeted file has access conditions set to Fh. |
|  |  | Enabling Secure Dynamic Messaging (FileOption Bit 6 set to 1b) is only allowed for FileNo 02h. |
| FILE\_NOT\_FOUND  | F0h  | File with targeted FileNo does not exist for the targeted application. |
| AUTHENTICATION\_ERROR  | AEh  | File access right Change of targeted file not granted as there is no active authentication with the required key while the access conditions is different from Fh. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

**10.7.2 GetFileSettings** 

The GetFileSettings command allows getting information on the properties of a specific file. The information provided by this command depends on the type of the file which is queried. 

| 1 1 1 1 1 1 1 CLA  CMD  P1  P2  Lc  Data  Le  PCD to PICC  90  F5  00  00  01  FileNo  00  1 1  Response data  PICC to PCDSW1statusSW2  FileType FileOption AccessRights FileSize \[SDMOptions SMDAccessRights UIDOffset SDMReadCtrOffset  PICCDataOffset SDMMACInputOffset SDMENCOffset SDMENCLength SDMMACOffset SDMReadCtrlLimit\]  *aaa-032579*  Figure 23.  GetFileSettings command protocol |

![Figure 23](images/nxp-datasheet/figureigure_23_page_069.svg)

![Figure 2](images/nxp-datasheet/figureigure_2_page_007.svg)
| ----- |

**Table 72. Command parameters description \- GetFileSettings**

![Table 72](images/nxp-datasheet/table_72_page_069.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| Cmd  | 1  | F5h  | Command code. |
| FileNo | 1  | \-  | File number of the targeted file. |
|  | Bit 7-5  |  | RFU |
|  | Bit 4-0  |  | File number |
| **Command Data Parameters** |  |  |  |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 69 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| \-  | \-  | \-  | No data parameters |

**Table 73.  Response data parameters description \- GetFileSettings**

![Table 73](images/nxp-datasheet/table_73_page_070.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | ----- | :---- |
| FileType  | 1 | \-  | File Type of the targeted file. |
|  |  | 00h  | StandardData File |
|  |  | Other values  | RFU |
| FileOption | 1  | \-  | Options for the targeted file. |
|  | Bit 7  |  | RFU |
|  | Bit 6 | \-  | Secure Dynamic Messaging and Mirroring |
|  |  | 0b  | disabled |
|  |  | 1b  | enabled |
|  | Bit 5-2  | 0000b  | RFU |
|  | Bit 1-0  |  | CommMode (see Table  CommunicationModes) |
| AccessRights  | 2  | \-  | Set of access conditions for the 1st set in the file (see Section 8.2.3.3). |
| FileSize  | 3  | \-  | File size of the targeted file. |
| SDMOptions  | \[1\]  | \-  | \[Optional, present if FileOption\[Bit 6\] set\] SDM Options, see Table 69 |

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)
| SDMAccessRights  | \[2\]  | \-  | \[Optional, present if FileOption\[Bit 6\] set\] SDM Access Rights, see Table 69 |

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)
| UIDOffset  | \[3\]  | \-  | \[Optional, present if ((SDMOptions\[Bit 7\] \= 1b) AND (SDMMetaRead access right \= Eh)\]  Mirror position (LSB first) for UID, see Table 69 |

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)
| SDMReadCtrOffset  | \[3\]  | \-  | \[Optional, present if ((SDMOptions\[Bit 6\] \= 1b) AND (SDMMetaRead access right \= Eh)\]  Mirror position (LSB first) for  SDMReadCtr, see Table 69 |

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)
| PICCDataOffset  | \[3\]  | \-  | \[Optional, present if SDMMetaRead access right \=0h..4h\]  Mirror position (LSB first) for encrypted PICCData, see Table 69 |

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)
| SDMMACInputOffset  | \[3\]  | \-  | \[Optional, present if SDMFileRead access right \!= Fh\]  Offset in the file where the SDM MAC computation starts (LSB first), see Table 69 |

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 70 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| SDMENCOffset  | \[3\]  | \-  | \[Optional, present if ((SDMFileRead access right \!= Fh) AND  (SDMOptions\[Bit 4\] \= 1b))\]  SDMENCFileData mirror position (LSB first), see Table 69 |

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)
| SDMENCLength  | \[3\]  | \-  | \[Optional, present if ((SDMFileRead access right \!= Fh) AND  (SDMOptions\[Bit 4\] \= 1b))\]  Length of the SDMENCFileData (LSB first), see Table 69 |

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)
| SDMMACOffset  | \[3\]  | \-  | \[Optional, present if SDMFileRead access right \!= Fh\]  SDMMAC mirror position (LSB first), see Table 69 |

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)
| SDMReadCtrLimit  | \[3\]  | \-  | \[Optional, present if SDMOptions\[Bit 5\] \= 1b\]  SDMReadCtrLimit value (LSB first), see Table 69 |

![Table 69](images/nxp-datasheet/table_69_page_065.svg)

![Table 6](images/nxp-datasheet/table_6_page_011.svg)
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 74 |

![Table 74](images/nxp-datasheet/table_74_page_071.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

**Table 74.  Return code description \- GetFileSettings** 

![Table 74](images/nxp-datasheet/table_74_page_071.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| INTEGRITY\_ERROR  | 1Eh  | Invalid secure messaging MAC (only). |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed. |
| PERMISSION\_DENIED  | 9Dh  | PICC level (MF) is selected. |
| FILE\_NOT\_FOUND  | F0h  | File with targeted FileNo does not exist for the targeted application. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

**10.7.3 GetFileCounters** 

The GetFileCounters command supports retrieving of the current values associated 

with the SDMReadCtr related with a StandardData file after enabling Secure Dynamic Messaging, see Section 9.3 and Section 10.7.1.

| 1 1 1 1 1 1  1  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  FileNr  90  F6  00  00  xx  00  8  1  1  status  Response data  PICC to PCD  SDMReadCtr Reserved  SW1  SW2  *aaa-032471*  Figure 24.  GetFileCounters command protocol |

![Figure 24](images/nxp-datasheet/figureigure_24_page_071.svg)

![Figure 2](images/nxp-datasheet/figureigure_2_page_007.svg)
| ----- |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 71 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**Table 75.  Command parameters description \- GetFileCounters** 

![Table 75](images/nxp-datasheet/table_75_page_072.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| Cmd  | 1  | F6h  | Command code. |
| FileNo  | 1  | \-  | File number of the targeted file. |
|  | Bit 7-5  | 000b  | RFU |
|  | Bit 4-0  | Limited range  | File number |
| **Command Data Parameters** |  |  |  |
| \-  | \-  | \-  | No data parameters |

**Table 76.  Response data parameters description \- GetFileCounters** 

![Table 76](images/nxp-datasheet/table_76_page_072.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| SDMReadCtr  | 3  | Full Range  | Current SDMReadCtr of the targeted file (LSB first). |
| Reserved  | 2  | 0000h  | RFU |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 77 |

![Table 77](images/nxp-datasheet/table_77_page_072.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

**Table 77.  Return code description \- GetFileCounters**

![Table 77](images/nxp-datasheet/table_77_page_072.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing |
| INTEGRITY\_ERROR  | 1Eh  | Invalid secure messaging MAC |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed |
| PERMISSION\_DENIED  | 9Dh | PICC level (MF) is selected. |
|  |  | Targeted file has no Secure Dynamic Messaging enabled. |
|  |  | Targeted file has SDMCtrRet access right set to Fh. |
| FILE\_NOT\_FOUND  | F0h  | Targeted file does not exist in the targeted application |
| AUTHENTICATION\_ERROR  | AEh  | SDMCtrRet access right not granted while different from Fh. |
| FILE\_NOT\_FOUND  | F0h  | File with targeted FileNo does not exist for the targeted application. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 72 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.8 Data management commands** 

The NT4H2421Gx provides the following command set for Data Management functions. 

**10.8.1 ReadData** 

The ReadData command allows reading data from StandardData Files. The Read 

command requires a preceding authentication either with the key specified for Read 

or ReadWrite access, see the access rights section Section 8.2.3.3. Depending 

on the communication mode settings of the file secure messaging is applied, see 

Section 8.2.3.5. 

| 1 1 1 1 1  1  1 3  3  CLA  CMD  P1  P2  Lc  Le  FileNo  Offset Length  PCD to PICC  90  AD  00  00  07  00  up to 256  1  1  status  Response data  PICC to PCD  \-  SW1  SW2  *aaa-032211*  Figure 25.  ReadData command protocol |

![Figure 25](images/nxp-datasheet/figureigure_25_page_073.svg)

![Figure 2](images/nxp-datasheet/figureigure_2_page_007.svg)
| ----- |

**Table 78.  Command parameters description \- ReadData**

![Table 78](images/nxp-datasheet/table_78_page_073.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| Cmd  | 1  | ADh  | Command code. |
| FileNo | 1  | \-  | File number of the targeted file. |
|  | Bit 7-5  | 000b  | RFU |
|  | Bit 4-0 |  | File number |
|  |  | Full Range |  |
| Offset  | 3  | 000000h ..  (FileSize \- 1\) | Starting position for the read operation. |
| Length  | 3 | \-  | Number of bytes to be read. |
|  |  | 000000h  | Read the entire StandardData file, starting from the position specified in the offset value. Note that the short length Le limits response data to 256 byte including secure messaging (if applicable). |
|  |  | 000001h ..  (FileSize \-  Offset) |  |
| **Command Data Parameters** |  |  |  |
| \-  | \-  | \-  | No data parameters |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 73 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**Table 79.  Response data parameters description \- ReadData** 

![Table 79](images/nxp-datasheet/table_79_page_074.svg)

![Table 7](images/nxp-datasheet/table_7_page_011.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| Response  data | up to 256  byte including secure  messaging | Full Range  | Data read from the file |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 80 |

![Table 80](images/nxp-datasheet/table_80_page_074.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

**Table 80.  Return code description \- ReadData**

![Table 80](images/nxp-datasheet/table_80_page_074.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing |
| INTEGRITY\_ERROR  | 1Eh  | Invalid secure messaging MAC (only) |
|  |  | SMDRdCtr overflow |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed |
| PERMISSION\_DENIED  | 9Dh | PICC level (MF) is selected. |
|  |  | Read, ReadWrite and SDMFileRead (if SDM is enabled) access right of targeted StandardData file only have access conditions set to Fh. |
|  |  | Targeted file cannot be read in not authenticated state as the related SDMReadCtr is equal or bigger than its SDMReadCtrLimit. |
| FILE\_NOT\_FOUND  | F0h  | Targeted file does not exist in the targeted application |
| AUTHENTICATION\_ERROR  | AEh  | Read, ReadWrite and SDMFileRead (if SDM enabled) access right of targeted file not granted while at least one of the access conditions is different from Fh. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 74 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.8.2 WriteData** 

The WriteData command allows writing data to StandardData Files. NT4H2421Gx 

supports tearing protection for data that is sent within one communication frame to the file. Consequently, when using ISO/IEC 14443-4 chaining to write to a StandardData file, each frame itself is tearing protected but an interrupted chaining can lead to inconsistent files. Using single-frame WriteData commands instead of using the chaining can enable better control of the overall write process. 

Depending on the communication mode settings of the Data file, data needs to be sent with either CommMode.Plain, CommMode.MAC or CommMode.Full. All cryptographic operations are done in CBC mode. In case of CommMode.MAC or CommMode.Full, the validity of data is verified by the PICC by checking the MAC. If the verification fails, the PICC stops further user memory programming and returns an Integrity Error to the PCD. As a consequence of the Integrity Error, any transaction, which might have begun, is automatically aborted. This can lead to the same situation as described above for an interrupted WriteData using chained communication. 

| 1 1 1 1 1  1  1 3  3  up to 248  CLA  CMD  P1  P2  Lc  Le  FileNo  Offset Length  Data  PCD to PICC  90  8D  00  00  XX  00  0  1  1  status  Response data  PICC to PCD  \-  SW1  SW2  *aaa-032212*  Figure 26. WriteData command protocol |

![Figure 26](images/nxp-datasheet/figureigure_26_page_075.svg)

![Figure 2](images/nxp-datasheet/figureigure_2_page_007.svg)
| ----- |

**Table 81.  Command parameters description \- WriteData**

![Table 81](images/nxp-datasheet/table_81_page_075.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| **Command Header Parameters** |  |  |  |
| Cmd  | 1  | 8Dh  | Command code. |
| FileNo | 1  | \-  | File number of the targeted file. |
|  | Bit 7-5  | 000b  | RFU |
|  | Bit 4-0 |  | File number |
|  |  | Full range |  |
| Offset  | 3  | 000000h ..  (FileSize \- 1\) | Starting position for the write operation. |
| Length  | 3  | 000001h ..  (FileSize \-  Offset) | Number of bytes to be written. |
| **Command Data Parameters** |  |  |  |
| Data  | up to 248  byte including secure  messaging | Full range  | Data to be written. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 75 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**Table 82.  Response data parameters description \- WriteData** 

![Table 82](images/nxp-datasheet/table_82_page_076.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| No response data parameters defined for this command |  |  |  |
| Response  data | 0  | \-  | No response data |
| SW1SW2  | 2  | 9100h  91XXh | successful execution  Refer to Table 83 |

![Table 83](images/nxp-datasheet/table_83_page_076.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

**Table 83.  Return code description \- WriteData**

![Table 83](images/nxp-datasheet/table_83_page_076.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

| Status  | Value  | Description |
| :---- | :---- | ----- |
| COMMAND\_ABORTED  | CAh  | Chained command or multiple pass command ongoing. |
| INTEGRITY\_ERROR  | 1Eh  | Invalid secure messaging MAC or encryption padding. |
| LENGTH\_ERROR  | 7Eh  | Command size not allowed. |
| PARAMETER\_ERROR  | 9Eh  | Parameter value not allowed. |
| PERMISSION\_DENIED  | 9Dh | PICC level (MF) is selected. |
|  |  | Write and ReadWrite of targeted file only have access conditions set to Fh. |
|  |  | Targeting a StandardData file with a chained command in MAC or Full while this is not allowed. |
| FILE\_NOT\_FOUND  | F0h  | Targeted file does not exist in the targeted application. |
| AUTHENTICATION\_ERROR  | AEh  | Write and ReadWrite of targeted file not granted while at least one of the access conditions is different from Fh. |
| BOUNDARY\_ERROR  | BEh  | Attempt to write beyond the file boundary as set during creation. |
| MEMORY\_ERROR  | EEh  | Failure when reading or writing to non-volatile memory. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 76 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.9 Inter-industry standard commands** 

NT4H2421Gx provides the following ISO/IEC 7816-4 wrapped commands. 

**10.9.1 ISOSelectFile** 

This command is implemented in compliance with ISO/IEC 7816-4. It selects either the PICC level, an application or a file within the application. 

If P1 is set to 00h, 01h or 02h, selection is done by a 2-byte ISO file identifier. For PICC level / MF selection, 3F00h or empty data has to be used. For Deticated application 

File (DF) and Elementary File (EF) selection, data holds the 2-byte ISO/IEC 7816-4 file identifier. 

If P1 is set to 04h, selection is done by Deticated File (DF) name which can be up to 16 bytes. The registered ISO DF name is D2760000850100h. When selecting this DF name, the PICC level (or MF) is selected. For selecting the application immediately, the ISO/IEC 7816-4 DF name D2760000850101h can be used. 

P2 indicates whether or not File Control Information (FCI) is to be returned in case of application selection. NT4H2421Gx does not support FCI and thus never returns any data, but does support both selection options to achieve broadest compatibility. The 

number of bytes requested by Le up to the complete file data will be returned in plain. There is no specific FCI template format checked, i.e. the data stored in the file will be sent back as is. In case of PICC level or file selection, FCI data is never returned. For NT4H2421Gx, no FCI will be returned as the pre-installed application does not contain 

such a file. 

| 1 1 1 1 \[1\] \[1..16\]  \[1\]  Data  CLA  CMD  P1  P2  Lc  Le  PCD to PICC  \-  00  A4  04  00  XX  00  1  1  status  PICC to PCD  SW1  SW2  *aaa-032226*  Figure 27. ISOSelectFile command protocol |

![Figure 27](images/nxp-datasheet/figureigure_27_page_077.svg)

![Figure 2](images/nxp-datasheet/figureigure_2_page_007.svg)
| ----- |

**Table 84.  Command parameters description \- ISOSelectFile**

![Table 84](images/nxp-datasheet/table_84_page_077.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | ----- |
| CLA  | 1  | 00h |  |
| INS  | 1  | A4h |  |
| P1  | 1 | \-  | Selection Control |
|  |  | 00h  | Select MF, DF or EF, by file identifier |
|  |  | 01h  | Select child DF |
|  |  | 02h  | Select EF under the current DF, by file identifier |
|  |  | 03h  | Select parent DF of the current DF |
|  |  | 04h  | Select by DF name, see \[3\] |
| P2  | 1 | \-  | Option |
|  |  | 00h  | Return FCI template: data stored in the file with ID 1Fh should be returned |
|  |  | 0Ch  | No response data: no FCI should be returned |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 77 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| Lc  | \[1\]  | 00h .. 10h  | Length of subsequent data field |
| Data  | \[1..16\] | \-  | Reference |
|  |  | Empty  | \[if P1 \== 00h OR P1 \== 03h\]  Select MF |
|  |  | Full range  | \[if P1 \== 00h OR P1 \== 01h OR P1== 02h\] Select with the given file identifier |
|  |  | Full range  | \[if P1 \== 04h\]  Select DF with the given DF name |
| Le  | \[1\]  | Full range  | Empty or length of expected response |

**Table 85.  Response data parameters description \- ISOSelectFile** 

![Table 85](images/nxp-datasheet/table_85_page_078.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| SW1SW2  | 2  | 9000h  XXXXh | successful execution  Refer to Table 86 |

![Table 86](images/nxp-datasheet/table_86_page_078.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

**Table 86.  Return code description \- ISOSelectFile**

![Table 86](images/nxp-datasheet/table_86_page_078.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

| SW1|SW2  | Value  | Description |
| :---- | :---- | ----- |
| ISO6700  | 6700h  | Wrong or inconsistent APDU length. |
| ISO6985  | 6985h  | Wrapped chained command or multiple pass command ongoing. |
| ISO6A82  | 6A82h  | Application or file not found, currently selected application remains selected. |
| ISO6A86  | 6A86h  | Wrong parameter P1 and/or P2 |
| ISO6A87  | 6A87h  | Wrong parameter Lc inconsistent with P1-P2 |
| ISO6E00  | 6E00h  | Wrong CLA |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 78 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**10.9.2 ISOReadBinary** 

The ISOReadBinary is a standard ISO/IEC 7816-4 command. It can be used to read data from the Standard Data File. This command does not support any secure messaging, it is always in plain. For executing ISOReadBinary command either "Read" or "Read\&Write", access right must be set to free access rights. 

| 1 1 1 1 1  1  Data  CLA  CMD  P1  P2  Le  Le  PCD to PICC  \-  00  B0  XX  XX  \-  00  up to 256  1  1  status  Response data  PICC to PCD  \-  SW1  SW2  *aaa-032227*  Figure 28. ISOReadBinary command protocol |

![Figure 28](images/nxp-datasheet/figureigure_28_page_079.svg)

![Figure 2](images/nxp-datasheet/figureigure_2_page_007.svg)
| ----- |

**Table 87.  Command parameters description \- ISOReadBinary**

![Table 87](images/nxp-datasheet/table_87_page_079.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| CLA  | 1  | 00h |  |
| INS  | 1  | B0h |  |
| P1 | 1  |  | ShortFile ID/Offset |
|  | Bit 7 |  | Encoding |
|  |  | 1b  | P1\[Bit 6..5\] are RFU.  P1\[Bit 4..0\] encode a short ISO FileID. P2\[Bit 7..0\] encode an offset from zero to 255\. |
|  |  | 0b  | P1 \- P2 (15 bits) encode an offset from zero to 32767\. |
|  | Bit 6-5  | 00b  | \[if P1\[7\] \== 1b\] RFU |
|  | Bit 4-0 |  | \[if P1\[7\] \== 1b\] short ISO FileID |
|  |  | 00h  | Targeting currently selected file. |
|  |  | 01h .. 1Eh  | Targeting and selecting file referenced by the given short ISO FileID. |
|  |  | 1Fh  | RFU |
|  | Bit 6-0  | (see P2)  | \[if P1\[7\] \== 0b\] Most significant bits of Offset |
| P2  | 1  | 000000h ..  (FileSize \- 1\) | Offset (see above) |
| Le  | 1 | \-  | The number of bytes to be read from the file. The length of a secure messaging MAC (depending on communication mode settings) should be included in this value. |
|  |  | 00h  | Read the entire StandardData file, starting from the position specified in the offset value. Note that the short length Le limits response data to 256 byte. |
|  |  | 01h .. FFh  | If bigger than (FileSize \- Offset), after  subtracting MAC length if MAC is to be returned, the entire StandardData file starting from the offset position is returned. |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 79 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
|  |  | Full range |  |

**Table 88. Response data parameters description \- ISOReadBinary** 

![Table 88](images/nxp-datasheet/table_88_page_080.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

| Name  | Length  | Value  | Description |
| :---- | :---- | :---- | :---- |
| Data  | up to 256  | \-  | Data read. |
| SW1SW2  | 2  | 9000h  XXXXh | successful execution  Refer to Table 89 |

![Table 89](images/nxp-datasheet/table_89_page_080.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

**Table 89.  Return code description \- ISOReadBinary**

![Table 89](images/nxp-datasheet/table_89_page_080.svg)

![Table 8](images/nxp-datasheet/table_8_page_012.svg)

| SW1|SW2  | Value  | Description |
| :---- | :---- | :---- |
| ISO6581  | 6581h  | Memory failure |
| ISO6700  | 6700h  | Wrong or inconsistent APDU length. |
| ISO6982  | 6982h | Security status not satisfied: no access allowed as Read and ReadWrite access rights are different from Eh and SDMFileRead (if SDM enabled) access right is set to Fh. |
|  |  | Security status not satisfied: SDMReadCtr overflow. |
|  |  | Security status not satisfied: Targeted file cannot be read in not authenticated state as the related SDMReadCtr is equal or bigger than its SDMReadCtrLimit. |
|  |  | Security status not satisfied: AuthenticatedEV2 not allowed. |
|  |  | Security status not satisfied: AuthenticatedLRP not allowed. |
| ISO6985  | 6985h  | Wrapped chained command or multiple pass command ongoing. No file selected.  Targeted file is not of StandardData.  Application of targeted file holds a TransactionMAC file. |
| ISO6A82  | 6A82h  | File not found |
| ISO6A86  | 6A86h  | Wrong parameter P1 and/or P2 |
| ISO6E00  | 6E00h  | Wrong CLA |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 80 / 97** 