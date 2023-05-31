import streamlit as st

import sqlite3
import numpy as np
import pandas as pd
import altair as alt

import utils  # saved shared functions in utils


# load data and vars
client = utils.connect_gcp()
wildfire_df = utils.load_wildfire_data_gcp(client)
list_fire_size_classes, list_states, list_years, list_causes = utils.get_wildfire_lists(wildfire_df)
max_fire_size, min_date, max_date = utils.get_wildfire_ranges(wildfire_df)
fire_size_class_range = utils.get_wildfire_size_class_range(max_fire_size)

descr_dict = utils.load_descriptions_wildfire()
shared_descr_dict = utils.load_descriptions_shared()
if(list_fire_size_classes[0] == 'A'):
    chart_key_alt = "charts_full"
else:
    chart_key_alt = "charts"

# tile and short background
st.title("U.S. Wildfire Data")
st.sidebar.header("U.S. Wildfire Data")
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
    value=('C', list_fire_size_classes[-1]))
choice_fire_size_min, choice_fire_size_max = left_col.slider("Filter by Fire Size (in acres):", \
    min_value=fire_size_class_range[choice_fire_class_min][0], max_value=fire_size_class_range[choice_fire_class_max][1], \
    value=(fire_size_class_range[choice_fire_class_min][0], fire_size_class_range[choice_fire_class_max][1]))
expander = right_col.expander("See Fire Size Class Legend")
expander.markdown(shared_descr_dict["fire_size_class_legend"])

choice_state = st.selectbox("Filter by U.S. State:", np.hstack(('All', list_states)))
choice_year = st.radio("Filter by Year:", np.hstack((list_years, 'All')), index=len(list_years), horizontal=True)
left_col, right_col = st.columns(2)
choice_date_from = left_col.date_input("Filter by Date Range:", min_value=min_date, max_value=max_date, \
    value=min_date, disabled=(choice_year != 'All'))
choice_date_to = right_col.date_input("", min_value=choice_date_from, max_value=max_date, \
    value=max_date, disabled=(choice_year != 'All'), label_visibility='hidden')

# filter data based on form inputs
st.header("Wildfire Incidents and their Location")
if choice_fire_class_min != 'A' or choice_fire_class_max != 'G':
    wildfire_df = wildfire_df.loc[(wildfire_df['fire_size_class'] >= choice_fire_class_min) & \
        (wildfire_df['fire_size_class'] <= choice_fire_class_max)]
if choice_fire_size_min > 0 or choice_fire_size_max < max_fire_size:
    wildfire_df = wildfire_df.loc[(wildfire_df['fire_size'] >= choice_fire_size_min) & \
        (wildfire_df['fire_size'] < choice_fire_size_max)]

if choice_state != 'All':
    wildfire_df = wildfire_df.loc[wildfire_df['region'] == choice_state]

if choice_year != 'All':
    choice_year = int(choice_year)
    wildfire_df = wildfire_df.loc[wildfire_df['date'].dt.year == choice_year]
else:
    wildfire_df = wildfire_df.loc[(wildfire_df['date'].dt.date >= choice_date_from) & \
        (wildfire_df['date'].dt.date <= choice_date_to)]

# display a map of fire incidents
st.map(wildfire_df[['latitude', 'longitude']])
expander = st.expander(shared_descr_dict["charts"]["label"])
expander.markdown(descr_dict["charts"]["map"])

# display bar chart (trend) by period
st.header("Wildfire Trend by Count and Total Size")
if choice_year == 'All':
    choice_display_period = st.radio("Display by Period:", options=['Daily', 'Monthly', 'Yearly'], horizontal=True)
else:
    choice_display_period = st.radio("Display by Period:", options=['Daily', 'Monthly'], horizontal=True)

if choice_display_period == 'Monthly':
    tmp_group = wildfire_df[['date', 'fire_size']].resample('M', on='date')
elif choice_display_period == 'Yearly':
    tmp_group = wildfire_df[['date', 'fire_size']].resample('Y', on='date')
else:
    tmp_group = wildfire_df[['date', 'fire_size']].groupby('date')

left_col, right_col = st.columns(2)
tmp_df = tmp_group.count()
tmp_df.rename(columns={'fire_size':'fire count'}, inplace=True)
left_col.line_chart(tmp_df)
tmp_df = tmp_group.sum()
tmp_df.rename(columns={'fire_size':'fire size'}, inplace=True)
right_col.line_chart(tmp_df)
expander = st.expander(shared_descr_dict["charts"]["label"])
expander.markdown(descr_dict["charts"]["trend"])


# display per fire size class, state
# table and bar chart
st.header("Wildfire Incidents by Fire Size and U.S. State")
st.write("Display by:")
choice_display_fire = st.checkbox("Fire Size Class", value=True)
choice_display_state = st.checkbox("U.S. State ", value=True)
tmp_df = wildfire_df[['fire_size_class', 'region', 'incident', 'fire_size']]
if choice_display_fire and choice_display_state:
    tmp_df2 = tmp_df.groupby(['region', 'fire_size_class']).sum().reset_index()
    st.dataframe(tmp_df2, use_container_width=True)
    tmp_df2 = tmp_df2.pivot(index='region', columns='fire_size_class', values='incident')
    st.bar_chart(tmp_df2)
