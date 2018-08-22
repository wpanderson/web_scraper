import os

__author__ = 'wpanderson'
import requests
from bs4 import BeautifulSoup as b
import re
import csv
from threading import Thread
import getpass
import Queue
requests.packages.urllib3.disable_warnings()
import time

#Used for emailing CSV's
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

#Email settings
FROM_ADDR = 'automation@siliconmechanics.com'
TO_ADDR  = ['weston.anderson@siliconmechanics.com']
EMAIL_PASS = 'Platinumcraftedmelon_15'
USER_NAME = FROM_ADDR

'''TROGDOR SCRAPER WARNING: VERY TAXING ON TROGDOR AND SHOULD ONLY BE RUN ON THE DEV SYSTEM OR AFTER HOURS'''


#Production instances for up to date data IT will get yelly though...
INDEX = 'https://trogdor.siliconmechanics.com'
# get all id fields from this list
ENGINEERING_TICKETS_LIST= 'https://trogdor.siliconmechanics.com/engineering/saleseng_ticket_list.php'
# attach all id fields to this sequentially
ENGINEERING_DETAILS= 'https://trogdor.siliconmechanics.com/engineering/saleseng_ticket.php?guid='
# search in ENGINEERING_DETAILS for
ENGINEERING_QUOTES= 'https://trogdor.siliconmechanics.com/quotes/quote.php?id='

ENGINEERING_ORDERS = 'https://trogdor.siliconmechanics.com/orders/order.php?id='
#Info page for a given rma ticket id
RMA_TICKET_INFO = 'https://trogdor.siliconmechanics.com/warehouse/vrma.php?id='


#TODO get new instance of dev environment for Trogdor these links are dead.
#dev instances for testing
# INDEX = 'https://trogdor-ccapps-trunk.siliconmechanics.com/'
#
# ENGINEERING_TICKETS_LIST = 'https://trogdor-ccapps-trunk.siliconmechanics.com/engineering/saleseng_ticket_list.php'
#
# ENGINEERING_DETAILS = 'https://trogdor-ccapps-trunk.siliconmechanics.com/engineering/saleseng_ticket.php?guid='
#E_QUOTES and E_ORDERS denote the location of specifications for a given ticket
# ENGINEERING_QUOTES = 'https://trogdor-ccapps-trunk.siliconmechanics.com/quotes/quote.php?id='
#
# ENGINEERING_ORDERS = 'https://trogdor-ccapps-trunk.siliconmechanics.com/orders/order.php?id='



#Not used by rma scraper.
USER = ''
PASSWORD = ''

rackDict = {}
idList = []
rackInfo= {'28810 - Rackform R4422.v5': [0, 0, 0], '32451 - Rackform R4422.v6': [0, 0, 0]} #specific info on v5 and v6 racks

#info lists regarding specific racks
rackInfoList = []
storFormInfoListv5 = []
storFormInfoListv6 = []

# startTime = datetime.now()
id_queue = Queue.LifoQueue()

#debug
quarterList = []

#TODO modify Trogscraper to allow Engineering ticket scraping.

#TODO change name to find_links
def findQuotes(list):
    """
    Searches Trogdor for quote and order links given an html page.
    Can be modified to find other relevent data from the page

    :param list: lines of html within ENGINEERING_DETAILS
    :return: quotes: a list of sales quotes on ENGINEERING_DETAILS
    """
    quoteCheck = r'Quote (\d+)'
    orderCheck = r'Order ([a-zA-Z]\d+)'
    quotes = []
    for item in list:
        match = re.search(quoteCheck, str(item))
        orderMatch = re.search(orderCheck, str(item))
        if match:
            quote = match.group(1)
            quotes.append(quote)
        elif orderMatch:
            # print(item)
            quote = orderMatch.group(1)
            quotes.append(quote)

    return quotes

