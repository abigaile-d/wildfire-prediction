# wildfire-prediction

[View in Streamlit] (https://abigaile-d-wildfire-prediction.streamlit.app/)

This project is an Exploratory Data Analysis of U.S. wildfires and how weather can be a factor in prevalence or spread of it. The aim of this project is to predict risks of wildfires based on various factors (e.g. weather data), which can help in the monitoring, triaging and prevention of large wildfires.

## Description

### Dataset

The wildfire data used in this project is from the ["1.88 Million U.S. Wildfires"](https://www.kaggle.com/datasets/rtatman/188-million-us-wildfires) Kaggle dataset, which contains 24 years of spatial information on wildfires that occurred in the United States from 1992 to 2015. For this project, only wildfires over 10 acres were considered, and the smaller wildfires were filtered out. The dataset was originally in sqlite format, but I uploaded it to Google Cloud's BigQuery for more flexibility.

The weather data is from ["National Oceanic and Atmospheric Administration (NOAA)"](https://console.cloud.google.com/marketplace/details/noaa-public/gsod) in Google BigQuery. Historical daily weather data were queried for each U.S. state location.

### Technologies

+ Web app: streamlit
+ Visualization: streamlit charts and altair
+ Data hosting: Google Cloud's BigQuery
+ Python
+ SQL

## Getting Started

Clone the repository, and run the following commands:

    pip install -r requirements_full.txt
    streamlit run view_wildfire_data.py

*Note: There is a separate requirements.txt and requirements_full.txt as the former is the only minimum packages needed by streamlit cloud.*
