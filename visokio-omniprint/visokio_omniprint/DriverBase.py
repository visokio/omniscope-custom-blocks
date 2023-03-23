import json
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from get_chrome_driver import GetChromeDriver



class DriverBase:

    def get_compatible_chromedriver(self):
        """
        This function checks if a compatible version of ChromeDriver is installed.
        If a compatible version is not found, an exception is raised.
        """
        get_driver = GetChromeDriver()
        version = get_driver.matching_version()
        if version is None:
            raise Exception("Chrome not installed or no compatible chrome version found")

    def create_options(self):
        """
        This function creates a set of options that will be used to configure the ChromeDriver instance.
        """
        webdriver_options = Options()
        webdriver_prefs = {}
        # Add arguments to options
        webdriver_options.add_argument("--headless")
        webdriver_options.add_argument("--disable-gpu")
        webdriver_options.add_argument("--no-sandbox")
        webdriver_options.add_argument("--disable-dev-shm-usage")
        webdriver_options.add_argument("--window-size=1920,1080")
        # Add preferences to options
        webdriver_options.experimental_options["prefs"] = webdriver_prefs
        webdriver_prefs["profile.default_content_settings"] = {"images": 2}
        return webdriver_options


    def get_driver_docker(self, options):
        """
        This function creates a ChromeDriver instance to be used in a Docker container.
        """
        chrome_service = Service("/chromedriver")
        return webdriver.Chrome(service=chrome_service, options=options)

    def get_driver_host(self, options):
        """
        This function creates a ChromeDriver instance to be used on the host machine.
        """
        version = self.get_compatible_chromedriver()
        return webdriver.Chrome(ChromeDriverManager(version=version).install(), options=options)


    def get_driver(self, is_docker):
        """
        This function creates and returns a ChromeDriver instance based on the provided configuration.
        """
        options = self.create_options()

        if is_docker:
            return self.get_driver_docker(options)
        else:
            return self.get_driver_host(options)


    def send_devtools(self, driver, cmd, params):
        """
        This function sends a command to the Chrome DevTools API and returns the result.
        """
        resource = "/session/%s/chromium/send_command_and_get_result" % driver.session_id
        url = driver.command_executor._url + resource
        body = json.dumps({"cmd": cmd, "params": params})
        response = driver.command_executor._request("POST", url, body)

        if not response:
            raise Exception(response.get("value"))

        return response.get("value")


    def get_driver_for_url(self, url, timeout, is_docker):
        driver = self.get_driver(is_docker)
        driver.get(url)  # Navigate to the specified URL

        try:
            # Wait until the page is fully loaded
            WebDriverWait(driver, timeout).until(
                staleness_of(driver.find_element(by=By.TAG_NAME, value="html"))
            )
        except TimeoutException:
            return driver

        driver.quit()
        raise Exception("page load unsuccessful")