elif choice_display_fire:
    tmp_df2 = tmp_df.groupby(['fire_size_class']).sum().reset_index()
    tmp_df2 = tmp_df2.sort_values(by='incident', ascending=False)
    st.dataframe(tmp_df2, use_container_width=True)
    st.bar_chart(tmp_df2[['fire_size_class', 'incident']], x='fire_size_class')
elif choice_display_state:
    tmp_df2 = tmp_df.groupby(['region']).sum()
    tmp_df2 = tmp_df2.sort_values(by='incident', ascending=False)
    st.dataframe(tmp_df2, use_container_width=True)
    st.bar_chart(tmp_df2[['incident']])

if choice_display_fire or choice_display_state:
    expander = st.expander(shared_descr_dict["charts"]["label"])
    expander.markdown(descr_dict[chart_key_alt]["region_and_size"])

# pie charts
st.markdown("Percentage distribution of fire occurrences based on fire size class and U.S. state:")
left_col, right_col = st.columns(2)
if choice_display_fire:
    tmp_df2 = tmp_df.groupby(['fire_size_class']).sum().reset_index()
    tmp_df2['incident'] = tmp_df2['incident'] / tmp_df2['incident'].sum() * 100
    tmp_df2['incident'] = tmp_df2['incident'].round(decimals=2)
    chart = alt.Chart(tmp_df2).mark_arc(innerRadius=50, outerRadius=110).encode(
        theta=alt.Theta(field="incident", type="quantitative", title="% of occurence"),
        color=alt.Color(field="fire_size_class", type="nominal")
    )
    left_col.altair_chart(chart, use_container_width=True)

if choice_display_state:
    tmp_df2 = tmp_df.groupby(['region']).sum().reset_index()
    tmp_df2['incident'] = tmp_df2['incident'] / tmp_df2['incident'].sum() * 100
    tmp_df2['incident'] = tmp_df2['incident'].round(decimals=2)
    chart = alt.Chart(tmp_df2).mark_arc(innerRadius=50, outerRadius=110).encode(
        theta=alt.Theta(field="incident", type="quantitative", title="% of occurence"),
        color=alt.Color(field="region", type="nominal")
    )
    right_col.altair_chart(chart, use_container_width=True)

if choice_display_fire or choice_display_state:
    expander = st.expander(shared_descr_dict["charts"]["label"])
    expander.markdown(descr_dict[chart_key_alt]["region_and_size_perc"])

# display per fire size and year
tmp_df = wildfire_df[['date', 'fire_size_class', 'region', 'incident', 'fire_size']]
if choice_display_fire:
    st.subheader("By Fire Size and Year")
    tmp_df2 = tmp_df.groupby([tmp_df.date.dt.year, 'fire_size_class']).sum().reset_index()
    print(tmp_df2)
    tmp_df2 = tmp_df2.pivot(index='date', columns='fire_size_class', values='incident')
    st.bar_chart(tmp_df2)
    if choice_year == 'All':
        st.line_chart(tmp_df2)

    expander = st.expander(shared_descr_dict["charts"]["label"])
    expander.markdown(descr_dict["charts"]["size_and_year"])

if choice_display_state:
    st.subheader("By U.S. State and Year")
    tmp_df2 = tmp_df.groupby([tmp_df.date.dt.year, 'region']).sum().reset_index()
    tmp_df2 = tmp_df2.pivot(index='date', columns='region', values='incident')
    st.bar_chart(tmp_df2)
    if choice_year == 'All':
        if choice_state == 'All':
            st.write("Displaying Top 5 U.S. States with Most Fires")
            top_states = tmp_df[['region', 'incident']].groupby('region').sum()
            top_states = top_states.sort_values(by='incident').index[-5::].values 
            st.line_chart(tmp_df2.loc[:, top_states])
        else:
            st.line_chart(tmp_df2)
    
    expander = st.expander(shared_descr_dict["charts"]["label"])
    expander.markdown(descr_dict[chart_key_alt]["state_and_year"])

    list_dates = tmp_df['date'].sort_values().unique()
    tmp_df2 = tmp_df[['date', 'incident', 'region']].groupby(['date', 'region']).count()
    tmp_df2 = tmp_df2.reindex(pd.MultiIndex.from_product([list_dates, list_states], names=['date', 'region']), fill_value=0)
    tmp_df2 = tmp_df2['incident'].reset_index()
    tmp_df2.loc[tmp_df2['incident'] > 0, 'incident'] = 1
    tmp_df2 = tmp_df2.groupby(['incident', 'region']).count().reset_index()
    tmp_df2 = tmp_df2.pivot(index='region', columns='incident', values='date').sort_index(axis=1)
    tmp_df2 = tmp_df2.rename(columns={0: "days with no fire", 1: "days with fire"})

    st.bar_chart(tmp_df2)

    expander = st.expander(shared_descr_dict["charts"]["label"])
    expander.markdown(descr_dict[chart_key_alt]["state_daily"])

