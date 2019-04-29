import pickle
import json
from utilities.common_utils import make_sure_path_exists
import os
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataframes', required=True, type=str, help='The pickle file containing the mapping between '
                                                                      'term ids and the renormalised '
                                                                      'dataframes.')
    parser.add_argument('--terms', required=True, type=str, help='The JSON file containing the mapping from terms to '
                                                                 'term ids.')
    parser.add_argument('--output_dir', required=True, type=str, help='The output directory.')
    args = parser.parse_args()

    df_dict = pickle.load(open(args.dataframes, 'rb'))
    terms_dict = json.load(open(args.terms, 'r', encoding='utf8'))
    result_dict = {x: df_dict[terms_dict[x]].rename(columns={terms_dict[x]: x}) for x in terms_dict}

    make_sure_path_exists(args.output_dir)

    with open(os.path.join(args.output_dir, 'final_df_dict.pkl'), 'wb') as f:
        pickle.dump(result_dict, f)

if __name__ == '__main__':
    main()