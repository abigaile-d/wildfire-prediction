import streamlit as st

import glob
import numpy as np
import altair as alt

import utils

# load data and vars
#client = utils.connect_gcp()
wildfire_df = utils.load_wildfire_data_local_csv()
weather_df = utils.load_weather_data_local_csv(filename='input/weather_data.csv')
list_fire_size_classes, _, list_years, list_causes = utils.get_wildfire_lists(wildfire_df)
max_fire_size, min_date, max_date = utils.get_wildfire_ranges(wildfire_df)
fire_size_class_range = utils.get_wildfire_size_class_range(max_fire_size)

list_states = utils.get_weather_lists(weather_df)
descr_dict = utils.load_descriptions_weather(filename='input/descr_weather_data_vcross.json')
shared_descr_dict = utils.load_descriptions_shared()

# tile and short background
st.title("Weather and Wildfire Data")
st.sidebar.header("Weather and Wildfire Data")
st.sidebar.subheader("Background:")
for descr in descr_dict['header']:
    st.sidebar.markdown(descr)
for descr in shared_descr_dict['header']:
    st.sidebar.markdown(descr)
for descr in shared_descr_dict['caption']:
    st.sidebar.caption(descr)

# define forms
st.markdown("Use the following widgets to filter the data used in below charts:")
left_col, right_col = st.columns((4, 1))
choice_fire_class_min, choice_fire_class_max = left_col.select_slider("Filter by Fire Size Class:", list_fire_size_classes, \
    value=('C', 'G'))
choice_fire_size_min, choice_fire_size_max = left_col.slider("Filter by Fire Size (in acres):", \
    min_value=fire_size_class_range[choice_fire_class_min][0], max_value=fire_size_class_range[choice_fire_class_max][1], \
    value=(fire_size_class_range[choice_fire_class_min][0], fire_size_class_range[choice_fire_class_max][1]))
expander = right_col.expander("See Fire Size Class Legend")
expander.markdown(shared_descr_dict["fire_size_class_legend"])

choice_state = st.selectbox("Filter by U.S. State:", np.hstack(('All', list_states)))
st.caption("Note: Limited U.S. states being shown as data is not yet complete due to API query limitations.")
choice_year = st.radio("Filter by Year:", np.hstack((list_years, 'All')), index=len(list_years), horizontal=True)
left_col, right_col = st.columns(2)
choice_date_from = left_col.date_input("Filter by Date Range:", min_value=min_date, max_value=max_date, value=min_date, disabled=(choice_year != 'All'))
choice_date_to = right_col.date_input("", min_value=choice_date_from, max_value=max_date, value=max_date, disabled=(choice_year != 'All'), label_visibility='hidden')
choice_cause = st.multiselect("Cause of Fire:", list_causes, default=list_causes)

# filter data based on form inputs
wildfire_df = wildfire_df[['date', 'region', 'fire_size_class', 'stat_cause', 'fire_size', 'incident']]
if choice_fire_class_min != 'A' or choice_fire_class_max != 'G':
    wildfire_df = wildfire_df.loc[(wildfire_df['fire_size_class'] >= choice_fire_class_min) & \
        (wildfire_df['fire_size_class'] <= choice_fire_class_max)]
if choice_fire_size_min > 0 or choice_fire_size_max < max_fire_size:
    wildfire_df = wildfire_df.loc[(wildfire_df['fire_size'] >= choice_fire_size_min) & \
        (wildfire_df['fire_size'] < choice_fire_size_max)]

if choice_state != 'All':
    wildfire_df = wildfire_df.loc[wildfire_df['region'] == choice_state]
    weather_df = weather_df.loc[weather_df['region'] == choice_state]

if choice_year != 'All':
    choice_year = int(choice_year)
    wildfire_df = wildfire_df.loc[wildfire_df['date'].dt.year == choice_year]
    weather_df = weather_df.loc[weather_df.date.dt.year == choice_year]
else:
    wildfire_df = wildfire_df.loc[(wildfire_df['date'].dt.date >= choice_date_from) & (wildfire_df['date'].dt.date <= choice_date_to)]
    weather_df = weather_df.loc[(weather_df['date'].dt.date >= choice_date_from) & (weather_df['date'].dt.date <= choice_date_to)]

wildfire_df = wildfire_df.loc[wildfire_df['stat_cause'].isin(choice_cause)]


# merge the weather dataframe with the wildfire dataframe
merged_df = weather_df.merge(wildfire_df, how='left')
merged_df[['fire_size', 'incident']] = merged_df[['fire_size', 'incident']].fillna(0)
merged_df[['fire_size_class', 'stat_cause']] = merged_df[['fire_size_class', 'stat_cause']].fillna('No Fire')
merged_df.fillna(0, inplace=True)

# display temperatures and wildfires by month of year
st.header("Temperature vs. Wildfires by Month of Year")
tmp_df = weather_df[['date', 'temp', 'tempmin', 'tempmax']]
tmp_df['date_month'] = tmp_df.date.dt.month
chart1 = alt.Chart(tmp_df, width=600, height=200).mark_boxplot(extent='min-max').encode(
    x='date_month:O',
    y=alt.Y('temp:Q', scale=alt.Scale(zero=False))
)

tmp_df = wildfire_df[['date', 'incident', 'fire_size']]
tmp_df['date_month'] = tmp_df.date.dt.month
tmp_df = tmp_df.groupby('date_month').sum().reset_index()
chart2 = alt.Chart(tmp_df, width=600, height=50).mark_area().encode(
    x='date_month:N',
    y='incident:Q'
)
st.altair_chart(alt.vconcat(chart1, chart2), use_container_width=True)

expander = st.expander(shared_descr_dict["charts"]["label"])
expander.markdown(descr_dict["charts"]["month"]["overview"].format(choice_state, descr_dict["charts"]["month"][choice_state]))


# display
st.header("Data Distribution on Weather Measurements")
tabs = st.tabs(["Temperature", "Dew Point", "Humidity", "Precipitation Probability", "Wind Speed", "Pressure", "Cloud Cover", "UV Index"])

i = 0
col_width = 100 * (len(list_fire_size_classes) + 1) / len(merged_df['fire_size_class'].sort_values().unique()) - 15
for col in ['temp', 'dew', 'humidity', 'precipprob', 'windspeed', 'pressure', 'cloudcover', 'uvindex']:
    tmp_df = merged_df[['date', 'fire_size_class',  'stat_cause', col]]
    with tabs[i]:
        scale_range = (min(tmp_df[col]), max(tmp_df[col]))
        
        violins =  alt.Chart().transform_density(
            col, 
            as_=[col, 'density'], 
            groupby=['fire_size_class']
        ).mark_area(orient='horizontal').encode(
            x=alt.X('density:Q', 
                    stack='center', 
                    impute=None, 
                    title=None,
                    axis=alt.Axis(labels=False, 
                                  values=[0], 
                                  grid=False, 
                                  ticks=False)),
            y=alt.Y(col + ':Q', 
                    scale=alt.Scale(domain=[scale_range[0], scale_range[1]])),
            color=alt.Color('fire_size_class:N', 
                            legend=None)
        )

        chart = alt.layer(
            violins,
            alt.Chart().mark_rule(clip=False).encode(
                y='mean('+col+'):Q',
                color=alt.value('black')),
        ).properties(
            width=col_width
        ).facet(
            data=tmp_df,
            column=alt.Column('fire_size_class:N')
        )

        st.altair_chart(chart)

        expander = st.expander(shared_descr_dict["charts"]["label"])
        expander.markdown(descr_dict["charts"]["weather_measure"][col])

    i = i + 1
