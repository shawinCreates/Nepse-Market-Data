import scrapy

def extract_token(response):
    return response.xpath(
        '//input[@name="_token"]/@value'
    ).get()

def has_market_data(response):
    no_record = response.xpath(
        '//td[contains(normalize-space(.),'
        '"No Record Found")]'
    ).get()

    return no_record is None

def parse_table(response):
    rows = response.xpath('//table//tr')

    table_data = []

    for row in rows:
        cells = row.xpath(
            './/th//text() | .//td//text()'
        ).getall()

        cells = [
            cell.strip()
            for cell in cells
            if cell.strip()
        ]

        if cells:
            table_data.append(cells)

    return table_data

def build_ajax_request(
    token,
    date_str,
    callback,
    **kwargs,
):
    return scrapy.FormRequest(
        url='https://www.sharesansar.com/ajaxtodayshareprice',
        formdata={
            '_token': token,
            'sector': 'all_sec',
            'date': date_str,
        },
        headers={
            'X-Requested-With': 'XMLHttpRequest',
            'Referer':
                'https://www.sharesansar.com/today-share-price',
        },
        callback=callback,
        cb_kwargs=kwargs,
    )

