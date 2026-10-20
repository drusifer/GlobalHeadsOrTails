try:
    from tests.sticker_pack_fixtures import select_fixture_pack
except ImportError:
    from game_server.tests.sticker_pack_fixtures import select_fixture_pack

__all__ = ["select_fixture_pack"]
