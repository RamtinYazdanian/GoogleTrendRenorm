from utilities.google_trends_renormalisation_tools import create_pytrends_obj, \
    find_all_interterm_conversion_rates_start, find_all_interterm_conversion_rates_continue, \
    compile_final_renormalisation_ratios, renormalise_all_tags
from utilities.common_utils import make_sure_path_exists
import json
import pickle
import os
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['continue', 'start'], required=True,
                        default='start', help='The mode of operation. If you were running this script before and '
                                              'were interrupted by an error (e.g. rate-limiting), use continue, '
                                              'otherwise use start.')
    parser.add_argument('--dataframes', required=True, type=str, help='Pickle file containing a term id to dataframe '
                                                                      'dictionary. The dataframes are all normalised '
                                                                      'to have a maximum of 100.')
    parser.add_argument('--time_settings', type=str, help='The JSON file containing the start and end times of the '
                                                          'time period you are using.')
    parser.add_argument('--state', type=str, help='Only for continue mode, the saved state file to load.')
    parser.add_argument('--proxy', type=str, help='Proxy server address if you need to use one. Needs to be HTTPS.')
    parser.add_argument('--sleep_time', type=int, default=1, help='Sleep time between subsequent queries, to '
                                                                  'avoid rate-limiting. If you\'re rate-limited, '
                                                                  'set this to 60 (unit is seconds).')
    parser.add_argument('--output_dir', type=str, required=True, help='Output directory for the resulting pickle file.')
    args = parser.parse_args()

    if args.mode == 'continue' and (args.state is None or
                                    args.time_settings is not None):
        parser.error('In "continue" mode, you should provide a pickle file containing the saved state.')
    if args.mode == 'start' and (args.state is not None or
                                 args.time_settings is None):
        parser.error('In "start" mode, you should provide a time settings json.')

    if args.proxy is not None:
        proxy = {'https': args.proxy}
    else:
        proxy = None
    pytrends_obj = create_pytrends_obj(proxies=proxy, sleep_time=args.sleep_time)
    term_dataframe_dict = pickle.load(open(args.dataframes, 'rb'))
    terms_list = list(term_dataframe_dict.keys())

    if args.mode == 'start':
        settings_dict = json.load(open(args.time_settings, 'r', encoding='utf8'))
        conversion_ratio_list = find_all_interterm_conversion_rates_start(pytrends_obj,
                                                            terms_list, settings_dict['time_start'],
                                                            settings_dict['time_end'])
    else:
        saved_state = pickle.load(open(args.state, 'rb'))
        conversion_ratio_list = find_all_interterm_conversion_rates_continue(pytrends_obj, saved_state[0],
                                saved_state[1], saved_state[2], saved_state[3], saved_state[4], saved_state[5],
                                saved_state[6], saved_state[7], saved_state[8], saved_state[9], saved_state[10])

    if conversion_ratio_list is not None:
        renormalisation_dict = compile_final_renormalisation_ratios(conversion_ratio_list, terms_list)
        renormalise_all_tags(term_dataframe_dict, renormalisation_dict)

        make_sure_path_exists(args.output_dir)
        with open(os.path.join(args.output_dir, 'renormalised_df_dict.pkl'), 'wb') as f:
            pickle.dump(term_dataframe_dict, f)
        with open(os.path.join(args.output_dir, 'conversion_ratios.pkl'), 'wb') as f:
            pickle.dump(conversion_ratio_list, f)
    else:
        print('If you have been rate-limited, increasing the sleep time to 60 seconds should do the trick!')

if __name__ == '__main__':
    main()