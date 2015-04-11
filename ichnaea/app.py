from pyramid.config import Configurator
from pyramid.tweens import EXCVIEW

from ichnaea import customjson
from ichnaea.cache import configure_redis
from ichnaea.content.views import configure_content
from ichnaea.db import (
    configure_db,
    db_rw_session,
    db_ro_session,
)
from ichnaea.geoip import configure_geoip
from ichnaea.logging import configure_raven
from ichnaea.logging import configure_stats
from ichnaea.service import configure_service


def main(global_config, app_config=None, init=False,
         _db_rw=None, _db_ro=None, _geoip_db=None,
         _raven_client=None, _redis_client=None, _stats_client=None):

    if app_config is not None:
        app_settings = app_config.get_map('ichnaea')
    else:
        app_settings = {}
    config = Configurator(settings=app_settings)

    # add support for pt templates
    config.include('pyramid_chameleon')

    configure_content(config)
    configure_service(config)

    # configure outside connections
    registry = config.registry
    settings = registry.settings

    registry.db_rw = configure_db(settings.get('db_master'), _db=_db_rw)
    registry.db_ro = configure_db(settings.get('db_slave'), _db=_db_ro)

    registry.raven_client = raven_client = configure_raven(
        settings.get('sentry_dsn'), _client=_raven_client)

    registry.redis_client = configure_redis(
        settings.get('redis_url'), _client=_redis_client)

    registry.stats_client = configure_stats(
        settings.get('statsd_host'), _client=_stats_client)

    registry.geoip_db = configure_geoip(
        settings.get('geoip_db_path'), raven_client=raven_client,
        _client=_geoip_db)

    config.add_tween('ichnaea.db.db_tween_factory', under=EXCVIEW)
    config.add_tween('ichnaea.logging.log_tween_factory', under=EXCVIEW)
    config.add_request_method(db_rw_session, property=True)
    config.add_request_method(db_ro_session, property=True)

    # replace json renderer with custom json variant
    config.add_renderer('json', customjson.Renderer())

    # Should we try to initialize and establish the outbound connections?
    if init:  # pragma: no cover
        registry.db_ro.ping()
        registry.redis_client.ping()
        registry.stats_client.ping()

    return config.make_wsgi_app()
