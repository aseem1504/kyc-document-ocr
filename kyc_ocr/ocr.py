"""OCR backends and the front/back image stitcher.

google_vision_text: the engine the original notebooks used (needs google-cloud-vision and
                    GOOGLE_APPLICATION_CREDENTIALS). Optional.
tesseract_text:     free local engine, used by the demo.
"""
import os


def google_vision_text(path_or_url):
    from google.cloud import vision
    import urllib.request
    client = vision.ImageAnnotatorClient()
    if path_or_url.startswith('http'):
        content = urllib.request.urlopen(path_or_url).read()
    else:
        content = open(path_or_url, 'rb').read()
    response = client.text_detection(image=vision.Image(content=content))
    return response.text_annotations[0].description if response.text_annotations else ''


def tesseract_text(path):
    import pytesseract
    from PIL import Image
    return pytesseract.image_to_string(Image.open(path))


def get_engine(name=None):
    name = name or os.environ.get('OCR_ENGINE', 'tesseract')
    return {'google': google_vision_text, 'tesseract': tesseract_text}[name]


def hconcat_resize_min(im_list):
    """Put the front and back of a card side by side at the same height, so a vendor OCR
    that bills per image reads both sides in one call (from 04_download_and_stitch...).
    The original used cv2.hconcat; PIL gives the same result with one less dependency."""
    from PIL import Image
    h_min = min(im.height for im in im_list)
    resized = [im.resize((int(im.width * h_min / im.height), h_min)) for im in im_list]
    out = Image.new('RGB', (sum(im.width for im in resized), h_min), 'white')
    x = 0
    for im in resized:
        out.paste(im, (x, 0))
        x += im.width
    return out
