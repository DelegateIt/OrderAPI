#!/usr/bin/env python3.4

import unittest

import sys, os
sys.path.append(os.path.abspath('../gator/'))
sys.path.append(os.path.abspath('../../api/'))

from models import *
import apiclient

# Connection to DynamoDB
conn = apiclient.init_connection()

# Tables
customers    = Table("DelegateIt_Customers", connection=conn)
delegators   = Table("DelegateIt_Delegators", connection=conn)
transactions = Table("DelegateIt_Transactions", connection=conn)
handlers     = Table("DelegateIt_Handlers", connection=conn)

def clear():
    apiclient.clear_database(conn)

class TestModel(unittest.TestCase):
    def setUp(self):
        clear()

    def tearDown(self):
        clear()

    def setUp(self):
        self.model = Model()

    def test_init(self):
        self.assertEquals(self.model.get_dirty_keys(), set([]))

    def test_get_item(self):
        self.model.item = "test_item"
        self.assertEquals(self.model.item, self.model["item"])

    def test_get_item_default(self):
        self.assertIsNone(self.model["non_existant_key"])

    # Testing Model as a parent class of Customer
    def test_dirty_keys(self):
        customer = Customer({
            CFields.UUID: "1",
            CFields.FIRST_NAME: "2"})

        customer[CFields.LAST_NAME] = "3"

        self.assertEquals(customer.get_dirty_keys(),
            set([CFields.UUID, CFields.FIRST_NAME, CFields.LAST_NAME]))

    def test_get_data(self):
        customer = Customer.create_new({
            CFields.FIRST_NAME: "1"})

        customer_data = customer.get_data()
        self.assertEquals(len(customer_data), 4)
        self.assertEquals(customer_data[CFields.FIRST_NAME], "1")
        self.assertIsNotNone(customer_data[CFields.UUID])
        self.assertEquals(customer_data[CFields.A_TRANS_UUIDS], [])
        self.assertEquals(customer_data[CFields.IA_TRANS_UUIDS], [])

    def  test_create(self):
        customer = Customer({
            CFields.UUID: "1",
            CFields.FIRST_NAME: "2",
            CFields.LAST_NAME: "3"})

        result = customer.create()
        self.assertTrue(result)

        # Check db
        customer_db = customers.get_item(
            uuid=customer[CFields.UUID],
            consistent=True)

        self.assertTrue(customer_db[CFields.UUID], "1")
        self.assertTrue(customer_db[CFields.FIRST_NAME], "2")
        self.assertTrue(customer_db[CFields.LAST_NAME], "3")

    def test_save(self):
        customer = Customer.create_new({
            CFields.FIRST_NAME: "1"})

        customer.create() 

        customer[CFields.FIRST_NAME] = "2"
        result = customer.save()
        self.assertTrue(result)

        # Check db
        customer_db = customers.get_item(
            uuid=customer_response_data["uuid"],
            consistent=True)

        self.assertEquals(customer_db[CFields.FIRST_NAME], "2")

class TestCustomer(unittest.TestCase):
    def setUp(self):
        clear()

    def tearDown(self):
        clear()

    def test_empy_init(self):
        customer = Customer({})
        self.assertEquals(customer.dirty_keys, set([]))

    def test_normal_init(self):
        customer = Customer({
            CFields.UUID: "1",
            CFields.FIRST_NAME: "2",
            CFields.STRIPE_ID: "3"})

        self.assertEquals(customer[CFields.UUID], "1")
        self.assertEquals(customer[CFields.FIRST_NAME], "2")
        self.assertEquals(customer[CFields.STRIPE_ID], "3")

    def test_invalid_init(self):
        with self.assertRaises(ValueError):
            customer = Customer({
                CFields.UUID: "1",
                "invalid_attr": "invalid"})

    def test_create_new(self):
        customer = Customer.create_new({
            CFields.FIRST_NAME: "1",
            CFields.LAST_NAME: "2"})

        self.assertEquals(customer[CFields.FIRST_NAME], "1")
        self.assertEquals(customer[CFields.LAST_NAME], "2")

        # Default values for the fields
        self.assertIsNotNone(customer[CFields.UUID])
        self.assertEquals(customer[CFields.A_TRANS_UUIDS], [])
        self.assertEquals(customer[CFields.IA_TRANS_UUIDS], [])

if __name__ == "__main__":
    test_loader = unittest.TestLoader()
    suite = test_loader.loadTestsFromTestCase(TestModel)
    suite.addTests(test_loader.loadTestsFromTestCase(TestCustomer))
    unittest.TextTestRunner(verbosity=3).run(suite)
