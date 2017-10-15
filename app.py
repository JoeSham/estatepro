# -*- coding: utf-8 -*-
import os
import urllib

import arrow

from flask import Flask, request, render_template
from models import db, Estate
from sqlalchemy import and_

app = Flask(__name__)

DB_URL = urllib.parse.urlparse(os.environ['DATABASE_URL'])
DB_HOST = DB_URL.hostname
DB_PORT = DB_URL.port
DB_DATABASE = DB_URL.path[1:]
DB_USERNAME = DB_URL.username
DB_PASSWORD = DB_URL.password
POSTGRES = {
    'user': DB_USERNAME,
    'pw': DB_PASSWORD,
    'db': DB_DATABASE,
    'host': DB_HOST,
    'port': DB_PORT,
}

app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
db.init_app(app)


@app.route('/', methods=['GET'])
def index():
    params = dict()
    params['price_min'] = request.args.get('price_min') or 0
    params['price_max'] = request.args.get('price_max') or 100000000
    params['date_from'] = request.args.get('date_from') or arrow.now().shift(days=-7).format('YYYY-MM-DD')
    params['date_to'] = request.args.get('date_to') or arrow.now().format('YYYY-MM-DD')
    params['m2_min'] = request.args.get('m2_min') or 0
    params['m2_max'] = request.args.get('m2_max') or 1000

    estates_query = db.session.query(Estate).filter(
        and_(
            Estate.edited.between(params['date_from'], params['date_to']),
            Estate.price_m2_floors > 0,
            Estate.ownership == 'osobní',
            Estate.price.between(params['price_min'], params['price_max']),
            Estate.m2_floors.between(params['m2_min'], params['m2_max']),
        )
    ).order_by(Estate.price_m2_floors) #.all()
    # print(estates_query)
    estates = estates_query.all()

    return render_template('index.html', estates=estates, params=params)


if __name__ == '__main__':
    app.run()
