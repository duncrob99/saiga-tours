from typing import Tuple
from re import match

def join_phone_number(code: str, number: str) -> str:
    if code == "" and number == "":
        return ""
    phone_number = f"+{code}\u202F{number}"
    if not is_phone_number(phone_number):
        raise ValueError(f"Invalid phone number: {phone_number}")
    return phone_number

def is_phone_number(phone_number: str) -> bool:
    # Very permissive check, just sufficient that it starts with + and has a \u202F split before the number
    return match(r"\+\d+\u202F\d+", phone_number) is not None

def split_phone_number(phone_number: str) -> Tuple[str, str]:
    if phone_number == "":
        return "", ""
    if not is_phone_number(phone_number):
        raise ValueError(f"Invalid phone number: {phone_number}")
    raw_split = phone_number.split("\u202F")
    code = raw_split[0][1:]
    number = raw_split[1]
    return code, number

