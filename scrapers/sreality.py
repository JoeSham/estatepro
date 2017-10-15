# -*- coding: utf-8 -*-
import json
import logging
import os
import re
import time
import urllib

import arrow
import psycopg2
import requests as rq
from geopy.geocoders import Nominatim

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

DB_URL = urllib.parse.urlparse(os.environ['DATABASE_URL'])
DB_HOST = DB_URL.hostname
DB_PORT = DB_URL.port
DB_DATABASE = DB_URL.path[1:]
DB_USERNAME = DB_URL.username
DB_PASSWORD = DB_URL.password

conn = psycopg2.connect(
    "host='{DB_HOST}' "
    "port={DB_PORT} "
    "user='{DB_USERNAME}' "
    "password='{DB_PASSWORD}' "
    "dbname='{DB_DATABASE}'".format(DB_HOST=DB_HOST, DB_PORT=DB_PORT, DB_USERNAME=DB_USERNAME, DB_PASSWORD=DB_PASSWORD,
                                    DB_DATABASE=DB_DATABASE)
)
cur = conn.cursor()

tms = round(time.time() * 1000)

# listings pages / jsons
urls = [
    'https://www.sreality.cz/api/cs/v2/estates?category_main_cb=1&category_type_cb=1&'
    'locality_district_id=72&locality_region_id=14&per_page=950&tms={0}'.format(tms),

    # 'https://www.sreality.cz/api/cs/v2/estates?category_main_cb=1&category_type_cb=1'
    # '&locality_district_id=73&locality_region_id=14&per_page=950&tms={0}'.format(tms),
]

cur.execute(
    """
        CREATE TABLE IF NOT EXISTS estate (
            title TEXT,
            type TEXT,
            edited DATE,
            price NUMERIC,
            real_price NUMERIC,
            price_m2 NUMERIC,
            price_m2_floors NUMERIC,
            price_notes TEXT,
            locality TEXT,
            state TEXT,
            ownership TEXT,
            link TEXT,
            floor SMALLINT,
            floor_string TEXT,
            m2 NUMERIC,
            m2_floors NUMERIC,
            m2_balcony NUMERIC,
            m2_cellar NUMERIC,
            garage BOOLEAN,
            final_inspection_year INTEGER,
            energy_rating CHAR(1),
            elevator BOOLEAN,
            description TEXT,
            seller TEXT,
            phone TEXT,
            email TEXT,
            attractive_offer BOOLEAN,
            img_links TEXT[],
            api_link TEXT,
            json JSON,
            location TEXT,
            latitude NUMERIC,
            longitude NUMERIC,
            id TEXT PRIMARY KEY,
            source TEXT,
            timestamp TIMESTAMP WITH TIME ZONE,
            updated TIMESTAMP WITH TIME ZONE,
            PRIMARY KEY (id, source)
        );
    """
)

