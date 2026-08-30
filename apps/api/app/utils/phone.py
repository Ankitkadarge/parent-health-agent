import phonenumbers


class InvalidPhoneNumberError(ValueError):
    pass


def to_e164(raw_number: str, default_region: str = "IN") -> str:
    """Parse a phone number and return it in E.164 format (e.g. +919876543210).

    default_region is used only when raw_number has no country code.
    """
    try:
        parsed = phonenumbers.parse(raw_number, default_region)
    except phonenumbers.NumberParseException as exc:
        raise InvalidPhoneNumberError(f"Could not parse phone number: {raw_number}") from exc

    if not phonenumbers.is_valid_number(parsed):
        raise InvalidPhoneNumberError(f"Not a valid phone number: {raw_number}")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
