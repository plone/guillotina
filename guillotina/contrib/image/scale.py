# -*- coding: utf-8 -*-
# Code from plone.scale
from io import BytesIO

import math
import PIL.Image
import PIL.ImageFile
import sys
import warnings


def none_as_int(the_int):
    """For python 3 compatibility, to make int vs. none comparison possible
    without changing the algorithms below.
    This should mimic python2 behaviour."""
    if the_int is None:
        return -sys.maxsize
    return the_int


# Set a larger buffer size. This fixes problems with jpeg decoding.
# See http://mail.python.org/pipermail/image-sig/1999-August/000816.html for
# details.
PIL.ImageFile.MAXBLOCK = 1000000

MAX_PIXELS = 8192 * 8192


def scaleImage(image, width=None, height=None, mode="contain", quality=88, result=None, direction=None):
    """Scale the given image data to another size and return the result
    as a string or optionally write in to the file-like `result` object.
    The `image` parameter can either be the raw image data (ie a `str`
    instance) or an open file.
    The `quality` parameter can be used to set the quality of the
    resulting image scales.
    The return value is a tuple with the new image, the image format and
    a size-tuple.  Optionally a file-like object can be given as the
    `result` parameter, in which the generated image scale will be stored.
    The `width`, `height`, `mode` parameters will be passed to
    :meth:`scalePILImage`, which performs the actual scaling.
    The generated image is a JPEG image, unless the original is a PNG or GIF
    image. This is needed to make sure alpha channel information is
    not lost, which JPEG does not support.
    """
    if isinstance(image, (bytes, str)):
        image = BytesIO(image)
    image = PIL.Image.open(image)
    # When we create a new image during scaling we loose the format
    # information, so remember it here.
    format_ = image.format
    if format_ not in ("PNG", "GIF"):
        # Always generate JPEG, except if format is PNG or GIF.
        format_ = "JPEG"
    elif format_ == "GIF":
        # GIF scaled looks better if we have 8-bit alpha and no palette
        format_ = "PNG"

    icc_profile = image.info.get("icc_profile")
    image = scalePILImage(image, width, height, mode, direction=direction)

    # convert to simpler mode if possible
    colors = image.getcolors(maxcolors=256)
    if image.mode not in ("P", "L") and colors:
        if format_ == "JPEG":
            # check if it's all grey
            if all(rgb[0] == rgb[1] == rgb[2] for c, rgb in colors):
                image = image.convert("L")
        elif format_ == "PNG":
            image = image.convert("P")

    if image.mode == "RGBA" and format_ == "JPEG":
        extrema = dict(zip(image.getbands(), image.getextrema()))
        if extrema.get("A") == (255, 255):
            # no alpha used, just change the mode, which causes the alpha band
            # to be dropped on save
            image.mode = "RGB"
        else:
            # switch to PNG, which supports alpha
            format_ = "PNG"

    new_result = False

    if result is None:
        result = BytesIO()
        new_result = True

    image.save(result, format_, quality=quality, optimize=True, progressive=True, icc_profile=icc_profile)

    if new_result:
        result = result.getvalue()
    else:
        result.seek(0)

    return result, format_, image.size


def _scale_thumbnail(image, width=None, height=None):
    """Scale with method "thumbnail".
    Aspect Ratio is kept. Resulting image has to fit in the given box.
    If target aspect ratio is different, either width or height is smaller
    than the given target width or height. No cropping!
    """
    dimensions = _calculate_all_dimensions(image.size[0], image.size[1], width, height, "scale")

    if (dimensions.target_width * dimensions.target_height) > MAX_PIXELS:
        # The new image would be excessively large and eat up all memory while
        # scaling, so return the potentially pre cropped image
        return image

    image.draft(image.mode, (dimensions.target_width, dimensions.target_height))
    image = image.resize((dimensions.target_width, dimensions.target_height), PIL.Image.ANTIALIAS)
    return image


def get_scale_mode(mode, direction):
    if direction is not None:
        warnings.warn("the 'direction' option is deprecated, use 'mode' instead", DeprecationWarning)
        mode = direction

    if mode in ("scale-crop-to-fit", "down"):
        mode = "contain"
    elif mode in ("scale-crop-to-fill", "up"):
        mode = "cover"
    elif mode in ("keep", "thumbnail"):
        mode = "scale"

    return mode


