# using NN Buy Signals to purchase stock - the results here will be compared to the results 
# from purchasing Options Contracts 

from datetime import timedelta
import pandas as pd  # data processing
import io # converting data to csv 
import requests # importing data from URL

class SmoothYellowFly(QCAlgorithm):
    def Initialize(self):
        # NOTE: QuantConnect provides equity options data from AlgoSeek going back as far as 2010.
        # The options data is available only in minute resolution, which means we need to consolidate
        # the data if we wish to work with other resolutions.
        
        # Download NN Buy Signals from Github Raw CSV
        #self.url = "https://raw.githubusercontent.com/SteenJennings/Neural-Net-Options/master/Kevin/QuantCSV/SNAP_pred_2021-05-28%20(1).csv"
        #self.url = "https://raw.githubusercontent.com/SteenJennings/Neural-Net-Options/master/Kevin/QuantCSV/GME_pred_2021-05-28.csv"
        self.url = "https://raw.githubusercontent.com/SteenJennings/Neural-Net-Options/master/Kevin/QuantCSV/AMC_pred_2021-05-28.csv"
        
        # modify dataframes
        df = pd.read_csv(io.StringIO(self.Download(self.url)))
        # split date column to three different columns for year, month and day 
        df[['year','month','day']] = df['date'].str.split("-", expand = True) 
        df.columns = df.columns.str.lower()
        df = df[df['prediction'] == 1]  # filter predictions
        df['year'] = df['year'].astype(int) 
        df['month'] = df['month'].astype(int) 
        df['day'] = df['day'].astype(int) 
        # filter predictions greater than 2010 because QuantConnect only provides
        # options data as far back as 2010
        df = df[df['year'] >= 2010]
        df = df.drop(columns=['date','prediction'])
        buyArray = df.to_numpy() # convert to array
        
        # Dates below are adjusted to match imported dates from NN
        self.SetStartDate(buyArray[0][1], buyArray[0][2], buyArray[0][3])
        self.SetEndDate(buyArray[-1][1], buyArray[-1][2], buyArray[-1][3])
        self.SetCash(100000) # Starting Cash for our portfolio
        
        # Equity Info Here
        self.stockSymbol = str(buyArray[0][0]) # stock symbol here
        self.equity = self.AddEquity(self.stockSymbol, Resolution.Daily)
        self.SetBenchmark(self.stockSymbol)
        self.ticket = None # Flag for position status
        self.ticketList = []
        self.buyOptionSignal = 0
        self.buyNumOfContracts = 0
        self.portfolioRisk = .05
        
        # iterate through the predictions and schedule a buy event
        for x in buyArray:
            self.Schedule.On(self.DateRules.On(x[1], x[2], x[3]), \
                            self.TimeRules.At(9,35), \
                            self.BuySignal)

    def OnData(self, data):
        ''' OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
            Arguments:
                data: Slice object keyed by symbol containing the stock data
        '''
        if self.buyOptionSignal == 1:
            self.buyNumOfContracts = int((self.portfolioRisk * self.Portfolio.Cash) / self.equity.Price)
            if self.buyNumOfContracts < 1:
                self.buyNumOfContracts = 1
            self.ticket = self.MarketOrder(self.stockSymbol, self.buyNumOfContracts)
            self.ticketList.append(self.ticket)
            self.buyOptionSignal = 0
        
        # Check if we're not invested      
        if self.ticketList:
            for i in self.ticketList:
                if self.UtcTime >= (i.Time + timedelta(days=3)): 
                    # Exit position
                    self.Liquidate(i.Symbol, "Liquidate: Ticket >= 3 Days")
                    self.ticketList.remove(i)
    
    # Sets 'Buy' Indicator to 1
    def BuySignal(self):
        self.Log("BuySignal: Fired at : {0}".format(self.Time))
        self.buyOptionSignal = 1