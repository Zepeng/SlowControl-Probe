"""
@Author: Andrei Gogosha

This is a python file to handle plotting of the temperature log files from the small cryostat as well as the radon log data from the
deradonator. You can comment or uncomment the code down bellow to do this or import this file into another file to use the functions.
"""

import os
import pandas as pd
#import matplotlib
import matplotlib.pyplot as plt   
import numpy as np

#Radon File Reading

def radon_data_read_txt(directory,file_name):
    output=np.array([[]],dtype='float32')
    with open(directory+file_name, encoding='utf8') as f:
        lines=f.readlines()[6:] #skip the header included in the data files created by radoneye
        for line in lines:
            temp_read=line.strip("\n ").split(")\t")    #deals with the funky formating of said log files
            output=np.append(output,np.array([[float(temp_read[1].strip(" "))]],dtype='float32'),axis=1)
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

def convert_pCi(data):
    return data*(0.037/0.001)

#Temperature Plotting
def get_tics(data, interval):
    tics=np.array([[],[]])
    for count, value in enumerate(data):
        if count%interval==0:
            tics=np.append(tics,[[count],[value]],axis=1)
    return tics

def temp_plot(x_data,y_data,title,lables,tics,cutoff):
    plt.figure(figsize=(20, 20))
    for count, y_cords in enumerate(y_data):
        plt.plot(x_data,y_cords,label=lables[count])
    if cutoff[0]:
        plt.ylim(cutoff[1],cutoff[2])
    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Temperature (\u00b0C)")
    plt.xticks(tics[0,:].astype('int'),tics[1,:],rotation='vertical', fontsize=10)
    plt.legend(loc='best')
    plt.show()

def radon_plot(x_data,y_data,titles,multiple):
    plt.figure(figsize=(20, 20))
    if multiple[0]:
        for count, y_cords in enumerate(y_data):
            plt.subplot(multiple[1],multiple[2],count+1)
            plt.plot(x_data[count],y_cords)
            plt.title(titles[count])
            plt.xlabel("Time (Hours)")
            plt.ylabel(r"Radon Level ($\frac{Bq}{m^3}$)")
    else:
        plt.plot(x_data,y_data)
        plt.title(titles)
        plt.xlabel("Time (Hours)")
        plt.ylabel(r"Radon Level ($\frac{Bq}{m^3}$)")
    plt.show()


