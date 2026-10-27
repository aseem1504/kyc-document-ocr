from kyc_ocr import parsers as P


def test_aadhaar_fields():
    t = 'Government of India\nSAMPLE PERSON 1\nDOB: 01/02/1990\nMale\n0123 4567 8901'
    assert P.adhaar_card(t) == {'aadhaar_number': '0123 4567 8901', 'dob': '01/02/1990', 'gender': 'Male'}


def test_verhoeff_and_mask():
    body = '01234567890'
    n = body + P.verhoeff_check_digit(body)
    assert P.aadhaar_ok(n) and not P.aadhaar_ok(n[:-1] + str((int(n[-1]) + 1) % 10))
    assert P.mask_aadhaar(n) == 'XXXX XXXX ' + n[-4:]


def test_pan_rules():
    t = 'INCOME TAX DEPARTMENT\n\nPermanent Account Number\n\nXXAPB1234C\n'
    assert P.front_pan_card(t)['pan_number'] == ''          # original rule trips on blank lines
    assert P.pan_from_text(t)['pan_number'] == 'XXAPB1234C'
    assert P.pan_ok('XXAPB1234C') and not P.pan_ok('XXAPB12345')


def test_doc_type():
    assert P.check_doc_front('Election Commission of India') == 'Voter'
    assert P.check_doc_front('Union of India Driving Licence') == 'Driving'
    assert P.check_doc_back('Unique Identification Authority') == 'Aadhar'
    assert P.check_doc_front('random text') == ''
