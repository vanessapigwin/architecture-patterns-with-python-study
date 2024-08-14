from flask import Flask, request
from allocation.domain import events
from allocation.adapters import orm
from allocation.service_layer import unit_of_work, messagebus
from allocation.service_layer.handlers import InvalidSku

from datetime import datetime


orm.start_mappers()
app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        event = events.AllocationRequired(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
        )
        result = messagebus.handle(event, unit_of_work.SqlAlchemyUnitOfWork())
        batchref = result.pop(0)
    except InvalidSku as e:
        return {"messages": str(e)}, 400

    return {"batch_ref": batchref}, 201


@app.route("/add_batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    messagebus.handle(
        events.BatchCreated(
            request.json["ref"], request.json["sku"], request.json["qty"], eta
        ),
        unit_of_work.SqlAlchemyUnitOfWork(),
    )

    return "OK", 201
