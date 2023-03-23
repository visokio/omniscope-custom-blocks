import os
from .DriverBase import DriverBase
from fpdf import FPDF

class ImagesPdf(DriverBase):

    def __init__(self):
        self.paths = []


    def add_path(self, path):
        self.paths.append(path)


    def _split_resolution(self, orientation, resolution):
        resSplit = resolution.split("x")
        #width, then height
        imgSize = [ int(resSplit[0]), int(resSplit[1]) ]

        if orientation == "P":
            resolution = resSplit[1]+"x"+resSplit[0]
            imgSize = [ int(resSplit[1]), int(resSplit[0]) ]

        #Pdf lib wants heigth then width
        resSplit[0], resSplit[1] = resSplit[1], resSplit[0]

        return resSplit

    def create_pdf_in_path(self, path, orientation, resolution, compressed):
        res = self._split_resolution(orientation, resolution)

        pdf = FPDF(orientation, 'pt', (int(res[0]),int(res[1])))
        pdf.set_margins(0,0,0)
        pdf.set_auto_page_break(False)
        pdf.set_compression(compressed)

        for image_path in self.paths:
            pdf.add_page()
            pdf.image(image_path)

        if os.path.exists(path):
            os.remove(path)
        pdf.output(path, "F")
