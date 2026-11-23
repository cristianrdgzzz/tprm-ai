"""Non-NER Spanish enterprise recognizers (tax ID, phone, email, IBAN)."""

from __future__ import annotations

import string
from typing import List, Optional, Tuple

import tldextract

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer

NIF_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
CIF_CONTROL_LETTERS = "JABCDEFGHI"
CIF_NUMERIC_CONTROL_TYPES = frozenset("NPQRSW")
CIF_ORGANIZATION_LETTERS = frozenset("ABCDEFGHJNPQRSUVW")

IBAN_LETTERS = {
    ord(char): str(index)
    for index, char in enumerate(string.digits + string.ascii_uppercase)
}


class EsSpanishTaxIdRecognizer(PatternRecognizer):
    """Detect and validate Spanish NIF, NIE, and CIF tax identifiers."""

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern(
            "Spanish tax ID (NIF/NIE/CIF)",
            r"\b(?:[0-9]{8}[-\s]?[A-Z]|[XYZ][-\s]?[0-9]{7}[-\s]?[A-Z]"
            r"|[A-HJ-NP-SUVW][-\s]?[0-9]{7}[-\s]?[0-9A-J])\b",
            0.55,
        ),
    ]

    CONTEXT = [
        "cif",
        "nif",
        "nie",
        "dni",
        "número de identificación fiscal",
        "identificación fiscal",
        "documento nacional de identidad",
        "identificación",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "CIF",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = replacement_pairs or [("-", ""), (" ", "")]
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns or self.PATTERNS,
            context=context or self.CONTEXT,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        normalized = EntityRecognizer.sanitize_value(pattern_text, self.replacement_pairs)
        if len(normalized) != 9:
            return False
        if normalized[0].isdigit():
            return _validate_nif(normalized)
        if normalized[0] in "XYZ":
            return _validate_nie(normalized)
        return _validate_cif(normalized)


class EsSpanishPhoneRecognizer(PatternRecognizer):
    """Detect Spanish phone numbers (+34 prefix or 9-digit national format)."""

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern(
            "Spanish phone with country code",
            r"\b(?:\+34|0034)[\s.\-]?(?:[67]\d{2}|[89]\d{2})[\s.\-]?\d{3}[\s.\-]?\d{3}\b",
            0.6,
        ),
        Pattern(
            "Spanish phone national",
            r"\b(?:[67]\d{2}|[89]\d{2})[\s.\-]?\d{3}[\s.\-]?\d{3}\b",
            0.5,
        ),
    ]

    CONTEXT = [
        "teléfono",
        "telefono",
        "móvil",
        "movil",
        "celular",
        "llamar",
        "contacto",
        "phone",
        "mobile",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "PHONE",
        name: Optional[str] = None,
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns or self.PATTERNS,
            context=context or self.CONTEXT,
            supported_language=supported_language,
            name=name,
        )


class EsSpanishEmailRecognizer(PatternRecognizer):
    """Detect email addresses with TLD validation for Spanish enterprise documents."""

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern(
            "Email (robust)",
            r"\b((([!#$%&'*+\-/=?^_`{|}~\wÁÉÍÓÚÜÑáéíóúüñ])|"
            r"([!#$%&'*+\-/=?^_`{|}~\wÁÉÍÓÚÜÑáéíóúüñ]"
            r"[!#$%&'*+\-/=?^_`{|}~\.\wÁÉÍÓÚÜÑáéíóúüñ]{0,}"
            r"[!#$%&'*+\-/=?^_`{|}~\wÁÉÍÓÚÜÑáéíóúüñ]))"
            r"[@]\w+([-.]\w+)*\.\w{2,}([-.]\w+)*)\b",
            0.6,
        ),
    ]

    CONTEXT = ["email", "correo", "e-mail", "mail", "correo electrónico"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "EMAIL",
        name: Optional[str] = None,
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns or self.PATTERNS,
            context=context or self.CONTEXT,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        result = tldextract.extract(pattern_text)
        return bool(result.domain and result.suffix)


class EsSpanishIbanRecognizer(PatternRecognizer):
    """Detect and validate Spanish IBAN codes (ES + 22 digits)."""

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern(
            "Spanish IBAN",
            r"(?<![A-Z0-9])(ES[\s\-]?[0-9]{2}[\s\-]?(?:[0-9]{4}[\s\-]?){4}[0-9]{4})"
            r"(?![A-Z0-9])",
            0.55,
        ),
    ]

    CONTEXT = ["iban", "cuenta", "banco", "transferencia", "ccc", "entidad"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "IBAN",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = replacement_pairs or [("-", ""), (" ", "")]
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns or self.PATTERNS,
            context=context or self.CONTEXT,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        normalized = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        ).upper()
        if len(normalized) != 24 or not normalized.startswith("ES"):
            return False
        if not normalized[4:].isdigit():
            return False
        return _generate_iban_check_digits(normalized) == normalized[2:4]


def _validate_nif(nif: str) -> bool:
    number = int(nif[:8])
    return nif[8] == NIF_LETTERS[number % 23]


def _validate_nie(nie: str) -> bool:
    if nie[1:8].isdigit() is False:
        return False
    number = int(str("XYZ".index(nie[0])) + nie[1:8])
    return nie[8] == NIF_LETTERS[number % 23]


def _validate_cif(cif: str) -> bool:
    if cif[0] not in CIF_ORGANIZATION_LETTERS:
        return False
    digits = cif[1:8]
    if not digits.isdigit():
        return False

    control = cif[8]
    sum_even = sum(int(digit) for digit in digits[1::2])
    sum_odd = 0
    for digit in digits[0::2]:
        doubled = int(digit) * 2
        sum_odd += doubled - 9 if doubled > 9 else doubled
    control_digit = (10 - ((sum_even + sum_odd) % 10)) % 10

    if cif[0] in CIF_NUMERIC_CONTROL_TYPES:
        return control == str(control_digit)
    return control == CIF_CONTROL_LETTERS[control_digit]


def _generate_iban_check_digits(iban: str) -> str:
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(IBAN_LETTERS[ord(char)] for char in rearranged)
    remainder = int(numeric[0])
    for digit in numeric[1:]:
        remainder = (remainder * 10 + int(digit)) % 97
    check_digits = 98 - remainder
    return f"{check_digits:02d}"
