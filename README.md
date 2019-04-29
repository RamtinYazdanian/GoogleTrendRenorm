# GoogleTrendRenorm
This is a Python tool that uses a fake API (PyTrends) in order to retrieve an unlimited number of terms for any period longer than 5 years with week-level detail from Google Trends, renormalising them on the same scale.

# Requirements
Python 3, PyTrends, Pandas.

# How to use
Run the scripts in this order:
1. get_list_of_terms.py: This allows you to choose, through the API, the specific terms or topics that you want to retrieve the trends for. You need to provide a text file with one term per line.
2. get_individual_trend_dataframes.py: The individual dataframes, normalised such that their maximum is 100, are retrieved.
3. renormalise_trend_dataframes.py: The dataframes are renormalised on the same scale by constructing a DAG of conversion ratios between the maxima of dataframes: one dataframe will become the one that every other is normalised against.
4. fix_dataframe_names.py: The column names in the dataframes are changed to the original terms. Optional step.

# What will be added
* Support finer-grained data -- right now everything is written with week-level data in mind.
* Support renormalisation based on a specific term at a specific time (aiming for a globally unique renormalisation).
