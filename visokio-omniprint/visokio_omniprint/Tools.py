from urllib.parse import unquote

class Tools:


    def _split(self, url):
        report_name = url.rsplit('/', 3)[-2]
        report_base_url = url.rsplit('/', 1)[-2]
        tab_name_with_filter = None
        tab_name = None
        if "#" in url:
            tab_name_with_filter = url.rsplit('#', 1)[-1]
            tab_name = unquote(tab_name_with_filter)

        return report_name, report_base_url, tab_name_with_filter, tab_name

    def _file_path(self, output_folder, file_name, report_name, tab_name, index):
        if (file_name is not None):
            file_name = file_name + ".pdf"
        else:
            if tab_name is not None:
                if '&' in tab_name:
                    tab_name = tab_name.split('&',2)[0]
                file_name = report_name + "-" + tab_name + "-" + str(index) + ".pdf"
            else:
                file_name = report_name + "-" + str(index) + ".pdf"

        file_path = output_folder + "/" + file_name
        return file_path, file_name

    def _scenario_file_path(self, output_folder, report_name, scenario_id):
        file_name = report_name + "-" + scenario_id + ".pdf"

        file_path = output_folder + "/" + file_name
        return file_path, file_name



    def _page_size(self, page_width, page_height):
        page_size = ""
        if (page_width is not None and page_width > 0):
            page_size = "&pageWidth="+str(page_width)

        if (page_height is not None and page_height > 0):
            page_size += "&pageHeight="+str(page_height)

        return page_size



    def scenario_report_url(self, url, scenario_id, page_width, page_height, output_folder):
        report_name, report_base_url, tab_name_with_filter, tab_name = self._split(url)
        page_size = self._page_size(page_width, page_height)

        report_url = report_base_url + "/s/" + scenario_id + "/" + "#device=printer"+ page_size

        if tab_name_with_filter is not None:
            report_url = report_url + "&tab=" + tab_name_with_filter

        print ("SCENARIO report_base_url: " + str(report_base_url))
        print ("SCENARIO report_url: " + str(report_url))

        print ("SCENARIO output_folder: " + str(output_folder))
        print ("SCENARIO report_name: " + str(report_name))
        print ("SCENARIO scenario_id: " + str(scenario_id))

        file_path, file_name = self._scenario_file_path(output_folder, report_name, scenario_id)

        print ("SCENARIO file_path: " + str(file_path))
        print ("SCENARIO file_name: " + str(file_name))


        return report_url, file_path, file_name

    def report_url(self, url, page_width, page_height, output_folder, file_name, index):
        report_name, report_base_url, tab_name_with_filter, tab_name = self._split(url)
        page_size = self._page_size(page_width, page_height)

        report_url = report_base_url + "/" + "#device=printer"+ page_size

        if tab_name_with_filter is not None:
            report_url = report_url + "&tab=" + tab_name_with_filter


        file_path, file_name = self._file_path(output_folder, file_name, report_name, tab_name, index)
        return report_url, file_path, file_name
