from flask import Flask
from flask import *
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from keras.models import Sequential 
from keras.layers import Dense, LSTM 
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from werkzeug.utils import secure_filename
import os
from sklearn.metrics import mean_squared_error,mean_absolute_error
import time
from statsmodels.tsa.api import VAR
import pmdarima as pm
import statsmodels.api as sm
import warnings
from statsmodels.tools.sm_exceptions import ConvergenceWarning



app = Flask(__name__) # create an app instance


#---------------------------------- LOAD DATA ---------------------------------
def load_data(file_path):
    data = pd.read_csv(file_path)
    return data

def load_data_new(file_path):
    data = pd.read_csv(file_path)
    df_numerical = data.select_dtypes(include=[float, int])
    df_final= df_numerical.dropna(axis=1)
    return df_final
#---------------------------------- END LOAD DATA ---------------------------------
#---------------------------------- START SCALE DATA ---------------------------------
def scale_data(data):
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)
    return scaled_data, scaler

def scale_data_original(test,predictions,scaler):
    predictions_actual = scaler.inverse_transform(predictions.reshape(1, -1))
    test_actual = scaler.inverse_transform(test.reshape(1, -1))
    return predictions_actual, test_actual

def scale_data_original_var(column_prediction,arrayData,scaler,result_var,test):
    testPredict_var_real = scaler.inverse_transform(np.array(result_var))[:,arrayData.index(column_prediction)]
    test_var_real = scaler.inverse_transform(test)[:,arrayData.index(column_prediction)]
    return testPredict_var_real, test_var_real

#---------------------------------- END SCALE DATA ---------------------------------
#---------------------------------- START SPLIT DATA --------------------------------
def split_data_default(data, split_ratio=0.8):
    train_size = int(len(data) * split_ratio)
    train, test = data[:train_size], data[train_size:]
    return train, test 


def split_data_new(data, split_ratio):
    train_size = int(len(data) * split_ratio)
    train, test = data[:train_size], data[train_size:]
    return train, test
#---------------------------------- END SPLIT DATA --------------------------------
#---------------------------------- Create time series sequences --------------------
def to_sequences(dataset,timestep , seq_size=1): 
    x = []
    y = []
    for i in range(0,len(dataset)-seq_size,timestep):
        window = dataset[i:(i+seq_size), 0]
        x.append(window)
        y.append(dataset[i+seq_size, 0])
    return np.array(x),np.array(y)


def to_sequences_multivariate_varnn(dataset,p):
    x = []
    y = []
    for i in range(p, len(dataset)):
        x.append(dataset[i - p:i, 0:dataset.shape[1]])
        y.append(dataset[i:i + 1, 0:dataset.shape[1]])
    x = np.array(x)
    y = np.array(y)
    return x,y.reshape(y.shape[0], y.shape[2])

def to_sequences_multivariate_lstm(dataset,p):
    x = []
    y = []
    for i in range(p, len(dataset)):
        x.append(dataset[i - p:i, 0:dataset.shape[1]])
        y.append(dataset[i:i + 1, 0:dataset.shape[1]])
    x = np.array(x)
    y = np.array(y)
    return x.reshape(x.shape[0], x.shape[1] * x.shape[2]),y.reshape(y.shape[0], y.shape[2])
#---------------------------------- END Create time series sequences -----------------
#---------------------------------- START VARNN ---------------------------------
#---------------------------------- END VARNN -----------------------------------
# ----------------------------------START FFNN ----------------------------------
def model_ffnn_exist(seq_size, hidden_neurons, weights_file):
    model = Sequential()
    model.add(Dense(hidden_neurons, input_dim=seq_size, activation='relu'))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam', metrics = ['acc'])
    model.load_weights(weights_file)
    return model

def model_ffnn_new(train, test, hidden_layers, seq_size, hidden_neurons, epoch, batchsize):
    trainX, trainY = to_sequences(train,1, seq_size)
    testX, testY = to_sequences(test,1, seq_size)
    model = Sequential()
    for j in range(1, hidden_layers+1):
        model.add(Dense(hidden_neurons, input_dim=seq_size, activation='relu'))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam', metrics = ['acc'])
    model.fit(trainX, trainY, validation_data=(testX, testY), verbose=0, epochs=epoch, batch_size=batchsize)
    return model

