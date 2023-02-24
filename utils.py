import streamlit as st
import pandas as pd
import glob
import json

# import sqlite3
from google.oauth2 import service_account
from google.cloud import bigquery


@st.cache_resource
def connect_gcp():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    client = bigquery.Client(credentials=credentials)

    return client

# load wildfire data from sqlite
@st.cache_data
def load_wildfire_data_local_db(filename='dataset/FPA_FOD_20170508.sqlite'):
    cnx = sqlite3.connect()

    df = pd.read_sql_query("SELECT fire_year as year, discovery_date as date, state, stat_cause_code, stat_cause_descr as stat_cause, latitude, longitude, fire_size, fire_size_class FROM 'Fires' ORDER BY fire_year, discovery_date", cnx)
    df['date'] = pd.to_datetime(df['date'] - pd.Timestamp(0).to_julian_date(), unit='D')
    df['incident'] = 1
    df.columns = df.columns.str.lower()

    return df


# load weather data from csv file
@st.cache_data
def load_wildfire_data_local_csv(filename='dataset/wildfire_data.csv'):
    df = pd.read_csv(filename)
    df['incident'] = 1
    df['datetime'] = pd.to_datetime(df['date'])
    df['date'] = pd.to_datetime(df['datetime'].dt.date)

    return df


# load wildfire data from google cloud big query
@st.cache_data
def load_wildfire_data_gcp(_client):
    query_job = _client.query("SELECT * FROM `vernal-shine-239106.US_Wildfire_Dataset.wildfire`")
    df = (query_job.result().to_dataframe())
    
    df['incident'] = 1
    df['datetime'] = df['date']
    df['date'] = pd.to_datetime(df['date'].dt.date)

    return df


# load weather data from visual crossing json files (api export)
@st.cache_data
def load_weather_data_local_json(filename='dataset/weather_vcross/weather_hist_*_*.json'):
    json_files = sorted(glob.glob(filename))

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


# load weather data csv from noaa (gcp export)
@st.cache_data
def load_weather_data_local_csv(filename='dataset/weather_noaa/weather_data_noaa_*.csv'):
    csv_files = sorted(glob.glob(filename))

    df_list = []
    for file in csv_files:
        df = pd.read_csv(file, index_col=None, header=0)
        df_list.append(df)

    df = pd.concat(df_list, ignore_index=True)
    df.rename(columns={'state': 'region'}, inplace=True)
    df['date'] = pd.to_datetime(df['date'])
    
    return df


# load weather data direct from gcp bigquery noaa dataset
@st.cache_data
def load_weather_data_gcp(_client, from_year=1992, to_year=2015):
    query_stmt = "SELECT CONCAT(year,'-',mo,'-',da) as date, \
                        country, state as region, AVG(s.lat) lat, AVG(s.lon) lon, COUNT(*) count, \
                        AVG(IF (temp=9999.9, null, temp)) as temp, \
                        AVG(IF (dewp=9999.9, null, dewp)) as dew_point, \
                        AVG(IF (slp=9999.9, null, slp)) as sea_level_pressure, \
                        AVG(IF (stp=9999.9, null, stp)) as station_pressure, \
                        AVG(IF (visib=999.9, null, visib)) as visibility, \
                        AVG(IF (wdsp='999.9', null, CAST(wdsp AS FLOAT64))) as wind_speed, \
                        MAX(IF (mxpsd='999.9', null, CAST(mxpsd AS FLOAT64))) as max_sustained_wind, \
                        MAX(IF (gust=999.9, null, gust)) as max_wind_gust, \
                        MAX(IF (max=9999.9, null, max)) as max_temp, \
                        MIN(IF (min=9999.9, null, min)) as min_temp, \
                        AVG(IF (prcp=99.9, null, prcp)) as precipitation, \
                        AVG(IF (sndp=999.9, null, sndp)) as snow_depth, \
                        MAX(CAST(fog AS INT64)) as fog, \
                        MAX(CAST(rain_drizzle AS INT64)) as rain_drizzle, \
                        MAX(CAST(snow_ice_pellets AS INT64)) as snow_ice_pellets, \
                        MAX(CAST(hail AS INT64)) as hail, \
                        MAX(CAST(thunder AS INT64)) as thunder, \
                        MAX(CAST(tornado_funnel_cloud AS INT64)) as tornado_funnel_cloud \
                    FROM `bigquery-public-data.noaa_gsod.gsod*` w \
                    JOIN `bigquery-public-data.noaa_gsod.stations` s \
                    ON w.stn = s.usaf AND w.wban = s.wban  \
                    AND _TABLE_SUFFIX BETWEEN '{}' AND '{}' \
                    AND s.country = 'US' AND state IS NOT NULL \
                    GROUP BY _TABLE_SUFFIX, date, country, state \
                    ORDER BY date, country, state".format(from_year, to_year)

    query_job = _client.query(query_stmt)
    df = (query_job.result().to_dataframe())
    df['date'] = pd.to_datetime(df['date'])

    return df


# precompute values (lists, ranges) to be used in forms
@st.cache_data
def get_wildfire_lists(df):
    list_fire_size_classes = df['fire_size_class'].sort_values().unique()
    list_states = df['region'].sort_values().unique()
    list_years = df['date'].dt.year.sort_values().astype(str).unique()
    list_causes = df['stat_cause'].sort_values().unique()

    return list_fire_size_classes, list_states, list_years, list_causes


@st.cache_data
def get_wildfire_ranges(df):
    max_fire_size = int(max(df['fire_size'])) + 1
    min_date = min(df['date'])
    max_date = max(df['date'])

    return max_fire_size, min_date, max_date


@st.cache_data
def get_wildfire_size_class_range(max_fire_size):
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
    return fire_size_class_range


@st.cache_data
def get_weather_lists(df):
    list_states = df['region'].sort_values().unique()

    return list_states


def load_descriptions(filename):
    with open(filename,'r') as f:
        dict = json.loads(f.read())

    return dict


@st.cache_data
def load_descriptions_shared(filename='input/descr_shared_data.json'):
    return load_descriptions(filename)


@st.cache_data
def load_descriptions_wildfire(filename='input/descr_wildfire_data.json'):
    return load_descriptions(filename)


@st.cache_data
def load_descriptions_weather(filename='input/descr_weather_data.json'):
    return load_descriptions(filename)