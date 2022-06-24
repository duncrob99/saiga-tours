from PIL import Image


def crop_center(pil_img: Image, crop_width: int, crop_height: int) -> Image:
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))


def crop_to_ar(image: Image, ar: float) -> Image:
    (old_width, old_height) = image.size

    original_ar = old_width / old_height

    print(original_ar, ar)
    if ar > original_ar:
        crop_height = int(old_width / ar)
        crop_width = old_width
    elif ar < original_ar:
        crop_width = int(old_height * ar)
        crop_height = old_height
    else:
        return image

    return crop_center(image, crop_width, crop_height)


def crop_to_dims(image: Image, width: int, height: int) -> Image:
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


def autorotate(img: Image):
    """
    Rotate a Pillow image based on exif data.
    Returns new Pillow image.
    """
    exif = img._getexif()
    orientation_key = 274

    if exif and orientation_key in exif:
        orientation = exif[orientation_key]

        rotate_values = {
            3: Image.ROTATE_180,
            6: Image.ROTATE_270,
            8: Image.ROTATE_90
        }

        if orientation in rotate_values:
            img = img.transpose(rotate_values[orientation])

    return img
