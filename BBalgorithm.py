import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import style
from tkinter import *
from PIL import ImageTk, Image
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

root = Tk()
root.title("BB trading algorithm")
root.geometry("800x600")

path = resource_path("bg.jpg")
img = ImageTk.PhotoImage(Image.open(path))
myLabel = Label(root,image = img)
myLabel.pack()

text = Label(root, text="Enter cryptocurrency:")
text_2 = Label(root, text="use ´-´ for space, for example: sportemon-go ")
text.pack()
text_2.pack()

def input():
    global coin
    global timespan
    coin = str(textbox.get()).lower()
    timespan = int(textbox2.get())
    root.destroy()







textbox = Entry(root,width=30)
textbox.pack()

text_3 = Label(root, text="Enter number of days in the past to analyze: (read instruction to see intervals)")
text_3.pack()

textbox2 = Entry(root,width=30)
textbox2.pack()

button = Button(root,text="Submit",command=input)
button.pack()




root.mainloop()



style.use("seaborn")

"""
Retrieve pricedate from the Coingecko API
Minutely data will be used for duration within 1 day, Hourly data will be used for duration between 1 day and 90 days,
Daily data will be used for duration above 90 days.
"""



granularity = ""
small_numbers = False
request = requests.get("https://api.coingecko.com/api/v3/coins/"+ coin +"/market_chart?vs_currency=USD&days="+
                       str(timespan) + "&interval="+granularity).text

"""
Reformat the data into a list of floats, data cleaning
"""
request_split = request.split('"')
stage_2 = request_split[2]
stage_3 = stage_2.split("]")
pricedata = []
for i in range(len(stage_3)):
    stage_4 = stage_3[i].split(",")
    for j in range(len(stage_4)):
        if "e" in stage_4[j]:
            small_numbers = True
            pricedata.append(stage_4[j])
        elif "." in stage_4[j]:
            pricedata.append(stage_4[j])

pricedata = [float(i) for i in pricedata]



"""
Create a Dataframe with columns for Price, Simple Moving  Average, and the four bollinger bands
"""
data = pd.DataFrame()
sma = 10
data["Price"] = pricedata


def bollinger_strat(data, window, no_of_std):
    if small_numbers:
        data["Price"] = data["Price"] * 10**10
        rolling_mean = data['Price'].rolling(window).mean()
        rolling_std = data['Price'].rolling(window).std(ddof=0)



        data['BB1'] = (rolling_mean + (rolling_std * no_of_std)) / 10**10
        data['BB-1'] = (rolling_mean - (rolling_std * no_of_std)) / 10**10
        data['BB2'] = (rolling_mean + 2 * (rolling_std * no_of_std)) / 10**10
        data['BB-2'] = (rolling_mean - 2 * (rolling_std * no_of_std)) / 10**10
        data["Price"] = data["Price"] / 10**10
        data["Width"] = data["BB2"] - data["BB-2"]

    elif not small_numbers:
        rolling_mean = data['Price'].rolling(window).mean()
        rolling_std = data['Price'].rolling(window).std(ddof=0)

        data['BB1'] = rolling_mean + (rolling_std * no_of_std)
        data['BB-1'] = rolling_mean - (rolling_std * no_of_std)
        data['BB2'] = rolling_mean + 2 * (rolling_std * no_of_std)
        data['BB-2'] = rolling_mean - 2 * (rolling_std * no_of_std)
        data["Width"] = data["BB2"] - data["BB-2"]



bollinger_strat(data,sma,1)


"""
Vizualise the data
-ANIMATION??
"""
plt.title(coin.capitalize())
plt.ylabel("$USD",color="forestgreen")
if timespan == 1:
    plt.xlabel("Minutes",color="black")
elif 1 < timespan <= 90:
    plt.xlabel("Hours",color="black")
else:
    plt.xlabel("Days",color="black")
plt.plot(data["Price"],color="blue")
plt.fill_between(data.index,data["BB2"],data["BB1"],color="slategray",alpha=0.5)
plt.fill_between(data.index,data["BB-2"],data["BB-1"],color="slategray",alpha=0.5)
#plt.plot(data["BB1"],color="limegreen")
# plt.plot(data["BB-1"],color="red")
#plt.plot(data["BB2"],color="green")
#plt.plot(data["BB-2"],color="firebrick")


