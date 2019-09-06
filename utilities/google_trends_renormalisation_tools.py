from utilities.pytrends_sleeper import SleepingTrendReq
import numpy as np
import pandas as pd
import pickle
from time import sleep
from datetime import timedelta, date, datetime
import traceback
from bisect import bisect
from utilities.constants import PYTRENDS_GEO, PYTRENDS_MAX_RATIO, \
                            INDIVIDUAL_CONTINUE_FILENAME, INTERTERM_CONTINUE_FILENAME, DT_FORMAT
from random import randint, seed as random_seed

def perform_term_lookup(pytrends_obj, term_name):
    return pytrends_obj.suggestions(term_name)

def remove_duplicates_and_preserve_order(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x['mid'] in seen or seen_add(x['mid']))]

def prompt_term_choice(pytrends_obj, term_name, default_choice=False):
    suggestion_list = perform_term_lookup(pytrends_obj, term_name)
    if term_name[0]!='"' or term_name[-1]!='"':
        suggestion_list.extend(perform_term_lookup(pytrends_obj, term_name[:-1]))
        suggestion_list.extend(perform_term_lookup(pytrends_obj, term_name.split('.')[0]))
    suggestion_list = remove_duplicates_and_preserve_order(suggestion_list)

    if default_choice:
        return suggestion_list[0]['mid']
    prompt_list = [(x['title']+' ---- Type: '+x['type'], x['mid']) for x in suggestion_list]
    prompt_text = 'Term: '+ term_name +'\nChoose one of the following by entering its index (0 to skip this term' \
                                       ', -1 to terminate the process):\n'+ \
                    '\n'.join([str(i+1)+'.'+prompt_list[i][0] for i in range(len(prompt_list))])+'\n'
    choice = int(input(prompt_text)) - 1
    if choice == -1:
        return ''
    elif choice == -2:
        return None
    else:
        return prompt_list[choice][1]

def clean_trend_value(t):
    if t == '<1':
        t = 1
    return int(t)


def get_interest_over_time(pytrends_obj, terms, start, end, verbose=True):
    # Sleep if necessary, as determined by our SleepingTrendReq object's sleep_time and the time of its last request.
    if pytrends_obj.sleep_time > 0 and\
            (datetime.now() - pytrends_obj.last_req_time).total_seconds() < pytrends_obj.sleep_time:
        sleep(pytrends_obj.sleep_time - (datetime.now() - pytrends_obj.last_req_time).total_seconds())
    # Make the request
    pytrends_obj.build_payload(kw_list=terms,
                               timeframe=date.strftime(start, '%Y-%m-%d') + ' ' +
                                date.strftime(end, '%Y-%m-%d'), geo=PYTRENDS_GEO)
    df = pytrends_obj.interest_over_time()
    if verbose:
        print('Request made: '+str(terms)+'; time frame: '+date.strftime(start, '%Y-%m-%d') + ' ' +
                                date.strftime(end, '%Y-%m-%d') + '; geo: '+PYTRENDS_GEO)
    # Update the last request time
    pytrends_obj.update_last_req_time()
    df = df.drop(columns='isPartial')
    # Cleaning potential "<1" values.
    for term in terms:
        df[term] = df[term].apply(clean_trend_value)
    return df

def create_pytrends_obj(proxies=None, sleep_time=0):
    if proxies is not None:
        return SleepingTrendReq(hl='en-US', tz=360, proxies=proxies, sleep_time=sleep_time)
    else:
        return SleepingTrendReq(hl='en-US', tz=360, sleep_time=sleep_time)

def create_time_periods(time_start, time_end, leap_size = 4, overlap_size = 1):
    """
    Takes a time period and generates overlapping intervals, each of size leap_size years, where each two
    subsequent intervals overlap by overlap_size years.

    :param time_start: Beginning of time period.
    :param time_end: End of time period.
    :param leap_size: Size of each interval in years.
    :param overlap_size: Size of subsequent interval overlap in years.
    :return: The list of intervals, each being a tuple.
    """
    current_time = time_start
    times_list = []
    while current_time < time_end:
        period_end = current_time + timedelta(days=7*52*leap_size)
        if period_end >= time_end:
            times_list.append((current_time, time_end))
            break
        else:
            times_list.append((current_time, period_end))
            current_time = current_time + timedelta(days=7*52*(leap_size-overlap_size))

    return times_list

