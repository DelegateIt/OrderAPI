#!/usr/bin/env python3

import os
from boto.dynamodb2.table import Table
from boto.dynamodb2.layer1 import DynamoDBConnection
from boto.dynamodb2.fields import HashKey, GlobalAllIndex, RangeKey

def init_connection():
    host = "localhost"
    port = 8040

    return DynamoDBConnection(
        aws_access_key_id='foo',
        aws_secret_access_key='bar',
        host=host,
        port=port,
        is_secure=False)


def create_tables():
    conn = init_connection()

    tables = conn.list_tables()["TableNames"]
    for name in tables:
        Table(name, connection=conn).delete()


    Table.create("DelegateIt_Customers",
        schema=[
            HashKey("uuid"),
        ],
        global_indexes=[
            GlobalAllIndex("phone_number-index", parts=[
                HashKey("phone_number"),
            ]),
            GlobalAllIndex("fbuser_id-index", parts=[
                HashKey("fbuser_id"),
            ]),
        ],
        connection=conn
    )
    Table.create("DelegateIt_Delegators",
        schema=[
            HashKey("uuid"),
        ],
        global_indexes=[
            GlobalAllIndex("phone_number-index", parts=[
                HashKey("phone_number"),
            ]),
            GlobalAllIndex("email-index", parts=[
                HashKey("email"),
            ]),
            GlobalAllIndex("fbuser_id-index", parts=[
                HashKey("fbuser_id"),
            ]),
        ],
        connection=conn
    )
    Table.create("DelegateIt_Transactions_CD",
        schema=[
            HashKey("customer_uuid"),
            RangeKey("timestamp", "N")
        ],
        global_indexes=[
            GlobalAllIndex("status-index", parts=[
                HashKey("status"),
            ]),
            GlobalAllIndex("delegator_uuid-index", parts=[
                HashKey("delegator_uuid"),
                RangeKey("timestamp", "N")
            ]),
        ],
        connection=conn
    )
    Table.create("DelegateIt_Handlers", schema=[HashKey("ip_address")], connection=conn)
    Table.create("DelegateIt_PushEndpoints",
        schema=[HashKey("device_id")],
        global_indexes=[
           GlobalAllIndex("customer_uuid-index", parts=[
              HashKey("customer_uuid"),
           ])
        ],
        connection=conn
    )

    tables = conn.list_tables()["TableNames"]
    for name in tables:
        print("Describing", name, "\n", Table(name, connection=conn).describe())

if __name__ == "__main__":
    create_tables()
