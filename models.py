from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker

Base = declarative_base()
engine = create_engine("mysql+mysqldb://@localhost/DelegateItDB")
Session = sessionmaker(bind=engine)

class Customer(Base):
    __tablename__ = "customers"

    # TODO: add nullable=False
    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=True)
    last_name  = Column(String(50), nullable=True)
    phone_number = Column(String(50), nullable=True) # TODO: use python phone numbers parsing library
    messages = relationship("Message", order_by="Message.id", backref="customer",
                                    cascade="all, delete, delete-orphan")

    def __repr__(self):
        return "<Customer(first_name='%s', last_name='%s', phone_number='%s', messages=[%s])>" % (
            self.first_name, self.last_name, self.phone_number, ", ".join([str(message) for message in self.messages]))


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    content = Column(String(50), nullable=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))

    def __repr__(self):
        return "<Message(content='%s', customer_id='%s')>" % (
            self.content, self.customer_id)


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    session = Session()

    customer = Customer(first_name="George", last_name="Farcasiu", phone_number="8176808185")
    customer.messages = [Message(content="Message content!!")]

    session.add(customer)
    session.commit()

    print session.query(Customer).order_by("id")[0]
