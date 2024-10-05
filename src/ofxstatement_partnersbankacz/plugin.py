import csv
from datetime import datetime

from ofxstatement import statement
from ofxstatement.plugin import Plugin
from ofxstatement.parser import CsvStatementParser

class PartnersbankaczPlugin(Plugin):
    """Partners Banka, a.s. (Czech Republic) (CSV, UTF-8 - exported from mobile app)
    """

    def get_parser(self, filename):
        PartnersbankaczPlugin.encoding = self.settings.get('charset', 'utf-8')
        f = open(filename, "r", encoding=PartnersbankaczPlugin.encoding)
        parser = PartnersbankaczParser(f)
        parser.statement.currency = self.settings.get('currency', 'CZK')
        parser.statement.bank_id = self.settings.get('bank', 'PTBNCZPP')
        parser.statement.account_id = self.settings.get('account', '')
        parser.statement.account_type = self.settings.get('account_type', 'CHECKING')
        parser.statement.trntype = "OTHER"
        return parser

class PartnersbankaczParser(CsvStatementParser):

    date_format = '%d. %m. %Y'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.columns = None
        self.mappings = None

    def split_records(self):
        """Return iterable object consisting of a line per transaction
        """
        # Field delimiter may be dependent on user settings in mobile App (English/Czech)
        return csv.reader(self.fin, delimiter=';', quotechar='"')

    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object
        """

        # First line of CSV file contains headers, not an actual transaction
        if self.cur_record == 1:
            # Prepare columns headers lookup table for parsing
            self.columns = {v: i for i,v in enumerate(line)}
            self.mappings = {
                "date": self.columns['Datum provedení'],
                "memo": self.columns['Zpráva pro příjemce'],
                "payee": self.columns['Název protistrany'],
                "check_no": self.columns['Variabilní symbol'],
                "refnum": self.columns['Identifikace transakce'],
            }
            # And skip further processing by parser
            return None

        # Shortcut
        columns = self.columns

        # Normalize string. Better safe than sorry.
        for i,v in enumerate(line):
            line[i] = v.strip()

        # Convert numbers - thousands delimiter (special char: " " = "\xa") and decimal point
        if line[columns["Částka"]] != '':
            line[columns["Částka"]] = float(line[columns["Částka"]].replace(' ', '').replace(',', '.'))
            if line[columns["Směr úhrady"]] == 'Odchozí':
                line[columns["Částka"]] = -abs(line[columns["Částka"]])

        if line[columns["Původní částka úhrady"]] != '':
            line[columns["Původní částka úhrady"]] = float(line[columns["Původní částka úhrady"]].replace(' ', '').replace(',', '.'))

        StatementLine = super(PartnersbankaczParser, self).parse_record(line)

        StatementLine.amount = line[columns["Částka"]]

        # Ignore lines, which do not have a posting date yet (typically pmts by debit cards are processed with a delay)
        if not line[columns["Datum zúčtování"]]:
            return None
        else:
            StatementLine.date_user = line[columns["Datum zúčtování"]]
            StatementLine.date_user = datetime.strptime(StatementLine.date_user, self.date_format)

        StatementLine.id = statement.generate_transaction_id(StatementLine)

        # Manually set some of the typical transaction types.
        # EDIT: the bank is new, many types may be missing.
        payment_type = line[columns["Typ úhrady"]]
        if payment_type.startswith("Daň z úroku"):
            StatementLine.trntype = "DEBIT"
        elif payment_type.startswith("Úroky"):
            StatementLine.trntype = "INT"
        elif payment_type.startswith("Příchozí platba"):
            StatementLine.trntype = "XFER"
        elif payment_type.startswith("Odchozí platba"):
            StatementLine.trntype = "XFER"
        elif payment_type.startswith("Platba kartou"):
            StatementLine.trntype = "POS"
        else:
            print("WARN: Unexpected type of payment appeared - \"{}\". Using XFER transaction type instead".format(payment_type))
            print("      Kindly inform the developer at https://github.com/archont00/ofxstatement-partnersbankacz/issues")
            StatementLine.trntype = "XFER"

        # .payee becomes OFX.NAME which becomes "Description" in GnuCash
        # .memo  becomes OFX.MEMO which becomes "Notes"       in GnuCash
        # When .payee is empty, GnuCash imports .memo to "Description" and keeps "Notes" empty

        # StatementLine.payee = "Název protistrany" + "Číslo účtu protistrany" + "Kód banky protistrany" + "IBAN protistrany"

        if StatementLine.payee == "":
            separator = ""
        else:
            separator = "|"

        if line[columns["Číslo účtu protistrany"]] != "":
            StatementLine.payee += separator + "ÚČ: " + line[columns["Číslo účtu protistrany"]]
            separator = "|"

        if line[columns["Kód banky protistrany"]] != "":
            StatementLine.payee += "/" + line[columns["Kód banky protistrany"]]
            separator = "|"

        if line[columns["IBAN protistrany"]] != "":
            StatementLine.payee += separator + "IBAN " + line[columns["IBAN protistrany"]]

        # StatementLine.memo: include other useful info, if available. Need to include also "Typ úhrady" as for saving account,
        # the "memo" is empty

        if StatementLine.memo == "":
            separator = ""
        else:
            separator = "|"

        if line[columns["Poznámka pro mě"]] != "" and line[columns["Poznámka pro mě"]] != line[columns["Zpráva pro příjemce"]]:
            StatementLine.memo += separator + line[columns["Poznámka pro mě"]]
            separator = "|"

        if line[columns["Variabilní symbol"]] != "":
            StatementLine.memo += separator + "VS: " + line[columns["Variabilní symbol"]]
            separator = "|"

        if line[columns["Konstantní symbol"]] != "":
            StatementLine.memo += separator + "KS: " + line[columns["Konstantní symbol"]]
            separator = "|"

        if line[columns["Specifický symbol"]] != "":
            StatementLine.memo += separator + "SS: " + line[columns["Specifický symbol"]]
            separator = "|"

        if line[columns["Držitel karty"]] != "":
            StatementLine.memo += separator + "Držitel karty: " + line[columns["Držitel karty"]]
            separator = "|"

        if line[columns["Číslo karty"]] != "":
            StatementLine.memo += separator + "Číslo karty: " + line[columns["Číslo karty"]]
            separator = "|"

        if line[columns["Původní měna úhrady"]] != line[columns["Měna"]] and line[columns["Původní měna úhrady"]] != "":
            StatementLine.memo += separator + "Původní měna: " + line[columns["Původní částka úhrady"]] + line[columns["Původní měna úhrady"]]
            separator = "|"

        if line[columns["Typ úhrady"]] != '':
           StatementLine.memo += separator + line[columns["Typ úhrady"]]

        return StatementLine
