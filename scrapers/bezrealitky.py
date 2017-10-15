# -*- coding: utf-8 -*-
from __future__ import division
import json
import os
import re
import time
import urllib

import arrow
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
import psycopg2
import requests

BASE_URL = 'https://www.bezrealitky.cz'
FLATS_URL_SUB_PART = '/nemovitosti-byty-domy/'

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

request_list = [
    {
        'url': 'https://www.bezrealitky.cz/api/search/map',
        'payload': {"action":"map","squares":"[\"{\\\"swlat\\\":48,\\\"swlng\\\":16,\\\"nelat\\\":50,\\\"nelng\\\":20}\"]","filter":{"order":"time_order_desc","advertoffertype":"nabidka-prodej","estatetype":["byt"],"disposition":[],"ownership":"","equipped":"","priceFrom": 0,"priceTo": 0,"construction":"","description":"","surfaceFrom":"","surfaceTo":"","balcony":"","terrace":"","polygons":[[{"lat":49.285305697158,"lng":16.59318011636401},{"lat":49.293561487008,"lng":16.59921924028299},{"lat":49.286743305975,"lng":16.648931488464996},{"lat":49.27812147415,"lng":16.617572870816957},{"lat":49.23353050028,"lng":16.673252785399995},{"lat":49.224973955024,"lng":16.664667637137995},{"lat":49.21803168933,"lng":16.676081231174066},{"lat":49.241931640386,"lng":16.72669993171496},{"lat":49.211740225328,"lng":16.712135988749992},{"lat":49.193402720949,"lng":16.72078924470793},{"lat":49.185055402043,"lng":16.69435427764904},{"lat":49.171993935571,"lng":16.70482451497105},{"lat":49.148502821265,"lng":16.700185282734992},{"lat":49.145550434818,"lng":16.712369956814996},{"lat":49.128206336719,"lng":16.706253451799967},{"lat":49.109880601728,"lng":16.62631252285405},{"lat":49.14509029711,"lng":16.64029255158607},{"lat":49.135826438005,"lng":16.589742400596037},{"lat":49.157476689683,"lng":16.595028653236},{"lat":49.152865482841,"lng":16.55842988552604},{"lat":49.196125037658,"lng":16.493182612501982},{"lat":49.193417843488,"lng":16.45803022259804},{"lat":49.216667169031,"lng":16.42798939985903},{"lat":49.282703325646,"lng":16.46271568074303},{"lat":49.263483832977,"lng":16.50831519252597},{"lat":49.256926576028,"lng":16.50192391105793},{"lat":49.241146283494,"lng":16.526361237196966},{"lat":49.254919165921,"lng":16.531992382555927},{"lat":49.253474846061,"lng":16.56207702868005},{"lat":49.265822080947,"lng":16.553320145507996},{"lat":49.285305697158,"lng":16.59318011636401},{"lat":49.285305697158,"lng":16.59318011636401},{"lat":49.285305697158,"lng":16.59318011636401},{"lat":49.285305697158,"lng":16.59318011636401}]]}}
    },
]


def ensure_destionation_table():
    cur.execute(
        '''
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
                id TEXT,
                source TEXT,
                timestamp TIMESTAMP WITH TIME ZONE,
                updated TIMESTAMP WITH TIME ZONE,
                PRIMARY KEY (id, source)
            );
        '''
    )


def upsert(conn, cur, data):
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
            'edited': data.get('edited'),
            'title': data.get('title'),
            'type': data.get('type'),
            'price': data.get('price'),
            'real_price': data.get('real_price'),
            'price_m2': data.get('price_m2'),
            'price_m2_floors': data.get('price_m2_floors'),
            'price_notes': data.get('price_notes'),
            'locality': data.get('locality'),
            'state': data.get('state'),
            'ownership': data.get('ownership'),
            'link': data.get('link'),
            'floor': data.get('floor'),
            'floor_string': data.get('floor_string'),
            'm2': data.get('m2'),
            'm2_floors': data.get('m2_floors'),
            'm2_balcony': data.get('m2_balcony'),
            'm2_cellar': data.get('m2_cellar'),
            'garage': data.get('garage'),
            'final_inspection_year': data.get('final_inspection_year'),
            'energy_rating': data.get('energy_rating'),
            'elevator': data.get('elevator'),
            'description': data.get('description'),
            'seller': data.get('seller'),
            'phone': data.get('phone'),
            'email': data.get('email'),
            'attractive_offer': data.get('attractive_offer'),
            'img_links': data.get('img_links'),
            'api_link': data.get('api_link'),
            'json': data.get('json.dumps(details)'),
            'location': data.get('location'),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'id': data.get('id'),
            'source': data.get('source'),
            # 'timestamp': data['None'],  # now() in sql
            # 'updated': data['None'],  # now() in sql
        }
    )
    cur.execute(query)
    conn.commit()  # save db changes
    print('Upsert successfull.')


