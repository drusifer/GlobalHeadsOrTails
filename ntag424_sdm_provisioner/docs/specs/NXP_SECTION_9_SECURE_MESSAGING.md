# NXP NT4H2421Gx NTAG 424 DNA - Section 9: Secure Messaging

**Source:** NT4H2421Gx Datasheet Rev. 3.0, 31 January 2019
**Copyright:** NXP B.V. 2019 - Extracted for technical reference

---

**9 Secure Messaging** 

Prior to data transmission a mutual three-pass authentication can be done between PICC and PCD which results in the generation of session keys used in the secure messaging. 

There are three secure messaging types available in the NT4H2421Gx including Secure Dynamic Messaging. One is using AES-128 and is referred to as AES mode in this data sheet. The other one is using AES-128 with a Leakage Resilient Primitive (LRP) wrapper, also referred to as LRP mode. The LRP mode can be permanently enabled using the SetConfiguration command. After this switch, it is not possible to revert back to AES 

mode. 

Compared to AES mode, the LRP mode has the advantage that it provides strong 

resistance against side-channel and fault attacks. It serves as a replacement for 

AES as it only uses standard cryptographic constructions based on AES without any proprietary cryptography. Thus, LRP can be seen as an alternative for AES which is 

itself based on AES, and is provably as secure as AES, but comes with better properties w.r.t. implementation security, see also \[10\]. The PCD requires the same LRP mode implementation. 

To improve the resistance against side-channel attacks and especially card only attacks for the AES mode, NT4H2421Gx provides a limit for unsuccessful authentication 

attempts. Every unsuccessful authentication is counted in the TotFailCtr. The parameters TotFailCtrLimit TotFailCtrDecr can be configured as described in Section 10.5.1 using the "Failed authentication counter configuration". 

Each unsuccessful authentication is counted internally in the total failed authentication counter TotFailCtr. After reaching the TotFailCtrLimit, see Section 10.5.1, the related key cannot be used for authentication anymore. 

In addition, after reaching a limit of *consecutive* unsuccessful authentication 

attempts, the NT4H2421Gx starts to slow down the authentication processing in 

order to hamper attacks. This is done by rejecting any authentication command 

with a AUTHENTICATION\_DELAY response. The response time of a single 

AUTHENTICATION\_DELAY response is depending on the FWT, see Section 8.1.1, and is about 65% of the maximum response time specified by FWT. The error response is sent until the total authentication delay time is reached which is equal to the sum of the frame delay times. The total authentication delay time increases with each unsuccessful authentication attempt up to a maximum value, only a successful authentication restores the full operational speed. 

Changing a blocked AES key by authenticating with the AppMasterKey and using the ChangeKey command makes the referenced key accessible again. If the AppMasterKey itself is blocked, no recovery is possible. 

Each successful AES authentication decrements the TotFailCtr by a value of 

TotFailCtrDecr. 

The AES and LRP authentications are initiated by commands sharing the same 

command code (First Authentication and Non-First Authentication variants). These 

authentication protocols are both AES-based, but differ with regards to the actual 

protocol applied and the subsequent secure messaging mode they initiate. An overview of the different modes is given in Figure 5.

![Figure 5](images/nxp-datasheet/figureigure_5_page_020.svg)

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 20 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Secure Messaging  Setup  Authentication  Type  71h  71h  AuthenticateEV2First  AuthenticateLRPFirst  (KeyNo) with  (KeyNo) with  PCDCap2.1 \= 0x00  PCDCap2.1 \= 0x02  AES  AES  (128 bit key)  (128 bit key)  Secure messaging using  Secure messaging using  standard AES construction  LRP AES construction  see section on  see section on  EV2 Secure Messaging  LRP Secure Messaging  *aaa-032190*  Figure 5.  NTAG 424 DNA secure messaging setup |

![Figure 5](images/nxp-datasheet/figureigure_5_page_020.svg)
| ----- |

A First Authentication can be executed at any time whether the PICC is in authenticated or not authenticated state. 

The Non-First Authentication can only be executed while the card is in authenticated state after a successful First or Non-First Authentication. 

Correct application of First Authentication and Non-First Authentication allows to cryptographically bind all messages within a transaction together by the transaction identifier established in a First Authentication, see Section 9.1.1, and a command counter, see Section 9.1.2, even if multiple authentications are required. 

The following table specifies when to authenticate using First Authentication and when to use Non-First Authentication. 

**Table 18. When to use which authentication command** 

![Table 18](images/nxp-datasheet/table_18_page_021.svg)

![Table 1](images/nxp-datasheet/table_1_page_004.svg)

| Purpose First Authentication Non-First Authentication |
| ----- |
| First authentication (i.e. when not in any  Allowed Not Allowed authenticated state) with any key different  from OriginalityKey  |
| Subsequent authentication (i.e. when  Allowed, recommended  Allowed, recommended  in any authenticated state) with any key  not to use.  to use. different from OriginalityKey  |
| Any LRP authentication with OriginalityKey Allowed Allowed |

The AuthenticateEV2First initiates a standard AES authentication and secure messaging, see Section 9.1. The other variant AuthenticateLRPFirst initiates an AES authentication and secure messaging based on the Leakage Resilient Primitive (LRP), see Section 9.2. 

The negotiation between those two variants is done using the capabilities of the First Authentication and the return message of the first part, where a PCD can distinguish between standard AES authentication and LRP authentication based on the message length.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 21 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

On First Authentication, the PCD can choose between AES and LRP secure messaging by setting bit 1 of PCDCap2.1 in the issued command. The PD is configured for either AES or LRP secure messaging by the setting of bit 1 from PDCap2.1. This setting is 

defined with SetConfiguration, see Section 10.5.1. 

If the PCD chooses for AES secure messaging, it sends PCDCap2.1 equaling 00h (or no PCDCap2 at all). A NT4H2421Gx will accept the authentication if its PDCap2.1 bit 1 is not set, i.e. the NT4H2421Gx is configured for AES secure messaging. The command is interpreted as AuthenticateEV2First, see Section 9.1.5 for detailed specification. If 

PDCap2.1 bit 1 is set, i.e. the NT4H2421Gx is configured for LRP secure messaging, the authentication request is rejected. 

If the PCD chooses for LRP secure messaging, it sends PCDCap2.1 equaling 02h. 

NTAG 424 DNA will accept the authentication if its PDCap2.1 bit 1 is set, i.e. the 

NT4H2421Gx is configured for LRP secure messaging. The command is interpreted as AuthenticateLRPFirst and replied with 18 bytes, i.e. ADDITIONAL\_FRAME, followed by an additional AuthMode indicating LRP secure messaging, and 16 bytes of data, 

see Section 10.4.3 for detailed specification. If PDCap2.1 bit 1 is not set, i.e. the 

NT4H2421Gx is configured for AES secure messaging, the authentication request is 

also accepted, but responded with 17 bytes, i.e. the AuthenticateEV2First response 

composed of ADDITIONAL\_FRAME, followed by 16 bytes of data, allowing the PCD to fall back to standard AES authentication as well. 

With Non-First Authentication, the PCD cannot choose between standard AES and 

LRP. If authenticated using AES mode, AuthenticateEV2NonFirst will be applied, see Section 9.1.6. If authenticated with LRP mode, AuthenticateLRPNonFirst will be applied, see Section 10.4.4. If not authenticated at all, e.g. if targeting one of the originality keys, only AuthenticateLRPNonFirst is supported. 

Below table provides possible negotiation outcomes on FirstAuthentication. 

**Table 19. Secure messaging mode negotiation**

![Table 19](images/nxp-datasheet/table_19_page_022.svg)

![Table 1](images/nxp-datasheet/table_1_page_004.svg)

| PCD PD |
| ----- |
| **Mode PCDCa  PDCap2.1  RC resp  resp  comment p2.1  (Mode)  PDCap2.1  PCDCap2.1**  |
| Requesting  00h  00h  ADDITIONAL\_  00h 00h Matching, AES SM  EV2  (AES)  FRAME: 17-byte  accepted and selected  Secure  response without  Messaging  AuthMode  02h  PERMISSION\_  N/A N/A No match, AES SM  (LRP)  DENIED  rejected |
| 00h  ADDITIONAL\_  00h 02h No match, PD replies  Requesting  02h  (AES)  FRAME  with AES response,  LRP  allowing a PCD to fall  Secure  back.  Messaging  02h  ADDITIONAL\_  02h 02h Matching, LRP SM  (LRP)  FRAME: 18-byte  accepted and selected response with  AuthMode set to  01h  |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 22 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**9.1 AES Secure Messaging** 

The AES Secure Messaging is managed by AuthenticateEV2First and 

AuthenticateEV2NonFirst. 

