from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

class WebDriverFactory:
    @staticmethod
    def create_driver(headless=True, disable_images=True):
        profile = FirefoxProfile()
        if disable_images:
            profile.set_preference("permissions.default.image", 2)  # Disable images

        options = Options()
        options.profile = profile
        options.headless = headless  # Enable headless mode by default

        driver = webdriver.Firefox(options=options)
        return driver
