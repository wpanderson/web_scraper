__author__ = 'wpanderson'

#Scraper Imports
import os
import requests
from bs4 import BeautifulSoup as b
import re
import csv
from threading import Thread
import getpass
import Queue
requests.packages.urllib3.disable_warnings() #Disable unwanted errors while scraping particularly on login
import time

#Used for emailing CSV's
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

#Email settings
FROM_ADDR = 'FROM'
TO_ADDR  = ['TO']
EMAIL_PASS = 'PW'
USER_NAME = FROM_ADDR

'''TROGDOR SCRAPER WARNING: VERY TAXING ON TROGDOR AND SHOULD ONLY BE RUN ON THE DEV SYSTEM OR AFTER HOURS'''

#Production instances for up to date data IT will get yelly though... So use after hours only!
INDEX = ''
RMA_TICKET_LIST = ''
RMA_TICKET_INFO = ''
TOTAL_ITEMS_INFO = '' #List of items

id_queue = Queue.LifoQueue() #Queue for keeping track of how many tickets are left to scrape.

#Color Codes!!!!!
HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

class Trogscraper():
    """
    Class which controls all objects of rma scraping, and allows organization of various components
    of the RMA scraping procedures including:

        - Session initialization
        - Thread Management
        - RMA Collection
        - RMA emailing
        - CSV output
        - More to come! (Data Visualization)
    """
    def __init__(self, userName, password):
        """
        Initialization for Trogscraper. Creates a new Trogscraper object and initializes parameters
        needed for it to run. This includes initialization of the rma dictionary, session, username and password.

        :param userName: userName of the user using the program.
        :param password: password of the user using the program.
        """

        self.user = userName
        self.password = password
        self.rmaDict = {}
        self.itemDict = {}
        self.session = self.login()

    def rmaThreadManager(self):
        """
        Thread manager for rma tickets. Kicks off 10 threads on rmaScraper to collect
        data from it. When all tasks have been completed sort_rma is called to sort the
        dictionary containing all of the RMAs into a readable form. Then exportRMA is called
        to create a CSV of the data and then send an email.
        """
        try:
            for i in range(10):
                time.sleep(.5)  # stagger threads so output isn't a jumbled mess
                t1 = Thread(target=self.rmaScraper)
                t1.daemon = True
                t1.start()
            while not id_queue.all_tasks_done:
                time.sleep(.1)
        except (KeyboardInterrupt, SystemExit):
            print('/n! Received keyboard interrupt.\n Exiting without saving...')
            exit()
        print('RIGHT BEFORE JOIN', id_queue.qsize())
        id_queue.join()  # wait for the queue to drop to zero before continuing
        self.sort_rma()
        self.exportRMA()

    def exportRMA(self):
        """
        Export method which will put the contents of rmaDict into a csv and email those contents to the indicated
        account. This is the final step of scraper and compiles all information

        """
        #DEBUG
        # for key, value in self.rmaDict.items():
        #     print(key, value[0], value[1], value[2], value[3], value[4])

        try:
            writer = csv.writer(open('RMA.csv', 'wb'))
            print('Exporting rma data to csv...')
            writer.writerow(['Manufacturer', 'Model Number', 'Serial Numbers', 'Items', 'Date Created'])

            #rmaDict structure: ticketNumber: [Vendor, Model_Number, [Serial_Numbers], items, date_created]

            for key, value in self.rmaDict.items():
                writer.writerow([value[0], value[1], value[2], value[3], value[4]])


            rma_file = "RMA.csv"
            rma_file = [os.getcwd() + '/RMA.csv']

            #TODO implement graph creation of data. ==========================

            try:
                print('Sending email...')
                # self.send_mail(FROM_ADDR, TO_ADDR, 'Daily RMA Accumulation', 'Trogscraper has completed automated'
                #                                                              ' scraping of Trogdor', files=['RMA.csv'])
            except KeyError:
                #TODO make better error logging
                print('Key error exception was thrown')
        except IOError as (errno, strerror):
            print('I/O error({0}: {1})'.format(errno, strerror))
        print('Success! RMA.csv in directory')

    def send_mail(self, send_from, send_to, subject, text, files=None, server="smtp.gmail.com:587"):
        """
        Helper function for sending mail from automation to a given address.

        :param send_from: Simech Automation email account
        :param send_to: Simech Sales and other interested parties.
        :param subject: Subject of the automation email.
        :param text: Text to send with the email.
        :param files: CSV file which will be attached to the email.
        :param server: default gmail server?
        """

        print('Sending email...')
        msg = MIMEMultipart()
        msg['From'] = send_from
        msg['To'] = COMMASPACE.join(send_to)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject

        msg.attach(MIMEText(text))
        # print('prefile')
        for f in files or []:
            print('File: ', f)
            with open(f, 'rb') as fil:
                part = MIMEApplication(fil.read(), Name=os.path.basename(f))
                part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(f)
                msg.attach(part)
        # print('complete')
        smtp = smtplib.SMTP(server)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(USER_NAME, EMAIL_PASS)
        smtp.sendmail(send_from, send_to, msg.as_string())
        smtp.close()
        print('Email sent to {0}!'.format(send_to))

    # TODO
    def scrape_items(self):
        """
        Query TOTAL_ITEMS_INFO and scrape page for Vendor and Quantity. Accumulates this data into a dictionary
        which identifies a vendor and the number of items we have ordered from them. This is useful for
        visualization data.
        """
        # The all powerful regex! Match 1: Vendor Match 2: Quantity (Don't really care about anything else yet.)
        vendorItemPattern = r'vendors.php\?edit=\d+">(.*?)</a></td>\s+?<td>.*\s+?.*?</td>\s+?.*?</td>\s+?.*?</td>\s+?.*?</td>\s+?.*?</td>\s+?<.*?>(\d+)</td>'

        data = self.session.get(TOTAL_ITEMS_INFO)
        soup = b(data.text, 'html.parser')
        print(soup)
        table = soup.find_all('tr')
        itemList = []

        for row in table:
            itemList.append(row)


        print(len(table))
        count = 0
        for row in itemList:
            if count < 20:
                print(row)
                print('======================================================================')
            count += 1
            match = re.search(vendorItemPattern, str(row))
            if match:
                if match.group(1) in self.itemDict.keys():
                    self.itemDict[match.group(1)] += int(match.group(2))
                else:
                    self.itemDict.update({match.group(1): int(match.group(2))})

        print(len(self.itemDict))
        for key, value in self.itemDict.items():
            print(key, value)

    def sort_rma(self):
        """
        Dictionary sort function for use after all tickets have been compiled. Sorts Entire dictionary by Vendor
        and Model number and combines tickets with same value. Including number of items and date created.

        Complexity: O(n^2)
        """
        #TODO optimize this sorting algorithm currently O(n^2) for 19000+ n...
        newDict = {}
        print('Sorting RMA list...')
        for key, value in self.rmaDict.items():
            temp_dict = {}
            temp_dict.update({key: self.rmaDict.pop(key)})
            if not newDict:
                newDict.update(temp_dict)
            else:
                updated = False
                for key1, value1 in newDict.items():
                    if value1[0] == temp_dict[key][0] and value1[1] == temp_dict[key][1]:
                        items = int(value1[3]) + int(temp_dict[key][3])
                        newDict[key1][3] = items
                        if type(newDict[key1][4]) == list:
                            newDict[key1][4].append(temp_dict[key][4])
                        else:
                            temp_date = newDict[key1][4]
                            newDict[key1][4] = [temp_date, temp_dict[key][4]]
                        updated = True
                if not updated:
                    newDict.update(temp_dict)

        # print('NEW DICTIONARY: ', newDict)
        self.rmaDict = newDict
        print('RMA sort complete!')

    def sort_rma_date(self):
        """
        Sort function to take all dates in the date created list of each dictionary pair and expands this data to reflect
        the amount of rma's in the last month, 3 months, 6 months, and year, then place this data in a new dictionary.
        Upon successful restructure the new dictionary is swapped with the current dictionary.
        :return:
        """


    def login(self):
        """
        Login to Trogdor using user and password then return the session data to be maintained
        throughout the program.

        :return session: Session data for the user so we can stay logged in.
        """
        #TODO add timeout and failure try catch
        print('Querying RMA Tickets')
        # start cookie monster session
        session = requests.session()

        login_data = {
            'ldap-uid': self.user,
            'ldap-password': self.password,
            'edit-login': 'submit'
        }

        #Authenticate me!
        print('Requesting Session...')
        try:
            r = session.post(INDEX, data=login_data, verify=False)
            print(WARNING + 'Login Response: ' + str(r) + ENDC)
        except requests.exceptions.RequestException as e:
            print(WARNING + e + ENDC)
            exit()
        print(str(session))
        return session

    def scraper(self, queryPage):
        """
        Begins scraping process by accumulating all of the id's from:
        https://trogdor.wpanderson.com/warehouse/vrma_list.php
        This allows an accumulation of all of the RMA tickets in trogdor, as well as a way to navigate to
        their various pages. Once accumulated rmaThreadManager is started.

        :param queryPage: https://trogdor.wpanderson.com/warehouse/vrma_list.php
        """
        rmaIDPattern = r'id=(\d+)">V\d+'
        # Matches: Group 1: Vendor, Group 2: Items, Group 3: Date created... One regex to rule them all
        rmaTablePattern = r'vendors.php\?edit=\d+&amp;tab=vrma">(.*?)</a></td><td>(.*?)</td><td>.*?</td><td>(.*?)<'

        data = self.session.get(queryPage)
        # print('session data: ' + str(data))
        soup = b(data.text, 'html.parser')
        # print('html stuff: ' + str(soup))
        table = soup.find_all('tr')
        rmaList = []

        for row in table:
            rmaList.append(row)

        print(len(rmaList))
        for rma in rmaList:
            # print(rmaList)
            rmaMatch = re.search(rmaIDPattern, str(rma))
            if rmaMatch:
                dataMatch = re.search(rmaTablePattern, str(rma))
                if dataMatch:
                    self.rmaDict.update({rmaMatch.group(1): [dataMatch.group(1), None, None, dataMatch.group(2),
                                                             dataMatch.group(3)]})
                #DEBUG
                # print(rmaMatch.group(1))
                # id_queue.put(rmaMatch.group(1))
                # idList.append(rmaMatch.group(1))

        print(len(self.rmaDict))
        for key, value in self.rmaDict.items():
            if not id_queue.qsize() > 100:
                id_queue.put(key)

            #DEBUG
            # print(key, value[0], value[1], value[2], value[3], value[4])

        print('Size of Queue: %d' % (id_queue.qsize()))

        self.rmaThreadManager()

    def rmaScraper(self):
        """
        Web scraping algorithm specific to RMA tickets and multithread compatible. Gathers information from the
        RMA table such as:
        - Manufacturer model no.
        - Manufacturer serial no.

        This continues until id_queue is empty
        """
        rmaModelPattern = r'mfr_model_number]" size="\d+" type="text" value="(.*?)"'
        rmaSerialPattern = r'mfr_serial_number]" size="\d+" type="text" value="(.*?)"'

        while not id_queue.empty():
            try:  # A more broad exception to try and encapsulate if anything happens during the request process

                print('Ticket Number: ', id_queue.qsize())
                quoteID = id_queue.get()
                print('Getting RMA ticket: ', 'V' + str(quoteID))
                r = self.session.get(RMA_TICKET_INFO + str(quoteID), verify=False)
                soup = b(r.text, 'html.parser')
                # caption = soup.find_all('caption')
                table = soup.find_all('tr')
                model_number = ''
                serial_number_list = []

                for row in table:
                    modelMatch = re.search(rmaModelPattern, str(row))
                    serialMatch = re.search(rmaSerialPattern, str(row))
                    if modelMatch:
                        model_number = modelMatch.group(1)
                        # print('Model Number')
                        # print('Model match', modelMatch.group(1))
                    if serialMatch:
                        serial_number_list.append(serialMatch.group(1))
                        # print('Serial')
                        # print('Serial Match', serialMatch.group(1))

                #Find dictionary index with rma ticket number
                if self.rmaDict.has_key(quoteID):
                    self.rmaDict[quoteID][1] = model_number
                    self.rmaDict[quoteID][2] = serial_number_list

                # print(self.rmaDict[quoteID])
                id_queue.task_done()
            #TODO better exception handling... this is baby games
            except Exception as e:
                import logging
                #Make a a none terrible logged exception
                logging.exception('Something Happened...')
                id_queue.task_done()
        print('Ended at: ', id_queue.qsize())

if __name__ == '__main__':
    """
    Gather username and password and start scraping process.
    """
    print(WARNING + 'Warning: Trogscraper is very taxing on the network and should '
                    'only be used during off hours.\n' + ENDC)
    print('Welcome to Trogscraper!\nPlease enter your info to get started.\n')

    userName = raw_input(OKGREEN + 'Trogdor Login: ' + ENDC)
    # userPassword = raw_input('Trogdor Password: ')
    userPassword = getpass.getpass(OKGREEN + 'Trogdor Password: ' + ENDC) #Allows password to not show.

    start_time = time.time()
    trog_object = Trogscraper(userName=userName, password=userPassword)
    # TODO get total item scrape working
    # trog_object.scrape_items()
    trog_object.scraper(RMA_TICKET_LIST)

    #Call graphing functions when we get there.
    # matplotlib??

    print("---Trogscraper completed in %s minutes ---" % ((time.time() - start_time)/60.0))
