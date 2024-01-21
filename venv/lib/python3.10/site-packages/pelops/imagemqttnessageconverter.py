import base64
from io import BytesIO
import json


class ImageMQTTMessageEncoder(object):
    """Static utility class - converts images and json structures into valid mqtt payloads."""

    @staticmethod
    def to_full_image_message(image):
        """Convert a PIL.Image instance to bytes - the format nedded if the mqtt payload consists of only the image."""
        bytes_image = BytesIO()
        image.save(bytes_image, format="png")
        result = bytes_image.getvalue()
        return result

    @staticmethod
    def to_partial_images_message(image_entry_list):
        """Takes a list containing [x,y,partial images] and converts the images into an utf-8 encoded string that can be
        accepted by mqtt and packs them into a json structure consisting of these string and their x/y values."""
        result = []
        for image_entry in image_entry_list:
            bytes_image = BytesIO()
            image_entry["image"].save(bytes_image, format="png")
            base64_bytes = base64.b64encode(bytes_image.getvalue())
            base64_string = base64_bytes.decode("utf-8")
            entry = {
                "x": int(image_entry["x"]),
                "y": int(image_entry["y"]),
                "image": base64_string
            }
            result.append(entry)
        return json.dumps(result)

