from flask import Flask, request
from allocation import config
from allocation.domain import model
from allocation.adapters import orm
from allocation.service_layer import services, unit_of_work

from datetime import datetime


orm.start_mappers()
app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        batchref = services.allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
            unit_of_work.SqlAlchemyUnitOfWork(),
        )
    except services.InvalidSku as e:
        return {"messages": str(e)}, 400

    return {"batch_ref": batchref}, 201


@app.route("/add_batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    services.add_batch(
        request.json["ref"],
        request.json["sku"],
        request.json["qty"],
        eta,
        unit_of_work.SqlAlchemyUnitOfWork(),
    )

    return "OK", 201
