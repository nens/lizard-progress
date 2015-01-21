"""Date utilities."""

import datetime


def weeknumber_to_date(year, week, day):
    # I don't know how to construct a date from week and day number
    # directly, so we use it as a timedelta from january a given date.

    # We use week numbers where monday is day 1, and week 1 is
    # the first week that has 4 days in it (= the ISO
    # standard, luckily).  So if jan 1 is on a friday,
    # saturday or sunday, _it is in the last week of the
    # previous year_. See 2012-01-01, which has isocalendar
    # (2011, 52, 7).

    # That is bad for this method if we used jan 1, because timedelta
    # doesn't work with years. We use one week later (jan 8), but any
    # date that is reliably in the same year should work.

    jan8 = datetime.date(year=year, month=1, day=8)
    _, jan8_week, jan8_day = jan8.isocalendar()

    date = jan8 + datetime.timedelta(
        weeks=(week - jan8_week), days=(day - jan8_day))

    return date
