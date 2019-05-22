# GoogleTrendRenorm
This is a Python tool that uses a fake API (PyTrends) in order to retrieve an unlimited number of terms for any period longer than 5 years with week-level detail from Google Trends, renormalising them on the same scale. The original trend values themselves are, according to Google, equal to the search volume index (number of queries for a term/topic and its related queries divided by the total number of queries in that time period, e.g. that week) that's normalised to have the maximum of the retrieved period equal to 100.

## Why do we need this package?

Google Trends returns values that are normalised for the chosen term (or set of terms) and the chosen time period such that the maximum is 100, and the values are all integers. In addition, you cannot request more than 5 terms at once. This means that there will be a lot of rounding errors and you will be limited in the number of terms you can get, normalised on the same scale.

# Requirements
Python 3, PyTrends, Pandas.

# How to use
Run the scripts in this order:
1. get_list_of_terms.py: This allows you to choose, through the API, the specific terms or topics that you want to retrieve the trends for. You need to provide a text file with one term per line.
2. get_individual_trend_dataframes.py: The individual dataframes, normalised such that their maximum is 100, are retrieved.
3. renormalise_trend_dataframes.py: The dataframes are renormalised on the same scale by constructing a partial order of conversion ratios between the maxima of dataframes: one dataframe will become the one that every other is normalised against. The output is a pickle file containing a dictionary that maps each term's id in Google Trends to a dataframe that has dates as its index, and the renormalised trend value for that term in the only other column.
4. fix_dataframe_names.py: The column names in the dataframes are changed to the original terms. Optional step.

## Parameters
The most important parameter in utilities/constants.py is PYTRENDS_MAX_RATIO. This value and its inverse are respectively the upper and lower bounds for the renormalise_trend_dataframes script, when it attempts to build a partial ordering where the conversion ratios are not outside these upper and lower bounds. This is in order to reduce rounding errors caused by the fact that Google Trends values are always integers.

# What will be added
* Support finer-grained data -- right now everything is written with week-level data in mind.
* Support renormalisation based on a specific term at a specific time (aiming for a globally unique renormalisation). Currently, renormalisation based on a specific term is possible, but the time will be determined by the maximum value of that term.
