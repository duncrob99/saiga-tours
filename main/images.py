from typing import Callable

from PIL import Image
from django.http import HttpResponse
from ua_parser import user_agent_parser


def crop_center(pil_img: Image.Image, crop_width: int, crop_height: int) -> Image.Image:
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))


def crop_to_ar(image: Image.Image, ar: float) -> Image.Image:
    (old_width, old_height) = image.size

    original_ar = old_width / old_height

    if ar > original_ar:
        crop_height = int(old_width / ar)
        crop_width = old_width
    elif ar < original_ar:
        crop_width = int(old_height * ar)
        crop_height = old_height
    else:
        return image

    return crop_center(image, crop_width, crop_height)


def crop_to_dims(image: Image.Image, width: int, height: int) -> Image.Image:
    if width is not None or height is not None:
        (old_width, old_height) = image.size
        old_ar = old_width / old_height

        if height != 0 and width != 0:
            ar = width / height
            image = crop_to_ar(image, ar)
        elif height == 0 and width != 0:
            height = int(width / old_ar)
        elif width == 0 and height != 0:
            width = int(height * old_ar)
        else:  # Don't crop if dims are 0x0
            width = old_width
            height = old_height

        image = image.resize((width, height))

    return image


def autorotate(img: Image.Image) -> Image.Image:
    """
    Rotate a Pillow image based on exif data.
    Returns new Pillow image.
    """
    exif = img.getexif()
    orientation_key = 274

    if exif and orientation_key in exif:
        orientation = exif[orientation_key]

        rotate_values = {
            3: Image.Transpose.ROTATE_180,
            6: Image.Transpose.ROTATE_270,
            8: Image.Transpose.ROTATE_90
        }

        if orientation in rotate_values:
            img = img.transpose(rotate_values[orientation])

    return img


def browser_supports_webp(request) -> bool:
    """Check if browser is Safari <16 and macOS <11 or Safari <14"""

    try:
        ua_info = user_agent_parser.Parse(request.META.get('HTTP_USER_AGENT'))
        if ua_info['os']['family'] == 'Mac OS X' and ua_info['user_agent']['family'] == 'Safari':
            if int(ua_info['os']['major']) < 11 and int(ua_info['user_agent']['major']) < 16 or int(
                    ua_info['user_agent']['major']) < 14:
                return False

        return True
    except KeyError:
        return False


def no_transparency(image) -> bool:
    """Check if image has transparency"""
    if image.mode in ('RGBA', 'LA'):
        return False
    return True


def get_image_format(request, image):
    if browser_supports_webp(request):
        img_format = 'webp'
        save_func = lambda img, loc: img.save(loc, img_format)
    elif no_transparency(image):
        img_format = 'jpeg'
        save_func = lambda img, loc: img.convert('RGB').save(loc, img_format, optimize=True, progressive=True)
    else:
        img_format = 'png'
        save_func = lambda img, loc: img.save(loc, img_format)
    return img_format, save_func
