# -*- coding: utf-8 -*-
from __future__ import division
import json
import os
import re
import time
import urllib
import urllib3

import arrow
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
import psycopg2
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        'url': 'https://www.bezrealitky.cz/api/record/markers?offerType=prodej&estateType=byt%2Cdum&boundary=%5B%5B%7B%22lat%22%3A49.29599792898956%2C%22lng%22%3A16.78011389402343%7D%2C%7B%22lat%22%3A49.284097329283846%2C%22lng%22%3A16.82773406086949%7D%2C%7B%22lat%22%3A49.25886694189089%2C%22lng%22%3A16.846440775899055%7D%2C%7B%22lat%22%3A49.20749603841644%2C%22lng%22%3A16.86137203201031%7D%2C%7B%22lat%22%3A49.1590032200752%2C%22lng%22%3A16.896797580217935%7D%2C%7B%22lat%22%3A49.06446181159556%2C%22lng%22%3A17.038986473049363%7D%2C%7B%22lat%22%3A48.735114944944414%2C%22lng%22%3A17.001468088695447%7D%2C%7B%22lat%22%3A48.70541377205597%2C%22lng%22%3A16.856822048449658%7D%2C%7B%22lat%22%3A48.90180204589122%2C%22lng%22%3A15.950732661330107%7D%2C%7B%22lat%22%3A49.24947705021509%2C%22lng%22%3A15.886054514590228%7D%2C%7B%22lat%22%3A49.41475929428654%2C%22lng%22%3A15.902301320312517%7D%2C%7B%22lat%22%3A49.480081880923%2C%22lng%22%3A16.143495934490602%7D%2C%7B%22lat%22%3A49.418584054221185%2C%22lng%22%3A16.33890390254669%7D%2C%7B%22lat%22%3A49.38025269543562%2C%22lng%22%3A16.52588706746178%7D%2C%7B%22lat%22%3A49.374485574435326%2C%22lng%22%3A16.592085944479095%7D%2C%7B%22lat%22%3A49.29599792898956%2C%22lng%22%3A16.78011389402343%7D%5D%5D&hasDrawnBoundary=true&locationInput=brno',
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

def td_that_doesnotcontainlink(tag):
    res = []
    tds = tag.find_all('td')
    for td in tds:
        if td.find('a') == None:
            res.append(td)
    return res

def getTodaysUpdate():
    cur.execute('select id from estate where source = \'bezrealitky.cz\' and timestamp > now() - interval \'1 day\'')
    res = [x[0] for x in cur.fetchall()]
    return res

ensure_destionation_table()
editedToday = getTodaysUpdate();

for request in request_list:
    with requests.Session() as session:
        if ('payload' in request):
            r = session.post(request['url'], json=request['payload'], verify=False)
        else:
            r = session.get(request['url'], verify=False)
        estate_list = json.loads(r.text)
        for estate in estate_list:
            id = int(estate['id'])
            url = BASE_URL + FLATS_URL_SUB_PART + str(id)
            if (str(id) in editedToday):
                print('Skipping ' + url)
            else:
                print(url)
                r_details = session.get(url, verify=False)
                soup = BeautifulSoup(r_details.text, 'html.parser')
                data = dict()
                data['source'] = 'bezrealitky.cz'
                data['id'] = id
                data['price'] = int(estate['advertEstateOffer'][0]['price'])
                data['m2'] = int(estate['advertEstateOffer'][0]['surface'])
                data['m2_floors'] = int(estate['advertEstateOffer'][0]['surface'])
                data['price_m2'] = round(data['price'] / data['m2']) if data['m2'] > 0 else 0
                data['price_m2_floors'] = data['price_m2']
                data['real_price'] = round(data['price'] * 1.04)

                gps = json.loads(estate['advertEstateOffer'][0]['gps'])
                data['latitude'] = gps['lat']
                data['longitude'] = gps['lng']
                data['location'] = None
                if data['latitude'] and data['longitude']:
                    try:
                        geolocator = Nominatim()
                        data['location'] = geolocator.reverse('{0}, {1}'.format(data['latitude'],
                                                                                data['longitude'])).address.encode('utf8')
                    except:
                        pass

                data['edited'] = min(arrow.get(estate['timeOrder']['date']), arrow.now()).date()
                data['link'] = url

                meta_title = soup.find('meta', attrs={'property': 'og:title'})
                if meta_title:
                    data['title'] = soup.find('meta', attrs={'property': 'og:title'}).get('content')
                else:
                    data['title'] = estate['uri']

                headerPerex = soup.find('p', attrs={'class': 'heading__perex'})
                if headerPerex:
                    data['locality'] = headerPerex.text.strip()
                else:
                    data['locality'] = ''

                box_description = soup.find('div', attrs={'class': 'b-desc'})
                if box_description:
                    data['description'] = list(box_description.find('p', attrs={'class': 'b-desc__info'}).stripped_strings)[0]
                else:
                    data['description'] = ''

                details = soup.find('table', attrs={'class': 'table', 'style': "border-collapse: initial;"})
                if details:
                    keys = details.find_all('th')
                    values = td_that_doesnotcontainlink(details)
                    for key, value in zip(keys, values):
                        # if key.text == 'číslo inzerátu:':
                        #     data['id'] = int(value.text.strip())
                        if key.text == 'Dispozice:':
                            data['type'] = value.text.strip()
                        # elif key.text == 'plocha:':
                        #     data['m2'] = int(value.text.strip().split(' ')[0])
                        # elif key.text == 'cena:':
                        #     data['price'] = int(value.text.strip().split(' ')[0].replace('.', ''))
                        elif key.text == 'Typ vlastnictví:':
                            data['ownership'] = value.text.strip().lower()
                        elif key.text == 'PENB:':
                            data['energy_class'] = value.text.strip().upper()
                        elif key.text == 'Typ budovy:':
                            data['building_type'] = value.text.strip().lower()
                        elif key.text == 'Vybavení:':
                            data['equipment'] = value.text.strip().lower()
                        elif key.text == 'Podlaží:':
                            data['floor'] = int(value.text.strip())
                        elif key.text == 'Balkón:':
                            data['balcony'] = True if value.text.strip().lower() == 'ano' else False
                        elif key.text == 'Terasa:':
                            data['terrace'] = True if value.text.strip().lower() == 'ano' else False

                    photos_div = soup.find('div', attrs={'class': 'b-gallery'})
                    data['img_links'] = [img['src'] for img in photos_div.find_all('img')]
                else:
                    r = re.search(r'([0-9]\+(?:kk|1))', data['title'])
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