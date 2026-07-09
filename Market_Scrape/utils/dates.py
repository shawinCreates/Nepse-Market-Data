from datetime import date, timedelta, datetime

def daterange(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)

def date_to_filename(d: date) -> str:
    return d.strftime("%Y_%m_%d.csv")

def filename_to_date(filename: str):
    try:
        return datetime.strptime(
            filename.replace(".csv", ""),
            "%Y_%m_%d",
        ).date()
    except ValueError:
        return None
