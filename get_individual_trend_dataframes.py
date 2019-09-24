from utilities.google_trends_renormalisation_tools import create_pytrends_obj,\
        retrieve_all_terms_start, retrieve_all_terms_continue
from utilities.common_utils import make_sure_path_exists
import json
import pickle
import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['continue', 'start'], required=True,
                        default='start', help='The mode of operation. If you were running this script before and '
                                              'were interrupted by an error (e.g. rate-limiting), use continue, '
                                              'otherwise use start.')
    parser.add_argument('--time_start', type=str, help='Starting point of the time period you want.')
    parser.add_argument('--time_end', type=str, help='Ending point of the time period you want.')
    parser.add_argument('--terms', type=str, help='The JSON file containing the mapping from terms to term ids.')
    parser.add_argument('--state', type=str, help='Only for continue mode, the saved state file to load.')
    parser.add_argument('--proxy', type=str, help='Proxy server address if you need to use one. Needs to be HTTPS.')
    parser.add_argument('--sleep_time', type=int, default=1, help='Sleep time between subsequent queries, to '
                                                                  'avoid rate-limiting. If you\'re rate-limited, '
                                                                  'set this to 60 (unit is seconds).')
    parser.add_argument('--leap_size', type=int, default=1)
    parser.add_argument('--output_dir', type=str, required=True, help='Output directory for the resulting pickle file.')
    args = parser.parse_args()

    if args.mode == 'continue' and (args.terms is not None or args.state is None):
        parser.error('In "continue" mode, you should provide a pickle file containing the saved state.')
    if args.mode == 'start' and (args.terms is None or args.state is not None or
                                 args.time_start is None or args.time_end is None):
        parser.error('In "start" mode, you should provide a json file mapping terms to their term ids ("mid"s), '
                     'in addition to the start and end times.')

    if args.proxy is not None:
        proxy = {'https': args.proxy}
    else:
        proxy = None
    pytrends_obj = create_pytrends_obj(proxies=proxy, sleep_time=args.sleep_time)

    if args.mode == 'start':
        terms_dict = json.load(open(args.terms, 'r', encoding='utf8'))
        terms_list = list(terms_dict.values())
        with open(os.path.join(args.output_dir, 'dataframe_settings.json'), 'w', encoding='utf8') as f:
            json.dump({'time_start': args.time_start, 'time_end': args.time_end}, f)
        df_dict = retrieve_all_terms_start(pytrends_obj, terms_list, args.time_start, args.time_end,
                                           leap_size=args.leap_size)
    else:
        saved_state = pickle.load(open(args.state, 'rb'))
        df_dict = retrieve_all_terms_continue(pytrends_obj, saved_state[0], saved_state[1],
                                      saved_state[2], saved_state[3], saved_state[4], leap_size=saved_state[5])

    if df_dict is not None:
        make_sure_path_exists(args.output_dir)
        with open(os.path.join(args.output_dir, 'individual_df_dict.pkl'), 'wb') as f:
            pickle.dump(df_dict, f)
    else:
        print('If you have been rate-limited, increasing the sleep time to 60 seconds should do the trick!')


if __name__ == '__main__':
    main()