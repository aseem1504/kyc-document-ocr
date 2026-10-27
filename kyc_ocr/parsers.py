"""Pull fields out of OCR text from Indian KYC documents, then decide what to do with the record.

Ported from:
  notebooks/original/01_kyc_image_ocr_google_vision.ipynb   -> adhaar_card, front_pan_card, back_adhaar
  notebooks/original/03_doc_type_classifier_aadhaar_dl_voter -> check_doc_front / check_doc_back
  notebooks/original/06_cash_slip_ocr_testing.ipynb         -> cashslip_check
  notebooks/original/07_ocr_vendor_response_handling.ipynb  -> route_record

In the original, each function called Google Vision itself. Here they take the OCR text, so
any OCR engine can feed them (see ocr.py). Regexes and keyword rules are unchanged.

Fixes:
  * front_pan_card crashed when no "Account Number" line was found, and only looked for the
    date of birth on the last line of text; both fixed
  * the doc-type check returned an unbound variable when no keyword matched; now returns ''

Added (not in the original):
  * Verhoeff checksum for Aadhaar numbers and a format check for PAN
  * mask_aadhaar, so only the last 4 digits are ever stored or shown
"""
import re

# ---------- Aadhaar ----------

def adhaar_card(text):
    try:
        adhaar_number = re.findall(r'(\d\d\d\d \d\d\d\d \d\d\d\d)', text)[0]
    except IndexError:
        adhaar_number = None
    try:
        DOB = re.findall(r'(\d\d/\d\d/\d\d\d\d)', text)[0]
    except IndexError:
        DOB = None
    try:
        male_female = re.findall(r'(Male|Female|MALE|FEMALE)', text)[0]
    except IndexError:
        male_female = None
    return {'aadhaar_number': adhaar_number, 'dob': DOB, 'gender': male_female}


def back_adhaar(text):
    try:
        phone_number = re.findall(r'\d\d\d\d\d\d\d\d\d\d', text)[0]
    except IndexError:
        phone_number = None
    pin = re.findall(r'\b(\d{6})\b', text)
    return {'phone_number': phone_number, 'pincode': pin[-1] if pin else None}


# ---------- PAN ----------

def front_pan_card(text):
    lines = text.splitlines()
    PAN_NUMBER = None
    for count, line in enumerate(lines, start=1):
        if re.findall(r'count|rmanent|Account|Number|umber', line) and count < len(lines):
            PAN_NUMBER = lines[count].strip()  # the line right after the label
    m = re.findall(r'\d\d/\d\d/\d\d\d\d', text)
    return {'pan_number': PAN_NUMBER, 'dob': m[0] if m else None}


def pan_from_text(text):
    """Added variant: find the PAN by its shape anywhere in the text. The original
    'line after the label' rule was tuned to Google Vision, which returns no blank lines.
    Tesseract puts a blank line between blocks, and the original rule then reads ''."""
    out = front_pan_card(text)
    m = re.findall(r'\b[A-Z]{5}\d{4}[A-Z]\b', text)
    if m:
        out['pan_number'] = m[-1]
    return out


# ---------- which document is this? ----------

FRONT_KEYS = [('Government', 'Government', 'Aadhar'), ('Election', 'Commission', 'Voter'), ('Driving', 'Licence', 'Driving')]
BACK_KEYS = [('Unique', 'Identification', 'Aadhar'), ('Election', 'Commission', 'Voter'), ('Driving', 'Licence', 'Driving')]


def _detect(text, keys):
    t = text.lower()
    hits = {label: (k.lower() in t and v.lower() in t) for k, v, label in keys}
    rvt = ''
    # same precedence as the original: Voter, then Driving, then Aadhar overrides
    if hits['Voter']:
        rvt = 'Voter'
    if hits['Driving']:
        rvt = 'Driving'
    if hits['Aadhar']:
        rvt = 'Aadhar'
    return rvt


def check_doc_front(text):
    return _detect(text, FRONT_KEYS)


def check_doc_back(text):
    return _detect(text, BACK_KEYS)


# ---------- toll cash slip ----------

def cashslip_check(text, words=('Vehicle', 'High', 'Jou')):
    """Is this upload really a toll receipt? The original checked for these word stems
    (Vehicle, Highway, Journey) through an internal OCR service."""
    t = text.lower()
    return {w: (w.lower() in t) for w in words}


# ---------- validation (added) ----------

_d = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
      [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
      [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
      [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_p = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
      [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
      [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]
_inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_check_digit(num):
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _d[c][_p[(i + 1) % 8][int(ch)]]
    return str(_inv[c])


def verhoeff_ok(num):
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _d[c][_p[i % 8][int(ch)]]
    return c == 0


def aadhaar_ok(number):
    n = re.sub(r'\s', '', number or '')
    return len(n) == 12 and n.isdigit() and verhoeff_ok(n)


def pan_ok(pan):
    return bool(re.fullmatch(r'[A-Z]{5}\d{4}[A-Z]', (pan or '').strip()))


def mask_aadhaar(number):
    n = re.sub(r'\s', '', number or '')
    return 'XXXX XXXX ' + n[-4:] if len(n) == 12 else None


def route_record(aadhaar_number, pan_number, address):
    """Same split as the original: complete records go to the bank, the rest to manual review.
    The original only checked lengths; checksum and PAN format checks are added here."""
    if aadhaar_ok(aadhaar_number) and pan_ok(pan_number) and address:
        return 'send_to_bank'
    return 'manual_review'
