import pandas as pd
import re
import warnings


def tidy_time_string(time):
    """
    Tidies a string `time` into a `date` in `datetime64[D]` format, and records the status of the conversion
        (`date_status`).
    The tidying aims to convert:
        * Easy to convert dates ("19 June 2014")
        * Various markers of uncertainty (e.g. "circa 2018", "c. 2018 " "c 2018", "[June] 2018"
        * Ranges of dates (e.g. "1920s", "2-6 June 1920", "2 June - 6 July 1920", "1920s - 1931"), by returning a 
            central date.
    It also aims to flag some entries to be looked at more closely by hand.
        * Some potential typos (e.g. "120s-1930s", or "2975")
            
    :param time: Input time string (e.g. "2-6 [June] 1934", "2018", "1930s")

    :return date: The date in `datetime64[D]` format. Not a time (`pd.NaT`) if could not convert. 
    :return date_status: String describing status of converted date. Possible values ("circa", "centred", "exact", or 
        "not_converted").
    """

    # TODO - :return date_range: Where date_status is "centred", date_range is a tuple (`first_date`, `last_date`) of
    #  `datetime64[D]` objects. Otherwise will return a tuple of Not a Time objects.
    # TODO - warnings/logging
    # TODO - change date offsets to rounding using MonthEnd/MonthBegin
    #   https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html
    # TODO - allow mulitple `date_status`es (circa and centred).

    date_status = 'not_converted'
    date = pd.NaT
    original_time_string = str(time)

    # IS THE STRING ALREADY PARSABLE AS AN EXACT TIME:
    if '-' not in time:  # to avoid accidentally parsing ranges as exact times. e.g. "25-27 june".

        try:
            date = pd.to_datetime(time)
            date_status = 'exact'
            return date, date_status
        except:
            pass

    # IS THE STRING "CIRCA" SOMETHING:
    if (('c' in time) or (('[' in time) or (']' in time))):
        if 'c' in time:  # contains 'c' (not in a month, e.g. Dec), so " c. ", "c ", t
            time = re.sub(r'(?<!\w)(c[.]?\s?)', '', time)

        if ('[' in time) and (']' in time):  # contains square brackets

            # We don't attempt to fix multiple pairs of brackets with one missing bracket
            num_sq_brackets = time.count(']') + time.count(']')
            if num_sq_brackets >= 3 and (num_sq_brackets % 2) != 0:
                warnings.warn("Cannot fix multiple pairs of brackets with one missing bracket.", warnings.INFO)
                return date, date_status

            reg2 = re.findall(r'\[(.*?)\]', time)
            if reg2 is not None:
                # remove square brackets
                for in_brackets in reg2:
                    time = time.replace(f"[{in_brackets}]", in_brackets)
        elif '[' in time:
            time = time.replace('[', '')
        elif ']' in time:
            time = time.replace(']', '')

        time = time.strip()

        try:
            date = pd.to_datetime(time)
            date_status = 'circa'
            return date, date_status
        except:
            pass

    # IS THE STRING A RANGE OF DATES? WHICH WE CAN AVERAGE OR CENTRE:
    # We are assuming an '[1,2]\d{2}0)s' pattern (e.g. 1970s, 1980s, 1730s, 1900s) implies a decade.
    if ('s' in time) or ('-') in time:
        if ('s' in time) and ('-' not in time):
            reg3 = re.findall(r'([1,2]\d{2}0)s', time)
            for reg in reg3:
                time = time.replace(f"{reg}s", str(int(reg) + 5))  # centre is 5 years later
            date = pd.to_datetime(time, format='%Y')
            date_status = 'centred'

        elif ('-' in time):
            if time.count('-') > 1:
                print('many hyphens', original_time_string)
                # Not attempting to deal with multiple hyphens at the moment.
                pass
            else:
                time = re.sub(r'\s?-\s?', '-', time)
                reg4 = re.match(r'(.*?)-(.*)$', time)

                first = time.replace(reg4.group(0), reg4.group(1))
                last = time.replace(reg4.group(0), reg4.group(2))

                if 's' in first:
                    reg5 = re.findall(r'([1,2]\d{2}0)s', time)
                    for reg in reg5:
                        first = first.replace(f"{reg}s", reg)

                if not re.search(r'[1,2]\d{3}', first):  # no year:
                    if not re.search(r'\d+', first):  # no days in `first` => varying month:
                        # Take the year from last and add it on
                        reg5 = re.findall(r'[1,2]\d{3}', last)
                        first = f"{first} {reg5[0]}"
                    else:  # days in `first` => varying days:
                        # Take the month and year from last and add it on.
                        reg6 = re.findall(r'\w+ [1,2]\d{3}', last)
                        if len(reg6) > 0:
                            first = f"{first} {reg6[0]}"

                if 's' in last:
                    reg7 = re.findall(r'([1,2]\d{2}0)s', time)
                    for reg in reg7:
                        last = last.replace(f"{reg}s", str(int(reg) + 10))  # end is 10 years later.

                if re.match(r'\w+\s\d+', last):  # assuming month and year
                    time_delta = pd.tseries.offsets.DateOffset(months=1)
                elif re.match(r'[a-zA-Z]', last):  # assuming it's a month
                    time_delta = pd.tseries.offsets.DateOffset(months=1)
                elif re.match(r'[1,2]\d{3}', last):  # assuming it's a year
                    time_delta = pd.tseries.offsets.DateOffset(months=12)
                elif re.match(r'\d+', last).span()[1] - re.match('\d+', last).span()[0] <= 2:  # assuming it's a day:
                    time_delta = pd.tseries.offsets.DateOffset(months=0)
                else:
                    warnings.warn(f"Can't guess format of {last} from {original_time_string}", warnings.INFO)
                    return date, date_status

                try:
                    last = pd.to_datetime(last)
                except:
                    warnings.warn(f"Could not parse `last` ({last}) into `datetime` format.", warnings.INFO)
                    return date, date_status

                last = last + time_delta

                try:
                    first = pd.to_datetime(first)
                except:
                    print(f"Could not parse `first` ({first}) into `datetime` format.")
                    return date, date_status

                centre_date = first + (last - first) / 2
                date_status = 'centred'
                return centre_date, date_status

    return date, date_status


