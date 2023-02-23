import streamlit as st

import sqlite3
import numpy as np
import pandas as pd
import altair as alt

import utils  # saved shared functions in utils


# load data and vars
wildfire_df = utils.load_wildfire_data_gcp()
list_fire_size_classes, list_states, list_years, list_causes = utils.precompute_values_lists(wildfire_df)
max_fire_size, min_date, max_date = utils.precompute_values_ranges(wildfire_df)
fire_size_class_range = utils.get_fire_size_class_range(max_fire_size)

# tile and short background
st.title("U.S. Wildfire Data")
st.sidebar.header("U.S. Wildfire Data")
st.sidebar.subheader("Background:")
st.sidebar.markdown("The wildfire data used in this project is from the **\"1.88 Million U.S. Wildfires\"** \
    [Kaggle](https://www.kaggle.com/datasets/rtatman/188-million-us-wildfires) dataset, which contains \
    24 years of spatial information on wildfires that occurred in the United States from 1992 to 2015.")
st.sidebar.markdown("This page shows wildfire trends over the available period, as well as the wildfire \
    characteristics based on location, size, and cause.")
st.sidebar.markdown("The aim of this project is to predict risks of wildfires based on various \
    factors (e.g. weather data), which can help in the monitoring, triaging and prevention of large wildfires.")
st.sidebar.caption("This project is ongoing and more features will be added in the future.")

# define forms
st.markdown("Use the following widgets to filter the data used in below charts:")
left_col, right_col = st.columns((4, 1))
choice_fire_class_min, choice_fire_class_max = left_col.select_slider("Filter by Fire Size Class:", list_fire_size_classes, \
    value=('C', list_fire_size_classes[-1]))
choice_fire_size_min, choice_fire_size_max = left_col.slider("Filter by Fire Size (in acres):", \
    min_value=fire_size_class_range[choice_fire_class_min][0], max_value=fire_size_class_range[choice_fire_class_max][1], \
    value=(fire_size_class_range[choice_fire_class_min][0], fire_size_class_range[choice_fire_class_max][1]))
expander = right_col.expander("See Fire Size Class Legend")
expander.markdown("In acres:  \n**A**: 0.+ - 0.25  \n**B**: 0.26 - 9.9   \n**C**: 10.0 - 99.9  \n" \
    "**D**: 100 - 299  \n**E**: 300 - 999  \n**F**: 1000 - 4999  \n**G**: 5000+")

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
expander = st.expander("Comments / Observations")
expander.markdown("From the map, it can be observed that more and larger wildfires occur in the western half \
    of the U.S. (including Alaska). This is especially true for wildfires larger than 100k acres.  \n \
    \nThis can be expected as the western states are in the more mountainous areas (i.e. Rocky mountains).")

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
expander = st.expander("Comments / Observations")
expander.markdown("There is no clear wildfire trend from 1992 to 2015. The wildfire incidents do not increase \
    year by year, and even dropped during 2007 to 2010, and 2012 to 2014. This is the case in both small and large wildfires.")


