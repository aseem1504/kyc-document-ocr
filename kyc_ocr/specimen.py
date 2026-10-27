"""Make fake, clearly labelled specimen documents for testing.

Every image carries a red "SPECIMEN - NOT A REAL DOCUMENT" banner. These are plain text
cards, not copies of any real card design. Numbers are invalid on purpose:
  * Aadhaar-style numbers start with 0 or 1, which UIDAI never issues
  * phone numbers start with 0, which no Indian mobile number does
  * names are "SAMPLE PERSON <n>"
"""
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .parsers import verhoeff_check_digit

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def _font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def fake_aadhaar(valid_checksum=True):
    body = str(random.randint(0, 1)) + ''.join(random.choice('0123456789') for _ in range(10))
    last = verhoeff_check_digit(body) if valid_checksum else str((int(verhoeff_check_digit(body)) + 1) % 10)
    n = body + last
    return f"{n[:4]} {n[4:8]} {n[8:]}"


def fake_pan():
    L = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    return 'XX' + random.choice(L) + 'P' + random.choice(L) + f"{random.randint(0, 9999):04d}" + random.choice(L)


def fake_dob():
    return f"{random.randint(1, 28):02d}/{random.randint(1, 12):02d}/{random.randint(1965, 2000)}"


def texts(kind, i):
    name = f"SAMPLE PERSON {i}"
    if kind == 'aadhaar_front':
        truth = {'aadhaar_number': fake_aadhaar(random.random() > 0.1), 'dob': fake_dob(),
                 'gender': random.choice(['Male', 'Female'])}
        lines = ['Government of India', name, f"DOB: {truth['dob']}", truth['gender'], '', truth['aadhaar_number']]
    elif kind == 'aadhaar_back':
        truth = {'phone_number': '0' + ''.join(random.choice('0123456789') for _ in range(9)),
                 'pincode': f"{random.randint(110001, 855999)}"}
        lines = ['Unique Identification Authority of India', 'Address:', f'{i} Sample Street, Test Nagar',
                 f"Sample City - {truth['pincode']}", f"Mobile: {truth['phone_number']}"]
    elif kind == 'pan':
        truth = {'pan_number': fake_pan(), 'dob': fake_dob()}
        lines = ['INCOME TAX DEPARTMENT', name, f'SAMPLE FATHER {i}', truth['dob'],
                 'Permanent Account Number', truth['pan_number']]
    elif kind == 'voter':
        truth = {}
        lines = ['Election Commission of India', 'Elector Photo Identity Card', name, f'XX{random.randint(1000000, 9999999)}']
    elif kind == 'driving':
        truth = {}
        lines = ['Union of India', 'Driving Licence', name, f'DL No: XX01 {random.randint(10**10, 10**11 - 1)}']
    elif kind == 'cash_slip':
        truth = {}
        lines = ['National Highway Toll Plaza', f'Vehicle No: XX01XX{random.randint(1000, 9999)}',
                 'Journey: Single', f'Amount: Rs {random.choice([65, 135, 215, 455])}']
    else:  # a random photo that is not a document
        truth = {}
        lines = ['Blurry photo of a truck dashboard']
    return lines, truth


def render(lines, path, rotate=True, blur=True):
    img = Image.new('RGB', (900, 520), (248, 248, 244))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 900, 46], fill=(200, 30, 30))
    d.text((20, 8), 'SPECIMEN - NOT A REAL DOCUMENT', font=_font(26), fill='white')
    y = 80
    for ln in lines:
        d.text((40, y), ln, font=_font(32), fill=(20, 20, 20))
        y += 62
    if rotate:
        img = img.rotate(random.uniform(-2.5, 2.5), expand=True, fillcolor=(248, 248, 244))
    if blur and random.random() < 0.4:
        img = img.filter(ImageFilter.GaussianBlur(random.uniform(0.6, 1.4)))
    img.save(path)
    return path
