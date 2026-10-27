"""Demo on fake specimen documents: python demo.py

1. render specimen KYC images (all fake, all watermarked)
2. OCR them (tesseract by default; set OCR_ENGINE=google to use Google Vision like the original)
3. classify document type, extract fields, validate, and route each operator's record
"""
import os
import random

import pandas as pd
from PIL import Image

from kyc_ocr import parsers as P
from kyc_ocr.ocr import get_engine, hconcat_resize_min
from kyc_ocr.specimen import render, texts

random.seed(42)
pd.set_option('display.width', 200)
out_dir = 'outputs/specimens'
os.makedirs(out_dir, exist_ok=True)
ocr = get_engine()

KINDS = {'aadhaar_front': ('front', 'Aadhar'), 'aadhaar_back': ('back', 'Aadhar'), 'pan': ('front', ''),
         'voter': ('front', 'Voter'), 'driving': ('front', 'Driving'), 'cash_slip': ('front', ''), 'other': ('front', '')}
N = 15

print("=== 1-2. Render and OCR specimen documents ===")
docs = []
for kind in KINDS:
    for i in range(N):
        lines, truth = texts(kind, i)
        path = render(lines, f'{out_dir}/{kind}_{i:02d}.png')
        docs.append({'kind': kind, 'i': i, 'path': path, 'truth': truth, 'text': ocr(path)})
print(f"{len(docs)} images OCR'd")

print("\n=== 3a. Document type check (keyword rules from the original) ===")
for d in docs:
    side, expected = KINDS[d['kind']]
    d['doc_type'] = P.check_doc_front(d['text']) if side == 'front' else P.check_doc_back(d['text'])
    d['type_ok'] = d['doc_type'] == expected
t = pd.DataFrame(docs)
print(t.groupby('kind').type_ok.mean().round(2).to_string())
slips = t[t.kind.isin(['cash_slip', 'other', 'aadhaar_front'])].copy()
slips['looks_like_toll_slip'] = slips.text.apply(lambda x: all(P.cashslip_check(x).values()))
print("\nCash-slip check (all of Vehicle / High / Jou present):")
print(slips.groupby('kind').looks_like_toll_slip.mean().round(2).to_string())

print("\n=== 3b. Field extraction ===")
rows = []
for d in docs:
    if d['kind'] == 'aadhaar_front':
        got = P.adhaar_card(d['text'])
    elif d['kind'] == 'aadhaar_back':
        got = P.back_adhaar(d['text'])
    elif d['kind'] == 'pan':
        got = P.front_pan_card(d['text'])
        alt = P.pan_from_text(d['text'])
        rows.append({'doc': 'pan', 'field': 'pan_number (shape regex, added)',
                     'correct': alt['pan_number'] == d['truth']['pan_number']})
    else:
        continue
    for field, true_val in d['truth'].items():
        name = field + (' (original rule)' if d['kind'] == 'pan' and field == 'pan_number' else '')
        rows.append({'doc': d['kind'], 'field': name, 'correct': got.get(field) == true_val})
f = pd.DataFrame(rows)
print(f.groupby(['doc', 'field']).correct.mean().round(2).to_string())

print("\n=== 3c. Validate and route each operator ===")
by = {(d['kind'], d['i']): d for d in docs}
recs = []
for i in range(N):
    a = P.adhaar_card(by[('aadhaar_front', i)]['text'])
    b = P.back_adhaar(by[('aadhaar_back', i)]['text'])
    p = P.pan_from_text(by[('pan', i)]['text'])
    recs.append({'operator': f'SAMPLE-{i:03d}',
                 'aadhaar_masked': P.mask_aadhaar(a['aadhaar_number']),
                 'aadhaar_checksum_ok': P.aadhaar_ok(a['aadhaar_number']),
                 'pan': p['pan_number'], 'pan_format_ok': P.pan_ok(p['pan_number']),
                 'route': P.route_record(a['aadhaar_number'], p['pan_number'], b['pincode'])})
r = pd.DataFrame(recs)
print(r.to_string(index=False))
print(f"\nsent to bank: {(r.route == 'send_to_bank').mean():.0%}   manual review: {(r.route == 'manual_review').mean():.0%}")
r.to_csv('outputs/kyc_routing.csv', index=False)

stitched = hconcat_resize_min([Image.open(by[('aadhaar_front', 0)]['path']), Image.open(by[('aadhaar_back', 0)]['path'])])
stitched.save('outputs/stitched_front_back.png')
print("\nImages in outputs/specimens, stitched example in outputs/stitched_front_back.png")