def findDate(list):
    """
    Searches a given html list for a date string using regex
    then returns the quarter in which the ticket appears.

    :param list: html of quote page
    :return: year quarter in the form 'yearQx'
    """
    dateCheck = r'created (\d+)-(\d+)'
    for item in list:
        match = re.search(dateCheck, str(item))
        if match:
            # quarterList.append(determineQuarter(month=match.group(2), year=match.group(1)) + ' ' + str(match.group(2)))
            return determineQuarter(month=match.group(2), year=match.group(1))

def determineQuarter(month, year):
    """
    Determines the fiscal quarter given month and year
    then returns a condensed string representing said value.

    :param month: month of the year
    :param year: year (2013 - 2016)
    :return: condensed string of the form 'yearQx' for logic later
    """
    #TODO fix fiscal quarter breakdown
    # print(month, year)
    if year == '2013':
        return '2013Q4'
    if year == '2014':
        if int(month) <= 3:
            return '2014Q1'
        elif int(month) <= 6:
            return '2014Q2'
        elif int(month) <= 9:
            return '2014Q3'
        else:
            return '2014Q4'
    if year == '2015':
        if int(month) <= 3:
            return '2015Q1'
        elif int(month) <= 6:
            return '2015Q2'
        elif int(month) <= 9:
            return '2015Q3'
        else:
            return '2015Q4'
    if year == '2016':
        if int(month) <= 3:
            return '2016Q1'
        if int(month) <= 6:
            return '2016Q2'
        if int(month) <= 9:
            return '2016Q3'
        else:
            return '2016Q4'

def findRack(list, quarter, session, quoteID):
    """
    RE search of html for which rack is attached to the ticket,
    If a rack is round the count is taken then data is passed to findRack Info to get the quarter and reasons.
    finally appending the result to rackDict.

    Explanation (accumulation of tickets):
    The accumulation of tickets is strictly the number of tickets a given rack is in and has no correlation
    with the number of total tickets in a list. This works because a ticket can have multiple racks in it which in
    turn accumulates the number of tickets that rack is in for both racks. So a ticket can count for 2 different racks
    and shows on the csv.

    I made this decision based on the fact that we only care about the number of tickets a rack is in and the total
    number of tickets is just one number that is nice to have.

    :param list: html of engineering details page
    :param quarter: quarter of the ticket
    :param session: login info
    :param quoteID: quote id of this ticket
    :return: none
    """
    #racks to search for add
    rackCheck = r'(\d+) - Rackform (\w+).(\w+)'
    stormCheck = r'(\d+) - Storform (\w+).(\w+)'
    workCheck = r'(\d+) - Workform (\w+).(\w+)'
    otherCheck = r'(\d+) - \w+form (\w+).(\w+)'
    countCheckQuote = r'name="quantity\[\d+]" size="\d" style="text-align: center" type="text" value="(\d+)"'
    countCheckOrder = r'<td align="center" rowspan="4">(\d+)'
    otherCheckOrder = r'<td align="center" rowspan="4" valign="top">\n            (\d+)' #blame this on trogdor...
    # racks = []
    rack = ''
    for item in list:
        rackMatch = re.search(rackCheck, str(item))
        stormMatch = re.search(stormCheck, str(item))
        workMatch = re.search(workCheck, str(item))
        otherMatch = re.search(otherCheck, str(item))
        countMatchQuote = re.search(countCheckQuote, str(item))
        countMatchOrder = re.search(countCheckOrder, str(item))
        countMatchOtherOrder = re.search(otherCheckOrder, str(item))
        if rackMatch:
            rack = rackMatch.group(0)
            # print(rack)
        elif stormMatch:
            rack = stormMatch.group(0)
            # print(rack)
        elif workMatch:
            rack = workMatch.group(0)
            # print(rack)
        elif otherMatch:
            rack = otherMatch.group(0)
            # print(rack)

        if rackMatch or stormMatch or workMatch or otherMatch:
            if countMatchQuote:
                # print('Quantity: ', countMatchQuote.group(1))
                count = countMatchQuote.group(1)
            elif countMatchOrder:
                # print('Quantity: ', countMatchOrder.group(1))
                count = countMatchOrder.group(1)
            elif countMatchOtherOrder:
                # print('Quantity: ', countMatchOtherOrder.group(1))
                count = countMatchOtherOrder.group(1)
            else:
                #TODO enhance the regex to catch all count types
                # print(item)
                count = 1

            get_rack_info(quoteID, rack, session) #rack info
            # print(rack, " Count: ", count)
            if rackDict.has_key(rack):
                # print(rack, quoteID)
                rackDict[rack][0] += 1
                rackDict[rack][1] += int(count)
                updateQuarter(rack, quarter)
            else:
                rackDict.update({rack: [1, int(count), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]})
                updateQuarter(rack, quarter)
            # racks.append(rack)
    #debugging
    if rack != '':
        pass
        # print('No racks in ticket.')
            # rackDict[rack][0] += 1
        # print(ENGINEERING_ORDERS + str(quoteID))
        # print(rack)
    # return racks

