import streamlit as st
import pandas as pd
import glob
import json

import sqlite3
from google.oauth2 import service_account
from google.cloud import bigquery


# load wildfire data from sqlite
@st.cache_data
def load_wildfire_data_local_db():
    cnx = sqlite3.connect('dataset/FPA_FOD_20170508.sqlite')

    df = pd.read_sql_query("SELECT fire_year as year, discovery_date as date, state, stat_cause_code, stat_cause_descr as stat_cause, latitude, longitude, fire_size, fire_size_class FROM 'Fires' ORDER BY fire_year, discovery_date", cnx)
    df['date'] = pd.to_datetime(df['date'] - pd.Timestamp(0).to_julian_date(), unit='D')
    df['incident'] = 1
    df.columns = df.columns.str.lower()

    return df


# load weather data from csv file
@st.cache_data
def load_wildfire_data_local_csv():
    df = pd.read_csv('dataset/wildfire_data.csv')
    df['incident'] = 1
    df['datetime'] = pd.to_datetime(df['date'])
    df['date'] = pd.to_datetime(df['date'].dt.date)

    return df


# load wildfire data from google cloud big query
@st.cache_data
def load_wildfire_data_gcp():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    client = bigquery.Client(credentials=credentials)

    query_job = client.query("SELECT * FROM `vernal-shine-239106.US_Wildfire_Dataset.wildfire` LIMIT 1000")
    df = (query_job.result().to_dataframe())
    
    df['incident'] = 1
    df['datetime'] = df['date']
    df['date'] = pd.to_datetime(df['date'].dt.date)

    return df


# load weather data from json files
@st.cache_data
def load_weather_data_local_json():
    file_path = "dataset/weather/weather_hist_*_*.json"

    json_files = sorted(glob.glob(file_path))

    df = None
    for json_file in json_files:
        with open(json_file,'r') as f:
            weather_dict = json.loads(f.read())
            state = json_file.split('_')[2]

            if df is None:
                df = pd.json_normalize(weather_dict, record_path=['days'])
                df['region'] = state
            else:
                tmp_df = pd.json_normalize(weather_dict, record_path=['days'])
                tmp_df['region'] = state
                df = pd.concat([df, tmp_df])
                del tmp_df

    df.rename(columns={'datetime': 'date'}, inplace=True)
    df['date'] = pd.to_datetime(df['date'])

    return df


# load weather data from csv file
@st.cache_data
def load_weather_data_local_csv():
    df = pd.read_csv('input/weather_data.csv')
    df['date'] = pd.to_datetime(df['date'])

    return df


# precompute values (lists, ranges) to be used in forms
@st.cache_data
def precompute_values_lists(df):
    list_fire_size_classes = df['fire_size_class'].sort_values().unique()
    list_states = df['region'].sort_values().unique()
    list_years = df['date'].dt.year.sort_values().astype(str).unique()
    list_causes = df['stat_cause'].sort_values().unique()

    return list_fire_size_classes, list_states, list_years, list_causes


@st.cache_data
def precompute_values_ranges(df):
    max_fire_size = int(max(df['fire_size'])) + 1
    min_date = min(df['date'])
    max_date = max(df['date'])

    return max_fire_size, min_date, max_date


@st.cache_data
def get_fire_size_class_range(max_fire_size):
    # fire size class range based on the values given by the dataset owners
    fire_size_class_range = {
        'A': (0, 1),
        'B': (0, 10),
        'C': (10, 100),
        'D': (100, 300),
        'E': (300, 1000),
        'F': (1000, 5000),
        'G': (5000, max_fire_size)
    }
    return fire_size_class_range;


@st.cache_data
def precompute_values_lists_weather(df):
    list_states = df['region'].sort_values().unique()
    print(df['region'])

    return list_states