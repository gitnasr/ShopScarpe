import csv
import os
import sys
import time
import datetime as dt
import logging
import chromedriver_autoinstaller
from selenium.webdriver.chrome.options import Options
import winsound
from selenium.webdriver.remote.remote_connection import LOGGER

frequency = 2500  # Set Frequency To 2500 Hertz
duration = 5000  # Set Duration To 1000 ms == 1 second
from captcha import TwoCaptcha
from selenium import webdriver

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
api_key = "2986f38f4866d4c3f187b159f1afd516"


class WalmartUSA:
    def __init__(self):
        LOGGER.setLevel(logging.CRITICAL)
        self.products = []
        self.solver = ""

        self.ZipCode = input("ZIP Code: ")
        self.shops = []
        self.current_url = ""
        chromedriver_autoinstaller.install()
        options = Options()
        options.add_argument("--log-level=3")
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.blockingUnwantedRequest()
        self.driver.get("https://www.walmart.com/")
        isca = self.DetectCaptchaModel()
        if isca:
            print("Captcha is Detected")
            input("enter done when you done: ")
        elif "/blocked" in self.driver.current_url:
            self.CaptchaHandler("https://www.walmart.com/")
        self.GetLocationsOfZipCode()
        print("You Selected {} Zip Code and {} Store. Starting....".format(self.ZipCode, self.Store))

        # atexit.register(self.onExit)
        self.LoopTargets()

    def LoopTargets(self):
        with open('targets.txt', 'r') as f:
            links = [line.strip() for line in f]
        f.close()
        links = list(filter(None, links))
        for link in links:
            if "https://www.walmart.com/" in link:
                self.current_url = link
            else:
                self.current_url = "https://www.walmart.com/search?q=" + link
            self.CaptchaHandler(self.current_url)
            self.GetHomeProducts()
            self.filename = "{}_{}_{}_1.csv".format(self.ZipCode, self.Store, time.time())
            self.SaveFileToDisk()

    def GetLocationsOfZipCode(self):
        try:
            # self.CaptchaHandler("https://www.walmart.com")
            self.WaitTillPopup()
            self.CheckLoadingSpinner()
            time.sleep(2)
            zip_input = self.driver.find_element("xpath", "//input[contains(@aria-label,'Enter zip code')]")
            zip_input.clear()
            zip_input.send_keys(self.ZipCode)
            self.CheckLoadingSpinner()
            time.sleep(1)
            isca = self.DetectCaptchaModel()
            if isca:
                print("Captcha Detected!, Please Solve")
                input("Type done when you solve the captcha")

            shops = self.driver.find_elements("xpath", "//div[contains(@class,'pt3 pb0 pl1')]/label/div/span[1]")
            for shop in shops:
                print(shop.text)
            self.Store = input("Please, Select a shop: ")
            self.driver.find_element("xpath", "//*[contains(text(),'{}')]".format(self.Store)).click()
            self.driver.find_element("xpath", "//button[contains(text(),'Save')]").click()
            time.sleep(5)
        except:
            print("Captch Detected")
            input("Enter when you done")

    def WaitTillPopup(self):
        while True:
            try:
                self.driver.find_element("xpath", "//input[contains(@aria-label,'Enter zip code')]")
                break
            except:
                self.driver.find_element("xpath", "//button[contains(@name,'select-store-button')]").click()
                time.sleep(1)

    def CheckLoadingSpinner(self):
        while True:
            try:
                self.driver.find_element("xpath", "//span[contains(@class,'w_B4 w_B7')]")
            except:
                print("Loaded")
                break

    def GetHomeProducts(self):
        current = 1
        total = int(self.TryToGetPagination())
        print("Max Pages: {}".format(total))
        if total * 1 == 1:
            print("Out of loop")
            products = self.driver.find_elements("xpath",
                                                 "//div[contains(@class,'mb1 ph1 pa0-xl bb b--near-white w-25')]")
            print("we in page #{} and it has #{} product".format(current, len(products)))
            for i, product in enumerate(products):
                self.HomePageFetcher(i)
        else:
            while current != total * 1:

                products = self.driver.find_elements("xpath",
                                                     "//div[contains(@class,'mb1 ph1 pa0-xl bb b--near-white w-25')]")
                print("we in page #{} and it has #{} product".format(current, len(products)))
                for i, product in enumerate(products):
                    self.HomePageFetcher(i)
                current += 1
                # Cooling ..
                time.sleep(1)
                if "search" in self.driver.current_url:
                    url = self.current_url + "&page={}".format(current)
                    self.CaptchaHandler(url)
                else:
                    url = self.current_url + "?page={}".format(current)
                    self.CaptchaHandler(url)
            else:
                products = self.driver.find_elements("xpath",
                                                    "//div[contains(@class,'mb1 ph1 pa0-xl bb b--near-white w-25')]")
                print("we in page #{} and it has #{} product".format(current, len(products)))
                for i, product in enumerate(products):
                    self.HomePageFetcher(i)
                # self.SaveFileToDisk()
                print("All products fetched. saving")
                self.TryToBeep(800,500)

    def TryToGetPagination(self):
        try:
            total = self.driver.find_elements("xpath", "//nav[contains(@aria-label,'page')]/ul/li")[-2].text
            if total and total != "":
                return total * 1
            return 1
        except:
            print("Failed to get pagination")
        return 1

    def CaptchaHandler(self, url=""):
        tries = 0
        self.driver.get(url)
        current = self.driver.current_url
        if "/blocked" in current:

            print("Captcha Detected ...")
            self.TryToGetGoogleCaptcha()
            sk = self.WaitForCaptcha()
            code = self.SolveCaptcha(sk)
            print("Sent to servers")
            self.SendCodeAndClickVerify(code)
            is_solved = self.IsCaptchaSolved()
            while not is_solved and tries != 4:
                try:
                    is_solved = self.IsCaptchaSolved()
                    if is_solved:

                        break
                    else:
                        print("Try #{} failed of ReCaptcha".format(tries))
                        tries = tries + 1
                        sk = self.WaitForCaptcha()
                        code = self.SolveCaptcha(sk)
                        self.SendCodeAndClickVerify(code)
                        is_solved = self.IsCaptchaSolved()
                except:
                    winsound.Beep(frequency, duration)
                    print("Something went wrong. Need Human interaction...")
                    input("enter when you done:     ")
                    break
            else:
                if tries == 5:
                    winsound.Beep(frequency, duration)
                    print("Tried 3 Times. Need Human interaction...")
                    input("enter when you done:     ")
                else:
                    print("Solved!")
            self.driver.get(url)


    def TryToGetGoogleCaptcha(self):
        while True:
            try:
                self.driver.find_element("xpath", '//*[@id="sign-in-widget"]/div[1]/div/a').click()
                break
            except:
                print("Failed to get google captcha")
                time.sleep(0.1)

    def IsCaptchaSolved(self):
        if "/blocked" not in self.driver.current_url:
            print("Captcha Solved")
            winsound.Beep(800, 500)
            return True
        else:
            return False

    def DetectCaptchaModel(self):
        w = 0
        while w != 3:
            try:
                self.driver.find_element("xpath", "//h2[text()='Robot or human?']")
                return True
            except Exception as e:
                print("Captcha detection failed. Continuing.....")
                time.sleep(1)
                w += 1
        return False

    def WaitForCaptcha(self):
        while True:
            try:
                return self.driver.find_element("xpath",
                                                '//div[contains(@data-callback,"handleCaptcha")]').get_attribute(
                    "data-sitekey")
            except:
                time.sleep(0.05)

    def SolveCaptcha(self, sitekey):
        try:
            solver = TwoCaptcha(api_key, sitekey, self.driver.current_url)
            token = solver.solve()
            return token
        except Exception as e:
            print("Something went error while captcha solving", e)

    def SendCodeAndClickVerify(self, code):
        tries = 0
        while "/blocked" in self.driver.current_url and tries != 2:
            try:
                tries += 1
                s = 'handleCaptcha("{}")'.format(code)
                self.driver.execute_script(s)
                time.sleep(2)
            except Exception as e:
                print("Error while sending captcha. need human interaction", e)
                winsound.Beep(frequency, duration)
                input("enter when you done:     ")
                break
        else:
            if tries == 3:
                print("Captcha can't be solved")
                winsound.Beep(frequency, duration)
                input("enter when you done:     ")

    def IsCaptchaSubmitted(self):
        try:

            is_visiable = self.driver.find_element('xpath', '//*[@id="g-recaptcha-response"]').is_displayed()
            while is_visiable:
                is_visiable = self.driver.find_element('xpath', '//*[@id="g-recaptcha-response"]').is_displayed()
            else:
                return True
        except:
            return True

    def HomePageFetcher(self, i):
        try:
            link = self.driver.find_elements("xpath",
                                             "//div[contains(@class,'mb1 ph1 pa0-xl bb b--near-white w-25')]/div/div/a")[
                i].get_attribute("href")
            title = self.driver.find_elements("xpath",
                                              "//div[contains(@class,'mb1 ph1 pa0-xl bb b--near-white w-25')]/div/div/a/span")[
                i].get_attribute("innerHTML")
            image = self.driver.find_elements("xpath",
                                              "//div[contains(@class,'mb1 ph1 pa0-xl bb b--near-white w-25')]/div/div/div/div/div/div/img")[
                i].get_attribute("src")
            product_object = {
                "link": link,
                "title": title,
                "image": image,
                "price": "",
                "original_price": "",
                "rate": "",
                "price_per_unit": "",
                "brand": "",
                "description": "",
                "is_out_of_stock": False,
                "target": self.current_url
            }
            self.products.append(product_object)
        except:
            print("Exception in HomePage Fetcher")

    def onExit(self):
        self.driver.quit()
        self.SaveFileToDisk()
        exit()

    def DeleteSession(self):
        self.driver.delete_cookie("ak_bmsc")

    def SaveFileToDisk(self):
        times = time.time()
        filename = "{}_{}_{}_1.csv".format(self.ZipCode, self.Store, times)
        with open(filename, 'w', newline='',
                  encoding="utf-8-sig", ) as Saver:
            headers = ['title', 'price', "original_price", "price_per_unit", "brand", "rate", 'link', 'image',
                       'description', "is_out_of_stock", "target"]
            dw = csv.DictWriter(Saver, delimiter=',', fieldnames=headers)
            dw.writeheader()
            results_writer = csv.writer(Saver)
            for p in self.products:
                try:
                    results_writer.writerow(
                        [p['title'], p['price'], p['original_price'], p['price_per_unit'], p['brand'], p['rate'],
                         p['link'], p['image'],
                         p['description'], p['is_out_of_stock'], p['target']])
                except Exception as e:
                    print("ERROR: Saving file error, ", e)
                    continue
            self.products = []
        Saver.close()

    def TryToBeep(self, f, d):
        try:
            winsound.Beep(f, d)
        except:
            print("Caan't beep")

    def blockingUnwantedRequest(self):
        self.driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": ["https://collector-pxu6b0qd2s.px-cloud.net/api/v2/collector/beacon",
                                                                        "https://insight.adsrvr.org/","https://www.walmart.com/px/PXu6b0qd2S/xhr/b/s",
                                                                        "https://collector-pxu6b0qd2s.px-cdn.net/b/s","https://www.walmart.com/px/PXu6b0qd2S/init.js"

                                                                        ]})
        self.driver.execute_cdp_cmd('Network.enable', {})
if __name__ == '__main__':
    app = WalmartUSA()