# display per fire size class, state
# table and bar chart
st.header("Wildfire Incidents by Fire Size and U.S. State")
st.write("Display by:")
choice_display_fire = st.checkbox("Fire Size Class", value=True)
choice_display_state = st.checkbox("U.S. State ", value=True)
tmp_df = wildfire_df[['date', 'fire_size_class', 'region', 'incident', 'fire_size']]
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
    expander = st.expander("Comments / Observations")
    if(list_fire_size_classes[0] == 'A'):
        expander.markdown("The states with the most wildfire incidents are: California (CA), Georgia (GA), Texas (TX), \
            North Carolina (NC) and Florida (FL). However, large wildfires (with over 1000 acres or over class F) \
            mostly occur in the states of Arkansas (AK), Idaho (ID), California (CA), Texas (TX), Nevada (NV), Oregon (OR) \
            and New Hampshire (NM).  \n\n It is curious that these two groups are comprised of mostly different states. \
            It is good to find out why even though the second group of states have less wildfires than the first group, \
            these wildfires develop into bigger ones.")
    else:
        expander.markdown("The states with the most wildfire incidents are: Texas (TX), Mississippi (MS), Alabama (AL), \
            Florida (FL) and Oklahoma (OK). However, very large wildfires (with over 1000 acres or over class F) \
            mostly occur in the states of California (CA), Idaho (ID), Arkansas (AK), Texas (TX) and New Hampshire (NM).  \n \
            \n It is curious that these two groups are comprised of mostly different states. \
            It is good to find out why even though the second group of states have less wildfires than the first group, \
            these wildfires develop into bigger ones.")

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
    expander = st.expander("Comments / Observations")
    if(list_fire_size_classes[0] == 'A'):
        expander.markdown("Only <3% of the total reported fire incidents are larger than 100 acres (class D & up), and <1% are \
            larger than 1000 acres (class F & up).\n \
            \n 10% of all fire incidents reported have occurred in California (CA), while almost 40% of fires \
            larger than 1000 acres  (class F & up) have occurred in in just 4 states: California (CA), Idaho (ID), \
            Arkansas (AK) and Texas(TX) (each of these 4 states have ~10%).")
    else:
        expander.markdown("More than 80% of wildfires from this dataset is between 10 to 100 acres (class C) and just <5% are \
            larger than 1000 acres (class F & up).\n \
            \n 11.69% of all fire incidents reported have occurred in Texas (CA), while almost 40% of fires \
            larger than 1000 acres  (class F & up) have occurred in just 4 states: California (CA), Idaho (ID), \
            Arkansas (AK) and Texas(TX) (each of these 4 states have ~10%).")

