import unittest

from gator import common
from gator import apiclient

from gator.models import Model, Customer, Delegator, Transaction,\
                         CFields, DFields, TFields, MFields, customers,\
                         delegators, transactions, handlers

def clear():
    apiclient.clear_database()

class TestModel(unittest.TestCase):
    def setUp(self):
        clear()
        self.customer = Model.load_from_data(Customer, {})

    def test_invalid_init(self):
        with self.assertRaises(ValueError):
            Model.load_from_data(Customer, {"invalid_key": "DOES NOT MATTER"})

    def test_load_from_db(self):
        new_customer = Customer.create_new({
            CFields.FIRST_NAME: "1",
            CFields.PHONE_NUMBER: "2"})

        new_customer.create()

        loaded_customer = Model.load_from_db(
            Customer,
            new_customer[Customer.KEY])

        for key in new_customer.get_data():
            # Ignore default initialized values
            if new_customer[key] != []:
                self.assertEquals(new_customer[key], loaded_customer[key])

    def test_invalid_load_from_db(self):
        class TempClass():
            pass

        with self.assertRaises(ValueError):
            Model.load_from_db(TempClass, {})

    def test_load_from_db_nonexistant_item(self):
        self.assertIsNone(Model.load_from_db(Customer, "INVALID KEY"))

    def test_load_from_data(self):
        customer = Model.load_from_data(Customer, {
            CFields.UUID: "1",
            CFields.FIRST_NAME: "2"
        })

        self.assertEquals(2, len(customer.get_data()))
        self.assertEquals(customer[CFields.UUID], "1")
        self.assertEquals(customer[CFields.FIRST_NAME], "2")

    def test_invalid_load_from_data(self):
        class TempClass():
            pass

        with self.assertRaises(ValueError):
            Model.load_from_data(TempClass, {})

    def test_get_item(self):
        self.customer[CFields.FIRST_NAME] = "1"
        self.assertEquals(self.customer[CFields.FIRST_NAME], "1")

    def test_get_item_default(self):
        self.assertIsNone(self.customer["non_existant_key"])

    def test_invalid_set_item(self):
        with self.assertRaises(ValueError):
            self.customer["invalid_key"] = "DOES NOT MATTER"

    def test_update(self):
        self.customer.update({
            CFields.UUID: "1",
            CFields.FIRST_NAME: "2"})

        self.assertEquals(self.customer[CFields.UUID], "1")
        self.assertEquals(self.customer[CFields.FIRST_NAME], "2")

    def test_atts_are_valid(self):
        customer = Model.load_from_data(Customer, {})
        self.assertTrue(customer._atts_are_valid({
            CFields.UUID,
            CFields.FIRST_NAME}))

    def test_empty_atts_are_valid(self):
        self.assertTrue(self.customer._atts_are_valid(self.customer.get_data()))

    def test_get_data(self):
        customer = Customer.create_new({
            CFields.FIRST_NAME: "1",
            CFields.PHONE_NUMBER: "2"})

        customer_data = customer.get_data()
        self.assertEquals(len(customer_data), 3)
        self.assertEquals(customer_data[CFields.FIRST_NAME], "1")
        self.assertEquals(customer_data[CFields.PHONE_NUMBER], "2")
        self.assertIsNotNone(customer_data[CFields.UUID])

    def test_save(self):
        customer = Customer.create_new({
            CFields.FIRST_NAME: "1",
            CFields.PHONE_NUMBER: "2"})

        customer.create()

        customer[CFields.FIRST_NAME] = "2"
        result = customer.save()
        self.assertTrue(result)

        # Check db
        customer_db = customers.get_item(
            uuid=customer[CFields.UUID],
            consistent=True)

        self.assertEquals(customer_db[CFields.FIRST_NAME], "2")

    def test_save_consistency(self):
        customer_1 = Customer.create_new({
            CFields.FIRST_NAME: "1",
            CFields.PHONE_NUMBER: "2"})

        customer_1.create()

        customer_2 = Model.load_from_db(
            Customer,
            customer_1[CFields.UUID])

        customer_1[CFields.FIRST_NAME] = "2"
        customer_1.save()

        customer_2[CFields.FIRST_NAME] = "3"

        self.assertFalse(customer_2.save())

    def  test_create(self):
        customer = Customer.load_from_data(Customer, {
            CFields.UUID: "1",
            CFields.FIRST_NAME: "2",
            CFields.LAST_NAME: "3",
            CFields.PHONE_NUMBER: "4"})

        result = customer.create()
        self.assertTrue(result)

        # Check db
        customer_db = customers.get_item(
            uuid=customer[CFields.UUID],
            consistent=True)

        self.assertTrue(customer_db[CFields.UUID], "1")
        self.assertTrue(customer_db[CFields.FIRST_NAME], "2")
        self.assertTrue(customer_db[CFields.LAST_NAME], "3")

