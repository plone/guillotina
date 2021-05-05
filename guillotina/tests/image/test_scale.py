# -*- coding: utf-8 -*-
from guillotina.contrib.image.scale import scaleImage
from guillotina.contrib.image.scale import scalePILImage
from guillotina.tests.image import TEST_DATA_LOCATION
from io import BytesIO
from unittest import TestCase

import os.path
import PIL.Image
import PIL.ImageDraw
import warnings


with open(os.path.join(TEST_DATA_LOCATION, "logo.png"), "rb") as fio:
    PNG = fio.read()
with open(os.path.join(TEST_DATA_LOCATION, "logo.gif"), "rb") as fio:
    GIF = fio.read()
with open(os.path.join(TEST_DATA_LOCATION, "logo.tiff"), "rb") as fio:
    TIFF = fio.read()
with open(os.path.join(TEST_DATA_LOCATION, "cmyk.jpg"), "rb") as fio:
    CMYK = fio.read()
with open(os.path.join(TEST_DATA_LOCATION, "profile.jpg"), "rb") as fio:
    PROFILE = fio.read()


class ScalingTests(TestCase):
    def testNewSizeReturned(self):
        (imagedata, format, size) = scaleImage(PNG, 42, 51, "contain")
        input = BytesIO(imagedata)
        image = PIL.Image.open(input)
        self.assertEqual(image.size, size)

    def testScaledImageKeepPNG(self):
        self.assertEqual(scaleImage(PNG, 84, 103, "contain")[1], "PNG")

    def testScaledImageKeepGIFto(self):
        self.assertEqual(scaleImage(GIF, 84, 103, "contain")[1], "PNG")

    def testScaledImageIsJpeg(self):
        self.assertEqual(scaleImage(TIFF, 84, 103, "contain")[1], "JPEG")

    def testAlphaForcesPNG(self):
        # first image without alpha
        src = PIL.Image.new("RGBA", (256, 256), (255, 255, 255, 255))
        for y in range(0, 256):
            for x in range(0, 256):
                src.putpixel((x, y), (x, y, 0, 255))
        result = BytesIO()
        src.save(result, "TIFF")
        self.assertEqual(scaleImage(result, 84, 103, "contain")[1], "JPEG")
        # now with alpha
        src = PIL.Image.new("RGBA", (256, 256), (255, 255, 255, 128))
        result = BytesIO()
        for y in range(0, 256):
            for x in range(0, 256):
                src.putpixel((x, y), (x, y, 0, x))
        src.save(result, "TIFF")
        self.assertEqual(scaleImage(result, 84, 103, "contain")[1], "PNG")

    def testScaledCMYKIsRGB(self):
        (imagedata, format, size) = scaleImage(CMYK, 42, 51, "contain")
        input = BytesIO(imagedata)
        image = PIL.Image.open(input)
        self.assertEqual(image.mode, "RGB")

    def testScaledPngImageIsPng(self):
        self.assertEqual(scaleImage(PNG, 84, 103, "contain")[1], "PNG")

    def testScaledPreservesProfile(self):
        (imagedata, format, size) = scaleImage(PROFILE, 42, 51, "contain")
        input = BytesIO(imagedata)
        image = PIL.Image.open(input)
        self.assertIsNotNone(image.info.get("icc_profile"))

    def testScaleWithFewColorsStaysColored(self):
        (imagedata, format, size) = scaleImage(PROFILE, 16, None, "contain")
        image = PIL.Image.open(BytesIO(imagedata))
        self.assertEqual(max(image.size), 16)
        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.format, "JPEG")

    def testAutomaticGreyscale(self):
        src = PIL.Image.new("RGB", (256, 256), (255, 255, 255))
        draw = PIL.ImageDraw.Draw(src)
        for i in range(0, 256):
            draw.line(((0, i), (256, i)), fill=(i, i, i))
        result = BytesIO()
        src.save(result, "JPEG")
        (imagedata, format, size) = scaleImage(result, 200, None, "contain")
        image = PIL.Image.open(BytesIO(imagedata))
        self.assertEqual(max(image.size), 200)
        self.assertEqual(image.mode, "L")
        self.assertEqual(image.format, "JPEG")

    def testAutomaticPalette(self):
        # get a JPEG with more than 256 colors
        jpeg = PIL.Image.open(BytesIO(PROFILE))
        self.assertEqual(jpeg.mode, "RGB")
        self.assertEqual(jpeg.format, "JPEG")
        self.assertIsNone(jpeg.getcolors(maxcolors=256))
        # convert to PNG
        dst = BytesIO()
        jpeg.save(dst, "PNG")
        dst.seek(0)
        png = PIL.Image.open(dst)
        self.assertEqual(png.mode, "RGB")
        self.assertEqual(png.format, "PNG")
        self.assertIsNone(png.getcolors(maxcolors=256))
        # scale it to a size where we get less than 256 colors
        (imagedata, format, size) = scaleImage(dst.getvalue(), 24, None, "contain")
        image = PIL.Image.open(BytesIO(imagedata))
        # we should now have an image in palette mode
        self.assertEqual(image.mode, "P")
        self.assertEqual(image.format, "PNG")

    def testSameSizeDownScale(self):
        self.assertEqual(scaleImage(PNG, 84, 103, "contain")[2], (84, 103))

    def testHalfSizeDownScale(self):
        self.assertEqual(scaleImage(PNG, 42, 51, "contain")[2], (42, 51))

    def testScaleWithCropDownScale(self):
        self.assertEqual(scaleImage(PNG, 20, 51, "contain")[2], (20, 51))

    def testNoStretchingDownScale(self):
        self.assertEqual(scaleImage(PNG, 200, 103, "contain")[2], (200, 103))

    def testHugeScale(self):
        # the image will be cropped, but not scaled
        self.assertEqual(scaleImage(PNG, 400, 99999, "contain")[2], (2, 103))

    def testCropPreWideScaleUnspecifiedHeight(self):
        image = scaleImage(PNG, 400, None, "contain")
        self.assertEqual(image[2], (400, 490))

    def testCropPreWideScale(self):
        image = scaleImage(PNG, 400, 100, "contain")
        self.assertEqual(image[2], (400, 100))

    def testCropPreTallScaleUnspecifiedWidth(self):
        image = scaleImage(PNG, None, 400, "contain")
        self.assertEqual(image[2], (326, 400))

    def testCropPreTallScale(self):
        image = scaleImage(PNG, 100, 400, "contain")
        self.assertEqual(image[2], (100, 400))

    def testRestrictWidthOnlyDownScaleNone(self):
        self.assertEqual(scaleImage(PNG, 42, None, "contain")[2], (42, 52))

    def testRestrictWidthOnlyDownScaleZero(self):
        self.assertEqual(scaleImage(PNG, 42, 0, "contain")[2], (42, 52))

    def testRestrictHeightOnlyDownScaleNone(self):
        self.assertEqual(scaleImage(PNG, None, 51, "contain")[2], (42, 51))

    def testRestrictHeightOnlyDownScaleZero(self):
        self.assertEqual(scaleImage(PNG, 0, 51, "contain")[2], (42, 51))

    def testSameSizeUpScale(self):
        self.assertEqual(scaleImage(PNG, 84, 103, "cover")[2], (84, 103))

    def testDoubleSizeUpScale(self):
        self.assertEqual(scaleImage(PNG, 168, 206, "cover")[2], (168, 206))

    def testHalfSizeUpScale(self):
        self.assertEqual(scaleImage(PNG, 42, 51, "cover")[2], (42, 51))

    def testNoStretchingUpScale(self):
        self.assertEqual(scaleImage(PNG, 200, 103, "cover")[2], (84, 103))

    def testRestrictWidthOnlyUpScaleNone(self):
        self.assertEqual(scaleImage(PNG, 42, None, "cover")[2], (42, 52))

    def testRestrictWidthOnlyUpScaleZero(self):
        self.assertEqual(scaleImage(PNG, 42, 0, "cover")[2], (42, 52))

    def testRestrictHeightOnlyUpScaleNone(self):
        self.assertEqual(scaleImage(PNG, None, 51, "cover")[2], (42, 51))

    def testRestrictHeightOnlyUpScaleZero(self):
        self.assertEqual(scaleImage(PNG, 0, 51, "cover")[2], (42, 51))

    def testNoRestrictionsNone(self):
        self.assertRaises(ValueError, scaleImage, PNG, None, None)

    def testNoRestrictionsZero(self):
        self.assertRaises(ValueError, scaleImage, PNG, 0, 0)

    def testKeepAspectRatio(self):
        self.assertEqual(scaleImage(PNG, 80, 80, "scale")[2], (65, 80))

    def testThumbnailHeightNone(self):
        self.assertEqual(scaleImage(PNG, 42, None, "scale")[2], (42, 51))

    def testThumbnailWidthNone(self):
        self.assertEqual(scaleImage(PNG, None, 51, "scale")[2], (41, 51))

    def testQuality(self):
        img1 = scaleImage(CMYK, 84, 103)[0]
        img2 = scaleImage(CMYK, 84, 103, quality=50)[0]
        img3 = scaleImage(CMYK, 84, 103, quality=20)[0]
        self.assertNotEqual(img1, img2)
        self.assertNotEqual(img1, img3)
        self.failUnless(len(img1) > len(img2) > len(img3))

    def testResultBuffer(self):
        img1 = scaleImage(PNG, 84, 103)[0]
        result = BytesIO()
        img2 = scaleImage(PNG, 84, 103, result=result)[0]
        self.assertEqual(result, img2)  # the return value _is_ the buffer
        self.assertEqual(result.getvalue(), img1)  # but with the same value

    def testAlternativeSpellings(self):
        """Test alternative and deprecated mode spellings and the old
        ``direction`` arguments instead of ``mode``.
        """

        # scale-crop-to-fit
        img = PIL.Image.new("RGB", (20, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 10, 5, direction="scale-crop-to-fit")
        self.assertEqual(img_scaled.size, (10, 5))
        # down
        img = PIL.Image.new("RGB", (20, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 10, 5, direction="down")
        self.assertEqual(img_scaled.size, (10, 5))

        # Test mode cover
        # scale-crop-to-fill
        img = PIL.Image.new("RGB", (20, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 40, 30, direction="scale-crop-to-fill")
        self.assertEqual(img_scaled.size, (30, 30))
        # up
        img = PIL.Image.new("RGB", (20, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 40, 30, direction="up")
        self.assertEqual(img_scaled.size, (30, 30))

        # Test mode scale
        # keep A
        img = PIL.Image.new("RGB", (20, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 20, 10, direction="keep")
        self.assertEqual(img_scaled.size, (10, 10))
        # keep B
        img = PIL.Image.new("RGB", (20, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 40, 80, direction="keep")
        self.assertEqual(img_scaled.size, (20, 20))
        # thumbnail A
        img = PIL.Image.new("RGB", (20, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 20, 10, direction="thumbnail")
        self.assertEqual(img_scaled.size, (10, 10))
        # thumbnail B
        img = PIL.Image.new("RGB", (20, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 40, 80, direction="thumbnail")
        self.assertEqual(img_scaled.size, (20, 20))

    def testModes(self):
        """Test modes to actually behavie like documented.
        """
        # Mode contain
        # v
        # A
        img = PIL.Image.new("RGB", (20, 40), (0, 0, 0))
        img_scaled = scalePILImage(img, 10, 10, mode="contain")
        self.assertEqual(img_scaled.size, (10, 10))
        # B
        img = PIL.Image.new("RGB", (40, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 10, 10, mode="contain")
        self.assertEqual(img_scaled.size, (10, 10))
        # ^
        # A
        img = PIL.Image.new("RGB", (20, 40), (0, 0, 0))
        img_scaled = scalePILImage(img, 60, 60, mode="contain")
        self.assertEqual(img_scaled.size, (60, 60))
        # B
        img = PIL.Image.new("RGB", (40, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 60, 60, mode="contain")
        self.assertEqual(img_scaled.size, (60, 60))

        # Mode cover
        # v
        # A
        img = PIL.Image.new("RGB", (20, 40), (0, 0, 0))
        img_scaled = scalePILImage(img, 10, 10, mode="cover")
        self.assertEqual(img_scaled.size, (5, 10))
        # B
        img = PIL.Image.new("RGB", (40, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 10, 10, mode="cover")
        self.assertEqual(img_scaled.size, (10, 5))
        # ^
        # A
        img = PIL.Image.new("RGB", (20, 40), (0, 0, 0))
        img_scaled = scalePILImage(img, 60, 60, mode="cover")
        self.assertEqual(img_scaled.size, (30, 60))
        # B
        img = PIL.Image.new("RGB", (40, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 60, 60, mode="cover")
        self.assertEqual(img_scaled.size, (60, 30))

        # Mode scale
        # v
        # A
        img = PIL.Image.new("RGB", (20, 40), (0, 0, 0))
        img_scaled = scalePILImage(img, 10, 10, mode="scale")
        self.assertEqual(img_scaled.size, (5, 10))
        # B
        img = PIL.Image.new("RGB", (40, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 10, 10, mode="scale")
        self.assertEqual(img_scaled.size, (10, 5))
        # ^
        # A
        img = PIL.Image.new("RGB", (20, 40), (0, 0, 0))
        img_scaled = scalePILImage(img, 60, 60, mode="scale")
        self.assertEqual(img_scaled.size, (20, 40))
        # B
        img = PIL.Image.new("RGB", (40, 20), (0, 0, 0))
        img_scaled = scalePILImage(img, 60, 60, mode="scale")
        self.assertEqual(img_scaled.size, (40, 20))

    def testDeprecations(self):
        import guillotina.contrib.image.scale

        # clear warnings registry, so the test actually sees the warning
        guillotina.contrib.image.scale.__warningregistry__.clear()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            scaleImage(PNG, 16, 16, direction="keep")
            self.assertEqual(len(w), 1)
            self.assertIs(w[0].category, DeprecationWarning)
            self.assertIn("the 'direction' option is deprecated", str(w[0].message))


def test_suite():
    from unittest import defaultTestLoader

    return defaultTestLoader.loadTestsFromName(__name__)