if __name__ == '__main__':
#   Ploting
    ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname("All plot.py")))
    target_dir=ROOT_DIR+"/Logs/"
    dir_list = os.listdir(ROOT_DIR+"/Logs/")
    dir_list.sort()

    # radon_data=radon_data_read_txt(ROOT_DIR+"/","radon data 12-1-22 15 11.txt")
    # radon_data2=radon_data_read_txt(ROOT_DIR+"/","last pCi l data 12-1-22 9 19.txt")
    # converted2=convert_pCi(radon_data2[0,:])
    # radon_data3=radon_data_read_txt(ROOT_DIR+"/",'radon data 12-2-22 8 08.txt')
    # converted=convert_pCi(radon_data3[0,:]) #use when you want to convert from pCi/l to bq/m^3
    # radon_data4=radon_data_read_txt(ROOT_DIR+"/",'radon data 11-29-22 7 58.txt')
    # input_x_data=np.array([radon_data4[1,-21:],radon_data2[1],radon_data2[1],radon_data[1],radon_data3[1],radon_data3[1]],dtype='object')
    
    # input_y_data=np.array([radon_data4[0,-21:],radon_data2[0],converted2,radon_data[0],radon_data3[0],converted],dtype='object')
    # radon_plot(input_x_data,input_y_data,[r"Radon Level $\frac{Bq}{m^3}$ vs Time Hours",r"Radon Level $\frac{pCi}{l}$ vs Time Hours",r"Converted Radon Level $\frac{Bq}{m^3}$ vs Time Hours",r"Converted Radon Level $\frac{Bq}{m^3}$ vs Time Hours",r"Radon Level $\frac{pCi}{l}$ vs Time Hours",r"Converted Radon Level $\frac{Bq}{m^3}$ vs Time Hours"]
    # ,[True,2,3])

    # Uncomment and change the following paramaters to plot either radon levle data or temperature data

    # radon_data=radon_data_read_csv(ROOT_DIR+"/","Radon_Full_Background.csv")
    # radon_data=radon_data_read_txt(ROOT_DIR+"/","radon data 12-1-22 15 11.txt")
    # print(np.average(radon_data[0,:]))
    # plt.figure(figsize=(20, 20))
    # plt.subplot(2,3,4)
    # plt.plot(radon_data[1,:],radon_data[0,:],label="Radon Level")
    # plt.title(r"Radon Level $\frac{Bq}{m^3}$ vs Time Hours")
    # plt.xlabel("Time (Hours)")
    # plt.ylabel(r"Radon Level ($\frac{Bq}{m^3}$)")

    # radon_data2=radon_data_read_txt(ROOT_DIR+"/","last pCi l data 12-1-22 9 19.txt")
    # print(np.average(radon_data2[0,:]))
    # plt.subplot(2,3,2)
    # plt.plot(radon_data2[1,:],radon_data2[0,:],label="Radon Level")
    # plt.title(r"Radon Level $\frac{pCi}{l}$ vs Time Hours")
    # plt.xlabel("Time (Hours)")
    # plt.ylabel(r"Radon Level ($\frac{pCi}{l}$)")

    # converted2=convert_pCi(radon_data2[0,:]) #use when you want to convert from pCi/l to bq/m^3
    # plt.subplot(2,3,3)
    # plt.plot(radon_data2[1,:],converted2,label="Radon Level")
    # plt.title(r"Converted Radon Level $\frac{Bq}{m^3}$ vs Time Hours")
    # plt.xlabel("Time (Hours)")
    # plt.ylabel(r"Converted Radon Level ($\frac{Bq}{m^3}$)")

    # radon_data3=radon_data_read_txt(ROOT_DIR+"/",'radon data 12-2-22 8 08.txt')
    # #converted=convert_pCi(radon_data2[0,:]) #use when you want to convert from pCi/l to bq/m^3
    # plt.subplot(2,3,5)
    # plt.plot(radon_data3[1,:],radon_data3[0,:],label="Radon Level")
    # plt.title(r"Radon Level $\frac{pCi}{l}$ vs Time Hours")
    # plt.xlabel("Time (Hours)")
    # plt.ylabel(r"Radon Level ($\frac{pCi}{l}$)")

    # converted=convert_pCi(radon_data3[0,:]) #use when you want to convert from pCi/l to bq/m^3
    # plt.subplot(2,3,6)
    # plt.plot(radon_data3[1,:],converted,label="Radon Level")
    # plt.title(r"Converted Radon Level $\frac{Bq}{m^3}$ vs Time Hours")
    # plt.xlabel("Time (Hours)")
    # plt.ylabel(r"Converted Radon Level ($\frac{Bq}{m^3}$)")
    

    # radon_data4=radon_data_read_txt(ROOT_DIR+"/",'radon data 11-29-22 7 58.txt')
    # plt.subplot(2,3,1)
    # plt.plot(radon_data4[1,-21:],radon_data4[0,-21:],label="Radon Level")
    # plt.title(r"Radon Level $\frac{Bq}{m^3}$ vs Time Hours")
    # plt.xlabel("Time (Hours)")
    # plt.ylabel(r"Radon Level ($\frac{Bq}{m^3}$)")
    # plt.show()
    
    # radon_data=radon_data_read_txt(ROOT_DIR+"/","radon data 12-13-22.txt")
    # print(np.average(radon_data[0,-8:]))
    # plt.figure(figsize=(20, 20))
    # # plt.subplot(2,3,4)
    # plt.plot(radon_data[1,-8:],radon_data[0,-8:],label="Radon Level")
    # plt.title(r"Radon Level $\frac{Bq}{m^3}$ vs Time Hours")
    # plt.xlabel("Time (Hours)")
    # plt.ylabel(r"Radon Level ($\frac{Bq}{m^3}$)")
    # plt.show()
    

    temp_data, time_data=temp_data_read_csv(ROOT_DIR+"/Logs/",dir_list[-14:])
    lin_names=["Cold Head","Heat Exchanger Front", "Heat Exchanger Back","Chamber"]
    plot_name="Cryostat Temperatures Vs Time"
    x_lables=get_tics(time_data,1000)
    temp_plot(temp_data[4],temp_data[0:4],plot_name,lin_names,x_lables,[False,0,0])