def normalise_by_background(dataframe_list, background_df, term_name):
    conversion_ratios = []
    background_df_index = background_df.index.tolist()
    for df in dataframe_list:
        max_index = df.loc[df[term_name] == 100].index[0]
        background_df_insertion_loc = bisect(background_df_index, max_index)
        if background_df_insertion_loc != 0:
            background_df_insertion_loc = background_df_insertion_loc - 1
        background_df_location = background_df_index[background_df_insertion_loc]
        current_conversion_ratio = 1.0 * background_df.loc[background_df_location, term_name] / 100.0
        conversion_ratios.append(current_conversion_ratio)
    conversion_ratios = np.array(conversion_ratios)
    max_conversion_ratio = conversion_ratios.max()
    conversion_ratios = conversion_ratios * (1.0/max_conversion_ratio)
    for i in range(len(dataframe_list)):
        df = dataframe_list[i]
        current_conversion_ratio = conversion_ratios[i]
        df[term_name] = df[term_name] * current_conversion_ratio
    final_df = pd.concat(dataframe_list, axis=0)
    final_df = final_df[~final_df.index.duplicated(keep='first')]
    return final_df



def retrieve_overlapping_term_time_series(pytrends_obj, term, time_start, time_end, leap_size=4, overlap_size=1):
    time_period_list = create_time_periods(time_start, time_end, leap_size=leap_size, overlap_size=overlap_size)
    retrieved_dataframes = list()
    for time_period in time_period_list:
        retrieved_dataframes.append(get_interest_over_time(pytrends_obj, [term], time_period[0], time_period[1]))

    return retrieved_dataframes

def retrieve_time_series_with_overall_series_normalisation(pytrends_obj, term, time_start, time_end):
    """
    Takes a term and a period, retrieves the whole period in 5-year windows (or shorter for the last window)
    such that the resolution is one data point per week, and then to renormalise all on the same scale, retrieves a
    (probably month-level resolution) dataframe for the entire period and renormalises each time window dataframe
    based on that, finally concatenating all of the window dataframes together.
    :param pytrends_obj: The PyTrends object
    :param term: The term
    :param time_start: The starting point of the period
    :param time_end: The end point of the period
    :return: A tuple consisting of the renormalised concatenated week-level dataframe and the background dataframe
    """
    time_period_list = create_time_periods(time_start, time_end, leap_size=5, overlap_size=0)
    retrieved_dataframes = list()

    for time_period in time_period_list:
        retrieved_dataframes.append(get_interest_over_time(pytrends_obj, [term], time_period[0], time_period[1]))

    if len(retrieved_dataframes) == 1:
        return retrieved_dataframes[0], retrieved_dataframes[0]
    else:
        background_df = get_interest_over_time(pytrends_obj, [term], time_start, time_end)
        return normalise_by_background(retrieved_dataframes, background_df, term), background_df

def calculate_intertag_conversion_ratio(pytrends_obj, term_1, term_2, time_start, time_end):
    joint_df = get_interest_over_time(pytrends_obj, [term_1, term_2], time_start, time_end)
    conversion_ratio = 1.0 * joint_df[term_2].max() / joint_df[term_1].max()
    return (term_1, term_2, conversion_ratio)

def find_all_interterm_conversion_rates_start(pytrends_obj, terms_list, time_start, time_end,
                                              max_ratio=PYTRENDS_MAX_RATIO, seed=1, starting_term=None):

    time_start = datetime.strptime(time_start, DT_FORMAT)
    time_end = datetime.strptime(time_end, DT_FORMAT)

    # Randomising the starting ref term or using the one provided by the user.
    # This part could be changed to decrease the risk of getting stuck.
    if starting_term is None:
        random_seed(seed)
        ref_term = terms_list[randint(0, len(terms_list)-1)]
    else:
        ref_term = starting_term

    # Removing the starting ref term from "rest".
    rest = set(terms_list)
    rest.remove(ref_term)
    rest = list(rest)

    ref_candidates = set()

    conversion_ratio_list = list()

    new_rest = set()
    current_minimum = (None, max_ratio + 1)
    current_maximum = (None, 1.0 / (max_ratio + 1))

    return find_all_interterm_conversion_rates_continue(pytrends_obj, rest,
                            ref_term, 0, time_start, time_end, ref_candidates,
                            conversion_ratio_list, new_rest, max_ratio, current_minimum, current_maximum)