Note that AuthenticateEV2First and AuthenticateEV2NonFirst can also be used to start LRP Secure Messaging, as defined in Section 9.2. This is done with the PCDCap2 sent in First Authentication and the return code, see Section 9 and Section 9.2.5 for details. 

**9.1.1 Transaction Identifier** 

In order to avoid interleaving of transactions from multiple PCDs toward one PICC, the Transaction Identifier (TI) is included in each MAC that is calculated over commands or responses. The TI is generated by the PICC and communicated to the PCD with a successful execution of an AuthenticateEV2First command, see Section 10.4.1. The size is 4 bytes and these 4 bytes can hold any value. The TI is treated as a byte array, so there is no notion of MSB and LSB. 

**9.1.2 Command Counter** 

A command counter is included in the MAC calculation for commands and responses in order to prevent e.g. replay attacks. It is also used to construct the Initialization Vector (IV) for encryption and decryption. 

Each command, besides few exceptions, see below, is counted by the command counter CmdCtr which is a 16-bit unsigned integer. Both sides count commands, so the actual value of the CmdCtr is never transmitted. The CmdCtr is reset to 0000h at PCD and PICC after a successful AuthenticateEV2First authentication and it is maintained as long as the PICC remains authenticated. In cryptographic calculations, the CmdCtr is represented LSB first. Subsequent authentications using AuthenticateEV2NonFirst do not affect the CmdCtr. Subsequent authentications using the AuthenticateEV2First will reset the CmdCtr to 0000h. The CmdCtr is increased between the command and response, for all communication modes. 

When a MAC on a command is calculated at PCD side that includes the CmdCtr, it uses the current CmdCtr. The CmdCtr is afterwards incremented by 1\. At PICC side, a MAC appended at received commands is checked using the current value of CmdCtr. If the MAC matches, CmdCtr is incremented by 1 after successful reception of the command, and before sending a response. 

For CommMode.Full, the same holds for both the MAC and encryption IV calculation, i.e. the non-increased value is used for the command calculations while the increased value is used for the response calculations. 

If the CmdCtr holds the value FFFFh and a command maintaining the active authentication arrives at the PICC, this leads to an error response and the command is handled like the MAC was wrong. 

Command chaining, see Section 8.5, does not affect the counter. The chained command is considered as a single command, just as for the other aspects of secure messaging, and thus the related counter is increased only once. 

**9.1.3 MAC Calculation** 

MACs are calculated using the underlying block cipher according to the CMAC standard described in \[6\]. Padding is applied according to the standard.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 23 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

The MAC used in NT4H2421Gx is truncated by using only the 8 even-numbered bytes out of the 16 bytes output as described \[6\] when represented in most-to-least-significant order. 

**Initialization Vector for MACing** 

The initialization vector used for the CMAC computation is the zero byte IV as prescribed \[6\]. 

**9.1.4 Encryption** 

Encryption and decryption are calculated using AES-128 according to the CBC mode of NIST SP800-38A \[5\]. 

Padding is applied according to Padding Method 2 of ISO/IEC 9797-1 \[7\], i.e. by adding always 80h followed, if required, by zero bytes until a string with a length of a multiple of 16 byte is obtained. Note that if the plain data is a multiple of 16 bytes already, an additional padding block is added. The only exception is during the authentication itself (AuthenticateEV2First and AuthenticateEV2NonFirst), where no padding is applied at all. 

The notation *E(key, message)* is used to denote the encryption and *D(key, message)* for decryption. 

**Initialization Vector for Encryption** 

When encryption is applied to the data sent between the PCD and the PICC, the Initialization Vector (IV) is constructed by encrypting with SesAuthENCKey according to the ECB mode of NIST SP800-38A \[5\] the concatenation of: 

**•** a 2-byte label, distinguishing the purpose of the IV: A55Ah for commands and 5AA5h for responses 

**•** Transaction Identifier TI 

**•** Command Counter CmdCtr (LSB first) 

**•** Padding of zeros acc. to NIST SP800-38B \[6\] 

This results in the following IVs: 

IV for CmdData *\= E(SesAuthENCKey; A5h || 5Ah ||* TI *||* CmdCtr *|| 0000000000000000h)* IV for RespData *\= E(SesAuthENCKey;5Ah || A5h ||* TI *||* CmdCtr *|| 0000000000000000h)* 

When an encryption or decryption is calculated, the CmdCtr to be used in the IV are the current values. Note that this means that if CmdCtr *\= n* before the reception of a command, after the validation of the command CmdCtr *\= n \+ 1* and that value will be used in the IV for the encryption of the response. 

For the encryption during authentication (both AuthenticateEV2First and 

AuthenticateEV2NonFirst), the IV will be 128 bits of 0\. 

**9.1.5 AuthenticateEV2First Command** 

This section defines the Authentication, which is mandatory to be used first in a transaction when using Secure Messaging, see Table 18. In this procedure both, the PICC as well as the PCD show in an encrypted way that they possess the same secret, i.e. the same key. This authentication is supported with AES keys. 

![Table 18](images/nxp-datasheet/table_18_page_021.svg)

![Table 1](images/nxp-datasheet/table_1_page_004.svg)

The authentication consists of two parts: AuthenticateEV2First \- Part1 and Section 9.1.6 \- Part2. Detailed command definition can be found in Section 10.4.1. The protocol cannot

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 24 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

be interrupted by other commands. On any command different from AuthenticateEV2First \- Part2 received after the successful execution of the first part, the PICC aborts the ongoing authentication. 

During this authentication phase, the PICC accepts messages from the PCD that are longer than the lengths derived from this specification as long as LenCap is correct. This feature is to support the upgradability to following generations of NT4H2421Gx. The PCD rejects answers from the PICC when they don’t have the proper length. Note that if present, PCDcap2:1:Bit1 must not be set, otherwise LRP authentication is targeted, see Section 9.2.5. 

Upon reception of AuthenticateEV2First, the PICC validates the targeted key. If the key does not exist, AuthenticateEV2First is rejected. 

The PICC generates a random 16-byte challenge *RndB* and send this encrypted to the PCD, according to Section 9.1.4. Additionally, the PICC resets CmdCtr to zero and generate a random Transaction Identifier (TI). 

Upon reception of the AuthenticateEV2First response from the PICC, the PCD also generates a random 16-byte challenge *RndA*. The PCD encrypts, on his turn, the concatenation of *RndA* with *RndB'*, which is the received challenge after decryption and rotating it left by one byte. Within AuthenticateEV2First \- Part2, this is sent to the PICC. Upon reception of AuthenticateEV2First \- Part2, the PICC decrypts the second message and validates the received *RndB'*. If not as expected, the command is rejected. Else it generates *RndA'* by rotating left the received *RndA* by one byte. This is returned together with the generated TI. Also, the PICC sends 12 bytes of capabilities to the PCD: 6 bytes of PICC capabilities PDcap2 and 6 bytes of PCD capabilities PCDcap2 that were received on the command (sent back for verification). 

The use of those capabilities, and the negotiation process is described in Section 9. Note that part of PDCap will be configurable with SetConfiguration. PCDcap2 is used to refer both to the value sent from the PCD to the PICC and to the value used in the encrypted response message from the PICC to the PCD where in this case the PCDcap2 is the adjusted version of the originally sent PCDcap2: i.e. truncated or padded with zero bytes to a length of 6 bytes if needed. 

On successful execution of the authentication protocol, the session keys 

SesAuthMACKey and SesAuthENCKey are generated according to Section 9.1.7. The PICC is in EV2 authenticated state and the Secure Messaging is activated. On any failure during the protocol or if one of the OriginalityKey were targeted, the PICC ends up in not authenticated state. 

If there is a mismatch between the capabilities expected by the PCD and the capabilities presented by the PICC to the PCD (both the PDcap2 and the echoed/adjusted PCDcap2), it is the responsibility of the PCD to take the proper actions based on the application the PCD is running. This decision is outside the scope of this specification. 

**9.1.6 AuthenticateEV2NonFirst Command** 

This section defines the Non-First Authentication, which is recommended to be used if Secure Messaging is already active, see Table 18. In this procedure both, the PICC as well as the PCD show in an encrypted way that they possess the same secret, i.e. the same key. This authentication is supported with AES keys. 

![Table 18](images/nxp-datasheet/table_18_page_021.svg)

![Table 1](images/nxp-datasheet/table_1_page_004.svg)

The authentication consists of two parts: AuthenticateEV2NonFirst \- Part1 and AuthenticateEV2NonFirst \- Part2. Detailed command definition can be found in Section 10.4.2. This command is rejected if there is no active authentication, except if the

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 25 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