# display per cause
st.header("Wildfire Incidents by Cause")
choice_cause = st.multiselect("Filter by Cause of Fire:", list_causes, default=list_causes)

if len(choice_cause) > 0:
    # summary
    tmp_df = wildfire_df[['date', 'fire_size_class', 'region', 'stat_cause', 'incident']]
    tmp_df = tmp_df.loc[tmp_df['stat_cause'].isin(choice_cause)]
    tmp_df2 = tmp_df.groupby(['stat_cause']).sum()
    st.bar_chart(tmp_df2[['incident']])

    _, mid_col, _ = st.columns((2,4,1))
    tmp_df2['incident'] = tmp_df2['incident'] / tmp_df2['incident'].sum() * 100
    tmp_df2['incident'] = tmp_df2['incident'].round(decimals=2)
    chart = alt.Chart(tmp_df2.reset_index()).mark_arc(innerRadius=50, outerRadius=110).encode(
        theta=alt.Theta(field="incident", type="quantitative", title="% of occurence"),
        color=alt.Color(field="stat_cause", type="nominal")
    )
    mid_col.altair_chart(chart)

    tmp_df2 = tmp_df.groupby(['region', 'stat_cause']).sum().reset_index()
    tmp_df2 = tmp_df2.pivot(index='stat_cause', columns='region', values='incident')

    expander = st.expander(shared_descr_dict["charts"]["label"])
    expander.markdown(descr_dict[chart_key_alt]["cause"])

    # and by yearly trend
    st.subheader("By Cause and Year")
    tmp_df2 = tmp_df.groupby([tmp_df.date.dt.year, 'stat_cause']).sum().reset_index()
    tmp_df2 = tmp_df2.pivot(index='date', columns='stat_cause', values='incident')
    st.bar_chart(tmp_df2)
    if choice_year == 'All':
        st.write("Displaying Trends in the Top 5 Causes of Fires")
        top_causes = tmp_df[['stat_cause', 'incident']].groupby('stat_cause').sum()
        top_causes = top_causes.sort_values(by='incident').index[-5::].values 
        st.line_chart(tmp_df2.loc[:, top_causes])

    expander = st.expander(shared_descr_dict["charts"]["label"])
    expander.markdown(descr_dict["charts"]["cause_and_year"])

    # and by fire size
    st.subheader("By Cause and Fire Size")
    tmp_df2 = tmp_df.groupby(['fire_size_class', 'stat_cause']).sum().reset_index()
    tmp_df2 = tmp_df2.pivot(index='stat_cause', columns='fire_size_class', values='incident')
    st.bar_chart(tmp_df2)

    top_fire_class = choice_fire_class_max
    st.markdown("Displaying % Causes in the Largest Fire Size Class: " + top_fire_class)
    _, mid_col, _ = st.columns((2,4,1))
    tmp_df2[top_fire_class] = tmp_df2[top_fire_class] / tmp_df2[top_fire_class].sum() * 100
    tmp_df2[top_fire_class] = tmp_df2[top_fire_class].round(decimals=2)
    chart = alt.Chart(tmp_df2[top_fire_class].reset_index()).mark_arc(innerRadius=50, outerRadius=110).encode(
        theta=alt.Theta(field=top_fire_class, type="quantitative", title="% of occurence"),
        color=alt.Color(field="stat_cause", type="nominal")
    )
    mid_col.altair_chart(chart)

    expander = st.expander(shared_descr_dict["charts"]["label"])
    expander.markdown(descr_dict[chart_key_alt]["cause_and_size"])

    # and by U.S. state
    st.subheader("By Cause and U.S. State")
    tmp_df2 = tmp_df.groupby(['region', 'stat_cause']).sum().reset_index()
    tmp_df2 = tmp_df2.pivot(index='region', columns='stat_cause', values='incident')
    st.bar_chart(tmp_df2)

    expander = st.expander(shared_descr_dict["charts"]["label"])
    expander.markdown(descr_dict[chart_key_alt]["cause_and_state"])

    st.markdown("Displaying % States of Wildfires Caused by: " + top_causes[-1])
    _, mid_col, _ = st.columns((2,4,1))
    tmp_df2[top_causes[0]] = tmp_df2[top_causes[0]] / tmp_df2[top_causes[0]].sum() * 100
    tmp_df2[top_causes[0]] = tmp_df2[top_causes[0]].round(decimals=2)
    chart = alt.Chart(tmp_df2[top_causes[0]].reset_index()).mark_arc(innerRadius=50, outerRadius=110).encode(
        theta=alt.Theta(field=top_causes[0], type="quantitative", title="% of occurence"),
        color=alt.Color(field="region", type="nominal")
    )
    mid_col.altair_chart(chart)

    expander = st.expander(shared_descr_dict["charts"]["label"])
    expander.markdown(descr_dict[chart_key_alt]["cause_and_state_perc"])
