import csv
import time
import os
from flask import Flask
from flask_restx import Api, Resource, fields, reqparse

app = Flask(__name__)
api = Api(app, version='1.0', title='Cloud Impact Rating API',
    description='A protoype API system allowing the storage and retrieval of Climate Impact Rating data for products',
    prefix='/v1'
)

from cloudant.client import Cloudant

# You must overwrite the values in api_access below with those from your service credential, that you created in IBM Cloud IAM for Cloudant.
# The actual values below are to just show the format - and these are no longer valid.
api_access = {
  "apikey": "cCUivpBA3xL0QeknRyh6J8Zqki52QH3RpGq-yOQ2dRNF",
  "host": "3591342c-5a32-4f8b-ac29-f75e02924d54-bluemix.cloudantnosqldb.appdomain.cloud",
  "iam_apikey_description": "Auto-generated for key 1b244492-12ac-431a-b9a1-cf6766065ff8",
  "iam_apikey_name": "Credenciais de serviço-1",
  "iam_role_crn": "crn:v1:bluemix:public:iam::::serviceRole:Manager",
  "iam_serviceid_crn": "crn:v1:bluemix:public:iam-identity::a/26d47d6373d290fb989afc05d12f6539::serviceid:ServiceId-f59afee4-e485-4767-bafb-a773062d733a",
  "url": "https://3591342c-5a32-4f8b-ac29-f75e02924d54-bluemix.cloudantnosqldb.appdomain.cloud",
  "username": "3591342c-5a32-4f8b-ac29-f75e02924d54-bluemix"
}

client = Cloudant.iam(
    api_access['username'],
    api_access['apikey'],
    connect=True
)

product_ns = api.namespace('product', description='User CIR Product Operations')

# Define the API models we will use (these will show up in the Swagger Specification).

rating = api.model('Rating', {
    'efficiency': fields.Integer(required=False, description='The efficiency-in-use rating (0-9, where 0 is best) of this item'),
    'energy': fields.Float(required=False, description='The energy (J) to produce this item'),
    'CO2': fields.Float(required=False, description='The CO2 released (Kg) to produce this item'),
    'otherGG': fields.Float(required=False, description='The other green house gases released (Kg) to produce this item'),
    'water': fields.Float(required=False, description='The volume of water (litres) to produce this item'),
    'plastic': fields.Float(required=False, description='The amout of plastic (Kg) included in this item'),
    'lifetime': fields.Float(required=False, description='The expected lifetime (years) of this item'),
    'recyclability': fields.Integer(required=False, description='The recyclability rating (0-9, where 0 is best) of this item'),
    'repairability': fields.Integer(required=False, description='The Right to Repair rating (0-9, where 0 is best) of this item')
})

product = api.model('Product', {
    'id': fields.String(readonly=True, description='The unique product registration identifier'),
    'barcode_id': fields.String(required=True, description='The barcode for this product id, in EAN-13 format'),
    'type': fields.String(required=True, description='The type of product'),
    'category': fields.String(required=True, description='The category of this product, with its type'),
    'model': fields.String(required=True, description='The model number of this product'),
    'brand': fields.String(required=True, description='The venfor of this item'),
    'rating_data': fields.Nested(rating)
})

db_name = 'cir-db'

# A Data Access Object to handle the reading and writing of Product records to the Cloudant DB

class ProductDAO(object):
    def __init__(self):
        if db_name in client.all_dbs():
            self.cir_db = client[db_name]
        else:
            # Create the DB and immport the dummy data
            self.cir_db = client.create_database(db_name)
            self.import_data()

    def import_data(self):
        print ("Importing dummy data", end = '', flush=True)
        with open('dummy-data.txt') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if line_count > 0:
                    data = {
                        'barcode_id': row[4],
                        'type': row[0],
                        'category': row[2],
                        'model': row[3],
                        'brand': row[1],
                        'rating_data': {
                            'efficiency': int(row[6]),
                            'energy': float(row[7]) + float(row[8]),
                            'CO2': float(row[13]),
                            'otherGG': float(row[14]),
                            'water': float(row[11]),
                            'plastic': float(row[9]),
                            'lifetime': float(row[10]),
                            'recyclability': int(row[12]),
                            'repairability': int(row[15])
                        }
                    }
                    time.sleep(0.15)     # Have to rate limit it to less than 10 a second, due to free tier
                    self.create(data)
                    print(".", end = '', flush=True)
                line_count += 1
        print ("complete")

    def list(self):
        return [x for x in self.cir_db]

    def get(self, id):
        try:
            my_document = self.cir_db[id]
            my_document['id'] = my_document['barcode_id']
        except KeyError:
            api.abort(404, "Product {} not registered".format(id))
        return my_document

    def get_by_barcode(self, barcode_id):
        # For now this is easy, since id is the same as barcode_id....in the future this would need an
        # index of some such search ability
        try:
            my_document = self.cir_db[barcode_id]
            my_document['id'] = my_document['barcode_id']
        except KeyError:
            api.abort(404, "Product {} not registered".format(id))
        return my_document

    def create(self, data):
        # For now, we'll set the id to be the same as the barcode_id. For production systems, we would
        # probably want these seperate, and to implement indexed searching by barcode_id for GET.
        try:
            data['_id'] = data['barcode_id']
            my_document = self.cir_db.create_document(data)
            my_document['id'] = my_document['barcode_id']
        except KeyError:
            api.abort(404, "Product {} already registered".format(id))
        return my_document

    def update(self, id, data):
        # Not currently supported
        return

    def delete(self, id):
        try:
            my_document = self.cir_db[id]
            my_document.delete()
        except KeyError:
            api.abort(404, "Product {} not registered".format(id))
        return

# Handlers for the actual API urls

# In a more production orientated version, you might well split these endpoints into
# those for a consumer (which is really just "look up by barcode"), and those that
# allow manufacturers to publish their product data.

@product_ns.route('')
class Product(Resource):
    @api.marshal_with(product)
    @api.doc('List products')
    @api.doc(params={'barcode_id': 'The barcode ID of this product (optional)'})
    def get(self):
        # Currently we support either a full list, or query by barcode_id.
        parser = reqparse.RequestParser()
        parser.add_argument('barcode_id', required=False, location='args')
        args = parser.parse_args()
        if args['barcode_id']:
            return [ProductDAO().get_by_barcode(args['barcode_id'])]
        else:
            return ProductDAO().list()    

    @api.marshal_with(product, code=201)
    @api.doc(body=product)
    def post(self):
        return ProductDAO().create(api.payload), 201

@product_ns.route('/<string:id>')
class ProductWithID(Resource):
    @api.marshal_with(product)
    @api.doc(params={'id': 'The unique ID of this product'})
    def get(self, id):
        return ProductDAO().get(id)

    @api.marshal_with(product)
    @api.doc(params={'id': 'The unique ID of this product'})
    def delete(self, id):
        return ProductDAO().delete(id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.1', port=port)
    #app.run()
