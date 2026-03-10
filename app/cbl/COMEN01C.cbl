>>SOURCE FREE
IDENTIFICATION DIVISION.
PROGRAM-ID. COMEN01C.
AUTHOR. AWS.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-DONE PIC X VALUE "N".
   88 MENU-DONE VALUE "Y".
   88 MENU-ACTIVE VALUE "N".
01 WS-CHOICE PIC 9(02) VALUE 0.
01 WS-CHOICE-TEXT PIC X(80) VALUE SPACES.
01 WS-MESSAGE PIC X(80) VALUE SPACES.
01 WS-IDX PIC 9(02) VALUE 0.

01 CARDDEMO-MAIN-MENU-OPTIONS.
   05 CDEMO-MENU-OPT-COUNT           PIC 9(02) VALUE 11.
   05 CDEMO-MENU-OPTIONS-DATA.
      10 FILLER                      PIC 9(02) VALUE 1.
      10 FILLER                      PIC X(35) VALUE
         "Account View                       ".
      10 FILLER                      PIC X(08) VALUE "COACTVWC".
      10 FILLER                      PIC X(01) VALUE "U".
      10 FILLER                      PIC 9(02) VALUE 2.
      10 FILLER                      PIC X(35) VALUE
         "Account Update                     ".
      10 FILLER                      PIC X(08) VALUE "COACTUPC".
      10 FILLER                      PIC X(01) VALUE "U".
      10 FILLER                      PIC 9(02) VALUE 3.
      10 FILLER                      PIC X(35) VALUE
         "Credit Card List                   ".
      10 FILLER                      PIC X(08) VALUE "COCRDLIC".
      10 FILLER                      PIC X(01) VALUE "U".
      10 FILLER                      PIC 9(02) VALUE 4.
      10 FILLER                      PIC X(35) VALUE
         "Credit Card View                   ".
      10 FILLER                      PIC X(08) VALUE "COCRDSLC".
      10 FILLER                      PIC X(01) VALUE "U".
      10 FILLER                      PIC 9(02) VALUE 5.
      10 FILLER                      PIC X(35) VALUE
         "Credit Card Update                 ".
      10 FILLER                      PIC X(08) VALUE "COCRDUPC".
      10 FILLER                      PIC X(01) VALUE "U".
      10 FILLER                      PIC 9(02) VALUE 6.
      10 FILLER                      PIC X(35) VALUE
         "Transaction List                   ".
      10 FILLER                      PIC X(08) VALUE "COTRN00C".
      10 FILLER                      PIC X(01) VALUE "U".
      10 FILLER                      PIC 9(02) VALUE 7.
      10 FILLER                      PIC X(35) VALUE
         "Transaction View                   ".
      10 FILLER                      PIC X(08) VALUE "COTRN01C".
      10 FILLER                      PIC X(01) VALUE "U".
      10 FILLER                      PIC 9(02) VALUE 8.
      10 FILLER                      PIC X(35) VALUE
         "Transaction Add                    ".
      10 FILLER                      PIC X(08) VALUE "COTRN02C".
      10 FILLER                      PIC X(01) VALUE "U".
      10 FILLER                      PIC 9(02) VALUE 9.
      10 FILLER                      PIC X(35) VALUE
         "Transaction Reports                ".
      10 FILLER                      PIC X(08) VALUE "CORPT00C".
      10 FILLER                      PIC X(01) VALUE "U".
      10 FILLER                      PIC 9(02) VALUE 10.
      10 FILLER                      PIC X(35) VALUE
         "Bill Payment                       ".
      10 FILLER                      PIC X(08) VALUE "COBIL00C".
      10 FILLER                      PIC X(01) VALUE "U".
      10 FILLER                      PIC 9(02) VALUE 11.
      10 FILLER                      PIC X(35) VALUE
         "Pending Authorization View         ".
      10 FILLER                      PIC X(08) VALUE "COPAUS0C".
      10 FILLER                      PIC X(01) VALUE "U".
   05 CDEMO-MENU-OPTIONS REDEFINES CDEMO-MENU-OPTIONS-DATA.
      10 CDEMO-MENU-OPT OCCURS 11 TIMES.
         15 CDEMO-MENU-OPT-NUM       PIC 9(02).
         15 CDEMO-MENU-OPT-NAME      PIC X(35).
         15 CDEMO-MENU-OPT-PGMNAME   PIC X(08).
         15 CDEMO-MENU-OPT-USRTYPE   PIC X(01).

