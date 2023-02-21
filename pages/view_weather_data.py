import streamlit as st

import glob
import numpy as np
import altair as alt

import utils

# load data and vars
wildfire_df = utils.load_wildfire_data()
weather_df = utils.load_weather_data()
list_fire_size_classes, _, list_years, list_causes = utils.precompute_values_lists(wildfire_df)
max_fire_size, min_date, max_date = utils.precompute_values_ranges(wildfire_df)
fire_size_class_range = utils.get_fire_size_class_range(max_fire_size)

list_states = utils.precompute_values_lists_weather(weather_df)

# tile and short background
st.title("Weather and Wildfire Data")
st.sidebar.header("Weather and Wildfire Data")
st.sidebar.subheader("Background:")
st.sidebar.markdown("The weather data used in this project is from **\"Visual Crossing Weather API\"** \
    [[Webpage]](https://www.visualcrossing.com/weather-api). Historical daily weather data were queried \
    for each U.S. state location via API. The wildfire data comes from the same Kaggle dataset as \
    mentioned in the previous page.")
st.sidebar.markdown("This page shows the relationship between wildfire incidents and different weather conditions.")
st.sidebar.markdown("The aim of this project is to predict risks of wildfires based on various \
    factors (e.g. weather data), which can help in the monitoring, triaging and prevention of large wildfires.")
st.sidebar.caption("This project is ongoing and more features will be added in the future.")

# define forms
st.markdown("Use the following widgets to filter the data used in below charts:")
left_col, right_col = st.columns((4, 1))
choice_fire_class_min, choice_fire_class_max = left_col.select_slider("Filter by Fire Size Class:", list_fire_size_classes, \
    value=('C', 'G'))
choice_fire_size_min, choice_fire_size_max = left_col.slider("Filter by Fire Size (in acres):", \
    min_value=fire_size_class_range[choice_fire_class_min][0], max_value=fire_size_class_range[choice_fire_class_max][1], \
    value=(fire_size_class_range[choice_fire_class_min][0], fire_size_class_range[choice_fire_class_max][1]))
expander = right_col.expander("See Fire Size Class Legend")
expander.markdown("In acres:  \n**A**: 0.+ - 0.25  \n**B**: 0.26 - 9.9   \n**C**: 10.0 - 99.9  \n" \
    "**D**: 100 - 299  \n**E**: 300 - 999  \n**F**: 1000 - 4999  \n**G**: 5000+")


choice_state = st.selectbox("Filter by U.S. State:", np.hstack(('All', list_states)))
st.caption("Note: Limited U.S. states being shown as data is not yet complete due to API query limitations.")
choice_year = st.radio("Filter by Year:", np.hstack((list_years, 'All')), index=len(list_years), horizontal=True)
left_col, right_col = st.columns(2)
choice_date_from = left_col.date_input("Filter by Date Range:", min_value=min_date, max_value=max_date, value=min_date, disabled=(choice_year != 'All'))
choice_date_to = right_col.date_input("", min_value=choice_date_from, max_value=max_date, value=max_date, disabled=(choice_year != 'All'), label_visibility='hidden')
choice_cause = st.multiselect("Cause of Fire:", list_causes, default=list_causes)

# filter data based on form inputs
wildfire_df = wildfire_df[['date', 'year', 'state', 'fire_size_class', 'stat_cause', 'fire_size', 'incident']]
if choice_fire_class_min != 'A' or choice_fire_class_max != 'G':
    wildfire_df = wildfire_df.loc[(wildfire_df['fire_size_class'] >= choice_fire_class_min) & \
        (wildfire_df['fire_size_class'] <= choice_fire_class_max)]
if choice_fire_size_min > 0 or choice_fire_size_max < max_fire_size:
    wildfire_df = wildfire_df.loc[(wildfire_df['fire_size'] >= choice_fire_size_min) & \
        (wildfire_df['fire_size'] < choice_fire_size_max)]

if choice_state != 'All':
    wildfire_df = wildfire_df.loc[wildfire_df['state'] == choice_state]
    weather_df = weather_df.loc[weather_df['state'] == choice_state]

if choice_year != 'All':
    choice_year = int(choice_year)
    wildfire_df = wildfire_df.loc[wildfire_df['year'] == choice_year]
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

desc = dict()
desc['All'] = "Observations about individual states will be displayed if a state was selected in the \
    options above."
desc['CA'] = "There is an obvious correlation between temperatures and wildfire incidents in CA, \
    which is what would have been expected. More wildfires occur during California summer months."
desc['TX'] = "The months with most wildfires in Texas are January to March, and August. \
    August is the hottest month in Texas, but January to March relatively colder. More analysis is needed \
    to understand why more wildfires happen during the winter months in Texas."
expander = st.expander("Comments / Observations")
expander.markdown("In general, the months of February to April have the most wildfire incidents, \
    even though the average temperatures during these months are lower.  More thorough \
    analysis needed to know why this is the case. \n \
    \n **{}:** {}".format(choice_state, desc[choice_state]))


# display
st.header("Data Distribution on Weather Measurements")
tabs = st.tabs(["Temperature", "Dew Point", "Humidity", "Precipitation Probability", "Wind Speed", "Pressure", "Cloud Cover", "UV Index"])

desc = dict()
desc['temp'] = ("The temperature values are from the average temperature for the day.",
    "On all fire size classes, more wildfires seem to occur on higher temperatures, and less on lower temperatures. \
    Larger wildfires also tend to happen at higher temperatures than smaller ones, on average.")
desc['dew'] = ("Dew point is the temperature to which air must be cooled for the water vapor in it \
    to condense into dew or frost.", 
    "More wildfires seem to occur on slightly higher dew points.")
desc['humidity'] = ("Humidity is the amount of water vapor in the air.", 
    "Lower humidity seems to cause more wildfires, and less wildfires happen on highly humid days.")
desc['precipprob'] = ("Precipitation Probability is the likelihood of measurable precipitation ranging from 0% to 100%.", 
    "More wildfires seem to occur on days with lower precipitation probability.")
desc['windspeed'] = ("Wind Speed is the maximum hourly average sustained wind speed value for the day.", 
    "Although wind speed does not seem to have a significant effect on small wildfires, faster wind speed seems to cause \
    bigger wildfires.")
desc['pressure'] = ("Pressure is the sea level atmospheric or barometric pressure in millibars (or hectopascals).", 
    "More and bigger wildfires seem to occur on days with lower pressure.")
desc['cloudcover'] = ("Cloud cover is how much of the sky is covered in clouds ranging from 0-100%.", 
    "More wildfires seem to occur on less cloudy days.")
desc['uvindex'] = ("UX Index is a value between 0 (=no exposure) and 10 (=high) indicating the level of \
    ultraviolet (UV) exposure for that day.", 
    "Although there are still many wildfires occurring during low UV days, high UV days seems to have been a factor in \
    causing more wildfires.")

i = 0
col_width = 75 * (len(list_fire_size_classes) + 1) / len(merged_df['fire_size_class'].sort_values().unique()) - 15
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

        expander = st.expander("Comments / Observations")
        expander.markdown("{}  \n \n {}".format(desc[col][0], desc[col][1]))

    i = i + 1
