import os
from .DriverBase import DriverBase
import tinify
from fpdf import FPDF

class Image(DriverBase):

    def grab_screenshot_in_path(self, url, timeout, is_docker, path):
        driver = self.get_driver_for_url(url, timeout, is_docker)
        driver.save_screenshot(path)
        driver.get("about:blank") # Navigate away to ensure page is unloaded properly


    def tinify(self, key, path, width):
        tinify.key = key
        img = tinify.from_file(path)
        resized = img.resize(method="scale", width=width)
        os.remove(path)
        resized.to_file(path)