def get_rack_info(quoteID, rack, session):
    """
    Determines reasons behind rackform v5 and v6 tickets in Trogdor by going back to the ID page
    to search for buzz words using regex.

    Three categroies:
    -Incorrect or missing RAID/OS/SUM notes
    -Incorrect configurations - parts swap/add/remove
    -Other

    :param quoteID: Quote number to be used in returning to the quote page for rack info.
    :param rack: Either R4422.v5 or R4422.v6 rackform.
    :param session: Session info so we don't have to log back in to request pages.
    :return: returns when process completed
    """
    #TODO Add ability to get in depth info on specific racks
    # print(rack)
    if str(rack) != '28810 - Rackform R4422.v5' and str(rack) != '32451 - Rackform R4422.v6':
        return
    r = session.get(ENGINEERING_DETAILS + str(quoteID), verify=False)
    soup = b(r.text, 'html.parser')
    table = soup.find_all('td')
    info = soup.find_all('div', {'class' : 'communicationthread'})
    for item in table:
        #regex check different categories
        #regex checks for mention of 'raid', 'os', 'sum', or 'raid/os/sum'
        raidMatch = re.search(r' (?i)raid ', str(item))
        osMatch = re.search(r' (?i)os ', str(item))
        sumMatch = re.search(r' (?i)sum ', str(item))
        allMatch = re.search(r'(?i)raid/os/sum', str(item))

        #regex checks for mention of 'swap', 'add', or 'remove' not the best way of doing it... but you know
        swapMatch = re.search(r' (?i)swap ', str(item))
        addMatch = re.search(r' (?i)add ', str(item))
        removeMatch = re.search(r' (?i)remove ', str(item))
        replacementMatch = re.search(r' (?i)replacement ', str(item))

        if raidMatch or osMatch or sumMatch or allMatch:
            if str(rack) == '28810 - Rackform R4422.v5':
                # rackInfoList.append(ENGINEERING_DETAILS + str(quoteID))
                rackInfo[str(rack)][0] += 1
                # print(rackInfo)
                return
            elif str(rack) == '32451 - Rackform R4422.v6':
                # rackInfoList.append(ENGINEERING_DETAILS + str(quoteID))
                rackInfo[str(rack)][0] += 1
                # print(rackInfo)
                return
        elif swapMatch or addMatch or removeMatch or replacementMatch:
            # print('swap Match')
            if str(rack) == '28810 - Rackform R4422.v5':
                # rackInfoList.append(ENGINEERING_DETAILS + str(quoteID))
                rackInfo[str(rack)][1] += 1
                # print(rackInfo)
                return
            elif str(rack) == '32451 - Rackform R4422.v6':
                # rackInfoList.append(ENGINEERING_DETAILS + str(quoteID))
                rackInfo[str(rack)][1] += 1
                # print(rackInfo)
                return
        # print('other match')
    if str(rack) == '28810 - Rackform R4422.v5':
        rackInfoList.append(ENGINEERING_DETAILS + str(quoteID))
        rackInfo[str(rack)][2] += 1
        # print(rackInfo)
    elif str(rack) == '32451 - Rackform R4422.v6':
        rackInfoList.append(ENGINEERING_DETAILS + str(quoteID))
        rackInfo[str(rack)][2] += 1
        # print(rackInfo)

    if str(rack) == '28974 - Storform R518.v5':
        storFormInfoListv5.append(ENGINEERING_DETAILS + str(quoteID))
    elif str(rack) == '32459 - Storform R518.v6':
        storFormInfoListv6.append(ENGINEERING_DETAILS + str(quoteID))

