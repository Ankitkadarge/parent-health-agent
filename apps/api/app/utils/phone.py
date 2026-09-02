import phonenumbers


class InvalidPhoneNumberError(ValueError):
    pass


def to_e164(raw_number: str, default_region: str = "IN") -> str:
    """Parse a phone number and return it in E.164 format."""
    try:
        parsed = phonenumbers.parse(raw_number, default_region)
    except phonenumbers.NumberParseException as exc:
        raise InvalidPhoneNumberError(
            "Enter a valid WhatsApp phone number."
        ) from exc

    if not phonenumbers.is_valid_number(parsed):
        raise InvalidPhoneNumberError(
            "Enter a valid WhatsApp phone number."
        )

    return phonenumbers.format_number(
        parsed,
        phonenumbers.PhoneNumberFormat.E164,
    )