targeted key is the OriginalityKey. For the rest, the behavior is exactly the same as for AuthenticateEV2First, except for the following differences: 

**•** No *PCDcap2* and *PDcap2* are exchanged and validated. 

**•** Transaction Identifier TI is not reset and not exchanged. 

**•** Command Counter CmdCtr is not reset. 

After successful authentication, the PICC remains in EV2 authenticated state. On any failure during the protocol, the PICC ends up in not authenticated state. 

**9.1.7 Session Key Generation** 

At the end of a valid authentication with AuthenticateEV2First or 

AuthenticateEV2NonFirst, both the PICC and the PCD generate two session keys for secure messaging, as shown in Figure 6: 

![Figure 6](images/nxp-datasheet/figureigure_6_page_026.svg)

**•** SesAuthMACKey for MACing of messages 

**•** SesAuthENCKey for encryption and decryption of messages 

Note that these identifiers are also used in context of the LRP protocol, though the actual calculation of the session keys is different, see Section 9.2.7. 

| PCD PICC  AES Key Kx AES Key Kx  NTAG Authentication  RndA  RndB  RndA  RndB  KDF  KDF  Session Key for encryptionSesAuthMACKey \= AES  SesAuthENCKey \= AES  Session Key for encryptionSesAuthMACKey \= AES  SesAuthENCKey \= AES  Session Key for MAC  Session Key for MAC  *aaa-032481*  Figure 6.  Session key generation for Secure Messaging |

![Figure 6](images/nxp-datasheet/figureigure_6_page_026.svg)
| ----- |

The session key generation is according to NIST SP 800-108 \[8\] in counter mode. 

The Pseudo Random Function PRF(key; message) applied during the key generation is the CMAC algorithm described in NIST Special Publication 800-38B \[6\]. The key derivation key is the key Kx that was applied during authentication. As the authentications are restricted to target AES keys, the generated session keys are also of AES. 

The input data is constructed using the following fields as defined by \[8\]. Note that NIST SP 800-108 allows defining a different order than proposed by the standard as long as it is unambiguously defined.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 26 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**•** a 2-byte label, distinguishing the purpose of the key: 5AA5h for MACing and A55Ah for encryption 

**•** a 2-byte counter, fixed to 0001h as only 128-bit keys are generated. 

**•** a 2-byte length, fixed to 0080h as only 128-bit keys are generated. 

**•** a 26-byte context, constructed using the two random numbers exchanged, RndA and RndB 

First, the 32-byte input session vectors *SVx* are derived as follows: 