def tidy_time_df(df, time_col, new_tidy_col='date_tidy', new_status_col='date_status'):
    """
    Creates additional columns in an archive catalogue's data frame, containing the tidied date and the date status.

    :param df: Data frame containing an archive catalogue.
    :param time_col: The column name where the date is stored in text format (used to create tidied date).
    :param new_tidy_col: The column name (default `date_tidy`) where the new tidied date will be stored, in
     `datetime64[D]` format.
    :param new_status_col: The column name (default `date_status`) where the status of the tidied date (either "circa",
    "centred", "exact", or "not_converted"), will be stored.

    :return: df
    """
    date_tidy_series = pd.Series(index=df.index, dtype='datetime64[D]')
    date_status_series = pd.Series(index=df.index, dtype='object')

    for ref_no, o_time in df[time_col].iteritems():
        time = str(o_time)
        # TODO: Add nd, n.d., n.d, no date to date_cleaner and remove from create_new_catalogue.
        date, date_status = tidy_time_string(time)
        if date_status == 'not_converted' and 'nd' not in o_time:
            print(f"COULD NOT CONVERT {ref_no} with {o_time}, recording `date` {date} `date_status` {date_status}.")

        date_tidy_series.loc[ref_no] = date
        date_status_series.loc[ref_no] = date_status

    df[new_tidy_col] = date_tidy_series
    df[new_status_col] = date_status_series

    return df


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
        '1-3 March 1920': (pd.to_datetime('02-03-1920', dayfirst=True))

    }

    for string_key in test_strings.keys():
        (a_date, a_date_status) = test_strings[string_key]
        date_info = tidy_time_string(string_key)
        print(date_info)
        assert (date_info == (a_date, a_date_status))

    return
