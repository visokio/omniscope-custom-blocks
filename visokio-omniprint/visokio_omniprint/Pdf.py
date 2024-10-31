import json
import base64
from selenium.webdriver.common.print_page_options import PrintOptions

from .DriverBase import DriverBase

class Pdf(DriverBase):

    def create_pdf(self, url, timeout, is_docker):

        driver = self.get_driver_for_url(url, timeout, is_docker)

        print_options = PrintOptions()
        print_options.orientation = "portrait"

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