# go over all the listings pages (Brno, Brno-okoli, ...)
for url in urls:
    r = rq.get(url)
    estate_list = json.loads(r.text)['_embedded']['estates']

    print('Estates: ' + str(len(estate_list)))

    counter = 1
    # go over all the estates for the listing
    for estate in estate_list:
        # get details json
        api_link = 'https://www.sreality.cz/api' + estate['_links']['self']['href']
        log.info(api_link)
        r1 = rq.get(api_link)
        details = json.loads(r1.text)

        locality = details['locality']['value'] if 'locality' in details and 'value' in details['locality'] else ''
        latitude = details['map']['lat'] if 'map' in details and 'lat' in details['map'] else None
        longitude = details['map']['lon'] if 'map' in details and 'lon' in details['map'] else None
        location = None
        if latitude and longitude:
            try:
                geolocator = Nominatim()
                location = geolocator.reverse('{0}, {1}'.format(latitude, longitude)).address.encode('utf8')
            except:
                pass

        title = details['name']['value'] if 'name' in details and 'value' in details['name'] else None
        description = details['text']['value'] if 'text' in details and 'value' in details['text'] else None
        type = re.search(r'([0-9]{1,2}\+[0-9]{1}|[0-9]{1,2}\+kk)', title)
        type = type.group(1) if type else ''

        seo_locality = details['seo']['locality'] if 'seo' in details and 'locality' in details['seo'] else ''
        link = 'https://www.sreality.cz/detail/prodej/byt/' + type + '/' + seo_locality + '/' + str(estate['hash_id'])

        price = int(details['price_czk']['value_raw']) \
            if 'price_czk' in details and 'value_raw' in details['price_czk'] else 0

        seller = details['_embedded']['seller']['user_name'] \
            if '_embedded' in details and 'seller' in details['_embedded'] and \
            'user_name' in details['_embedded']['seller'] else None
        phone = details['_embedded']['seller']['phones'][0]['number'] \
            if '_embedded' in details and 'seller' in details['_embedded'] and \
            'phones' in details['_embedded']['seller'] and len(details['_embedded']['seller']['phones']) > 0 and \
            'number' in details['_embedded']['seller']['phones'][0] else None
        email = details['_embedded']['seller']['email'] \
            if '_embedded' in details and 'seller' in details['_embedded'] and \
            'email' in details['_embedded']['seller'] else None

        attractive_offer = bool(estate['attractive_offer']) if 'attractive_offer' in estate else False

        img_links = []
        for img in details['_embedded']['images']:
            img_links.append(img['_links']['view']['href'])
        # img_links_str = str(img_links).replace('[', '{').replace(']', '}').replace('\'', '"')

        price_notes = ''
        edited = ''
        state = None
        ownership = None
        floor_string = None
        floor = 0
        m2 = 0
        m2_floors = 0
        m2_balcony = 0
        m2_cellar = 0
        garage = False
        final_inspection_year = 0
        energy_rating = 'N'
        elevator = False
        for detail in details['items']:
            if detail['name'] == 'Poznámka k ceně':
                price_notes = detail['value']
            if detail['name'] == 'Aktualizace':
                edited = detail['value']
            if detail['name'] == 'Stav objektu':
                state = detail['value']
            if detail['name'] == 'Vlastnictví':
                ownership = detail['value'].lower()
            if detail['name'] == 'Podlaží':
                floor_string = detail['value']
                floor = re.search(r'([-]?[0-9]{1,2})\.', detail['value'])
                floor = int(floor.group(1)) if floor else None
            if detail['name'] == 'Užitná plocha':
                m2 = int(detail['value'])
            if detail['name'] == 'Plocha podlahová':
                m2_floors = int(detail['value'])
            if detail['name'] == 'Terasa':
                m2_balcony = int(detail['value'])
            if detail['name'] == 'Sklep':
                m2_cellar = int(detail['value'])
            if detail['name'] == 'Garáže':
                garage = detail['value']
            if detail['name'] == 'Rok kolaudace':
                final_inspection_year = int(detail['value'])
            if detail['name'] == 'Energetická náročnost budovy':
                m = re.search(r'Třída ([A-Z]{1})', detail['value'])
                if m:
                    energy_rating = m.group(1)
            if detail['name'] == 'Výtah':
                elevator = detail['value']

        # real price
        real_price = price
        no_tax_notes = ('nehradíte daň', 'neplatíte 4% daň', 'neplatíte daň', 'neplatíte provizi a daň',
                        'osvobozeno od daně', 'včetně daně')
        no_commission_notes = ('konečná cena', 'nehradíte provizi', 'neplatíte provizi', 'obsahuje provizi',
                               'včetně odměny zprostředkovatele', 'vč.provize', 'vč. provize', 'včetně provize')
        if all(note not in price_notes.lower() for note in no_tax_notes):
            real_price += round(price * 0.04)
        if all(note not in price_notes.lower() for note in no_commission_notes):
            real_price += round(price * 0.05)

        now = arrow.now()
        if edited.lower() in('dnes', ''):
            edited = now.date()
        elif edited.lower() == 'včera':
            edited = now.shift(days=-1).date()
        else:
            edited = arrow.get(edited, 'DD.MM.YYYY').date()

        price_m2 = round(real_price / m2, 0) if m2 > 0 else 0
        price_m2_floors = round(real_price / m2_floors, 0) if m2_floors > 0 else price_m2

        print(str(counter) + ': ' + title + '; ' + locality + '; ' + str(price) + ' Kc')
        print(link)
        counter += 1

        # note: psycopg2's cursor.execute automatically converts None to NULL
        query = cur.mogrify(
            '''
                INSERT INTO estate VALUES (
                    %(title)s, %(type)s, %(edited)s, %(price)s, %(real_price)s, %(price_m2)s, %(price_m2_floors)s,
                    %(price_notes)s, %(locality)s, %(state)s, %(ownership)s, %(link)s, %(floor)s,
                    %(floor_string)s, %(m2)s, %(m2_floors)s, %(m2_balcony)s, %(m2_cellar)s, %(garage)s,
                    %(final_inspection_year)s, %(energy_rating)s, %(elevator)s, %(description)s, %(seller)s,
                    %(phone)s, %(email)s, %(attractive_offer)s, %(img_links)s, %(api_link)s, %(json)s, 
                    %(location)s, %(latitude)s, %(longitude)s,
                    %(id)s, %(source)s, now(), now()
                )
                ON CONFLICT (id, source) DO UPDATE SET
                    title = EXCLUDED.title,
                    type = EXCLUDED.type,
                    edited = EXCLUDED.edited,
                    price = EXCLUDED.price,
                    real_price = EXCLUDED.real_price,
                    price_m2 = EXCLUDED.price_m2,
                    price_m2_floors = EXCLUDED.price_m2_floors,
                    price_notes = EXCLUDED.price_notes,
                    locality = EXCLUDED.locality,
                    state = EXCLUDED.state,
                    ownership = EXCLUDED.ownership,
                    link = EXCLUDED.link,
                    floor = EXCLUDED.floor,
                    floor_string = EXCLUDED.floor_string,
                    m2 = EXCLUDED.m2,
                    m2_floors = EXCLUDED.m2_floors,
                    m2_balcony = EXCLUDED.m2_balcony,
                    m2_cellar = EXCLUDED.m2_cellar,
                    garage = EXCLUDED.garage,
                    final_inspection_year = EXCLUDED.final_inspection_year,
                    energy_rating = EXCLUDED.energy_rating,
                    elevator = EXCLUDED.elevator,
                    description = EXCLUDED.description,
                    seller = EXCLUDED.seller,
                    phone = EXCLUDED.phone,
                    email = EXCLUDED.email,
                    attractive_offer = EXCLUDED.attractive_offer,
                    img_links = EXCLUDED.img_links,
                    api_link = EXCLUDED.api_link,
                    json = EXCLUDED.json,
                    location = EXCLUDED.location,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    id = EXCLUDED.id,
                    source = EXCLUDED.source,
                    -- timestamp = EXCLUDED.timestamp, -- keep original timestamp
                    updated = EXCLUDED.updated
            ''',
            {
                'edited': edited,
                'title': title,
                'type': type,
                'price': price,
                'real_price': real_price,
                'price_m2': price_m2,
                'price_m2_floors': price_m2_floors,
                'price_notes': price_notes,
                'locality': locality,
                'state': state,
                'ownership': ownership,
                'link': link,
                'floor': floor,
                'floor_string': floor_string,
                'm2': m2,
                'm2_floors': m2_floors,
                'm2_balcony': m2_balcony,
                'm2_cellar': m2_cellar,
                'garage': garage,
                'final_inspection_year': final_inspection_year,
                'energy_rating': energy_rating,
                'elevator': elevator,
                'description': description,
                'seller': seller,
                'phone': phone,
                'email': email,
                'attractive_offer': attractive_offer,
                'img_links': img_links,
                'api_link': api_link,
                'json': json.dumps(details),
                'location': location,
                'latitude': latitude,
                'longitude': longitude,
                'id': estate['hash_id'],
                'source': 'sreality.cz',
                # 'timestamp': None,  # now() in sql
                # 'updated': None,  # now() in sql
            }
        )
        cur.execute(query)
        conn.commit() # save db changes
        # time.sleep(0.25)

conn.close()