def get_param_ffnn(default_split_ratio,default_hidden_neurons,default_seq_size,default_epochs,default_batch_size,default_hidden_layers):
   split_ratio_get = global_parameters.get('splitdata',default_split_ratio)
   if split_ratio_get == 'split73':
       split_ratio = 0.7
   else:
       split_ratio = 0.8
   hidden_neurons = int(global_parameters.get('Hidden_Neurons', default_hidden_neurons))
   seq_size = int(global_parameters.get('Data_window_size', default_seq_size))
   epochs = int(global_parameters.get('Epoch', default_epochs))
   batch_sizes = int(global_parameters.get('Batch_size', default_batch_size))
   hidden_layers = int(global_parameters.get('Hidden_Layers', default_hidden_layers))
   return split_ratio, hidden_neurons,seq_size,epochs,batch_sizes,hidden_layers

def get_param_ffnn_datasetNew():
   split_ratio_get = global_parameters.get('splitdata')
   if split_ratio_get == 'split73':
       split_ratio = 0.7
   else:
       split_ratio = 0.8
   hidden_neurons = int(global_parameters.get('Hidden_Neurons'))
   seq_size = int(global_parameters.get('Data_window_size'))
   epochs = int(global_parameters.get('Epoch'))
   batch_sizes = int(global_parameters.get('Batch_size'))
   hidden_layers = int(global_parameters.get('Hidden_Layers'))
   return split_ratio, hidden_neurons,seq_size,epochs,batch_sizes,hidden_layers
# ---------------------------------- END FFNN ----------------------------------
# ---------------------------------- LSTM ----------------------------------
def LSTM_exist(train,outputs,seq,hidden_neural,weights_file):
    seq_size = seq
    trainX_LSTM, trainY_LSTM = to_sequences_multivariate_lstm(train,seq_size)
    model_LSTM = Sequential()
    model_LSTM.add(LSTM(hidden_neural, return_sequences=False, input_shape= (trainX_LSTM.shape[1], 1)))
    model_LSTM.add(Dense(outputs))
    model_LSTM.compile(loss='mean_squared_error', optimizer='adam', metrics = ['acc'])
    model_LSTM.load_weights(weights_file)
    return model_LSTM

def LSTM_new( train,test,outputs,seq,hidden_neural,epochs,batch_size,hidden_layers):
    seq_size = seq
    trainX_LSTM, trainY_LSTM = to_sequences_multivariate_lstm(train,seq_size)
    testX_LSTM, testY_LSTM = to_sequences_multivariate_lstm(test,seq_size)
    model_LSTM = Sequential()
    for j in range(1, hidden_layers+1):
         model_LSTM.add(LSTM(hidden_neural, return_sequences=False, input_shape= (trainX_LSTM.shape[1], 1)))
    model_LSTM.add(Dense(outputs))
    model_LSTM.compile(loss='mean_squared_error', optimizer='adam', metrics = ['acc'])
    model_LSTM.fit(trainX_LSTM, trainY_LSTM, validation_data=(testX_LSTM, testY_LSTM), verbose=0, epochs=epochs, batch_size=batch_size)
    return model_LSTM

def LSTM_Predict(result_LSTM,testY_LSTM,predict_LSTM_real,textY_LSTM_real,arrayValue,column_prediction,alogrithm):
    predict_LSTM = result_LSTM[:,arrayValue.index(column_prediction)]
    textY_LSTM = testY_LSTM[:,arrayValue.index(column_prediction)]  
    testScore_mse, testScore_rmse, testScore_mae = calculate_metrics(textY_LSTM, predict_LSTM)                     
    
    predict_LSTM_real = predict_LSTM_real[:,arrayValue.index(column_prediction)]
    textY_LSTM_real = textY_LSTM_real[:,arrayValue.index(column_prediction)]                   
    testScore_mse_real, testScore_rmse_real, testScore_mae_real = calculate_metrics(textY_LSTM_real, predict_LSTM_real)                      
    eda_model(textY_LSTM,predict_LSTM,column_prediction,alogrithm)
    return testScore_mse, testScore_rmse, testScore_mae, testScore_mse_real, testScore_rmse_real, testScore_mae_real

#---------------------------------- END LSTM ----------------------------------
#---------------------------------- VAR ----------------------------------
def VAR_exist(train,p):
    model_var = VAR(train)
    result =  model_var.fit(p)
    return model_var, result

