import json
import base64
from selenium.webdriver.common.print_page_options import PrintOptions

from .DriverBase import DriverBase

class Pdf(DriverBase):

    def create_pdf(self, url, timeout, is_docker):

        driver = self.get_driver_for_url(url, timeout, is_docker)

        print_options = PrintOptions()
        print_options.orientation = "portrait"
        print_options.margin_left = 0
        print_options.margin_right = 0
        print_options.margin_top = 0
        print_options.margin_bottom = 0

        # A4 in cm
        print_options.page_width = 21.0
        print_options.page_height = 29.7

        result = driver.print_page(print_options)
        driver.get("about:blank") # Navigate away to ensure page is unloaded properly.
        driver.quit()
        return base64.b64decode(result)


    def write_pdf_to_path(self, path, pdf):
        with open(file_path, "wb") as file:
            file.write(pdf)

    def create_pdf_in_path(self, url, timeout, is_docker, path):
        pdf = self.create_pdf(url, timeout, is_docker)
        self.write_pdf_to_path(path, pdf)
