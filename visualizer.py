__author__ = 'wpanderson'

#plotly initialization
import plotly
plotly.tools.set_credentials_file(username='', api_key='') #initialize plotly key
plotly.tools.set_config_file(world_readable=False, sharing='private')

#bokeh imports
from bokeh.charts import Bar, output_file, show
from bokeh.models import *

#data analytics
import pandas as pd
import numpy as np

#line plot imports
import plotly.plotly as py
import plotly.graph_objs as go

#csv imports
import csv

#Color Codes!!!!!
HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

class Visualizer():
    """
    visualizer is a class for generating data visualization of RMA tickets
    collected from trogdor. This is accomplished by either graphing data from
    a CSV file specified by the user or passed dictionary.
    """
    def __init__(self):
        """
        Initialization of Visualizer. Can be initialized using a CSV file
        or a dictionary passed from rma_query.
        """
        self.dataDict = {} #Data dictionary from Trogscraper
        self.dataList = [] #data list of dictionaries from CSV

    def get_csv(self, fileName):
        """
        Given the filename of csv file retrieve the data from it and store it in a list of dictionaries
        Format Sample:
        [{'Serial Numbers' "", 'Items': "", 'Date Created': "", 'Model Number': "", 'Manufacturer': ""}, ...]

        :param fileName: fileName of CSV to read from

        """
        with open('RMA_Data/' + fileName) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['Items'] is not None: #Catch data that would crash later stuff
                    self.dataList.append(row)

        print('Number of RMAs: ' + str(len(self.dataList)))

    def man_vis(self):
        """
        Creates a visualization which accumulates all ticket information for all manufacturers
        and displays it.

        X-Axis: Manufacturer
        Y-Axis: Number of Tickets

        """
        manList = [] #For X-Axis Labeling
        itemList = [] #For Y-Axis Labeling
        manDict = {} #For number of rmas per manufacturer
        for item in self.dataList:
            if item['Manufacturer'] not in manDict:
                manDict.update({item['Manufacturer']: int(item['Items'])})

            if item['Manufacturer'] in manDict:
                manDict[item['Manufacturer']] += int(item['Items'])

        #Ask user if they would like to split high rma data from low rma.
        split = raw_input("Would you like to split outliers from data?(Y/N) ")
        if "Y" in str.upper(split):
            split = True
        else:
            split = False

        splitManH = [] #List of manufacturers (high rma)
        splitItemH = [] #List of rma numbers (high rma)
        splitManL = [] #List of manufacturers (low rma)
        splitItemL = [] #List of manufacturers (low rma)
        for rma in sorted(manDict, key=lambda s: s.lower()):
            if split == True:
                if int(manDict[rma]) > 400:
                    splitManH.append(rma)
                    splitItemH.append(manDict[rma])
                else:
                    splitManL.append(rma)
                    splitItemL.append(manDict[rma])
            else:
                manList.append(rma)
                itemList.append(manDict[rma])

        #DEBUG: Displays each manufacturer and the number of RMA's it has
        # for index in range(len(manList)):
        #     print(manList[index] + ' ' + str(itemList[index]))

        #bokeh chart
        print(split)
        if split:
            h = pd.Series(splitItemH, index=splitManH)
            print('Outlier data')
            print(h)
            hb = Bar(h, title='High RMA Manufacturers', xlabel="Manufacturer",
                     ylabel="Amount of RMA's", legend=False)
            output_file("high_rma.html")
            show(hb)
            l = pd.Series(splitItemL, index=splitManL)
            print('Condenced data')
            print(l)
            lb = Bar(l, title='Low RMA Manufacturers', width=1500, xlabel="Manufacturer",
                     ylabel="Amount of RMA's",
                     legend=False)
            output_file("low_rma.html")
            show(lb)
        else:
            s = pd.Series(itemList, index=manList)
            print('Entire list: ')
            print(s)
            p = Bar(s, width=2000, legend=False)
            output_file("rma.html")
            show(p)

        # p = Bar(s, width=2000, legend=False)
        # output_file("rma.html")
        # show(p)

        #Plotly stuff
        # trace0 = go.Bar(
        #     x=manList,
        #     y=itemList,
        #     text=manList,
        #     marker=dict(
        #         color='rgb(158,202,225)',
        #         line=dict(
        #             color='rgb(8,48,107)',
        #             width=1.5,
        #         )
        #     ),
        #     opacity=0.6
        # )
        #
        # data = [trace0]
        # layout = go.Layout(
        #     title="Number of RMA's per manufacturer",
        # )
        # fig = go.Figure(data=data, layout=layout)
        # py.iplot(fig, filename='Manufacturer RMA')

    def date_vis(self, man):
        """
        Creates a data visualization which accumulates tickets for a specific manufacturer and
        displays it according to date the ticket was created.

        X-Axis: Date
        Y-Axis: Number of Tickets

        :param man: Manufacturer to display information on

        """

if __name__ == '__main__':
    """
    Initialize standalone Visualizer which will gather information from a
    specified csv and display visualization data based on that. The benefit
    of this is that we don't need to run trogscraper every time we want to
    see different data visualizations.
    """
    print(HEADER + 'Visualizer version: 1.0\n' + ENDC)
    fileName = raw_input('Please enter the name of the file for data visualization: ')
    print('retrieving ' + fileName)
    vs = Visualizer()
    vs.get_csv(fileName)
    vs.man_vis()