def VAR_New(train,test,p_max):
    mse = 999
    p_optimize = 0
    for p in range(1,p_max+1):
        a = [] 
        model = VAR(train)
        result = model.fit(p)
        b=train[:]
        for j in range(len(test)):
            forecast = result.forecast(b[-p:], steps=1)
            a.append(forecast[0])
            b=np.append(b,[test[j]], axis=0)
        if mse > mean_squared_error(test, np.array(a)):
            mse = mean_squared_error(test, np.array(a))
            p_optimize = p
    
    model_var = VAR(train)
    result_pop = model_var.fit(p_optimize)
    return model_var, result_pop,p_optimize

def Extract_test_predict_var(column_prediction,arrayData,result_var,test):
    index = arrayData.index(column_prediction)
    predict_var = [result[index] for result in result_var]
    test_var = [t[index] for t in test]
    predict_var = np.array(predict_var)
    test_var = np.array(test_var)
    return predict_var,test_var

def VAR_forecast(train,test,result,p):
    result_var=[]
    b=train[:]
    for i in range(len(test)):
        forecast_var = result.forecast(b[-p:], steps=1)
        result_var.append(forecast_var[0])
        b=np.append(b,[test[i]], axis=0)
    return result_var

def get_Var_param():
    split_ratio_get = global_parameters.get('splitdata')
    if split_ratio_get == 'split73':
       split_ratio = 0.7
    else:
       split_ratio = 0.8
    orderlags = int(global_parameters.get('Max_lag_order_p_'))
    return split_ratio,orderlags

#---------------------------------- END VAR ----------------------------------
#---------------------------------- ARIMA ----------------------------------
#---------------------------------- END ARIMA ----------------------------------
def calculate_metrics(test, predictions):
    mse = mean_squared_error(test, predictions)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(test, predictions)
    return mse, rmse, mae


#---------------------------------- START EDA ----------------------------------
def eda_model(y,test_pred,column_prediction,alogrithm):
    global global_name
    plt.clf() 
    plt.plot(y,label="Actual value")
    plt.plot(test_pred,label="Predicted value")
    if alogrithm == 'algorithm-ffnn':
        plt.title('FFNN Predictions vs Actual {} Values for {}'.format(column_prediction,global_name))
    elif alogrithm == 'algorithm-lstm':
        plt.title('LSTM Predictions vs Actual {} Values for {}'.format(column_prediction,global_name))
    elif alogrithm == 'algorithm-var':
        plt.title('VAR Predictions vs Actual {} Values for {}'.format(column_prediction,global_name))
    elif alogrithm == 'algorithm-varnn':
        plt.title('VARNN Predictions vs Actual {} Values for {}'.format(column_prediction,global_name))
    else:
        plt.title('ARIMA Predictions vs Actual {} Values for {}'.format(column_prediction,global_name))
    plt.legend()
    plt.savefig('static/images/plot_predict.png')

    
#---------------------------------- END EDA ----------------------------------
@app.route('/')
def index():
    return render_template('login.html')

global_data = None
global_name = None


@app.route('/data', methods=['GET', 'POST'])
def data():
    data_loaded = False
    stock_name = None
    data = None
    columns = None
    num_columns = None
    count_data = None
    file_path= None
    data_out = None
    filename = None
    output_columns = None
    global global_data
    global global_name
    if request.method == 'POST':
        if 'data' in request.form and request.form['data']:  # Check if the request has the data part
            stock_name = request.form['data']
            file_path = f"./dataset/{stock_name}.csv"
            data = load_data(file_path)
            global_data = data.copy()
            global_name = stock_name
            count_data = data.shape[0]
            data_loaded = True  
            
            columns = data.columns.tolist()
            num_columns = len(columns)
        elif 'text' in request.files and request.files['text'].filename != '':  # Check if the request has the file part
            file = request.files['text']
            filename = secure_filename(file.filename)
            file_path = os.path.join('./dataset/new_dataset/', filename)
            file.save(file_path)  # Save the file to a destination
            data = load_data(file_path)
            global_data = data.copy()
            filename_without_extension = filename.split(".")[0]
            global_name = filename_without_extension
            count_data = data.shape[0]
            data_loaded = True
            
            data_out = load_data_new(file_path)
            output_columns = data_out.columns.tolist()   
            
            columns = data.columns.tolist()
            num_columns = len(columns)
        else:
            return render_template('index.html', message="Please choose a dataset or upload a file"), 400
        
    return render_template('index.html', data=data.to_html() if data is not None else None, data_loaded=data_loaded,columns = columns,stock_name=stock_name,
                           count_data=count_data,num_columns=num_columns,file_path=file_path, filename=filename, global_name=global_name,output_columns=output_columns)

   