ensure_destionation_table()
for request in request_list:
    with requests.Session() as session:
        r = session.post(request['url'], json=request['payload'], verify=False)
        estate_list = json.loads(r.text)['squares'][0]['records']
        for estate in estate_list:
            url = BASE_URL + FLATS_URL_SUB_PART + estate['id']
            print(url)
            r_details = session.get(url, verify=False)
            soup = BeautifulSoup(r_details.text, 'html.parser')
            data = dict()
            data['source'] = 'bezrealitky.cz'
            data['id'] = int(estate['id'])
            data['price'] = int(estate['price'])
            data['m2'] = int(estate['surface'])
            data['m2_floors'] = int(estate['surface'])
            data['price_m2'] = round(data['price'] / data['m2']) if data['m2'] > 0 else 0
            data['price_m2_floors'] = data['price_m2']
            data['real_price'] = round(data['price'] * 1.04)

            data['latitude'] = estate['lat']
            data['longitude'] = estate['lng']
            data['location'] = None
            if data['latitude'] and data['longitude']:
                try:
                    geolocator = Nominatim()
                    data['location'] = geolocator.reverse('{0}, {1}'.format(data['latitude'],
                                                                            data['longitude'])).address.encode('utf8')
                except:
                    pass

            data['edited'] = min(arrow.get(estate['time_order']), arrow.now()).date()
            data['link'] = url

            meta_title = soup.find('meta', attrs={'property': 'og:title'})
            if meta_title:
                data['title'] = soup.find('meta', attrs={'property': 'og:title'}).get('content')
            else:
                data['title'] = estate['title']

            header = soup.find('header')
            if header:
                data['locality'] = header.find('h2').text
            else:
                data['locality'] = ''

            box_description = soup.find('div', attrs={'class': 'box-description'})
            if box_description:
                data['description'] = list(box_description.find('div', attrs={'class': 'full'}).stripped_strings)[0]
            else:
                data['description'] = ''

            details = soup.find('div', attrs={'class': 'block-params'})
            if details:
                keys = details.find_all(class_='key')
                values = details.find_all(class_='value')
                for key, value in zip(keys, values):
                    # if key.text == 'číslo inzerátu:':
                    #     data['id'] = int(value.text.strip())
                    if key.text == 'dispozice:':
                        data['type'] = value.text.strip()
                    # elif key.text == 'plocha:':
                    #     data['m2'] = int(value.text.strip().split(' ')[0])
                    # elif key.text == 'cena:':
                    #     data['price'] = int(value.text.strip().split(' ')[0].replace('.', ''))
                    elif key.text == 'typ vlastnictví:':
                        data['ownership'] = value.text.strip().lower()
                    elif key.text == 'energetická třída:':
                        data['energy_class'] = value.text.strip().upper()
                    elif key.text == 'typ budovy:':
                        data['building_type'] = value.text.strip().lower()
                    elif key.text == 'vybavení:':
                        data['equipment'] = value.text.strip().lower()
                    elif key.text == 'podlaží:':
                        data['floor'] = int(value.text.strip())
                    elif key.text == 'balkón:':
                        data['balcony'] = True if value.text.strip().lower() == 'ano' else False
                    elif key.text == 'terasa:':
                        data['terrace'] = True if value.text.strip().lower() == 'ano' else False

                photos_div = soup.find('div', attrs={'class': 'other-photos'})
                data['img_links'] = [img['src'] for img in photos_div.find_all('img')]
            else:
                r = re.search(r'([0-9]\+(?:kk|1))', estate['title'])
                if r:
                    data['type'] = r.group(1)
                else:
                    data['type'] = None
                data['ownership'] = None
                data['energy_class'] = None
                data['building_type'] = None
                data['equipment'] = None
                data['floor'] = None
                data['balcony'] = False
                data['terrace'] = False
                data['img_links'] = []

            upsert(conn, cur, data)
            # time.sleep(0.5)