def find_all_interterm_conversion_rates_continue(pytrends_obj, rest, ref_term, starting_index,
                                                 time_start, time_end, ref_candidates, conversion_ratio_list,
                                                 new_rest, max_ratio, current_minimum, current_maximum):
    while len(rest) > 0:
        for index in range(starting_index, len(rest)):
            current_term = rest[index]
            try:
                current_conversion_ratio = calculate_intertag_conversion_ratio(pytrends_obj,
                                                                               ref_term, current_term, time_start,
                                                                               time_end)
                if current_conversion_ratio[2] <= max_ratio and current_conversion_ratio[2] >= 1.0 / max_ratio:
                    conversion_ratio_list.append(current_conversion_ratio)
                    if current_conversion_ratio[2] < current_minimum[1]:
                        current_minimum = (current_term, current_conversion_ratio[2])
                    elif current_conversion_ratio[2] > current_maximum[1]:
                        current_maximum = (current_term, current_conversion_ratio[2])
                else:
                    new_rest.add(current_term)
            except Exception as e:
                print('An error occured! Details follow:')
                print(traceback.print_exc())
                print(e)
                with open(INTERTERM_CONTINUE_FILENAME, 'wb') as f:
                    pickle.dump((rest, ref_term, index, time_start, time_end,
                                 ref_candidates, conversion_ratio_list, new_rest,
                                 max_ratio, current_minimum, current_maximum), f)
                return None

        if len(new_rest) == 0:
            break
        starting_index = 0
        rest = list(new_rest)
        new_candidates = {current_maximum[0], current_minimum[0]}
        new_candidates = {x for x in new_candidates if x is not None}
        ref_candidates = ref_candidates.union(new_candidates)
        print(ref_candidates)
        print('-----')
        print(conversion_ratio_list)

        new_rest = set()
        current_minimum = (None, max_ratio + 1)
        current_maximum = (None, 1.0 / (max_ratio + 1))

        if len(ref_candidates) == 0:
            print('Failed to empty "rest"!')
            return list()

        ref_term = ref_candidates.pop()
    print('"rest" emptied, conversion ratios compiled')
    return conversion_ratio_list


def compile_final_renormalisation_ratios(conversion_ratio_list, terms_list):
    """
    Takes the conversion ratio list which is the output of find_all_intertag_conversion_rates, and a list of terms,
    and for each term in calculates the final conversion ratio which is the multiplication of all the steps.
    :param conversion_ratio_list: a list of tuples of the form (ref, term, conversion ratio term/ref)
    :param terms_list: A list of all the terms.
    :return: A dictionary mapping each term to its final renormalisation multiplier.
    """
    conversion_ratio_dict = {x[1]: (x[2], x[0]) for x in conversion_ratio_list}
    renormalisation_dict = dict()
    for term in terms_list:
        multiplier = 1
        current_ratio_tuple = conversion_ratio_dict.get(term, None)
        while current_ratio_tuple is not None:
            multiplier *= current_ratio_tuple[0]
            current_ratio_tuple = conversion_ratio_dict.get(current_ratio_tuple[1], None)
        renormalisation_dict[term] = multiplier
    return renormalisation_dict

def renormalise_all_tags(dataframe_dict, renormalisation_dict):
    """
    Takes a dictionary mapping terms (the term ids as given by the API) to dataframes and another mapping terms to
    their renormalisation multipliers, and renormalises all the dataframes.
    :param dataframe_dict: The term to dataframe dict.
    :param renormalisation_dict: The term to renormalisation multiplier dict.
    :return: Nothing, the renormalisation is in-place.
    """
    for term in dataframe_dict:
        renormalisation_multiplier = renormalisation_dict[term]
        current_df = dataframe_dict[term]
        current_df[term] = current_df[term] * renormalisation_multiplier

def retrieve_all_terms_start(pytrends_obj, target_terms_list, time_start, time_end):
    dataframe_dict=dict()
    time_start = datetime.strptime(time_start, DT_FORMAT)
    time_end = datetime.strptime(time_end, DT_FORMAT)
    return retrieve_all_terms_continue(pytrends_obj, target_terms_list, time_start, time_end,
                                       dataframe_dict, starting_index=0)

def retrieve_all_terms_continue(pytrends_obj, target_terms_list, time_start, time_end,
                                dataframe_dict, starting_index=0):

    for index in range(starting_index, len(target_terms_list)):
        term = target_terms_list[index]
        try:
            normalised_df, background_df = retrieve_time_series_with_overall_series_normalisation(pytrends_obj,
                                                                              term, time_start, time_end)
            dataframe_dict[term] = normalised_df
        except Exception as e:
            print('An error occured! Details follow:')
            print(traceback.print_exc())
            print(e)
            with open(INDIVIDUAL_CONTINUE_FILENAME, 'wb') as f:
                pickle.dump((target_terms_list, time_start, time_end, dataframe_dict, index), f)
            return None
    return dataframe_dict
