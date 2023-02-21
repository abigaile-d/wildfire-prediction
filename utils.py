import streamlit as st
import sqlite3
import pandas as pd
import glob
import json


# load wildfire data from sqlite
@st.cache
def load_wildfire_data():
    cnx = sqlite3.connect('input/FPA_FOD_20170508.sqlite')

    df = pd.read_sql_query("SELECT fire_year as year, discovery_date as date, state, stat_cause_code, stat_cause_descr as stat_cause, latitude, longitude, fire_size, fire_size_class FROM 'Fires' ORDER BY fire_year, discovery_date", cnx)
    df['date'] = pd.to_datetime(df['date'] - pd.Timestamp(0).to_julian_date(), unit='D')
    df['incident'] = 1
    df.columns = df.columns.str.lower()

    return df

# load weather data from json files
@st.cache(allow_output_mutation=True)
def load_weather_data():
    file_path = "input/weather_hist_*_*.json"

    json_files = sorted(glob.glob(file_path))

    df = None
    for json_file in json_files:
        with open(json_file,'r') as f:
            weather_dict = json.loads(f.read())
            state = json_file.split('_')[2]

            if df is None:
                df = pd.json_normalize(weather_dict, record_path=['days'])
                df['state'] = state
            else:
                tmp_df = pd.json_normalize(weather_dict, record_path=['days'])
                tmp_df['state'] = state
                df = pd.concat([df, tmp_df])
                del tmp_df

    df.rename(columns={'datetime': 'date'}, inplace=True)
    df['date'] = pd.to_datetime(df['date'])

    return df

# precompute values (lists, ranges) to be used in forms
@st.cache
def precompute_values_lists(df):
    list_fire_size_classes = df['fire_size_class'].sort_values().unique()
    list_states = df['state'].sort_values().unique()
    list_years = df['year'].sort_values().astype(str).unique()
    list_causes = df['stat_cause'].sort_values().unique()

    return list_fire_size_classes, list_states, list_years, list_causes

@st.cache
def precompute_values_ranges(df):
    max_fire_size = int(max(df['fire_size'])) + 1
    min_date = min(df['date'])
    max_date = max(df['date'])

    return max_fire_size, min_date, max_date

@st.cache
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

@st.cache
def precompute_values_lists_weather(df):
    list_states = df['state'].sort_values().unique()
    print(df['state'])

    return list_states