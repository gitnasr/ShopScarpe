import csv
import json
import time
import urllib
import undetected_chromedriver as uc
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException, \
    NoSuchElementException

import requests
from selenium.webdriver import Keys


class Instacart:
    def __init__(self):
        self.current_url = ""
        self.products = []
        self.links = []
        self.zip = input("ZIP Code: ")
        self.GetLocationsFromZip()
        self.Location = input("Select from above locations: ")
        self.Address = input("Type Address: ")
        self.GetAddressesFromLocation()
        self.Area = input("Select from above areas: ")

        self.driver = uc.Chrome()
        self.driver.maximize_window()

        print("For ZIP {} you selected {} location with {} address at {} area".format(self.zip, self.Location,
                                                                                      self.Address, self.Area))
        self.LoopTargets()

    def GetLocationsFromZip(self):
        q1 = {"query": str(self.zip), "coordinates": None}
        q1 = self.convert_obj_to_var(q1)
        q2 = {"persistedQuery": {"version": 1,
                                 "sha256Hash": "f720dae8b46e5d5cb6bd351762296829f4c6efbfc2d19b96c64021f75424e747"}}
        q2 = self.convert_obj_to_var(q2)

        req = requests.get(
            "https://www.instacart.com/graphql?operationName=AutoCompleteLocations&variables={}&extensions={}".format(
                q1, q2)).json()

        locations = req['data']['autocompleteLocations']['locations']

        for location in locations:
            print(location['viewSection']['lineTwoString'])

    def GetAddressesFromLocation(self):
        q1 = {"query": self.Address, "coordinates": None}
        q1 = self.convert_obj_to_var(q1)
        q2 = {"persistedQuery": {"version": 1,
                                 "sha256Hash": "f720dae8b46e5d5cb6bd351762296829f4c6efbfc2d19b96c64021f75424e747"}}
        q2 = self.convert_obj_to_var(q2)
        req = requests.get(
            "https://www.instacart.com/graphql?operationName=AutoCompleteLocations&variables={}&extensions={}".format(
                q1, q2)).json()

        locations = req['data']['autocompleteLocations']['locations']
        for location in locations:
            print(location['streetAddress'], location['postalCode'], location['viewSection']['lineOneString'],
                  location['viewSection']['lineTwoString'])

    def convert_obj_to_var(self, q):
        j = json.dumps(q)
        return urllib.parse.quote_plus(j)

    def LoopTargets(self):
        with open('targets.txt', 'r') as f:
            links = [line.strip() for line in f]
        f.close()
        links = list(filter(None, links))
        for link in links:
            if "https://www.instacart.com/" in link:
                self.current_url = link
            else:
                self.current_url = "https://www.instacart.com/store/foodhall/search/" + link
            print(self.current_url)
            self.GetHomeProducts()

    def GetHomeProducts(self):
        print("Home products")
        self.driver.get("https://www.instacart.com/store/publix/storefront")
        self.SelectLocation()
        self.driver.get(self.current_url)
        self.IsLoading()
        self.LoadMore()
        self.FetchProducts()
        self.SaveToFile()

    def SelectLocation(self):
        self.driver.find_element("xpath", "//div[contains(@class,'DeliveryAddressPicker')]").click()
        self.ShimmerEffectDetection()
        self.EnterZipCode()
        self.ShimmerEffectDetection()
        self.SelectLocationFromAddress()
        self.ShimmerEffectDetection()
        self.SelectAddress()
        self.ShimmerEffectDetection()
        self.SelectArea()
        self.driver.find_element("xpath", "//span[text()='Save Address']").click()
        time.sleep(5)
        self.CheckIfModalIsShowing()

    def CheckIfModalIsShowing(self):
        while True:
            try:
                self.driver.find_element("xpath", "//span[text()='No thanks']").click()
            except:
                print("Modal Not Found")
                break

    def ShimmerEffectDetection(self):
        while True:
            try:
                self.driver.find_elements("xpath", "//div[contains(@data-testid,'loading-list-test-id')]")
                print("Loading...")
                time.sleep(0.5)
                break
            except:
                print("Loaded!")
                break

    def EnterZipCode(self):
        while True:
            try:
                self.driver.find_element("xpath", "//input[contains(@id,'streetAddress')]").send_keys(self.zip)
                break
            except:
                print("Need time to load..")
                time.sleep(1)

    def SelectArea(self):
        while True:
            try:
                self.driver.find_element("xpath", "//span[text()='{}']".format(self.Area)).click()
                break
            except:
                print("Need time to load..")
                time.sleep(1)

    def SelectLocationFromAddress(self):
        while True:
            try:
                self.driver.find_element("xpath", "//span[text()='{}']".format(self.Location)).click()
                break
            except:
                print("Need time to load..")
                time.sleep(1)

    def SelectAddress(self):
        while True:
            try:
                self.driver.find_element("xpath", "//input[contains(@id,'streetAddress')]").send_keys(self.Address)
                break
            except:
                print("Need time to load..")
                time.sleep(1)

    def IsHasMore(self):
        try:
            self.driver.find_element("xpath", "//button[contains(@class,'LoadMore')]")
            return True
        except:
            print("No is more")
            return False

    def IsLoading(self):
        count = 1
        while count != 0:
            try:
                count = len(self.driver.find_elements("xpath", "//div[contains(@aria-label,'Loading')]"))
                time.sleep(2)
            except:
                count = 0

    def LoadMore(self):
        more = self.IsHasMore()
        while more:
            try:
                self.driver.find_element("xpath", "//button[contains(@class,'LoadMore')]").click()
                self.IsLoading()
                more = self.IsHasMore()
            except StaleElementReferenceException as e:
                print("Loading..")
                more = True
            except ElementClickInterceptedException:
                time.sleep(1)
                self.driver.find_element_by_css_selector("body").send_keys(Keys.PAGE_UP)
                self.driver.find_element_by_css_selector("body").send_keys(Keys.PAGE_DOWN)
                self.driver.find_element_by_css_selector("body").send_keys(Keys.PAGE_UP)
                self.driver.find_element_by_css_selector("body").send_keys(Keys.PAGE_DOWN)
                more = self.IsHasMore()

            except NoSuchElementException:
                self.driver.find_element_by_css_selector("body").send_keys(Keys.PAGE_UP)
                self.driver.find_element_by_css_selector("body").send_keys(Keys.PAGE_DOWN)
                more = self.IsHasMore()
        else:
            print("Loaded all products")

    def FetchProducts(self):
        products = self.driver.find_elements("xpath", "//div[contains(@class,'ItemCardHoverProvider')]")
        for i, product in enumerate(products):
            link = self.driver.find_elements("xpath", "//div[contains(@class,'ItemCardHoverProvider')]/div/div/a")[
                i].get_attribute("href")
            self.links.append(link)
            print("#{} - #{}".format(i + 1, len(products)))
        print("We got #{} product(s). start fetching data".format(len(self.links)))
        self.driver.close()
        self.GoThroughEveryProduct()
        self.driver.quit()

    def GoThroughEveryProduct(self):
        for link in self.links:
            item = link.split("/items/")[1]
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'Cookie': '__Host-instacart_sid=7UgrCEYOF-qGKuN08_yj_UvsXU5AboBaacxdWwSFAv0'}
            try:
                req = requests.get("https://www.instacart.com/v3/containers/items/{}".format(item), headers=headers)
                req = req.json()
                title = req['container']['title']
                price = req['container']['modules'][0]['data']['item']['pricing']['price']
                price_per_unit = req['container']['modules'][0]['data']['item']['pricing']['price_per_unit']
                units = req['container']['modules'][0]['data']['item']['size']
                image = req['container']['modules'][0]['data']['item']['image']['url']
                description = self.TryToGetProductDescription(req)
                ingredient = self.TryToGetProductIngredient(req)
                product_object = {
                    "title": title,
                    "price": price,
                    "price_per_unit": price_per_unit,
                    "units": units,
                    "image": image,
                    "description": description,
                    "ingredient": ingredient,
                    "link": link
                }
                self.products.append(product_object)
            except Exception as e:
                print("ERROR:{}".format(e))
                pass

    def TryToGetProductDescription(self, j_request):
        modules_len = len(j_request['container']['modules'])
        modules = j_request['container']['modules']
        for m in range(0, modules_len):
            try:
                desc_len = len(modules[m]['data']['details'])
                for ii in range(0, desc_len):
                    if modules[m]['data']['details'][ii]['header'] == "Details":
                        return modules[m]['data']['details'][ii]['body']
                    return "No Description Detected!"
            except:
                pass

    def TryToGetProductIngredient(self, j_request):
        modules_len = len(j_request['container']['modules'])
        modules = j_request['container']['modules']
        for m in range(0, modules_len):
            try:
                desc_len = len(modules[m]['data']['details'])
                for ii in range(0, desc_len):
                    if modules[m]['data']['details'][ii]['header'] == "Ingredients":
                        return modules[m]['data']['details'][ii]['body']
                    return "No ingredient Detected!"
            except:
                pass

    def SaveToFile(self):
        with open('{}_{}_{}.csv'.format(self.zip, self.Area, time.time()), 'w', newline='',
                  encoding="utf-8-sig", ) as Saver:
            headers = ['Title', 'Price', 'Price Per Unit', 'Units', 'Link', 'Image',
                       'Description']
            dw = csv.DictWriter(Saver, delimiter=',', fieldnames=headers)
            dw.writeheader()
            results_writer = csv.writer(Saver)
            for p in self.products:
                try:

                    results_writer.writerow(
                        [p['title'], p['price'], p['price_per_unit'], p['units'], p['link'],
                         p['image'],
                         p['description']])
                except Exception as e:
                    print("ERROR: Saving file error, ", e)
                    continue
            self.products = []


if __name__ == '__main__':
    app = Instacart()