def updateQuarter(rack, quarter):
    """
    Sorts quarter info into appropriate location so it can be broken down in the CSV later.

    :param rack: Rack to compare against rackDict
    :param quarter: Quarter ticket appears in
    """
    #FIXME somehow somewhere the index is slightly off for getting the quarter. FIND IT!
    # print('Update Quarter', rack, quarter)
    if quarter == '2013Q4':
        rackDict[rack][2] += 1
    elif quarter == '2014Q1':
        rackDict[rack][2] += 1
    elif quarter == '2014Q2':
        rackDict[rack][3] += 1
    elif quarter == '2014Q3':
        rackDict[rack][4] += 1
    elif quarter == '2014Q4':
        rackDict[rack][5] += 1
    elif quarter == '2015Q1':
        rackDict[rack][6] += 1
    elif quarter == '2015Q2':
        rackDict[rack][7] += 1
    elif quarter == '2015Q3':
        rackDict[rack][8] += 1
    elif quarter == '2015Q4':
        rackDict[rack][9] += 1
    elif quarter == '2016Q1':
        rackDict[rack][10] += 1
    elif quarter == '2016Q2':
        rackDict[rack][11] += 1
    elif quarter == '2016Q3':
        rackDict[rack][12] += 1
    elif quarter == '2016Q4':
        rackDict[rack][13] += 1

def exportCSV():
    """
    Export to csv from rackDict and rackInfo, does so line by line, with breakdown of quarter info
    as well as specific information regarding v5 and v6 racks

    rackDict:
    value[0] is the amount of tickets associated with the given server rack.
    value[1] is the total amount of server racks we have sold.
    value[2] - value[x] are associated with the amount of tickets a given server rack has had each quarter

    Exports to local directory

    files: TOQ.csv, rackInfo.csv
    """
    print(rackInfo)
    try:
        writer = csv.writer(open('TOQ.csv', 'wb'))
        print('Exporting TOQ CSV...')
        writer.writerow(['Server Model', 'Number of Tickets', 'Total Servers in Tickets', 'Quarter 4 Tickets (2013)',
                         'Quarter 1 Tickets (2014)', 'Quarter 2 Tickets (2014)', 'Quarter 3 Tickets (2014)', 'Quarter 4 Tickets (2014)',
                         'Quarter 1 Tickets (2015)', 'Quarter 2 Tickets (2015)', 'Quarter 3 Tickets (2015)', 'Quarter 4 Tickets (2015)',
                         'Quarter 1 Tickets (2016)', 'Quarter 2 Tickets (2016)', 'Quarter 3 Tickets (2016)', 'Quarter 4 Tickets (2016)'])

        #TODO find where index messes up. currently 2013 doesn't work... So i hotfixed the index at 5 for two values
        for key, value in rackDict.items():
            writer.writerow([key, value[0], value[1], value[2], value[3], value[4], value[5], value[5],
                            value[6], value[7], value[8], value[9], value[10], value[11], value[12], value[13]])

    except IOError as (errno, strerror):
        print('I/O error({0}: {1})'.format(errno, strerror))
    print('Success! TOQ.csv in directory')

    #export csv of rack info
    #key: server model
    #value[0]: incorrect or missing raid/os/sum notes
    #value[1]: incorrect configuration, missing parts and such
    #value[2]: other
    try:
        writer = csv.writer(open('rackInfo.csv', 'wb'))
        print('Exporting rackInfo.csv...')
        writer.writerow(['Server Model', 'raid/os/sum notes', 'incorrect configuration', 'other'])
        for key, value in rackInfo.items():
            writer.writerow([key, value[0], value[1], value[2]])
    except IOError as (errno, strerror):
        print('I/O error({0}: {1})'.format(errno, strerror))
    print('Success! rackInfo.csv in directory')