class TestCustomer(unittest.TestCase):
    def setUp(self):
        clear()

    def test_create_new(self):
        customer = Customer.create_new({
            CFields.FIRST_NAME: "1",
            CFields.LAST_NAME: "2"})

        self.assertEquals(customer[CFields.FIRST_NAME], "1")
        self.assertEquals(customer[CFields.LAST_NAME], "2")

        # Default values for the fields
        self.assertIsNotNone(customer[CFields.UUID])

    def test_is_unique(self):
        customer_1 = Customer.create_new({})

        self.assertFalse(customer_1.is_unique())

        customer_1[CFields.PHONE_NUMBER] = "1"
        self.assertTrue(customer_1.is_unique())

        customer_1.create()

        customer_2 = Customer.create_new({
            CFields.PHONE_NUMBER: "1"})

        self.assertFalse(customer_2.is_unique())

    def test_create(self):
        customer = Customer.create_new({})

        self.assertFalse(customer.create())

        customer[CFields.PHONE_NUMBER] = "1"

        self.assertTrue(customer.create())

class TestDelegator(unittest.TestCase):
    def setUp(self):
        clear()

    def test_create_new(self):
        delegator = Delegator.create_new({
            DFields.EMAIL: "1"})

        self.assertEquals(len(delegator.get_data()), 2)
        self.assertEquals(delegator[DFields.EMAIL], "1")
        self.assertIsNotNone(delegator[DFields.UUID])

    def test_is_unqiue(self):
        delegator = Delegator.create_new({
            DFields.EMAIL: "1",
            DFields.FIRST_NAME: "2",
            DFields.LAST_NAME: "3"})

        self.assertFalse(delegator.is_unique())

        delegator[DFields.PHONE_NUMBER] = "4"
        self.assertTrue(delegator.is_unique())

        delegator.create()
        self.assertFalse(delegator.is_unique())

    def test_create(self):
        delegator = Delegator.create_new({
            DFields.EMAIL: "1",
            DFields.FIRST_NAME: "2",
            DFields.LAST_NAME: "3"})

        self.assertFalse(delegator.create())

        delegator[DFields.PHONE_NUMBER] = "2"
        self.assertTrue(delegator.create())

class TestTransaction(unittest.TestCase):
    def test_create_new(self):
        transaction = Transaction.create_new({
            TFields.CUSTOMER_UUID: "1"})

        self.assertEquals(transaction[TFields.CUSTOMER_UUID], "1")
        self.assertEquals(transaction[TFields.STATUS], common.TransactionStates.STARTED)

    def test_get_data(self):
        transaction = Transaction.create_new({
            TFields.CUSTOMER_UUID: "1"})

        transaction.add_message(Message(from_customer="2"))

        data = transaction.get_data()
        self.assertEquals(len(data), 5)
        self.assertIsNotNone(data[TFields.UUID])
        self.assertEquals(data[TFields.CUSTOMER_UUID], "1")
        self.assertEquals(data[TFields.STATUS], common.TransactionStates.STARTED)
        self.assertIsNotNone(data[TFields.TIMESTAMP])
        self.assertEquals(data[TFields.MESSAGES][0][MFields.FROM_CUSTOMER], "2")
        self.assertIsNotNone(data[TFields.MESSAGES][0][MFields.TIMESTAMP])

    def test_add_message(self):
        transaction = Transaction.create_new({
            TFields.CUSTOMER_UUID: "1"})

        transaction.add_message(Message(from_customer="2"))

        self.assertEquals(transaction[TFields.MESSAGES][0][MFields.FROM_CUSTOMER], "2")
        self.assertIsNotNone(transaction[TFields.MESSAGES][0][MFields.TIMESTAMP])


class TestMessage(unittest.TestCase):
    def test_init(self):
        message = Message(
            from_customer="1",
            content="2")

        self.assertEquals(message.from_customer, "1")
        self.assertEquals(message.content, "2")
        self.assertIsNone(message.platform_type)
        self.assertIsNotNone(message.timestamp)

    def test_get_data(self):
        message = Message(
            from_customer="1",
            content="2")

        data = message.get_data()
        self.assertEquals(len(data), 3)
        self.assertEquals(data["from_customer"], "1")
        self.assertEquals(data["content"], "2")
        self.assertIsNone(data.get("platform_type"))
        self.assertIsNotNone(data["timestamp"])
