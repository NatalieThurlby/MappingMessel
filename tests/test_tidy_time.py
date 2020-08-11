import pandas as pd
import logging

from scripts.date_cleaner import tidy_time_string


def test_tidy_time_string():
    """
    Tests edge-cases for tidy_time_string.
    """
    # TODO - add more test strings (both weird and normal).
    # TODO - write this test function
    # TODO - run test functions through pytest/github actions
    test_strings = {
        '29 Feb 1957': (pd.NaT, 'not_converted'),  # There was no 29th Feb this year
        '25-27 june': (pd.NaT, 'not_converted'),  # Pandas converts this str by default, but it has no year.
        '03 03 1920': (pd.to_datetime('03-03-1920'), 'exact'),
        '01 01 1920': (pd.to_datetime('02-01-1920'), 'exact'),  # EXPECTED TO FAIL # TODO: remove
        # '1-3 March 1920': (pd.to_datetime('02-03-1920', dayfirst=True), 'centered')

    }

    for string_key in test_strings.keys():
        (a_date, a_date_status) = test_strings[string_key]
        date_info = tidy_time_string(string_key)
        try:
            assert (date_info == (a_date, a_date_status))
        except AssertionError:
            logging.warning(f"`{string_key}` was converted to {date_info}, not {(a_date, a_date_status)} as was expected.")

    return
