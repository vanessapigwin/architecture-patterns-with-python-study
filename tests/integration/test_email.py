import pytest
from allocation import bootstrap
from allocation.adapters import notifications
from allocation.service_layer import unit_of_work
from sqlalchemy.orm import clear_mappers


@pytest.fixture
def bus(sqlite_session_factory):
    bus = bootstrap.bootstrap(
        start_orm=True,
        uow=unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory),
        notifications=notifications.EmailNotifications(),
        publish=lambda *args: None,
    )
    yield bus
    clear_mappers()