"""
Trading algorithm logic
- Give points based on which bollinger band the price is between.
-if prolonged between bb-2 and bb-1 --> downwards trend
-If prolonged between bb2 and bb1 --> upwards trend
"""
recommendation = "Neutral"
def strategy(data):
    global recommendation
    buysignals = []
    sellsignals = []
    data["Signal"] = pd.Series(dtype="int64")

    for i in data.index:
        if data["Price"][i] <= data["BB-2"][i]:
            data["Signal"][i] = -2
        elif data["BB-2"][i] < data["Price"][i] <= data["BB-1"][i]:
            data["Signal"][i] = -1
        elif data["BB-1"][i] < data["Price"][i] <= data["BB1"][i]:
            data["Signal"][i] = 0
        elif data["BB1"][i] < data["Price"][i] <= data["BB2"][i]:
            data["Signal"][i] = 1
        elif data["Price"][i] > data["BB2"][i]:
            data["Signal"][i] = 2


    """
     -2 -1 0 --> buy signal
     0 1 2 --> buy signal
     1/2 1/2 1/2 1/2 --> buy signal
     -1/-2 1/2 --> buy signal
     
     -1/-2  -1/-2   -1/-2   -1/-2 --> sell signal
     0 -1 -2 -->sell signal
     1 0 -1 -->sell signal
     1/2 -1/-2 -->sell signal
     
    """
    sequence = []
    y = 0
    for i in data.index:
        sequence.append(data["Signal"][i])
        if len(sequence) >= 5:
            if sequence[-3] == -2 and sequence[-2] == -1 and sequence[-1] == 0 and y != 1:
                buysignals.append([i, data["Price"][i]])
                y = 1

            elif sequence[-3] == 0 and sequence[-2] == 1 and sequence[-1] == 2 and y != 1:
                buysignals.append([i, data["Price"][i]])
                y = 1

            elif sequence[-4] in [1,2] and sequence[-3] in [1,2] and sequence[-2] in [1,2] and sequence[-1] in [1,2] and y != 1:
                buysignals.append([i, data["Price"][i]])
                y = 1

            elif sequence[-2] in [-1,-2] and sequence[-1] in [1,2] and y != -1:
                sellsignals.append([i, data["Price"][i]])

                y = -1
            elif sequence[-4] in [-1,-2] and sequence[-3] in [-1,-2] and sequence[-2] in [-1,-2] and sequence[-1] in [-1,-2] and y != -1:
                sellsignals.append([i, data["Price"][i]])

                y = -1
            elif sequence[-3] == 0 and sequence[-2] == -1 and sequence[-1] == -2 and y != -1:
                sellsignals.append([i, data["Price"][i]])
                y = -1

            elif sequence[-3] == 1 and sequence[-2] == 0 and sequence[-1] == -1 and y != -1:
                sellsignals.append([i, data["Price"][i]])
                y = -1

            elif sequence[-2] in [1,2] and sequence[-1] in [-1,-2] and y != -1:
                sellsignals.append([i, data["Price"][i]])

                y = -1
    """
    Scatter signals on chart and calculate PnL
    """
    pnl = 1
    for i in buysignals:
        plt.scatter(i[0],i[1],marker="^",color="green",linewidths=3)
        pnl -= i[1]

    for i in sellsignals:
        plt.scatter(i[0],i[1],marker="v",color="red",linewidths=3)
        pnl += i[1]


    # buynhold = data["Price"].tail(1) - data["Price"][0]
    # print(pnl)
    # print(buynhold)

    if buysignals[-1][0] > sellsignals[-1][0] and buysignals[-1][0] >= data.index[-10]:
        recommendation = "Buy"
    elif buysignals[-1][0] < sellsignals[-1][0] and sellsignals[-1][0] >= data.index[-10]:
        recommendation = "Sell"





strategy(data)

plt.figtext(0.68,0.89,"Current signal: "+ recommendation,size=12,weight=400)
plt.show()