@app.route('/eda_column', methods=['GET', 'POST'])
def eda_data():
    global global_data  
    global global_name
    data_1 = global_data.copy()
    column_name = None
    if request.method == 'POST':
        if 'column' in request.form:
            column_name = request.form.get('column')
            plt.figure(figsize=(10, 5))
            if global_name == 'GOOGLE' or global_name == 'APPLE' or global_name == 'AMAZON':
                data_1['Date'] = pd.to_datetime(data_1['Date'])
                plt.plot(data_1['Date'],data_1[column_name])
                plt.xlabel('Date') 
            elif global_name == 'Weather_WS':
                data_1['Date Time'] = pd.to_datetime(data_1['Date Time'])
                plt.plot(data_1['Date Time'],data_1[column_name])
                plt.xlabel('Date') 
            elif global_name == 'weather-HCM':
                data_1['date'] = pd.to_datetime(data_1['date'])
                plt.plot(data_1['date'],data_1[column_name])
                plt.xlabel('Date')  # Add x-axis label
            else:
                plt.plot(data_1[column_name])
            plt.title(column_name)
            plt.savefig('static/images/plot.png')
    return jsonify(column_name=column_name)



@app.route('/model', methods=['GET', 'POST'])
def Predict():
    global global_data 
    global global_name
    global array_column_new
    algorithm =None
    column_prediction = None
    useExistingModel = None
    train = []
    test = []
    train_new = []
    test_new = []
    testScore_mse = 0
    testScore_rmse = 0
    testScore_mae = 0
    testScore_mse_real = 0
    testScore_rmse_real = 0
    testScore_mae_real = 0
    model_path_apple = 'Model/Apple/'
    model_path_amazon = 'Model/Amazon/'
    model_path_google = 'Model/Google/'
    model_path_WS = 'Model/DUC-WS/'
    model_path_HCM = 'Model/weather-HCM/'
    algorithm = request.form.get('algorithm')
    column_prediction = request.form.get('column_prediction')
    useExistingModel = request.form.get('useExistingModel') 
    
    scaled_data = None  
    scaler = None 
    start_train = 0
    end_train = 0
    time_train = 0
    start_predict = 0
    end_predict = 0    
    time_predict = 0 
    # Param FFNN
    model = None
    model_path_ffnn = None
    default_hidden_neurons = None
    default_seq_size = None
    default_epochs = None
    default_batch_size = None 
    test_pred = None
    x = None
    y = None
    y_real = None
    test_pred_real = None
    # Param LSTM
    model_path_lstm = None
    model_lstm = None
    
    array_temp = []
    array_stock = list(["Open","High","Low","Close","Adj Close"])
    array_WS = list(["Pressure","Temperature","Saturation_vapor_pressure","Vapor_pressure_deficit","Specific_humidity","Airtight","Wind_speed"])
    array_HCM = list(["max","min","wind","rain","humidi","pressure"])