class ScaledDimensions(object):
    pass


def _calculate_all_dimensions(original_width, original_height, width, height, mode="contain"):
    """ Calculate all dimensions we need for scaling.
    final_width and final_height are the dimensions of the resulting image and
    are always present.
    The other values are required for cropping and scaling."""

    if width is None and height is None:
        raise ValueError("Either width or height need to be given.")

    if mode not in ("contain", "cover", "scale"):
        raise ValueError("Unknown scale mode '%s'" % mode)

    dimensions = ScaledDimensions()

    if mode == "scale":
        # first store original size, as it is possible that we won't scale at all
        dimensions.final_width = original_width
        dimensions.final_height = original_height

        # calculate missing sizes
        if width is None:
            width = float(original_width) / float(original_height) * height
        elif height is None:
            height = float(original_height) / float(original_width) * width

        # keep aspect ratio of original
        target_width = original_width
        target_height = original_height
        if target_width > width:
            target_height = int(max(target_height * width / target_width, 1))
            target_width = int(width)
        if target_height > height:
            target_width = int(max(target_width * height / target_height, 1))
            target_height = int(height)

        dimensions.target_width = target_width
        dimensions.target_height = target_height

        if (target_width * target_height) > MAX_PIXELS:
            # The new image would be excessively large and eat up all memory while
            # scaling, so return the dimensions of the potentially cropped image
            return dimensions

        dimensions.final_width = dimensions.target_width
        dimensions.final_height = dimensions.target_height
        return dimensions

    # now for 'cover' and 'contain' scaling

    # Determine scale factors needed
    factor_height = factor_width = None
    if height is not None:
        factor_height = float(height) / float(original_height)
    if width is not None:
        factor_width = float(width) / float(original_width)

    dimensions.factor_width = factor_width
    dimensions.factor_height = factor_height
    dimensions.final_width = width
    dimensions.final_height = height

    if factor_height == factor_width:
        # The original already has the right aspect ratio
        return dimensions

    # figure out which axis to scale. One of the factors can still be None!
    use_height = none_as_int(factor_width) > none_as_int(factor_height)
    if mode == "cover":  # for 'cover': invert
        use_height = not use_height

    # keep aspect ratio
    if height is None or (use_height and width is not None):
        target_width = width
        target_height = int(round(original_height * factor_width))

    if width is None or (height is not None and not use_height):
        target_width = int(round(original_width * factor_height))
        target_height = height

    # determine whether we need to crop before scaling
    pre_scale_crop = (width is not None and target_width > width) or (
        height is not None and target_height > height
    )
    dimensions.pre_scale_crop = pre_scale_crop

    if pre_scale_crop:
        # crop image before scaling to avoid excessive memory use
        if use_height:
            left = 0
            right = original_width
            top = int(math.floor(((target_height - height) / 2.0) / factor_width))
            bottom = int(math.ceil((((target_height - height) / 2.0) + height) / factor_width))
            pre_scale_crop_height = bottom - top
            # set new height in case we abort
            dimensions.final_height = pre_scale_crop_height
            # calculate new scale target_height from cropped height
            target_height = int(round(pre_scale_crop_height * factor_width))
        else:
            left = int(math.floor(((target_width - width) / 2.0) / factor_height))
            right = int(math.ceil((((target_width - width) / 2.0) + width) / factor_height))
            top = 0
            bottom = original_height
            pre_scale_crop_width = right - left
            # set new width in case we abort
            dimensions.final_width = pre_scale_crop_width
            # calculate new scale target_width from cropped width
            target_width = int(round(pre_scale_crop_width * factor_height))
        dimensions.pre_scale_crop = (left, top, right, bottom)

    dimensions.target_width = target_width
    dimensions.target_height = target_height

    if (target_width * target_height) > MAX_PIXELS:
        # The new image would be excessively large and eat up all memory while
        # scaling, so return the dimensions of the potentially cropped image
        return dimensions

    dimensions.final_width = target_width
    dimensions.final_height = target_height

    # determine whether we have to crop after scaling due to rounding
    post_scale_crop = (width is not None and target_width > width) or (
        height is not None and target_height > height
    )
    dimensions.post_scale_crop = post_scale_crop

    if post_scale_crop:
        if use_height:
            left = 0
            right = target_width
            top = int((target_height - height) / 2.0)
            bottom = top + height
            dimensions.final_height = bottom - top
        else:
            left = int((target_width - width) / 2.0)
            right = left + width
            top = 0
            bottom = target_height
            dimensions.final_width = right - left
        dimensions.post_scale_crop = (left, top, right, bottom)

    return dimensions


