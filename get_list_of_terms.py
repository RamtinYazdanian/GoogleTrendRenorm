from utilities.google_trends_renormalisation_tools import create_pytrends_obj, prompt_term_choice
from utilities.common_utils import make_sure_path_exists
import json
import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--term_list', required=True, type=str, help='A txt file containing one term per line.')
    parser.add_argument('--output_dir', required=True, type=str, help='Output directory for the resulting dictionary.')
    parser.add_argument('--use_original_terms', action='store_true', help='Whether to just use the original terms '
                                                                          'and to avoid going through the suggestions. '
                                                                          'Not recommended.')
    parser.add_argument('--choose_first', action='store_true', help='If you don\'t feel like going through the entire '
                                                                    'list of suggestions for each term, use this '
                                                                    'option to always select the first one. '
                                                                    'Not recommended.')
    parser.add_argument('--proxy', type=str, help='Proxy server address if you need to use one. Needs to be HTTPS.')
    parser.add_argument('--sleep_time', type=int, default=0, help='Sleep time between subsequent queries, to '
                                                                  'avoid rate-limiting. If you\'re rate-limited, '
                                                                  'set this to 60 (unit is seconds).')
    args = parser.parse_args()

    if args.use_original_terms and args.choose_first:
        parser.error('--use_original_terms and --choose_first are mutually exclusive')

    terms = open(args.term_list, 'r').readlines()
    terms = [x.strip() for x in terms if len(x.strip()) > 0]
    if args.use_original_terms:
        terms_dict = {x: x for x in terms}
    else:
        if args.proxy is not None:
            proxy = {'https': args.proxy}
        else:
            proxy = None
        pytrends_obj = create_pytrends_obj(proxies=proxy, sleep_time=args.sleep_time)
        terms_dict = dict()
        for term in terms:
            chosen_term = prompt_term_choice(pytrends_obj, term, default_choice=args.choose_first)
            if chosen_term != '':
                terms_dict[term] = chosen_term

    make_sure_path_exists(args.output_dir)
    with open(os.path.join(args.output_dir, 'term_to_mid.json'), mode='w', encoding='utf8') as f:
        json.dump(terms_dict, f)

if __name__ == '__main__':
    main()