#-----------FFNN-------------------
    if  algorithm == 'algorithm-ffnn':       
        if useExistingModel == 'on': # For existing model
            default_hidden_layers = 1
            default_split_ratio = 0.8             
            scaled_data, scaler = scale_data(global_data[column_prediction].values.reshape(-1,1))
            train, test = split_data_default(scaled_data)
            if global_name == 'APPLE':
                if column_prediction == 'Open': 
                    default_hidden_neurons = 16
                    default_seq_size = 18
                    default_epochs = 400
                    default_batch_size = 32  
                    model_path_ffnn = model_path_apple + 'FFNN/FFNN_Model_Apple_Open.h5'                      
                elif column_prediction == 'High':
                    default_seq_size = 16
                    default_hidden_neurons = 22
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_apple + 'FFNN/FFNN_Model_Apple_High.h5'
                elif column_prediction == 'Low':
                    default_seq_size = 19
                    default_hidden_neurons = 13
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_apple + 'FFNN/FFNN_Model_Apple_Low.h5'
                elif column_prediction == 'Close':
                    default_seq_size = 12
                    default_hidden_neurons = 5
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_apple + 'FFNN/FFNN_Model_APPLE_Close.h5'
                else:
                    default_seq_size = 11
                    default_hidden_neurons = 20
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_apple + 'FFNN/FFNN_Model_APPLE_AdjClose.h5'
            elif global_name == 'GOOGLE':
                if column_prediction == 'Open': 
                    default_seq_size = 7
                    default_hidden_neurons = 9
                    default_epochs = 400
                    default_batch_size = 32  
                    model_path_ffnn = model_path_google + 'FFNN/FFNN_Model_GOOGLE_Open.h5' 
                elif column_prediction == 'High':
                    default_seq_size = 6
                    default_hidden_neurons = 15
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_google + 'FFNN/FFNN_Model_GOOGLE_High.h5'
                elif column_prediction == 'Low':
                    default_seq_size = 6
                    default_hidden_neurons = 11
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_google + 'FFNN/FFNN_Model_GOOGLE_Low.h5'
                elif column_prediction == 'Close':
                    default_seq_size = 11
                    default_hidden_neurons = 6
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_google + 'FFNN/FFNN_Model_GOOGLE_Close.h5'
                else:
                    default_seq_size = 11
                    default_hidden_neurons = 6
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_google + 'FFNN/FFNN_Model_GOOGLE_AdjClose.h5'
            elif global_name == 'AMAZON':
                if column_prediction == 'Open': 
                    default_seq_size = 10
                    default_hidden_neurons = 21
                    default_epochs = 400
                    default_batch_size = 32  
                    model_path_ffnn = model_path_amazon + 'FFNN/FFNN_Model_AMAZON_Open.h5'
                elif column_prediction == 'High':    
                    default_seq_size = 7
                    default_hidden_neurons = 21
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_amazon + 'FFNN/FFNN_Model_AMAZON_High.h5'
                elif column_prediction == 'Low':
                    default_seq_size = 11
                    default_hidden_neurons = 9
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_amazon + 'FFNN/FFNN_Model_AMAZON_Low.h5'
                else:
                    default_seq_size = 12
                    default_hidden_neurons = 5
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_amazon + 'FFNN/FFNN_Model_AMAZON_Close.h5'
            elif global_name == 'Weather_WS':
                if column_prediction == 'Pressure': 
                    default_seq_size = 90
                    default_hidden_neurons = 19
                    default_epochs = 400
                    default_batch_size = 32  
                    model_path_ffnn = model_path_WS + 'FFNN/FFNN_Model_Temperature_Presure.h5'
                elif column_prediction == 'Temperature':
                    default_seq_size = 90
                    default_hidden_neurons = 16
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_WS + 'FFNN/FFNN_Model_Temperature_Temperature.h5'
                elif column_prediction == 'Saturation_vapor_pressure':
                    default_seq_size = 7
                    default_hidden_neurons = 30
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_WS + 'FFNN/FFNN_Model_Temperature_Saturation_vapor_pressure.h5'
                elif column_prediction == 'Vapor_pressure_deficit':
                    default_seq_size = 16
                    default_hidden_neurons = 15
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_WS + 'FFNN/FFNN_Model_Temperature_Vapor_pressure_deficit.h5'
                elif column_prediction == 'Specific_humidity':
                    default_seq_size = 8
                    default_hidden_neurons = 11
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_WS + 'FFNN/FFNN_Model_Temperature_Specific_humidity.h5'
                elif column_prediction == 'Airtight':
                    default_seq_size = 75
                    default_hidden_neurons = 13
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_WS + 'FFNN/FFNN_Model_Temperature_Airtight.h5'
                else:
                    default_seq_size = 4
                    default_hidden_neurons = 8
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_WS + 'FFNN/FFNN_Model_Temperature_Wind_speed.h5'
            else:
                if column_prediction =='max':
                    default_seq_size = 15
                    default_hidden_neurons = 40
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_HCM + 'FFNN/Train-FFNN-temperature-HCM-tmax.h5'
                elif column_prediction =='min':
                    default_seq_size = 50
                    default_hidden_neurons = 65
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_HCM + 'FFNN/Train-FFNN-temperature-HCM-tmin.h5'
                elif column_prediction =='wind':
                    default_seq_size = 5
                    default_hidden_neurons = 4
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_HCM + 'FFNN/Train-FFNN-temperature-HCM-wind.h5'
                elif column_prediction =='rain':
                    default_seq_size = 10
                    default_hidden_neurons = 8
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_HCM + 'FFNN/Train-FFNN-temperature-HCM-rain.h5'
                elif column_prediction =='humidi':
                    default_seq_size = 20
                    default_hidden_neurons = 19
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_HCM + 'FFNN/Train-FFNN-temperature-HCM-humidi.h5'
                else:
                    default_seq_size = 15
                    default_hidden_neurons = 16
                    default_epochs = 400
                    default_batch_size = 32
                    model_path_ffnn = model_path_HCM + 'FFNN/Train-FFNN-temperature-HCM-pressure.h5'
            
            start_train = time.time()
            model = model_ffnn_exist(default_seq_size, default_hidden_neurons, model_path_ffnn)
            end_train = time.time()
            
            x,y = to_sequences(test,1,default_seq_size)
            start_predict = time.time()
            test_pred = model.predict(x)
            end_predict = time.time()
            testScore_mse, testScore_rmse, testScore_mae = calculate_metrics(y, test_pred)
            
            y_real, test_pred_real = scale_data_original(y,test_pred,scaler)                                         
            testScore_mse_real, testScore_rmse_real, testScore_mae_real = calculate_metrics(y_real, test_pred_real)
            
            time_train = round(end_train - start_train, 5)
            time_predict = round(end_predict - start_predict, 5)
            eda_model(y,test_pred,column_prediction,algorithm)
            return jsonify(algorithm=algorithm, column_prediction=column_prediction, 
                            testScore_mse=testScore_mse, testScore_rmse = testScore_rmse,testScore_mae = testScore_mae,
                            testScore_mse_real=testScore_mse_real, testScore_rmse_real = testScore_rmse_real,testScore_mae_real = testScore_mae_real,
                            hidden_neurons=default_hidden_neurons, seq_size=default_seq_size, 
                            hidden_layers=default_hidden_layers, epochs=default_epochs, 
                            batch_sizes=default_batch_size, split_ratio=default_split_ratio,
                            time_train = time_train,time_predict = time_predict)                                      
        else: # For new dataset or train no existing model
            split_ratio_new,hidden_neurons_new,seq_size_new,epochs_new,batch_sizes_new,hidden_layers_new = get_param_ffnn_datasetNew()            
            scaled_data, scaler = scale_data(global_data[column_prediction].values.reshape(-1,1))
            train_datanew, test_datanew = split_data_new(scaled_data,split_ratio_new)
            start_train = time.time()
            model = model_ffnn_new(train_datanew, test_datanew,hidden_layers_new, seq_size_new, hidden_neurons_new, epochs_new, batch_sizes_new)
            end_train = time.time()
            x,y = to_sequences(test_datanew,1,seq_size_new)      
            
            start_predict = time.time()
            test_pred = model.predict(x)
            end_predict = time.time()
            
            testScore_mse, testScore_rmse, testScore_mae = calculate_metrics(y, test_pred)
            
            y_real, test_pred_real = scale_data_original(y,test_pred,scaler)                                         
            testScore_mse_real, testScore_rmse_real, testScore_mae_real = calculate_metrics(y_real, test_pred_real)
            
            eda_model(y,test_pred,column_prediction,algorithm)
            
            time_train = round(end_train - start_train, 5)
            time_predict = round(end_predict - start_predict, 5)
            return jsonify(algorithm=algorithm, column_prediction=column_prediction, 
                           testScore_mse=testScore_mse,testScore_rmse=testScore_rmse,testScore_mae=testScore_mae,
                           testScore_mse_real=testScore_mse_real, testScore_rmse_real = testScore_rmse_real,testScore_mae_real = testScore_mae_real,
                           hidden_neurons=hidden_neurons_new, seq_size=seq_size_new, hidden_layers=hidden_layers_new, 
                           epochs=epochs_new, batch_sizes=batch_sizes_new, split_ratio=split_ratio_new,
                           time_train = time_train,time_predict = time_predict)     