def calculate_scaled_dimensions(original_width, original_height, width, height, mode="contain"):
    """ Calculate the scaled image dimensions from the originals using the
    same logic as scalePILImage """
    dimensions = _calculate_all_dimensions(original_width, original_height, width, height, mode)

    return (dimensions.final_width, dimensions.final_height)


def scalePILImage(image, width=None, height=None, mode="contain", direction=None):
    """Scale a PIL image to another size.
    This is all about scaling for the display in a web browser.
    Either width or height - or both - must be given.
    Three different scaling options are supported via `mode` and correspond to
    the CSS background-size values
    (see https://developer.mozilla.org/en-US/docs/Web/CSS/background-size):
    `contain`
        Alternative spellings: `scale-crop-to-fit`, `down`.
        Starts by scaling the smallest dimension to the required
        size and crops the other dimension if needed.
    `cover`
        Alternative spellings: `scale-crop-to-fill`, `up`.
        Starts by scaling the largest dimension up to the required size
        and crops the other dimension if needed.
    `scale`
        Alternative spellings: `keep`, `thumbnail`.
        Scales to the requested dimensions without cropping. The resulting
        image may have a different size than requested. This option
        requires both width and height to be specified.
        Does not scale up.
    The `image` parameter must be an instance of the `PIL.Image` class.
    The return value the scaled image in the form of another instance of
    `PIL.Image`.
    """
    # convert zero to None, same sematics: calculate this scale
    if width == 0:
        width = None
    if height == 0:
        height = None
    if width is None and height is None:
        raise ValueError("Either width or height need to be given")

    mode = get_scale_mode(mode, direction)

    if image.mode == "1":
        # Convert black&white to grayscale
        image = image.convert("L")
    elif image.mode == "P":
        # If palette is grayscale, convert to gray+alpha
        # Else convert palette based images to 3x8bit+alpha
        palette = image.getpalette()
        if palette[0::3] == palette[1::3] == palette[2::3]:
            image = image.convert("LA")
        else:
            image = image.convert("RGBA")
    elif image.mode == "CMYK":
        # Convert CMYK to RGB, allowing for web previews of print images
        image = image.convert("RGB")

    # for scale we're done:
    if mode == "scale":
        return _scale_thumbnail(image, width, height)

    dimensions = _calculate_all_dimensions(image.size[0], image.size[1], width, height, mode)

    if dimensions.factor_height == dimensions.factor_width:
        # The original already has the right aspect ratio, so we only need
        # to scale.
        if mode == "contain":
            image.thumbnail((dimensions.final_width, dimensions.final_height), PIL.Image.ANTIALIAS)
            return image
        return image.resize((dimensions.final_width, dimensions.final_height), PIL.Image.ANTIALIAS)

    if dimensions.pre_scale_crop:
        # crop image before scaling to avoid excessive memory use
        # in case the intermediate result would be very tall or wide
        image = image.crop(dimensions.pre_scale_crop)

    if (dimensions.target_width * dimensions.target_height) > MAX_PIXELS:
        # The new image would be excessively large and eat up all memory while
        # scaling, so return the potentially pre cropped image
        return image

    image.draft(image.mode, (dimensions.target_width, dimensions.target_height))
    image = image.resize((dimensions.target_width, dimensions.target_height), PIL.Image.ANTIALIAS)

    if dimensions.post_scale_crop:
        # crop off remains due to rounding before scaling
        image = image.crop(dimensions.post_scale_crop)

    return image