def userLogin():
    """
    Log in user with given credentials and get the list of ticket ids

    :return: session cookie to maintain login throughout program
    """
    print('Querying all Engineering tickets...')
    #start cookie monster session
    session = requests.session()

    login_data = {
        'ldap-uid': USER,
        'ldap-password': PASSWORD,
        'edit-login': 'submit'
    }

    #Authenticate me!!
    print('Requesting Session...')
    r = session.post(INDEX, data=login_data, verify=False)
    #get engineering ticket list data after login
    r = session.get(ENGINEERING_TICKETS_LIST)

    soup = b(r.text, 'html.parser')
    table = soup.find_all('a')
    soupList = []

    for link in table:
        soupList.append(link)

    for item in soupList:
        if '<a href="/engineering/saleseng_ticket.php?guid=' in str(item):
            ticketId = str(item)[47:54] # a little fragile... at some point change to regex
            if ticketId in idList:
                pass
            else:
            # elif len(idList) < 150: #limit the amount of tickets to 50 for testing
                id_queue.put(ticketId)
                idList.append(ticketId)
    print(len(idList))
    print('Size of Queue', id_queue.qsize())
    return session

def queued_data_loop(session):
    """
    Main data loop once logged in, gets list of ids and initializes a queue to iterate through and gathers data.
    :param session: User Login info
    """
    while not id_queue.empty():
        try: #A more broad exception to try and encapsulate if anything happens during the request process

            print('Ticket Number: ', id_queue.qsize())
            quoteID = id_queue.get()
            print('getting id: ', str(quoteID))
            r = session.get(ENGINEERING_DETAILS+str(quoteID), verify=False)
            soup = b(r.text, 'html.parser')
            table = soup.find_all('a')
            dateTable = soup.find_all('caption')
            dateTableList=[]
            soupList = []
            for link in table:
                soupList.append(link)
            quotes = findQuotes(soupList)

            orderMatch = r'(^[a-zA-Z])(\w+)'

            #Determine the quarter of ticket
            for item in dateTable:
                dateTableList.append(item)
            date = findDate(dateTableList)

            if not quotes:
                print("No quotes...Next ticket!")
                id_queue.task_done()
            else:
                for quote in quotes:  # get rack from each quote
                    #TODO test this area
                    if re.search(orderMatch, str(quote)):
                        r = session.get(ENGINEERING_ORDERS + str(re.search(orderMatch, str(quote)).group(2)),
                                        verify=False)
                        # print(ENGINEERING_ORDERS + str(re.search(orderMatch, str(quote)).group(2)))
                    else:
                        r = session.get(ENGINEERING_QUOTES + str(quote), verify=False)
                    quotehtml = b(r.text, 'html.parser')
                    quotelinks = quotehtml.find_all('tr')
                    quoteDetails = []
                    for link in quotelinks:
                        quoteDetails.append(link)
                    findRack(quoteDetails, date, session, quoteID)  # list of racks from each quote
                    # print("Racks in dict: ", rackDict)
                    # print(racks)
                id_queue.task_done()

        #TODO create more informative error handeling
        except Exception as e:
            import logging
            logging.exception('Something Happened...')
            id_queue.task_done()
    print('Ended at: ', id_queue.qsize())