LINKAGE SECTION.
01 CARDDEMO-COMMAREA.
   05 CDEMO-GENERAL-INFO.
      10 CDEMO-FROM-TRANID             PIC X(04).
      10 CDEMO-FROM-PROGRAM            PIC X(08).
      10 CDEMO-TO-TRANID               PIC X(04).
      10 CDEMO-TO-PROGRAM              PIC X(08).
      10 CDEMO-USER-ID                 PIC X(08).
      10 CDEMO-USER-TYPE               PIC X(01).
         88 CDEMO-USRTYP-ADMIN         VALUE "A".
         88 CDEMO-USRTYP-USER          VALUE "U".
      10 CDEMO-PGM-CONTEXT             PIC 9(01).
         88 CDEMO-PGM-ENTER            VALUE 0.
         88 CDEMO-PGM-REENTER          VALUE 1.
   05 CDEMO-CUSTOMER-INFO.
      10 CDEMO-CUST-ID                 PIC 9(09).
      10 CDEMO-CUST-FNAME              PIC X(25).
      10 CDEMO-CUST-MNAME              PIC X(25).
      10 CDEMO-CUST-LNAME              PIC X(25).
   05 CDEMO-ACCOUNT-INFO.
      10 CDEMO-ACCT-ID                 PIC 9(11).
      10 CDEMO-ACCT-STATUS             PIC X(01).
   05 CDEMO-CARD-INFO.
      10 CDEMO-CARD-NUM                PIC 9(16).
   05 CDEMO-MORE-INFO.
      10 CDEMO-LAST-MAP                PIC X(07).
      10 CDEMO-LAST-MAPSET             PIC X(07).

PROCEDURE DIVISION USING CARDDEMO-COMMAREA.
MAIN-PARA.
    SET MENU-ACTIVE TO TRUE

    PERFORM UNTIL MENU-DONE
        PERFORM DISPLAY-MENU
        DISPLAY "Select option (0 to exit): " WITH NO ADVANCING
        ACCEPT WS-CHOICE-TEXT
        MOVE 0 TO WS-CHOICE
        IF FUNCTION TRIM(WS-CHOICE-TEXT) NOT = SPACES
            COMPUTE WS-CHOICE = FUNCTION NUMVAL(FUNCTION TRIM(WS-CHOICE-TEXT))
        END-IF
        PERFORM HANDLE-CHOICE
    END-PERFORM

    GOBACK.

DISPLAY-MENU.
    DISPLAY SPACE
    DISPLAY "CardDemo GNUCobol User Menu"
    DISPLAY "Signed in as: " CDEMO-USER-ID
    IF WS-MESSAGE NOT = SPACES
        DISPLAY WS-MESSAGE
        MOVE SPACES TO WS-MESSAGE
    END-IF
    PERFORM VARYING WS-IDX FROM 1 BY 1 UNTIL WS-IDX > CDEMO-MENU-OPT-COUNT
        DISPLAY CDEMO-MENU-OPT-NUM(WS-IDX) ". "
            FUNCTION TRIM(CDEMO-MENU-OPT-NAME(WS-IDX))
    END-PERFORM
    DISPLAY "0. Exit".

HANDLE-CHOICE.
    EVALUATE WS-CHOICE
        WHEN 0
            SET MENU-DONE TO TRUE
        WHEN 1
            CALL "COACTVWC" USING CARDDEMO-COMMAREA
        WHEN 2
            CALL "COACTUPC" USING CARDDEMO-COMMAREA
        WHEN 3
            CALL "COCRDLIC" USING CARDDEMO-COMMAREA
        WHEN 4
            CALL "COCRDSLC" USING CARDDEMO-COMMAREA
        WHEN 5
            CALL "COCRDUPC" USING CARDDEMO-COMMAREA
        WHEN 6
            CALL "COTRN00C" USING CARDDEMO-COMMAREA
        WHEN 7
            CALL "COTRN01C" USING CARDDEMO-COMMAREA
        WHEN 8
            CALL "COTRN02C" USING CARDDEMO-COMMAREA
        WHEN 9
            CALL "CORPT00C" USING CARDDEMO-COMMAREA
        WHEN 10
            CALL "COBIL00C" USING CARDDEMO-COMMAREA
        WHEN 11
            STRING "Option not yet ported from CICS: "
                FUNCTION TRIM(CDEMO-MENU-OPT-NAME(WS-CHOICE))
                DELIMITED BY SIZE
                INTO WS-MESSAGE
        WHEN OTHER
            MOVE "Please enter a valid option number." TO WS-MESSAGE
    END-EVALUATE.