*SV1 \= A5h||5Ah||00h||01h||00h||80h||RndA\[15..14\]||* 

   *( RndA\[13..8\]* \# *RndB\[15..10\])||RndB\[9..0\]||RndA\[7..0\]* 

*SV2 \= 5Ah||A5h||00h||01h||00h||80h||RndA\[15..14\]||* 

   *( RndA\[13..8\] \# RndB\[15..10\])||RndB\[9..0\]||RndA\[7..0\]* 

with \# being the XOR-operator. 

Then, the 16-byte session keys are constructed as follows: 

*SesAuthENCKey \= PRF(Kx, SV1)*   
*SesAuthMACKey \= PRF(Kx, SV2)* 

**9.1.8 Plain Communication Mode** 

The command and response data is not secured. The data is sent in plain, see Figure 7, i.e. as defined in the command specification tables, see Section 10. 

![Figure 7](images/nxp-datasheet/figureigure_7_page_027.svg)

| C \= Value of CmdCtr at start of this sequence 1 1 1 1 1 \[a\] \[b\]  1  Command counter (CmdCtr)  ~~ISO 7816 Data Field~~PCD to PICC  incremented after validating the  CLA  P1  P2  Le  90h CMD CmdHeader  00h Lc  command before sending the  CmdData  00h  00h  response. CmdCtr is a 16-bit  unsigned integer.  \[c\]  1  1  status  RespData  ~~PICC to PCD~~  SW1  SW2  *aaa-032773*  Figure 7. Plain Communication Mode |

![Figure 7](images/nxp-datasheet/figureigure_7_page_027.svg)
| ----- |

However, note that, as the PICC is in authenticated state (EV2 authenticated state or LRP authenticated state), the command counter CmdCtr is still increased as defined in Section 9.1.2. 

This allows the PCD and PICC to detect any insertion and/or deletion of commands sent in CommMode.Plain on any subsequent command that is sent in CommMode.MAC (e.g. CommitTransaction) or CommMode.Full. 

**9.1.9 MAC Communication Mode** 

The Secure Messaging applies MAC to all commands listed as such in Section 10.2. 

In case MAC is to be applied, the following holds. The MAC is calculated using the current session key SesAuthMACKey. MAC calculation is done as defined in Section 9.1.3. 

For commands, the MAC is calculated over the following data (according to the definitions from Section 8.3) in this order: 

**•** Command, Cmd

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 27 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**•** Command Counter CmdCtr 

**•** Transaction Identifier TI 

**•** Command header \- CmdHeader (if present) 

**•** Command data \- CmdData (if present) 

For responses, the MAC is calculated over the following data in this order: 

**•** Return code \- RC 

**•** Command Counter \- CmdCtr (The already increased value) 

**•** Transaction Identifier \- TI 

**•** Response data \- RespData (if present) 

CmdCtr is the Command Counter as defined in Section 9.1.2. Note that the CmdCtr is increased between the computation of the MAC on the command and the MAC on the response. TI is the Transaction Identifier, as defined in Section 9.1.1. The other input parameters are as defined in Section 8.3. The calculation is illustrated in Figure 8. 

![Figure 8](images/nxp-datasheet/figureigure_8_page_028.svg)

In case of command chaining, the MAC calculation is not interrupted. The MAC is calculated over the data including the complete data field (i.e. either CmdData or RespData of all frames) at once. The MAC is always transmitted by appending to the unpadded plain command. If necessary, an additional frame is sent. If a MAC over the command is received, the PICC verifies the MAC and rejects commands that do not contain a valid MAC by returning INTEGRITY\_ERROR. 

In this case, the ongoing command and transaction are aborted (see also Section 10). The authentication state is immediately lost and the error return code is sent without a MAC appended. Note that any other error during the command execution has the same consequences. 

| C \= value of CmdCtr at start of this sequenceT \= Value of TI (will stay constant)  8  1 1 1 1  \[a\] \[b\] 1  Command counter (CmdCtr)  1MACt(SesAuthMACKey, CMD ||  ISO 7816 Data Field  incremented after validating the  CLA  90h Cmd P1  P2  Le  PCD to PICC  Lc  command before sending the  CmdHeader  CmdCtr || TI \[|| CmdHeader\] \[|| CmdData\])  CmdData  00h  00h  00h  response and related MAC calculation  MAC(SesAuthMACKey, CMD || CmdCtr || TI  MAC Truncation from 16 to 8 byte  \[|| CmdHeader\] \[|| CmdData\])  by use of the even-numbered bytes  1  2  4  \[a\] \[b\]  ISO 7816 Data Field  Cmd  CmdCtr  TI  CmdHeader  CmdData  C T  \[c\]  8  1  1  status  MACt(SesAuthMACKey, RC ||  PICC to PCD  RespData  CmdCtr || TI \[|| RespData\])  SW1  SW2  MAC(SesAuthMACKey, RC ||  CmdCtr || TI \[|| RespData\])  \[c\]  2  4  1  status  CmdCtr  TI  RespData  SW2  C+1 T  *aaa-032192*  CLA, P1, P2, LC, Le and SW1 not included in secure messaging calculation. SW2 is the return code (RC) and appended in the beginning for secure messaging calculation  Figure 8.  Secure Messaging: MAC Communication mode |

![Figure 8](images/nxp-datasheet/figureigure_8_page_028.svg)
| ----- |

**9.1.10 Full Communication Mode** 

The Secure Messaging applies encryption (CommMode.Full) to all commands listed as such in Section 10.2. In case CommMode.Full is to be applied, the following holds. The encryption/decryption is calculated using the current session key SesAuthENCKey. Calculation is done as defined in Section 9.1.4 over either the command or the response

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 28 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

data field (i.e. CmdData or RespData). Note that none of the commands have a data field in both the command and the response frame. 

After the encryption, the command and response frames are handled as with MAC. This means that additionally a MAC is calculated and appended for transmission using the current session key SesAuthMACKey. This is exactly done as specified for MAC in Section 9.1.9, replacing the plain CmdData or RespData by the encrypted field: *E(SesAuthENCKey; CmdData)* or *E(SesAuthENCKey; RespData)*. The complete calculation is illustrated in Figure 9. In case of command chaining, the encryption/ decryption is applied over the complete data field (i.e. of all frames). If necessary, due to the padding or the MAC added, an additional frame is sent. If encryption of the command is required, after the MAC verification as described for MAC, the PICC verifies and removes the padding bytes. Commands without a valid padding are also rejected by returning INTEGRITY\_ERROR. 

![Figure 9](images/nxp-datasheet/figureigure_9_page_029.svg)

In this case, the ongoing command and transaction are aborted (see also Section 10). The authentication state is immediately lost and the error return code is sent without a MAC appended. Note that any other error during the command execution has the same consequences. 

| \[b\] p C \= value of CmdCtr at start of this sequence  CmdData Padding  T \= Value of TI (will stay constant)  8  1 1 1 1  \[a\] \[b+p\] 1  Command counter (CmdCtr)  1MACt(SesAuthMACKey, CMD || CmdCtr  ISO 7816 Data Field  incremented after validating the  CLA  90h Cmd P1  P2  Le  PCD to PICC  Lc  command before sending the  CmdHeader  || TI \[|| CmdHeader\] \[|| E(Ke, CmdData)\])  E(SesAuthENCKey, CmdData)  00h  00h  response and related MAC calculation  MAC(SesAuthMACKey, CMD || CmdCtr || TI  MAC Truncation from 16 to 8 byte  \[|| CmdHeader\] \[|| E(Ke, CmdData\])  by use of the even-numbered bytes  1  2  4  \[a\] \[b+p\]  ISO 7816 Data Field  Cmd  CmdCtr  TI  CmdHeader  E(SesAuthENCKey, CmdData)  \[c\] p  C  T  RespData Padding  \[c+p\]  8  1  1  status  MACt(SesAuthMACKey, RC ||  E(SesAuthENCKey, RespData)  PICC to PCD  CmdCtr || TI \[|| E(Ke, RespData)\])  SW1  SW2  MAC(SesAuthMACKey, RC ||  CmdCtr || TI \[|| E(Ke, RespData)\])  \[c+p\]  1  2  4  status  CmdCtr  TI  E(SesAuthENCKey, RespData)  SW2  C+1 T  *aaa-032193*  Figure 9.  Secure Messaging: CommMode.Full |

![Figure 9](images/nxp-datasheet/figureigure_9_page_029.svg)
| ----- |

**9.2 LRP Secure Messaging** 

The LRP Secure Messaging is using AES-128 to construct a Leakage Resilient Primitive. This way, it allows side-channel resistant implementation. 

Like the AES secure messaging, this secure messaging mode is managed by commands with the same command code as AuthenticateEV2First and AuthenticateEV2NonFirst. To distinguish and ease the descriptions, they are renamed for the LRP case into AuthenticateLRPFirst and AuthenticateLRPNonFirst. The recommendations of Section 9 on when to use one or the other command also apply for LRP secure messaging. 

**9.2.1 Transaction identifier** 

The Transaction Identifier (TI) is treated exactly in the same way by LRP secure messaging as defined for AES secure messaging, see Section 9.1.1.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 29 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**9.2.2 Command counter** 

The Command counter (CmdCtr) is treated exactly in the same way by LRP secure messaging as defined for AES secure messaging, see Section 9.1.2. 

**9.2.3 MAC calculation** 

MACs are computed by using a CMAC construction on top of the LRP primitive. This is specified in \[10\]. This document uses the following notation where the right hand refers to the notation of \[10\]. 

*MACLRP(key,message) \= CMAC\_LRP(4,key, Len(message),message)* 

Note that in the LRP context a key is not purely a single value, but rather consists of the associated set of plain texts, an updated key and in context of CMAC also the subkeys K1 and K2. Therefore K1 and K2 are not shown (contrary to \[10\]) as they can be calculated inside. 

*MACtLRP(key, message)* denotes the CMAC after truncation to 8 bytes which is identical to the truncation of the AES secure messaging i.e. the even-numbered bytes are retained in most-to-least-significant order, see Section 9.1.3. 

The initialization vector used for the CMAC computation is the zero byte IV as prescribed \[10\]. 

**9.2.4 Encryption** 

Encryption and decryption are calculated using a Leakage Resilient Indexed CodeBook (LRICB) construction on top of the LRP primitive: *LRICB*of \[10\]. 

For this purpose an Encryption Counter is maintained: EncCtr is a 32-bit unsigned integer as Input Vector (IV) for encryption/decryption. The EncCtr is reset to 000000000h at PCD and PICC when starting an authentication with AuthenticateLRPFirst or AuthenticateLRPNonFirst targeting LRP. The counter is incremented during each encryption/decryption of each 16-byte block. i.e. for 64-byte encryption/decryption the EncCtr is increased by 5 due to 4 blocks of 16-byte of data plus one block of padding. Note that for AuthenticateLRPFirst the value 00000000h is already used for the response of part 2, so the actual secure messaging starts from 00000001h. For AuthenticateLRPNonFirst, secure messaging starts from 00000000h as the counter is not used during the authentication. EncCtr is further maintained as long as the PICC remains in LRP authenticated state. Note that for the key stream calculation \[10\], the counter is represented MSB first. 

Padding is applied according to Padding Method 2 of ISO/IEC 9797-1 \[7\], i.e. by adding always 80h followed, if required, by zero bytes until a string with a length of a multiple of 16 bytes is obtained. Note that if the plain data is a multiple of 16 bytes already, an additional padding block is added. The only exception is during the authentication itself (AuthenticateLRPFirst and AuthenticateLRPNonFirst), where no padding is applied at all. 

The notation *ELRP(key, plaintext)* is used to denote the encryption, i.e. *LRICBEnc* of \[10\] and *DLRP(key, ciphertext)* for the complementary decryption operation. Note that in the LRP context a key is not purely a single value, but rather consists of the associated set of plain texts and updated key. Also, as specified in \[10\], the EncCtr is updated as part of the operation. 

Note that the EncCtr cannot overflow. Due to the supported file sizes, the CmdCtr will always expire before.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 30 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

Note that the MSB representation of EncCtr is different from other counter representations in this specification, but allows saving some AES calculations in the key stream generation. 

**9.2.5 AuthenticateLRPFirst command** 

The AuthenticateLRPFirst command reuses the same command code as AuthenticateEV2First. The distinction is made via the PCDCap2.1 parameter, as explained in Section 9. 

The AuthenticateLRPFirst command is fully compliant with the mutual three-pass authentication of ISO/IEC 9798-4 \[7\]. 

The authentication consists of two parts: AuthenticateLRPFirst \- Part1 and AuthenticateLRPFirst Part2. Detailed command definition can be found in Section 10.4.3. 

The protocol cannot be interrupted by other commands. On any command different from AuthenticateLRPFirst \- Part2 received after the successful execution of the first part, the PICC aborts the ongoing authentication. 

During this authentication phase, the PICC accepts messages from the PCD that are longer than the lengths derived from this specification as long as *LenCap* is correct. This feature is to support the upgradability to following generations of NTAG 424 DNA. 

Apart from bit 1 of PCDCap2.1, which need to be set to 1 for AuthenticateLRPFirst resulting into 020000000000h, the content of PCDCap2 is not interpreted by the PICC. The PCD rejects answers from the PICC when they don’t have the proper length. 

Upon reception of AuthenticateLRPFirst, the PICC validates the targeted key. If the key does not exist, AuthenticateLRPFirst is rejected. At PICC level, the only available key is the OriginalityKey. 

The PICC generates a random 16-byte challenge *RndB* and send this in plain to the PCD. Additionally, the PICC and PCD reset both CmdCtr and EncCtr to zero and generate a random TI. 

Upon reception of the AuthenticateLRPFirst response from the PICC, the PCD also generates a random 16-byte challenge *RndA*. Now the PCD calculates the session keys SesAuthMACKey and SesAuthENCKey, as specified in Section 9.2.7. As explained there for LRP, a session key consists of a set of plain texts and an updated key. 

Then the PCDResponse computes a MAC over the concatenation of *RndA* with *RndB*, applying the SesAuthMACKey with the algorithm defined in Section 9.2.3. Note that MACs are not truncated during the authentication. Within AuthenticateLRPFirst \- Part2, the concatenation of *RndA* and this MAC is sent to the PICC. 

Upon reception of AuthenticateLRPFirst \- Part2, the PICC validates the received MAC. If not as expected, the command is rejected. Else it encrypts the generated TI concatenated with 12 bytes of capabilities to the PCD: 6 bytes of PICC capabilities *PDCap2* and 6 bytes of PCD capabilities *PCDCap2* that were received on the command (sent back for verification). Encryption is done according to Section 9.2.4, applying SesAuthENCKey. 

Note that part of PDCap is configurable with SetConfiguration. *PCDCap2* is used to refer both to the value sent from the PCD to the PICC and to the value used in the encrypted response message from the PICC to the PCD where in this case the *PCDCap2* is the adjusted version of the originally sent *PCDCap2*: i.e. truncated or padded with zero bytes to a length of 6 bytes if needed. After that encryption, the PICCResponse will also compute a MAC over the concatenation of *RndB*, *RndA* and the encrypted data.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 31 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**9.2.6 AuthenticateLRPNonFirst command** 

This section defines the LRP Non-First Authentication, which is recommended to be used if LRP Secure Messaging is already active, see Table 18. 

![Table 18](images/nxp-datasheet/table_18_page_021.svg)

![Table 1](images/nxp-datasheet/table_1_page_004.svg)

The authentication consists of two parts: AuthenticateLRPNonFirst \- Part1 and AuthenticateLRPNonFirst Part2. Detailed command definition can be found in Section 10.4.4. 

This command is rejected if there is no active LRP authentication, except if the targeted key is the OriginalityKey. 

For the rest, the behavior is exactly the same as for AuthenticateLRPFirst, except for the following differences: 

**•** PCDCap2 and PDCap2 are not exchanged and validated 

**•** TI is not reset and not exchanged 

**•** CmdCtr is not reset 

Note that EncCtr is reset to zero also on AuthenticateLRPNonFirst. 

After successful authentication, the PICC remains in LRP authenticated state, except if the OriginalityKey was targeted. In that case, the PICC is in not authenticated state. On any failure during the protocol, the PICC ends up in not authenticated state. 

**9.2.7 Session key generation** 

Next to the algorithms for MAC calculation and encryption, one of the major differences between the LRP secure messaging and the AES secure messaging is that the session keys are generated and already applied during the authentication with AuthenticateLRPFirst or AuthenticateLRPNonFirst. 

Also for the LRP protocol, two keys are generated: 

**•** SesAuthMACKey for MACing of messages 

**•** SesAuthENCKey for encryption and decryption of messages 

During the authentication, the SesAuthMACKey is used for both AuthenticateLRPFirst and AuthenticateLRPNonFirst. SesAuthENCKey is only used for AuthenticateLRPFirst. 

Being LRP keys, this section shows how both the plain texts and the updated key \[10\] related to these session keys are computed. In the remainder of the document, when the session key is applied in the LRP context the combination of those plain texts and updated key is meant. 

The session key generation is according to NIST SP 800-108 \[8\] in counter mode. 

The Pseudo Random Function *PRF(key; message)* applied during the key generation is the CMAC algorithm on top of the LRP primitive. This is specified in \[10\], see also Section 9.2.3. The key derivation key is the key *Kx* that was applied during authentication. Note that from this key a set of plaintexts and updated key is computed, so the static key is only used in this derivation. The generated session keys are AES keys. The input data is constructed using the following fields as defined by \[8\]. Note that NIST SP 800-108 allows defining a different order than proposed by the standard as long as it is unambiguously defined. 

**•** a 2-byte counter, fixed to 0001h as only 128-bit keys are generated

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 32 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**•** a 2-byte length, fixed to 0080h as only 128-bit keys are generated 

**•** a 26-byte context, constructed using the two random numbers exchanged, *RndA* and *RndB* 

**•** a 2-byte label: 9669h 

Firstly, the 32-byte input session vector *SV* is derived as follows: 

*SV \= 00h || 01h || 00h || 80h || RndA\[15::14\] ||* 

  *(RndA\[13::8\] \# RndB\[15::10\]) || RndB\[9::0\] || RndA\[7::0\] || 96h || 69h* 

with \# being the XOR-operator. 

Then, the session key material is constructed as follows: 

*AuthSPT \= generatePlaintexts(4; Kx)*   
*{AuthUpdateKey} \= generateUpdatedKeys(1; Kx)*   
*SesAuthMasterKey \= MACLRP (Kx; SV )*   
*SesAuthSPT \= generatePlaintexts(4; SesAuthMasterKey)* 

*{SesAuthMACUpdateKey; SesAuthENCUpdateKey} \= generateUpdatedKeys(2;* 

*SesAuthMasterKey)* 

with *generatePlaintexts* and *generateUpdatedKeys* the functions from \[10\]. Note that the output of *generateUpdatedKeys* is shown in the order that the keys are generated. The actual SesAuthMACKey then consists for LRP of the set of plaintexts SesAuthSPT (consisting of 16 16-byte values) and SesAuthMACUpdateKey. The SesAuthENCKey consists of the same set of plaintexts SesAuthSPT and SesAuthENCUpdateKey. 

**9.2.8 Plain communication mode** 

For CommMode.Plain, command processing in LRP authenticated state is identical to AES secure messaging in EV2 authenticated state, see Section 9.1.8. 

**9.2.9 MAC communication mode** 

For MAC, apart from using the LRP MAC algorithm, as specified in Section 9.2.3, the command processing in LRP authenticated state is identical to AES secure messaging in EV2 authenticated state, see Section 9.1.9. The calculation is illustrated in Figure 10.

![Figure 10](images/nxp-datasheet/figureigure_10_page_033.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)

| C \= value of CmdCtr at start of this sequenceT \= Value of TI (will stay constant)  8  1 1 1 1  \[a\] \[b\] 1  Command counter (CmdCtr)  1MACt(SesAuthMACKey, CMD ||  ISO 7816 Data Field  incremented after validating the  CLA  90h Cmd P1  P2  Le  PCD to PICC  Lc  command before sending the  CmdHeader  CmdCtr || TI \[|| CmdHeader\] \[|| CmdData\])  CmdData  00h  00h  00h  response and related MAC calculation  MACLRP(SesAuthMACKey, CMD || CmdCtr || TI  MAC Truncation from 16 to 8 byte  \[|| CmdHeader\] \[|| CmdData\])  by use of the even-numbered bytes  1  2  4  \[a\] \[b\]  ISO 7816 Data Field  Cmd  CmdCtr  TI  CmdHeader  CmdData  C T  \[c\]  8  1  1  status  MACt(SesAuthMACKey, RC ||  PICC to PCD  RespData  CmdCtr || TI \[|| RespData\])  SW1  SW2  MAC(SesAuthMACKey, RC ||  CmdCtr || TI \[|| RespData\])  \[c\]  2  4  1  status  CmdCtr  TI  RespData  SW2  C+1 T  *aaa-032194*  Figure 10. LRP Secure Messaging: MAC Protection Mode |

![Figure 10](images/nxp-datasheet/figureigure_10_page_033.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)
| ----- |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 33 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**9.2.10 Full communication mode** 

For CommMode.Full, apart from using the LRP encryption and MAC algorithm, as specified in Section 9.2.4, the command processing in LRP authenticated state is identical to AES secure messaging in EV2 authenticated state, see Section 9.1.10. This is as well illustrated in Figure 11. 

![Figure 11](images/nxp-datasheet/figureigure_11_page_034.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)

| \[b\] pCmdData Padding  C \= value of CmdCtr at start of this sequence  T \= Value of TI (will stay constant)  8 Command counter (CmdCtr)  1 1 1 1  1  \[a\] \[b+p\] 1  ISO 7816 Data Field  incremented after validating the  MACtLRP(SesAuthMACKey, CMD || CmdCtr || TI \[||  Le  CLA  90h Cmd P1  P2  PCD to PICC  Lc  command before sending the  CmdHeader  ELRP(SesAuthENCKey, CmdData)  CmdHeader\] \[|| ELRP(SesAuthENCKey, CmdData)\])  00h  00h  00h  response and related MAC calculation  MACtLRP(SesAuthMACKey, CMD || CmdCtr || TI \[||  CmdHeader\] \[|| ELRP(SesAuthENCKey, CmdData)\])MAC Truncation from 16 to 8 byte  by use of the even-numbered bytes  1  2 4  \[a\] \[b+p\]  ISO 7816 Data Field  Cmd  CmdCtr  TI  CmdHeader  ELRP(SesAuthENCKey, CmdData)  C T  \[c\] p  RespData Padding  \[c+p\]  8  1  1  status  MACLRP(SesAuthMACKey, RC || CmdCtr  ELRP(SesAuthENCKey, RespData)  PICC to PCD  || TI \[|| ELRP(SesAuthENCKey, RespData)\])  SW1  SW2  MACLRP(SesAuthMACKey, RC || CmdCtr  || TI \[|| ELRP(SesAuthENCKey, RespData)\])  \[c+p\]  1  2  4  status  CmdCtr  TI  ELRP(SesAuthENCKey, RespData)  SW2  C+1 T  *aaa-032195*  Figure 11. LRP Secure Messaging: CommMode.Full |

![Figure 11](images/nxp-datasheet/figureigure_11_page_034.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)
| ----- |

**9.3 Secure Dynamic Messaging** 

The Secure Dynamic Messaging (SDM) allows for confidential and integrity protected data exchange, without requiring a preceding authentication. NT4H2421Gx supports SDM for reading from one of the StandardData files on the PICC. Secure Dynamic Messaging allows adding security to the data read, while still being able to access it with standard NDEF readers. The typical use case is an NDEF holding a URI and some meta data, where SDM allows this meta-data to be communicated confidentiality and integrity protected toward a backend server. 

When using SDM, residual risks coming with the Secure Dynamic Messaging for Reading have to be taken into account. As SDM allows free reading of the secured message, i.e. without any up-front reader authentication, anybody can read out the message. This means that also a potential attacker is able to read out and store one ore multiple messages, and play them at a later point in time to the verifier. 

If this residual risk is not acceptable for the system’s use case, the legacy mutual authentication (using challenge response protocol) and subsequent secure messaging should be applied. This would require using an own application and operating outside a standard NDEF read operation. 

Other risk mitigation may be applied for SDM to limit the residual risk, without completely removing it: 

**•** Track SDMReadCtr per tag at the verifying side. Reject SDMReadCtr values that have been seen before or that are played out-of-order. This is a minimum requirement any verifier should implement. 

**•** Limit the time window of an attacker by requiring tags to be presented regularly (e.g. at least once a day) in combination with the previous mitigation.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 34 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**•** Read out the SDM-protected file more than once. This does not protect against attackers that have read out the valid tag also multiple times and play the received responses in the same sequence. 

**9.3.1 SDM Read Counter** 

In order to allow replay detection by the party validating the data read, a read counter is associated with the file for which Secure Dynamic Messaging is enabled. 

SDMReadCtr is a 24-bit unsigned integer. The SDMReadCtr is reset to 000000h when enabling SDM with ChangeFileSettings. In cryptographic calculations and represented with binary encoding on the external interface, the SDMReadCtr is represented LSB first. When represented with ASCII encoding on the contactless interface, it is represented MSB first. Note that this is in line with the NFC counter representation in \[14\] 

In not Authenticated state, the SDMReadCtr is incremented by 1 before calculating the response of the first read command, ReadData or ISOReadBinary, if successful. On subsequent read commands targeting the same file, the SDMReadCtr is not increased, and the current value is used. As soon as a different command has been received, the counter is incremented again on a subsequent read command. Also when varying between ReadData and ISOReadBinary, the counter is incremented on each first instance of the read command type. Note that the SDMReadCtr is not incremented when authenticated. 

If the SDMReadCtr reaches the SDMReadCtrLimit (see Section 9.3.2) or the value FFFFFFh (if SDMReadCtrLimit is not enabled) and a first read command arrives at the PICC, an error is being returned. Command chaining, see Section 8.5, does not 

additionally affect the counter increase. The chained command is considered as a single command. 

SDMReadCtr can be retrieved via the mirroring as part of the PICCData, see Section 9.3.3, or it can be retrieved via GetFileCounters. 

**9.3.2 SDM Read Counter Limit** 

In order to allow limiting the number of reads that can be done with a single device applying Secure Dynamic Messaging, an optional SDM Read Counter Limit can be configured. There are two main use cases: 

**•** limit the number of usages from the card side. Note that typically this can also be controlled from the backend verifying the SDM for Read protected message. **•** limit the number of traces that can be collected on the symmetric crypto processing. This way potential side channel attacks can be mitigated, see also the Failed Authentication Counter feature for the mutual authentication. In this case, it is recommended to have the configured limit aligned with TotFailCtrLimit. 

The number of reads that can be executed for an SDM configured file can be limited by setting an SDM Read Counter Limit (SDMReadCtrLimit). This is an unsigned integer of 3 bytes, related with SDMReadCtr. On the interface, the SDMReadCtrLimit is represented LSB first. The SDMReadCtrLimit can be enabled by setting a customized value with ChangeFileSettings. It can be retrieved with GetFileSettings. 

Once the SDMReadCtr equals the SDMReadCtrLimit, no reading of the file with ReadData or ISOReadBinary in not authenticated state can be executed. Note that if authenticated, reading is always possible even if SDMReadCtrLimit is reached, applying the regular secure messaging. If the SDMReadCtrLimit is disabled with ChangeFileSettings, this is also equivalent to putting it to the maximum value: FFFFFFh.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 35 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**9.3.3 PICCData** 

The PICCData holds metadata of the targeted PICC and file, consisting of the UID and/or the SDMReadCtr. Whether PICCData is transmitted in plain or encrypted depends on the configuration of the SDMMetaRead access rights on the file, see Section 8.2.3.4. If the SDMMetaRead access right is configured for free access (Eh), PICCData is plain and is defined according to Table 20. 

![Table 20](images/nxp-datasheet/table_20_page_036.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

ASCII mirroring is reflected by the function EncodeASCII(), which means that each hexadecimal character of the hexadecimal representation will be ASCII encoded using capitals. For example, the UID 04E141124C2880h becomes: 30h 34h 45h 31h 34h 31h 31h 32h 34h 43h 32h 38h 38h 30h. 

**Table 20. PICCData: plain encoding and lengths** 

![Table 20](images/nxp-datasheet/table_20_page_036.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

| Mode  | PICCData Value  | Length with 7-byte UID |
| :---- | :---- | :---- |
| ASCII  | EncodeASCII(UID)  | UIDLength \= 14 (i.e. 2\*UIDLen) |
| ASCII  | EncodeASCII(SDMReadCtr)  | SDMReadCtrLength \= 6 (i.e. 2\*3) |

Note that the SDMReadCtr, as defined in Section 9.3.1, is represented MSB first for ASCII case. If the SDMMetaRead access right is configured for an application key, PICCData will be encrypted as defined in Section 9.3.4. In this case, the input plaintext for the encryption is always in binary encoding, while the output ciphertext will be ASCII encoded. 

The PICCData is mirrored within the file. This is configured with ChangeFileSettings via the related offsets. 

In case of plain mirroring (i.e. access right SDMMetaRead \= Eh): 

**•** UIDOffset configures the UID mirroring position. It is only given if UID mirroring is enabled. 

**•** SDMReadCtrOffset configures the SDMReadCtr mirroring position. It is only given if SDMReadCtr mirroring is enabled. Note that it is possible to enable the SDMReadCtr but without mirroring by putting SDMReadCtrOffset to FFFFFFh. In this case it can be retrieved with the GetFileCounters command. 

If UID and SDMReadCtr are mirrored within the file, they shall not overlap: 

**•** UIDOffset ≥ SDMReadCtrOffset \+ SDMReadCtrLength OR SDMReadCtrOffset ≥ UIDOffset \+ UIDLength. 

In case of encrypted mirroring (i.e. SDMMetaRead \= 0h..4h), PICCDataOffset configures the PICCData mirroring. The encryption is outlined in Section 9.3.4. 

If the PICCData is mirrored within the file, the mirroring shall always be applied in not authenticated state, independently of whether Secure Dynamic Messaging applies. This means it will also be applied if reading the file with free access due to Read or ReadWrite access right. Note that if authenticated, no mirroring is done, i.e. the regular secure messaging is always applied on the static file data. 

With NT4H2421Gx, PICCData is always ASCII encoded. 

When both the UID and SDMReadCtr are mirrored, “x” (78h) is used as a separator character with NTAG2x \[14\]. This can be achieved by leaving one byte space between the placeholders defined by UIDOffset and SDMReadCtrOffset, and writing “x” (78h) in the static file data.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 36 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**9.3.4 Encryption of PICCData** 

In case of encrypted PICCData mirroring (both binary and ASCII), PICCDataTag specifies what metadata is mirrored, together with the length of the UID if mirrored, as defined in Table 21. 

![Table 21](images/nxp-datasheet/table_21_page_037.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

**Table 21. PICCDataTag** 

![Table 21](images/nxp-datasheet/table_21_page_037.svg)

![Table 2](images/nxp-datasheet/table_2_page_005.svg)

| Bit  | Value  | Description |
| :---- | :---- | :---- |
| Bit7 | \-  | UID mirroring |
|  | 0  | disabled |
|  | 1  | enabled |
| Bit6 | \-  | SDMReadCtr mirroring |
|  | 0  | disabled |
|  | 1  | enabled |
| Bit5-4  | 00  | RFU |
| Bit3-0 | \-  | UID Length |
|  | 0h  | RFU (if UID is not mirrored) |
|  | 7h  | 7 byte UID |

The format of the plain text is: *PICCDataTag \[ || UID\] \[|| SDMReadCtr\].* 

To ensure that the encrypted PICCData cannot be abused for tracking purposes, random padding is added to the actual plain text input. 

The random padding is generated for the response of the first read command, ReadData or ISOReadBinary. On subsequent read commands targeting the same file the same random padding is reused. This allows for reading the file in chunks, where a chunk border might even be in the middle of the encrypted PICCData. As soon as a different command has been received, fresh random padding is generated on a subsequent read command. Also when varying between ReadData and ISOReadBinary, fresh random padding is generated. 

The key applied for encryption of PICCData is the SDMMetaReadKey as defined by the SDMMetaRead access right. 

**9.3.4.1 AES mode encryption** 

Encryption and decryption of the PICCData are calculated using the underlying block cipher according to the CBC mode of NIST SP800-38A \[5\], applying zero byte IV. Therefore PICCData is defined as follows: 

*PICCData \= E(*SDMMetaReadKey*; PICCDataTag \[ || UID \] \[ || SDMReadCtr \] || RandomPadding)* 

with PICCDataTag as defined in Section 9.3.3, and RandomPadding being a random byte string generated by the PICC to make the input 16 bytes long. Note that because of the ASCII encoding the required placeholder length doubles. 

**9.3.4.2 LRP mode encryption** 

Encryption and decryption of the PICCData are calculated using a leakage resilient indexed codebook (LRICB) construction on top of the LRP primitive: LRICB of \[14\].

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 37 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

For this operation, the LRP key material is constructed as follows: 

*SDMMetaReadSPT \= generatePlaintexts(4;* SDMMetaReadKey*)* 

*{SDMMetaReadUpdateKey} \= generateUpdatedKeys(1;* SDMMetaReadKey*)* 

As input counter for the CTR construction, the 8-byte random PICCRand, generated by the PICC, is used. Apart from the counter applied, this is identical to the encryption used for LRP secure messaging, see Section 9.2.4. 

Therefore PICCData is defined as follows: 

*PICCData \= PICCRand || ELRP (*SDMMetaReadKey*; PICCDataTag \[|| UID\] \[ || SDMReadCtr\] || RandomPadding)* 

with PICCDataTag as defined in Section 9.3.3, and PICCRand being an 8-byte long random byte string generated by the PICC. RandomPadding is applied like for AES mode. 

The required placeholder length in the NDEF message is 48 bytes due to ASCII encoding. 

Note that due to the different sizes of encrypted PICCData with AES mode and LRP mode, the Secure Dynamic Messaging and mirroring will be disabled when switching from AES mode to LRP mode with SetConfiguration. 

**9.3.5 SDMENCFileData** 

SDM for Reading supports mirroring (part of the) file data encrypted. This part is called the SDMENCFileData. 

If the SDMFileRead access right is configured for an application key, part of the file data can optionally be encrypted as defined in Section 9.3.6 when being read out in not authenticated state. 

In this case, the input plaintext for the encryption is always in binary encoding, while the output ciphertext is ASCII encoded. 

Note that if authenticated, no Secure Dynamic Messaging is applied, i.e. the regular secure messaging is always applied on the static file data. 

The SDMENCFileData (if any) is always mirrored within the file. This is configured with ChangeFileSettings, see Section 10.7.1 via SDMENCOffset and SDMENCLength. If the SDMFileRead access right is disabling Secure Dynamic Messaging for reading (i.e. set to Fh), SDMENCOffset and SDMENCLength are not present in ChangeFileSettings. 

If PICCData is mirrored within the file, SDMENCFileData shall not overlap with it. Depending on what is exactly mirrored, the following holds: 

**•** SDMENCOffset ≥ PICCDataOffset \+ PICCDataLength OR PICCDataOffset ≥ SDMENCOffset \+ SDMENCLength. 

**•** SDMENCOffset ≥ UIDOffset \+ UIDLength OR UIDOffset ≥ SDMENCOffset \+ SDMENCLength. 

**•** SDMENCOffset ≥ SDMReadCtrOffset \+ SDMReadCtrLength OR SDMReadCtrOffset ≥ SDMENCOffset \+ SDMENCLength. 

It shall be ensured that SDMENCOffset \+ SDMENCLength is smaller than or equal to the file size. Note that as the SDMMAC is as well mirrored into the file, additional conditions apply, see Section 9.3.7. The SDMENCLength shall be a multiple of 32 bytes for the ASCII encoding. With NT4H2421Gx, only ASCII encoding is supported.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 38 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**9.3.6 Encryption of SDMENCFileData** 

The key applied for the encryption is a session key SesSDMFileReadENCKey derived from the application key defined by the SDMFileRead access right as specified in Section 9.3.9. 

From user point of view, the SDMENCOffset and SDMENCLength define a placeholder within the file where the plain data is to be stored when writing the file. 

For ASCII encoding, only the first half of the placeholder is used for storing the plain data, the second half is ignored for constructing the returned data when reading with SDM. For example, if targeting to encrypt 2 AES blocks, i.e. 32 bytes, a placeholder of 64 bytes is reserved via SDMENCOffset and SDMENCLength. The first 32 bytes hold the plaintext, and the next 32 bytes are ignored when reading with Secure Dynamic Messaging. 

**9.3.6.1 AES mode encryption** 

Encryption and decryption of the SDMENCFileData are calculated using the underlying block cipher according to the CBC mode of NIST SP800-38A \[5\]. The following IV is applied: 

*IV \= E(SesSDMFileReadENCKey; SDMReadCtr||00000000000000000000000000h)* with SDMReadCtr LSB first. 

For applying SDM with ASCII encoding, the SDMENCFileData is defined as follows: 

*SDMENCFileData \= E(SesSDMFileReadENCKey; StaticFileData\[SDMENCOffset:: SDMENCOffset \+ SDMENCLength=2 \- 1\])* 

with StaticFileData being the current file data as written in the placeholder. The file configuration ensures via SDMENCLength that the input is a multiple of 16 bytes, so no padding is applied. 

Note that it is possible via the read command parameters to read-only part of the file. If the SDMENCFileData is partially read as per the issued offset and length, a truncated part of the ciphertext will be returned. As truncation might happen in the middle of an AES block, this means subsequent read commands to fetch the remainder of the file might be required to be able to decrypt. 

**9.3.6.2 LRP mode encryption** 

Encryption and decryption of the SDMENCFileData are calculated using a leakage resilient indexed codebook (LRICB) construction on top of the LRP primitive: LRICB of \[10\]. 

As input counter for the CTR construction, a 6-byte counter is used, consisting of the concatenation of SDMReadCtr and three zero bytes: SDMReadCtr || 000000h. SDMReadCtr is LSB first. After concatenation the 6-byte are treated as unsigned integer for the counting. 

Apart from the counter applied, this is identical to the encryption used for LRP secure messaging, see Section 9.2.4. 

If applying SDM with ASCII encoding, the SDMENCFileData is defined as follows: 

*SDMENCFileData \= ELRP (SesSDMFileReadENCKey; StaticFileData\[SDMENCOffset ... SDMENCOffset \+ SDMENCLength/2 \- 1\])*

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 39 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

with StaticFileData being the file data as it was written in the placeholder. The file configuration ensures via SDMENCLength that the input is a multiple of 16 bytes. No padding is applied. 

**9.3.7 SDMMAC** 

SDM for Reading supports calculating a MAC over the response data. This message authentication code is called the SDMMAC. 

If SDMFileRead access right is configured for an application key, a MAC will be calculated as defined in Section 9.3.8 when being read out in no authenticated state. 

The SDMMAC is to be mirrored within the file via SDMMACOffset. This is configured with ChangeFileSettings, see Section 10.7.1. 

If SDMMAC is mirrored within the file, it is limited to start only after SDMENCFileData, i.e. SDMMACOffset ≥ SDMENCOffset \+ SDMENCLength. The SDMMACInputOffset must ensure that the complete SDMENCFileData is included in the MAC calculation. 

As the mirrored SDMMAC is ASCII encoded, the output size doubles to 16 bytes. 

It shall be ensured that SDMMACOffset \+ SDMMACLength is smaller or equal than the file size. Note that if authenticated, no Secure Dynamic Messaging is applied and the placeholder data at SDMMACOffset is not replaced, i.e. the regular secure messaging is always applied on the static file data. 

The SDMMACInputOffset will define from which position in the file the MAC calculation starts. If SDMMAC is mirrored within the file, SDMMACInputOffset must be smaller than or equal to SDMMACOffset. 

MACing is mandatory if the SDMFileRead access right is configured for an application key. If the SDMFileRead access right is disabling Secure Dynamic Messaging for reading (i.e. set to Fh), SDMMACOffset and SDMMACInputOffset are not present in ChangeFileSettings. 

With NT4H2421Gx, only ASCII encoding is supported. SDMMAC is always mirrored within the file. 

**9.3.8 MAC Calculation** 

The key applied for the MAC calculation is a session key SesSDMFileReadMACKey derived from the application key defined by the SDMFileRead access right, as specified in Section 9.3.9. 

**9.3.8.1 AES mode MAC calculation** 

The 8-byte SDMMAC is calculated using AES according to the CMAC standard described in NIST Special Publication 800-38B \[6\] applying the same truncation as the AES mode secure messaging, see Section 9.1.3. 

The SDMMAC is defined as follows: 

*SDMMAC \= MACt (SesSDMFileReadMACKey; DynamicFileData\[SDMMACInputOffset ... SDMMACOffset \- 1\])* 

with DynamicFileData being the file data as how it is put on the contactless interface, i.e. replacing any placeholders by the dynamic data.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 40 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**9.3.8.2 LRP mode MAC calculation** 

The 8-byte SDMMAC is calculated using a CMAC construction on top of the LRP primitive. This is specified in \[10\]. 

It is identical to the MAC calculation of LRP secure messaging, see Section 9.2.3, also applying the same truncation. 

Therefore SDMMAC is defined as follows: 

*SDMMAC \= MACtLRP (SesSDMFileReadMACKey;*   
*DynamicFileData\[SDMMACInputOffset ... SDMMACOffset \- 1\])* 

with DynamicFileData being the file data as how it is put on the contactless interface, i.e. replacing any placeholders by the dynamic data. 

**9.3.9 SDM Session Key Generation** 

For Secure Dynamic Messaging for reading, the following session keys are calculated: 

**•** SesSDMFileReadMACKey for MACing of file data. 

**•** SesSDMFileReadENCKey for encryption of file data 

The session key generation is according to NIST SP 800-108 \[8\] in counter mode. 

The pseudo random function applied during the key generation is the CMAC algorithm described in NIST Special Publication 800-38B \[6\]. The key derivation key is the SDMFileReadKey as configured with the SDMFileRead access right. 

**9.3.9.1 AES mode session key generation for SDM** 

The input data is constructed using the following fields as defined by \[8\]. Note that NIST SP 800-108 allows defining a different order than proposed by the standard as long as it is unambiguously defined. 

**•** a 2-byte label, distinguishing the purpose of the key: 3CC3h for MACing and C33Ch for encryption. 

**•** a 2-byte counter, fixed to 0001h as only 128-bit keys are generated. 

**•** a 2-byte length, fixed to 0080h as only 128-bit keys are generated. 

**•** a context, constructed using the UID and/or SDMReadCtr, followed by zero-byte padding if needed. 

Firstly, the input session vectors SV x are derived as follows: 

*SV1 \= C3h || 3Ch || 00h || 01h || 00h || 80h || UID || SDMReadCtr* 

*SV2 \= 3Ch || C3h || 00h || 01h || 00h || 80h \[ || UID\] \[ || SDMReadCtr\] \[ || ZeroPadding\]* 

Whether or not the UID and/or SDMReadCtr are included in session vector SV2, depends on whether they are mirrored, see Section 9.3.3. Note that in case of encrypting file data, mirroring of both is mandatory. 

Therefore they are always included in SV1. 

Padding with zeros is done up to a multiple of 16 bytes. So in case of 7-byte UID and both elements are mirrored, no padding is added. Then, the 16-byte session keys are constructed as follows: 

*SesSDMFileReadENCKey \= MAC(*SDMFileReadKey*; SV1)* 

*SesSDMFileReadMACKey \= MAC(*SDMFileReadKey*; SV2)*

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 41 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

**9.3.9.2 LRP mode session key generation for SDM** 

The input data is constructed using the following fields as defined by \[8\]. Note that NIST SP 800-108 allows defining a different order than proposed by the standard as long as it is unambiguously defined. 

**•** a 2-byte counter, fixed to 0001h as only 128-bit keys are generated. 

**•** a 2-byte length, fixed to 0080h as only 128-bit keys are generated. 

**•** a context, constructed using the UID and/or SDMReadCtr, followed by zero-byte padding if needed. 

**•** a 2-byte label: 1EE1h 

Firstly, the input session vector SV is derived as follows: 

*SV \= 00h || 01h || 00h || 80h \[ || UID\] \[ || SDMReadCtr\] \[ || ZeroPadding\] || 1Eh || E1h* 

Whether or not the UID and/or SDMReadCtr are included in the session vectors, depends on whether they are mirrored, see Section 9.3.3. Note that in case of encrypting file data, mirroring of both is mandatory. Padding with zeros is done up to a multiple of 16 bytes. So in case of 7-byte UID and both elements are mirrored, no padding is added. Then, the session key material is constructed as follows: 

*SDMFileReadSPT \= generatePlaintexts(4;* SDMFileReadKey*)* 

*{SDMFileReadUpdateKey} \= generateUpdatedKeys(1;* SDMFileReadKey*) SesSDMFileReadMasterKey \= MACLRP (*SDMFileReadKey*; SV)*   
*SesSDMFileReadSPT \= generatePlaintexts(4; SesSDMFileReadMasterKey)* 

*{SesSDMFileReadMACUpdateKey; SesSDMFileReadENCUpdateKey} \=* 

*generateUpdatedKeys(2; SesSDMFileReadMasterKey)* 

with generatePlaintexts and generateUpdatedKeys the functions from \[10\]. Note that the output of generateUpdatedKeys is shown in the order that the keys are generated. 

The actual SesSDMFileReadMACKey then consists for LRP of the set of 

plaintexts SesSDMFileReadSPT (consisting of 16 16-byte values) and 

SesSDMFileReadMACUpdateKey. The SesSDMFileReadENCKey consists of the same set of plaintexts SesSDMFileReadSPT and SesSDMFileReadENCUpdateKey. 

**9.3.10 Output Mapping Examples** 

The following figure shows an example with the static file content and how it will be read.

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 42 / 97**   
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

| Static File Output Offset  CtrOffset  \+  SDMENCOffset  VCUID  SDMRead  SDMENCOffset SDMRead CtrOffset SDMMACOffset  \+ 14  \+ 6  SDMENCLength/2  \+  SDMENCLength  \+ 16  VCUIDOffset  SDMENCOffset  SDMMACOffset FileLength  Plain  Placeholder  File  Placeholder  Plain File  Placeholder  Plain File Data  data Plain File Data Placeholder data  Data  data  Data  Plain File Data  data  Plain File Data  Nlen \=  SDMMAC  \`'http://www.nxp.com/index.html?p=''  XXh .. XXh XXh .. XXh  “x''  “\&c=''  20h, 21h, ... 2Fh  XXh .. XXh  \`'\&m=''  XXh, XXh, XXh, .. XXh  41h, 42h, ... 4Fh  Offset \+ 16  SDMMACInputOffset  MAC(SesSDMFileReadMACKey, “www.nxp.com/index.html?p= || “04E134FE9D7CD3x000001  || “\&c= || “E(Ses SDMFileReadENCKey, 20h, 21h, 22h, ... 2Dh, 2Eh, 2Fh) || “\&m= )  Dynamic File Output  Offset  CtrOffset  SDMENCOffset  VCUID  SDMRead  SDMRead CtrOffset SDMMACOffset  \+ 14  \+ 6  \+  VCUIDOffset SDMMACOffset  SDMENCOffset  SDMENCLength  \+ 16  FileLength  Plain  Plain File  Plain UID  File  SDMReadCtr  Plain File  Encrypted File Data  Plain File Data  Computed MAC  Plain File Data  (ASCII)  Data  (ASCII)  Data  (ASCII encoded)  Plain File Data (ASCII encoded)  (typically not read out)  Nlen \=  “04E134FE9  “E(SesSDMFileReadENCKey,  SDMMAC  \`'http://www.nxp.com/index.html?p=''  D7CD3\`'\&m=''  “x''  “000001''  “\&c=''  “MACt  41h, 42h, ... 4Fh  20h, 21h, 22h, ... 2Dh, 2Eh, 2Fh)  Offset \+ 16  *aaa-032483*  SDMMACInputOffset NLen Figure 12. Secure Dynamic Messaging for Reading example |

![Figure 12](images/nxp-datasheet/figureigure_12_page_043.svg)

![Figure 1](images/nxp-datasheet/figureigure_1_page_006.svg)
| ----- |

465430 All information provided in this document is subject to legal disclaimers. © NXP B.V. 2019\. All rights reserved. **Product data sheet Rev. 3.0 — 31 January 2019**   
**COMPANY PUBLIC 465430 43 / 97**  
**NXP Semiconductors NT4H2421Gx NTAG 424 DNA – Secure NFC T4T compliant IC** 

