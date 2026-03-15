"""
IMO number validation (checksum).
IMO ship number: 7 digits, last digit is check digit.
Check digit = (d1*7 + d2*6 + d3*5 + d4*4 + d5*3 + d6*2) % 10.
Ref: https://en.wikipedia.org/wiki/IMO_number
"""


def is_valid_imo(imo) -> bool:
    """Return True if the IMO number has a valid 7-digit structure and checksum."""
    if imo is None or (isinstance(imo, float) and (imo != imo or imo != int(imo))):
        return False
    s = str(int(imo)).strip()
    if len(s) != 7:
        return False
    digits = [int(c) for c in s]
    weights = (7, 6, 5, 4, 3, 2)
    check = sum(d * w for d, w in zip(digits[:6], weights)) % 10
    return digits[6] == check


if __name__ == "__main__":
    assert is_valid_imo(9074729)
    assert not is_valid_imo(1000000)
    assert not is_valid_imo(0)
    assert not is_valid_imo(1234560)  # wrong check digit
    print("IMO validation tests passed.")
