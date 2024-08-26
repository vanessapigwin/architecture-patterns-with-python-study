from flask import Flask, request, jsonify
from allocation.domain import commands
from allocation.adapters import orm
from allocation.service_layer import unit_of_work, messagebus
from allocation.service_layer.handlers import InvalidSku
from allocation import views
from datetime import datetime


orm.start_mappers()
app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        cmd = commands.Allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
        )
        messagebus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())
    except InvalidSku as e:
        return {"messages": str(e)}, 400

    return "OK", 202


@app.route("/add_batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    messagebus.handle(
        commands.CreateBatch(
            request.json["ref"], request.json["sku"], request.json["qty"], eta
        ),
        unit_of_work.SqlAlchemyUnitOfWork(),
    )

    return "OK", 201


@app.route("/allocations/<orderid>", methods=["GET"])
def allocations_view_endpoint(orderid):
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    result = views.allocations(orderid, uow)
    if not result:
        return "Not Found", 404
    return jsonify(result), 200