# display per fire size and year
if choice_display_fire:
    st.subheader("By Fire Size and Year")
    tmp_df2 = tmp_df.groupby([tmp_df.date.dt.year, 'fire_size_class']).sum().reset_index()
    tmp_df2 = tmp_df2.pivot(index='date', columns='fire_size_class', values='incident')
    st.bar_chart(tmp_df2)
    if choice_year == 'All':
        st.line_chart(tmp_df2)

    expander = st.expander("Comments / Observations")
    expander.markdown("The wildfire incidents over different fire size classes have moved correlatively/proportionally \
        over the years.")
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
    
    expander = st.expander("Comments / Observations")
    if(list_fire_size_classes[0] == 'A'):
        expander.markdown("The number of fire incidents in Texas (TX) have significantly jumped from 2005. \
            This can mean that either more fires are happening from 2005, or that reporting has improved from this year.\
            From 2005, Texas (TX) became the state with most wildfires, and the 2nd top state with largest wildfires.")
    else:
        expander.markdown("The number of fire incidents in Texas (TX) have significantly jumped from 2005. \
            This can mean that either more fires are happening from 2005, or that reporting has improved from this year.")

    list_dates = tmp_df['date'].sort_values().unique()
    tmp_df2 = tmp_df[['date', 'incident', 'region']].groupby(['date', 'region']).count()
    tmp_df2 = tmp_df2.reindex(pd.MultiIndex.from_product([list_dates, list_states], names=['date', 'region']), fill_value=0)
    tmp_df2 = tmp_df2['incident'].reset_index()
    tmp_df2.loc[tmp_df2['incident'] > 0, 'incident'] = 1
    tmp_df2 = tmp_df2.groupby(['incident', 'region']).count().reset_index()
    tmp_df2 = tmp_df2.pivot(index='region', columns='incident', values='date').sort_index(axis=1)
    tmp_df2 = tmp_df2.rename(columns={0: "days with no fire", 1: "days with fire"})

    st.bar_chart(tmp_df2)

    expander = st.expander("Comments / Observations")
    if(list_fire_size_classes[0] == 'A'):
        expander.markdown("During the available time period, there are almost daily wildfire incidents in California (CA), \
            Florida (FL) and Georgia (GA). On the other hand, in the District of Columbia (DC) and Delaware (DE), there are very \
            few days where a wildfire was reported. \n \
            \n In California (CA), there are wildfires over 1000 acres (class F & up) in 19% of the days. \n \
            \n After 2005, there are also almost daily wildfires reported in Texas (TX).")
    else:
        expander.markdown("In California (CA), there are wildfires over 1000 acres (class F & up) in 19% of the days. \n \
            \n After 2005, there are wildfires reported in Texas (TX) 82% of the days.")

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

    expander = st.expander("Comments / Observations")
    if(list_fire_size_classes[0] == 'A'):
        expander.markdown("The most common cause of wildfires during the available time period is debris burning (22.81%), \
            followed by miscellaneous (17.22%), arson (14.97%) and lightning (14.81%). \n \
            \n For wildfires over 10 acres (class C & up), the most recorded cause is arson. For wildfires \
            over 100 acres (class D & up), it is lightning. \
            In addition, more than 50% of wildfires over 1000 acres (class F & up) started with lightning.")
    else:
        expander.markdown("The most common cause of wildfires during the available time period is arson (23.84%), \
            followed by debris burning (22.21%), lightning (14.69%) and miscellaneous (13.6%). \n \
            \n For wildfires over 100 acres (class D & up), the most recorded cause is lightning. \
            In addition, more than 50% of wildfires over 1000 acres (class F & up) started with lightning.")

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

    expander = st.expander("Comments / Observations")
    expander.markdown("Arson incidents seem to have decreased in the later years of the period (after 2007). \
        The trend of the rest of the major causes looks to have continued.")

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

    expander = st.expander("Comments / Observations")
    if(list_fire_size_classes[0] == 'A'):
        expander.markdown("Majority of wildfires caused by arson and debris burning reached a size of 0.25 to 10 acres (class B). \
            As mentioned above, lightning caused most of the larger wildfires (greater than 100 acres). \
            It also is the major cause of wildfires on the largest fire size class: G, \
            i.e. it caused 64.11% of wildfires over 5000 acres.")
    else:
        expander.markdown("As mentioned above, lightning caused most of the larger wildfires (greater than 100 acres). \
            It also is the major cause of wildfires on the largest fire size class: G, \
            i.e. it caused 64.11% of wildfires over 5000 acres.")

    # and by U.S. state
    st.subheader("By Cause and U.S. State")
    tmp_df2 = tmp_df.groupby(['region', 'stat_cause']).sum().reset_index()
    tmp_df2 = tmp_df2.pivot(index='region', columns='stat_cause', values='incident')
    st.bar_chart(tmp_df2)

    expander = st.expander("Comments / Observations")
    if(list_fire_size_classes[0] == 'A'):
        expander.markdown("The top causes of wildfires in California (CA) are miscellaneous and equipment use. \
            It is debris burning in Georgia (GA), North Carolina (NC) and Texas (TX). \n \
            \n The most common cause of wildfires over 100 acres (class D & up) is lightning in most of the \
            U.S. states that gets many wildfire incidents.")
    else:
        expander.markdown("The top causes of wildfires in Texas (TX) are debris burning and miscellaneous. \
            It is arson in Mississippi (MS) and Alabama (AL). \n \
            \n The most common cause of wildfires over 100 acres (class D & up) is lightning in most of the \
            U.S. states that gets many wildfire incidents.")

    st.markdown("Displaying % States of Wildfires Caused by: " + top_causes[-1])
    _, mid_col, _ = st.columns((2,4,1))
    tmp_df2[top_causes[0]] = tmp_df2[top_causes[0]] / tmp_df2[top_causes[0]].sum() * 100
    tmp_df2[top_causes[0]] = tmp_df2[top_causes[0]].round(decimals=2)
    chart = alt.Chart(tmp_df2[top_causes[0]].reset_index()).mark_arc(innerRadius=50, outerRadius=110).encode(
        theta=alt.Theta(field=top_causes[0], type="quantitative", title="% of occurence"),
        color=alt.Color(field="region", type="nominal")
    )
    mid_col.altair_chart(chart)

    expander = st.expander("Comments / Observations")
    if(list_fire_size_classes[0] == 'A'):
        expander.markdown("Majority of fires caused by debris burning happened in South Carolina (SC) (13.42%) and \
            Puerto (PR) (13.09%). Most wildfires caused by lightning and got to a size of over 100 acres (class D & up) \
            happened in Oklahoma (OK), i.e. 22.24% from all wildfires of this category.")
    else:
        expander.markdown("Majority of fires caused by arson happened in Oklahoma (OK) (19.5%). \
            Most wildfires caused by lightning and got to a size of over 100 acres (class D & up) \
            also happened in Oklahoma (OK), i.e. 22.24% from all wildfires of this category.")
