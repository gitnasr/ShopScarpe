import csv
import logging
import os
import shutil
import sys
import time
import winsound
import humanize
import datetime as dt
from shutil import copyfile
import chromedriver_autoinstaller
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.remote_connection import LOGGER

from captcha import TwoCaptcha

api_key = "2986f38f4866d4c3f187b159f1afd516"
frequency = 2500  # Set Frequency To 2500 Hertz
duration = 2000  # Set Duration To 1000 ms == 1 second
from tinydb import TinyDB, Query

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


class product_fetcher:
    def __init__(self):
        self.products = []
        LOGGER.setLevel(logging.CRITICAL)
        self.folder = input("Folder: ")
        chromedriver_autoinstaller.install()
        options = Options()
        self.is_location_set = False
        options.add_argument("--log-level=3")
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-dev-shm-usage')

        self.driver = webdriver.Chrome(options=options)

        self.driver.maximize_window()
        self.blockingUnwantedRequest()
        for f in os.listdir(self.folder):
            self.file_name = f
            self.zip = self.file_name.split("_")[0]
            self.area = self.file_name.split("_")[1]
            self.db = TinyDB('{}.json'.format(f))
            self.convert_csv_to_array(self.folder)
            if not self.is_location_set:
                self.SetLocation()
            self.ProductFetcher()
            self.TryToBeep(1000, 500)

    def SetLocation(self):
        self.CaptchaHandler("https://www.walmart.com")
        self.WaitTillPopup()
        self.CheckLoadingSpinner()
        zip_input = self.driver.find_element("xpath", "//input[contains(@aria-label,'Enter zip code')]")
        zip_input.clear()
        zip_input.send_keys(self.zip)
        self.CheckLoadingSpinner()
        isca = self.DetectCaptchaModel()
        if isca:
            print("Captcha Detected!, Please Solve")
            input("Type done when you solve the captcha")

        self.driver.find_element("xpath", "//*[contains(text(),'{}')]".format(self.area)).click()
        self.driver.find_element("xpath", "//button[contains(text(),'Save')]").click()
        time.sleep(5)
        self.is_location_set = True

    def convert_csv_to_array(self, folder):
        content = []
        with open("{}/{}".format(folder, self.file_name), newline='', encoding='utf-8-sig') as csvfile:
            csv_reader = csv.reader(csvfile)
            headers = next(csv_reader)

            for row in csv_reader:
                row_data = {key: value for key, value in zip(headers, row)}
                content.append(row_data)

        self.products = content

    def CaptchaHandler(self, url=""):
        tries = 0
        if url:
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
                        print("Try #{} failed of Recaptcha".format(tries))
                        tries = tries + 1
                        sk = self.WaitForCaptcha()
                        code = self.SolveCaptcha(sk)
                        self.SendCodeAndClickVerify(code)
                        is_solved = self.IsCaptchaSolved()
                except:
                    self.TryToBeep(frequency, duration)
                    print("Something went wrong. Need Human interaction...")
                    input("enter when you done:     ")
                    break
            else:
                if tries == 5:
                    print("Last try before beeping")
                    self.driver.get(url)
                    if self.IsCaptchaSolved():
                        print("Solved. But in last try")
                    else:
                        self.TryToBeep(frequency, duration)
                        print("Tried 5 Times. Need Human interaction...")
                        input("enter when you done:     ")
                else:
                    print("Solved!")

            self.driver.get(url)

    def IsCaptchaSolved(self):
        is_blocked = True

        if "/blocked" not in self.driver.current_url:
            is_blocked = False

        is_try_again = self.IsCaptchaTryAgain()
        is_refreshed_captcha = self.IsRefreshedCaptcha()
        if not is_blocked and not is_try_again and not is_refreshed_captcha:
            print("Captcha Solved")
            return True
        else:
            return False

    def IsRefreshedCaptcha(self):
        try:
            self.driver.find_element("xpath",
                                     '//p[text()="Activate and hold the button to confirm that you’re human. Thank You!"]')
            self.TryToGetGoogleCaptcha()
            return True
        except:
            return False

    def IsCaptchaTryAgain(self):
        try:
            self.driver.find_element("xpath", "//p[text()='Please try again']")
            self.driver.find_element("xpath", '//*[@id="sign-in-widget"]/div[1]/div/a').click()
            return True
        except:
            return False

    def TryToGetGoogleCaptcha(self):
        while True:
            try:
                self.driver.find_element("xpath", '//*[@id="sign-in-widget"]/div[1]/div/a').click()
                break
            except:
                print("Failed to get google captcha")
                time.sleep(0.1)

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
                print("Waiting For Loading captcha")
                self.IsCaptchaTryAgain()
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
                self.FillCode(code)
                s = 'handleCaptcha("{}")'.format(code)
                self.driver.execute_script(s)
                time.sleep(2)
            except Exception as e:
                print("Error while sending captcha. need human interaction", e)
                self.TryToBeep(frequency, duration)
                input("enter when you done:     ")
                break
        else:
            if tries == 3:
                print("Captcha can't be solved")
                self.TryToBeep(frequency, duration)
                input("enter when you done:     ")

    def FillCode(self, code):
        while True:
            try:
                self.driver.execute_script(
                    "arguments[0].style.display='inline'",
                    self.driver.find_element("xpath",
                                             '//*[@id="g-recaptcha-response"]'
                                             ),
                )
                self.driver.find_element('xpath', '//*[@id="g-recaptcha-response"]').clear()

                self.driver.execute_script(
                    "document.getElementById('g-recaptcha-response').innerHTML='{}';".format(code))
                self.driver.find_element('xpath', '//*[@id="g-recaptcha-response"]').click()
                break
            except Exception as e:
                print("Loading Captcha ....", e)
                time.sleep(0.1)

    def ProductFetcher(self):
        self.products = self.products[:300]
        for i, product in enumerate(self.products):

            print("#{} of #{}".format(i + 1, len(self.products)))
            is_exited = self.isAlreadyFetched(product['link'])
            if is_exited:
                print("We found: {} already fetched. Skipping...".format(product['link']))
            else:
                start_time = time.time()
                self.CaptchaHandler(product['link'])
                time.sleep(0.5)
                rate = self.TryToGetRate()
                price_per_unit = self.TryToGetPricePerUnit()
                brand = self.TryToGetBrand()
                price = self.TryToGetPrice()

                product['title'] = self.driver.title
                product['brand'] = brand
                product['rate'] = rate
                product['price'] = price
                product['price_per_unit'] = price_per_unit
                product['description'] = self.TryToGetDescription()
                product['is_out_of_stock'] = self.CheckIfOutOfStock()
                product['original_price'] = self.TryToGetOriginalPrice()
                product['extra'] = self.GetProductExtras(product)
                self.db.insert({"title": product['title'], "brand": product['brand'], "rate": product['rate'],
                                "price": product['price'], "price_per_unit": product["price_per_unit"],
                                "description": product['description'],
                                "is_out_of_stock": product['is_out_of_stock'],
                                "original_price": product['original_price'],
                                "extra": product['extra'], "link": product['link'],
                                "image": product['image']})
                end_time = time.time()

                time_used = end_time - start_time

                hum_time = humanize.naturaldelta(time_used)

                estimated = time_used * (len(self.products) - i)

                hum_estimated = humanize.naturaldelta(estimated)

                print("estimated time is {}".format(i, hum_time, hum_estimated))

        self.SaveFileToDisk()

    def isAlreadyFetched(self, link):
        Product = Query()
        is_exited = self.db.contains(Product.link == link)
        if is_exited:
            return True
        return False

    def GetProductExtras(self, product):
        t = ''
        try:
            for e, i in enumerate(
                    self.driver.find_elements("xpath", '//section[@class="expand-collapse-section"]/div/div/div')):
                s = self.driver.find_elements('//section[@class="expand-collapse-section"]/div/div/div')[
                    e].get_attribute("innerHTML")
                text = BeautifulSoup(s, features="html.parser").get_text()
                t += str(text)
            return t
        except Exception:
            return "Extras !"

    def DeleteSession(self):
        self.driver.delete_cookie("ak_bmsc")

    def TryToGetPrice(self):
        try:
            return self.driver.find_elements("xpath", '//span[@itemprop="price"]')[1].get_attribute("innerHTML")
        except:
            return "No Price Detected"

    def TryToGetPricePerUnit(self):
        try:
            return self.driver.find_element("xpath", '//div[@data-testid="oos-price"]/span[2]').text
        except Exception:
            return "No Price Per Unit"

    def TryToGetOriginalPrice(self):
        try:
            return self.driver.find_elements("xpath",
                                             "//div[contains(@class,'di nowrap')]/span[2]")[1].get_attribute(
                "innerHTML")
        except:
            return "No Original Price"

    def TryToGetBrand(self):
        try:
            return self.driver.find_element("xpath", "//div[contains(@itemprop,'brand')]").text
        except:
            return "No Brand Detected"

    def TryToGetRate(self):
        try:
            return self.driver.find_element("xpath", "//span[contains(@class,'rating-number')]").text
        except Exception:
            return "(0)"

    def CheckIfOutOfStock(self):
        try:
            self.driver.find_element("xpath", "//button[text()='Check availability nearby']")
            return True
        except:
            return False

    def TryToGetDescription(self):
        try:
            descriptions = self.driver.find_elements("xpath", "//div[contains(@class,'dangerous-html')]")
            description = ""

            for desc in descriptions:
                text = BeautifulSoup(desc.get_attribute("innerHTML"), features="html.parser").get_text()
                description += str(text)
            return description
        except:
            return "No Description Detected"

    def WaitTillPopup(self):
        while True:
            try:
                self.driver.find_element("xpath", "//input[contains(@aria-label,'Enter zip code')]")
                break
            except:
                self.driver.find_element("xpath", '//*[@id="__next"]/div[1]/div/div/div/section/div/button[1]').click()
                time.sleep(1)

    def CheckLoadingSpinner(self):
        while True:
            try:
                self.driver.find_element("xpath", "//span[contains(@class,'w_B4 w_B7')]")
            except:
                print("Loaded")
                break

    def SaveFileToDisk(self):
        save_name = self.file_name.replace("_1.csv", "_2.csv")
        with open(save_name, 'w', newline='',
                  encoding="utf-8-sig", ) as Saver:
            headers = ['title', 'price', "original_price", "price_per_unit", "brand", "rate", 'link', 'image',
                       'description', "is_out_of_stock", "target", "extras"]
            dw = csv.DictWriter(Saver, delimiter=',', fieldnames=headers)
            dw.writeheader()
            results_writer = csv.writer(Saver)
            for p in self.db.all():
                try:
                    results_writer.writerow(
                        [p['title'], p['price'], p['original_price'], p['price_per_unit'], p['brand'], p['rate'],
                         p['link'], p['image'],
                         p['description'], p['is_out_of_stock'], self.file_name, p['extra']])
                except Exception as e:
                    print("ERROR: Saving file error, ", e)
                    continue
            self.products = []
        Saver.close()
        self.MoveFolder(save_name)

    def MoveFolder(self, save_name):
        try:
            os.makedirs("Synced Folder", exist_ok=True)
            shutil.move(save_name, "Synced Folder")
            shutil.move("{}/{}".format(self.folder, self.file_name), "Synced Folder")
            print("Saved to Synced Folder")
        except:
            print("Already Saved to Synced Folder: {}".format(save_name))

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
    app = product_fetcher()
