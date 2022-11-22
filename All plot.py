import pandas as pd
import matplotlib
import matplotlib.pyplot as plt   
import numpy as np
import os

#Radon File Reading

def radon_data_read_txt(directory,file_name):
    output=np.array([[]],dtype='int')
    with open(directory+file_name, encoding='utf8') as f:
        lines=f.readlines()[6:] #skip the header included in the data files created by radoneye
        for line in lines:
            temp_read=line.strip("\n ").split(")\t")    #deals with the funky formating of said log files
            output=np.append(output,np.array([[int(temp_read[1].strip(" "))]],dtype='int'),axis=1)
    # add an index to the output, this will be used for the x values of plots
    output= np.append(output,np.array([np.arange(0,len(output[0]))]),axis=0)
    return output
#essentialy the same as the previousfunction but used for the log data Nolan provided
def radon_data_read_csv(directory,file_name):
    data=pd.read_csv(directory+file_name,header=0)
    output = np.array([np.ndarray.flatten(data[["mCu/l"]].to_numpy(dtype='float32'))])
    output= np.append(output,np.array([np.arange(0,len(output[0]))]),axis=0)
    return output

#Temp File Reading

def temp_data_read_csv(directory,file_names):
    output=np.array([[],[],[],[]])
    time_out=np.array([])
    prev_head=[]
    for file in file_names:
        if file.endswith(".csv") and os.stat(os.path.join(ROOT_DIR, 'Logs', file)).st_size> 0:  # makes sure the file type is correct and there is data in the file
            if "Rt" not in list(pd.read_csv(directory+file,header=0)) and file!=file_names[0]:  # makes sure thee is a data header and if there isn't re use the previous lines header
                data=pd.read_csv(directory+file,header=0,names=prev_head)
            else:
                data=pd.read_csv(directory+file,header=0)
                prev_head= list(data)
            if "temp_hex_b" in list(data):  # check for newer log file where there are 2 temperatures for the heat exchanger
                # output is a numpy array created by using pandas built in function to export data to numpy arrays then the data is flattened becuase pandas outputs things weird
                output=np.append(output,np.array([np.ndarray.flatten(data[["temp_ch"]].to_numpy(dtype='float32')),
                np.ndarray.flatten(data[["temp_hex_f"]].to_numpy(dtype='float32')),
                np.ndarray.flatten(data[["temp_hex_b"]].to_numpy(dtype='float32')),
                np.ndarray.flatten(data[["temp_chamber"]].to_numpy(dtype='float32'))]),axis=1)
                # time out is created because numpy has trouble doing different data types per dimensions of an array
                # the code also only keeps the HH-MM-SS part of the time stored in the log
                time_out=np.append(time_out,np.array([item.split(" ",1)[-1] for item in np.ndarray.flatten(data[["Rt"]].to_numpy(dtype='str'))]))
            else:
                output=np.append(output,np.array([np.ndarray.flatten(data[["temp_ch"]].to_numpy(dtype='float32')),
                np.zeros(len(np.ndarray.flatten(data[["temp_ch"]].to_numpy(dtype='float32')))),
                np.ndarray.flatten(data[["temp_hex"]].to_numpy(dtype='float32')),
                np.ndarray.flatten(data[["temp_chamber"]].to_numpy(dtype='float32'))]),axis=1)
                time_out=np.append(time_out,np.array([item.split(" ",1)[-1] for item in np.ndarray.flatten(data[["Rt"]].to_numpy(dtype='str'))]))
        else:
            continue
    # add an index to the output, this will be used for the x values of plots
    output= np.append(output,np.array([np.arange(0,len(output[0]))]),axis=0)
    return output, time_out

#Temperature Plotting

def p_plot(x_data,y_data,title,lables,tics):
    plt.figure(figsize=(20, 20))
    for i in range(len(y_data)):
        plt.plot(x_data,y_data[i],label=lables[i])
    #plt.ylim(-94,-95)
    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Temperature (\u00b0C)")
    plt.xticks(tics[0],tics[1],rotation='vertical', fontsize=10)
    plt.legend(loc='best')
    plt.show()

def get_tics(data, interval):
    tics=[[],[]]
    for i in range(len(data)):
        if i%interval==0:
            tics[0].append(i)
            tics[1].append(data[i])
    return tics

#Ploting
ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname("All plot.py")))
target_dir=ROOT_DIR+"/Logs/"
dir_list = os.listdir(ROOT_DIR+"/Logs/")
dir_list.sort()

# Uncomment and change the following paramaters to plot either radon levle data or temperature data

# radon_data=radon_data_read_csv(ROOT_DIR+"/","Radon_Full_Background.csv")
# radon_data=radon_data_read_txt(ROOT_DIR+"/","radon levels 11-22-22.txt")
# plt.plot(radon_data[1,-6:],radon_data[0,-6:],label="Radon Level")
# plt.title(r"Radon Level $\frac{Bq}{m^3}$ vs Time Hours")
# plt.xlabel("Time (Hours)")
# plt.ylabel(r"Radon Level ($\frac{Bq}{m^3}$)")
# plt.show()

# temp_data, time_data=temp_data_read_csv(ROOT_DIR+"/Logs/",dir_list)
# lin_names=["Cold Head","Heat Exchanger Front", "Heat Exchanger Back","Chamber"]
# title="Cryostat Temperatures Vs Time"
# tics=get_tics(time_data,50000)
# p_plot(temp_data[4],temp_data[0:4],title,lin_names,tics)