def toq_ops_query():
    """
    Log in user and assemble list of TOQ Ops tickets from Sales Engineering Ticket list
    continue execution as normal.

    :return: Session data to maintain login
    """
    print('Querying TOQ ops Tickets')
    # start cookie monster session
    session = requests.session()

    login_data = {
        'ldap-uid': USER,
        'ldap-password': PASSWORD,
        'edit-login': 'submit'
    }

    # Authenticate me!!
    print('Requesting Session...')
    r = session.post(INDEX, data=login_data, verify=False)
    # get engineering ticket list data after login
    r = session.get(ENGINEERING_TICKETS_LIST)

    soup = b(r.text, 'html.parser')
    table = soup.find_all('tr')
    soupList = []

    for link in table:
        soupList.append(link)

    #TODO figure out escape character notation for regex
    ticketMatch = r'href="/engineering/saleseng_ticket.php?guid=(+d)'

    print(len(soupList))
    for item in soupList:
        if 'TOQ Ops' in str(item):
            ticketId = str(item)[87:94] #fragile but works for now
            id_queue.put(ticketId)
            idList.append(ticketId)

    print(len(idList))
    print('Size of Queue: %d' % (id_queue.qsize()))

    return session

def threadManager(session):
    """
    Thread manager for trogscraper initializes threads to speed up scraping.
    increase or decrease range(x) to modify speed of scraping process

    :param session: User login info
    """
    #TODO implement keyboard interrupt for multithreading
    try:
        for i in range(2):
            time.sleep(.5)  #stagger threads so output isn't a jumbled mess
            t1 = Thread(target=queued_data_loop, args=(session,))
            t1.start()
        while not id_queue.all_tasks_done:
            time.sleep(.1)
    except (KeyboardInterrupt, SystemExit):
        print('/n! Received keyboard interrupt.\n Exiting...')
        exit()
    id_queue.join()  # wait for the queue to drop to zero before continuing
    exportCSV()  # when threads have finished export to csv

def rack_info_export():
    """
    Exports a file of Trogdor links to all specified racks for in depth analysis.
    :return:
    """

    rackInfo = open('rack_info.txt', 'w')
    rackInfo.write('4422.v5 and 4422.v6')
    for line in rackInfoList:
        rackInfo.write(str(line))
    rackInfo.write('Storform 518.v5')
    for line in storFormInfoListv5:
        rackInfo.write(str(line))
    rackInfo.write('Storform 518.v6')
    for line in storFormInfoListv6:
        rackInfo.write(str(line))

    rackInfo.close()