#-----------LSTM-------------------   
    elif algorithm == 'algorithm-lstm':
        if useExistingModel == 'on': 
            epochs_lstm = 300
            batch_sizes_lstm = 16
            hidden_layers_lstm = 1
            split_ratio_lstm = 0.8
            
            if global_name == 'APPLE' or global_name == 'GOOGLE' or global_name == 'AMAZON':
                seq_size_lstm = 12
                hidden_neurons_lstm = 5
                output_lstm = 5
                array_temp = array_stock   
                if global_name == 'APPLE':      
                    model_path_lstm = model_path_apple + 'LSTM/LSTM_APPLE.h5'
                elif global_name == 'GOOGLE':
                    model_path_lstm = model_path_google + 'LSTM/LSTM_GOOGLE.h5'
                else:
                    model_path_lstm = model_path_amazon + 'LSTM/LSTM_AMAZON.h5'
            elif global_name == 'Weather_WS':
                seq_size_lstm = 16
                hidden_neurons_lstm = 35
                output_lstm = 7
                array_temp = array_WS
                model_path_lstm = model_path_WS + 'LSTM/LSTM_DucWS.h5'
            else:
                seq_size_lstm = 35
                hidden_neurons_lstm = 5
                output_lstm = 6
                array_temp = array_HCM
                model_path_lstm = model_path_HCM + 'LSTM/LSTM_HCM.h5'
                
            scaled_data, scaler = scale_data(global_data[array_temp])
            train, test = split_data_default(scaled_data)    
            
            start_train = time.time()         
            model_lstm = LSTM_exist(train, output_lstm, seq_size_lstm, hidden_neurons_lstm, model_path_lstm)
            end_train = time.time()
            
            testX_LSTM, testY_LSTM = to_sequences_multivariate_lstm(test,seq_size_lstm)           
            
            start_predict = time.time()
            result_LSTM = model_lstm.predict(testX_LSTM) 
            end_predict = time.time()
            
            predict_LSTM_real = scaler.inverse_transform(result_LSTM)
            textY_LSTM_real = scaler.inverse_transform(testY_LSTM)
            time_train = round(end_train - start_train, 5)
            time_predict = round(end_predict - start_predict, 5) 
                                                            
            testScore_mse, testScore_rmse, testScore_mae, testScore_mse_real, testScore_rmse_real, testScore_mae_real = LSTM_Predict(result_LSTM,testY_LSTM,predict_LSTM_real,textY_LSTM_real,array_temp,column_prediction,algorithm)
            
            return jsonify(algorithm=algorithm, column_prediction=column_prediction,
                            testScore_mse=testScore_mse,testScore_rmse=testScore_rmse,testScore_mae=testScore_mae,
                            testScore_mse_real=testScore_mse_real, testScore_rmse_real = testScore_rmse_real,testScore_mae_real = testScore_mae_real,
                            hidden_neurons = hidden_neurons_lstm, 
                            seq_size=seq_size_lstm, 
                            hidden_layers= hidden_layers_lstm,
                            epochs=epochs_lstm, 
                            batch_sizes=batch_sizes_lstm, 
                            split_ratio=split_ratio_lstm,
                            time_train = time_train,time_predict = time_predict)          
        else: # Train a new model or use a new dataset
            output_lstm_new = len(array_column_new)
            split_ratio_lstm_new, hidden_neurons_lstm_new,seq_size_lstm_new, epochs_lstm_new, batch_sizes_lstm_new, hidden_layers_lstm_new = get_param_ffnn_datasetNew()                                          
            
            scaled_data, scaler = scale_data(global_data[array_column_new])
            train_new, test_new  = split_data_new(scaled_data,split_ratio_lstm_new)
            
            start_train = time.time()
            model_new = LSTM_new(train_new,test_new,output_lstm_new, seq_size_lstm_new, hidden_neurons_lstm_new,epochs_lstm_new,batch_sizes_lstm_new, hidden_layers_lstm_new,algorithm)
            end_train = time.time()
            
            testX_LSTM_new, testY_LSTM_new = to_sequences_multivariate_lstm(test_new, seq_size_lstm_new)                               
            
            start_predict = time.time()
            result_LSTM_new = model_new.predict(testX_LSTM_new) 
            end_predict = time.time()
            
            predict_LSTM_real = scaler.inverse_transform(result_LSTM_new)
            textY_LSTM_real = scaler.inverse_transform(testY_LSTM_new)   
            testScore_mse, testScore_rmse, testScore_mae, testScore_mse_real, testScore_rmse_real, testScore_mae_real = LSTM_Predict(result_LSTM_new,testY_LSTM_new,predict_LSTM_real,textY_LSTM_real,array_column_new,column_prediction,algorithm)
            time_train = round(end_train - start_train, 5)
            time_predict = round(end_predict - start_predict, 5)
                        
            return jsonify(algorithm=algorithm, column_prediction=column_prediction, 
                           testScore_mse=testScore_mse, testScore_rmse=testScore_rmse,testScore_mae=testScore_mae,  
                           testScore_mse_real=testScore_mse_real, testScore_rmse_real = testScore_rmse_real,testScore_mae_real = testScore_mae_real,
                           hidden_layers=hidden_layers_lstm_new,
                           hidden_neurons=hidden_neurons_lstm_new, 
                           seq_size=seq_size_lstm_new,
                           epochs=epochs_lstm_new, 
                           batch_sizes=batch_sizes_lstm_new, 
                           split_ratio=split_ratio_lstm_new,
                           time_train = time_train,time_predict = time_predict)
    elif algorithm == 'algorithm-var':
        if useExistingModel == 'on':
            p = None
            if global_name == 'AMAZON' or global_name == 'GOOGLE':
                p =1
                array_temp = array_stock                
            elif global_name == 'APPLE':
                p = 2
                array_temp = array_stock
            elif global_name == 'Weather_WS':
                p = 11
                array_temp = array_WS
            else:
                p = 14
                array_temp = array_HCM
            
            scaled_data, scaler = scale_data(global_data[array_temp])
            train, test = split_data_default(scaled_data)            
            start_train = time.time()
            model_var, result = VAR_exist(train,p)
            end_train = time.time()
            
            start_predict = time.time()
            result_var = VAR_forecast(train,test,result,p)
            end_predict = time.time()
            
            predict_var,test_var = Extract_test_predict_var(column_prediction, array_temp, result_var, test)
            predict_var_real,test_var_real = scale_data_original_var(column_prediction, array_temp, scaler, result_var, test)
            
            testScore_mse, testScore_rmse, testScore_mae = calculate_metrics(test_var, predict_var)
            testScore_mse_real, testScore_rmse_real, testScore_mae_real = calculate_metrics(test_var_real, predict_var_real)
            
            time_train = round(end_train - start_train, 5)
            time_predict = round(end_predict - start_predict, 5)
            eda_model(test_var,predict_var,column_prediction,algorithm)
            return jsonify(algorithm=algorithm, column_prediction=column_prediction, 
                            testScore_mse=testScore_mse,testScore_rmse=testScore_rmse,testScore_mae=testScore_mae,
                            testScore_mse_real=testScore_mse_real, testScore_rmse_real = testScore_rmse_real,testScore_mae_real = testScore_mae_real,
                            p=p,split_ratio=0.8,
                            time_train = time_train,time_predict = time_predict) 
        else:
            split_ratio_var_new, p_max = get_Var_param()
            scaled_data, scaler = scale_data(global_data[array_column_new])
            train_new, test_new  = split_data_new(scaled_data,split_ratio_var_new)
                       
            start_train = time.time()
            model_var, result_new,p_optimize = VAR_New(train_new,test_new,p_max)
            end_train = time.time()
            
            start_predict = time.time()
            result_var_new = VAR_forecast(train_new,test_new,result_new,p_optimize)
            end_predict = time.time()
                        
            predict_var_new,test_var_new = Extract_test_predict_var(column_prediction, array_column_new, result_var_new, test_new)
            predict_var_new_real,test_var_new_real = scale_data_original_var(column_prediction, array_column_new, scaler, result_var_new, test_new)
            
            testScore_mse, testScore_rmse, testScore_mae = calculate_metrics(test_var_new, predict_var_new)
            testScore_mse_real, testScore_rmse_real, testScore_mae_real = calculate_metrics(test_var_new_real, predict_var_new_real)
            
            time_train = round(end_train - start_train, 5)
            time_predict = round(end_predict - start_predict, 5)    
            eda_model(test_var_new,predict_var_new,column_prediction,algorithm)        
            return jsonify(algorithm=algorithm, column_prediction=column_prediction, 
                            testScore_mse=testScore_mse,testScore_rmse=testScore_rmse,testScore_mae=testScore_mae,
                            testScore_mse_real=testScore_mse_real, testScore_rmse_real = testScore_rmse_real,testScore_mae_real = testScore_mae_real,
                            p=p_optimize,split_ratio=split_ratio_var_new,
                            time_train = time_train,time_predict = time_predict) 
    else:
        return render_template('index.html', message="Please choose a model"), 400

    
global_parameters = {}

@app.route('/save_parameters', methods=['GET', 'POST'])
def save_param():
    global global_parameters
    parameters = request.get_json()
    for param_name, value in parameters.items():
        print(f"Parameter {param_name} has value {value}")
    global_parameters = parameters

    name = global_parameters.get('name', None)
    if name is not None:
        print(f"The value of 'name' is {name}")
    return jsonify({'message': 'Received'}), 200

array_column_new = []
@app.route('/getcolumn_ouput_multi', methods=['POST'])
def get_columns():
    global array_column_new
    array_column_new = request.get_json()
    print(array_column_new)
    return jsonify({'message': 'Received'}), 200
    
if __name__ == '__main__':
    app.run(debug=True) 