class Trogscraper():
    """
    Class which controls all objects of rma scraping, and allows organization of various components
    of the RMA scraping procedures including:
        - Session initialization
        - Thread Management
        - RMA Collection
        - RMA emailing
        - CSV output
        - More to come!
    """
    def __init__(self, type, userName, password):
        """
        Initialization for Trogscraper. Creates a new Trogscraper object and initializes parameters
        needed for it to run. This includes initialization of the rma dictionary, user name and password,
        session, and type.

        :param type
        """
        self.typeName = type
        self.session = ''
        self.user = userName
        self.password = password
        self.rmaDict = {}

    def rmaThreadManager(self, queryPage):
        """
        Thread manager for rma tickets. Kicks off scraper to

        :return:
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
            print('/n! Received keyboard interrupt.\n Exiting...')
            exit()
        print('RIGHT BEFORE JOIN', id_queue.qsize())
        id_queue.join()  # wait for the queue to drop to zero before continuing
        self.sort_rma()
        self.exportRMA()

    def exportRMA(self):
        """
        Export method which will put the contents of rmaDict into a csv and email those contents to the indicated
        account.

        """
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

            try:
                # print('test')
                self.send_mail(FROM_ADDR, TO_ADDR, 'Daily RMA Accumulation', 'Trogscraper has completed automated'
                                                                             ' scraping of Trogdor', files=['RMA.csv'])
            except KeyError:
                #TODO make better error logging
                print('Key error exception was thrown')
        except IOError as (errno, strerror):
            print('I/O error({0}: {1})'.format(errno, strerror))
        print('Success! RMA.csv in directory')

    def send_mail(self, send_from, send_to, subject, text, files=None, server="smtp.gmail.com:587"):
        """
        Helper function for sending mail from automation to a given address

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
        Login to Trogdor and initialize session data
        """
        #TODO add timeout and failure try catch
        print('Querying RMA Tickets')
        # start cookie monster session
        self.session = requests.session()

        login_data = {
            'ldap-uid': self.user,
            'ldap-password': self.password,
            'edit-login': 'submit'
        }

        #Authenticate me!
        print('Requesting Session...')
        r = self.session.post(INDEX, data=login_data, verify=False)

    def scraper(self, queryPage):
        """
        Begins scraping process by directing function to page with a table and grabbing all tr tagged lines of html then
        returns them

        :return:
            - list of rmaTickets in trogdor
        """
        rmaIDPattern = r'id=(\d+)">V\d+'
        # Matches: Group 1: Vendor, Group 2: Items, Group 3: Date created... One regex to rule them all
        rmaTablePattern = r'vendors.php\?edit=\d+&amp;tab=vrma">(.*?)</a></td><td>(.*?)</td><td>.*?</td><td>(.*?)<'

        data = self.session.get(queryPage)

        soup = b(data.text, 'html.parser')
        #Find all tickets in
        table = soup.find_all('tr')
        # print(type(table))
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
                # print(rmaMatch.group(1))
                # id_queue.put(rmaMatch.group(1))
                # idList.append(rmaMatch.group(1))

        print(len(self.rmaDict))
        for key, value in self.rmaDict.items():
            if not id_queue.qsize() > 100:
                id_queue.put(key)


            # print(key, value[0], value[1], value[2], value[3], value[4])

        print('Size of Queue: %d' % (id_queue.qsize()))

        self.rmaThreadManager(session)

    #TODO convert this to rma scraping it is copy and pasted from id_queue loop.
    def rmaScraper(self):
        """
        Web scraping algorithm specific to RMA tickets. Gathers information from the RMA table such as:
        Manufacturer model no. and manufacturer serial no.
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
                    # print(row)
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

    selected = '3'
    while selected == '':
        print('Welcome to Trogscraper!')
        print('1. RMA Data')
        print('2. RMA ticket accumulator')
        selected = raw_input('What do you want to do? ')
        if selected == '1':
            print('Which vendor would you like to see graphed?')
    #     print('1. Full TOQ grab')
    #     print('2. TOQ Ops tickets')
    #     print('3. RMA ticket accumulator')
    #     selected = raw_input('What do you want to do? ')
    #     if selected == '1':
    #         print('Login using Trogdor credentials')
    #     elif selected == '2':
    #         print('Login using Trogdor credentials')
    #     elif selected == '3':
    #         print('Login using Trogdor credentials')
    #     else:
    #         selected = ''
    userName = raw_input('Trogdor Login: ')
    # userPassword = raw_input('Trogdor Password: ')
    userPassword = getpass.getpass('Trogdor Password: ') #Allows password to not show.
    USER = userName
    PASSWORD = userPassword

    session = ''
    start_time = time.time()
    if selected == '1':
        session = userLogin()
    elif selected == '2':
        session = toq_ops_query()
    elif selected == '2':
        trog_object = Trogscraper('RMA Query', userName=userName, password=userPassword)
        trog_object.login()
        trog_object.scraper('https://trogdor.siliconmechanics.com/warehouse/vrma_list.php')

    # session = userLogin()
    # session = toq_ops_query()
    # threadManager(session)

    # if selected != '3':
    #     threadManager(session)
    #     for item in quarterList:
    #         print(item)


    print("---Trogscraper completed in %s minutes ---" % ((time.time() - start_time)/60.0))
