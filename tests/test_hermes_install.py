from pathlib import Path

from whoop_local_sync.hermes_install import install_hermes_plugin


def test_install_hermes_plugin_copies_bundled_plugin_and_patches_config(tmp_path):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / "config.yaml").write_text(
        "plugins:\n  enabled:\n    - existing-plugin\nplatform_toolsets:\n  whatsapp:\n    - web\n",
        encoding="utf-8",
    )

    result = install_hermes_plugin(hermes_home=hermes_home, enable=True, platforms=["whatsapp", "cli"])

    plugin_dir = hermes_home / "plugins" / "whoop-local-sync"
    assert result["ok"] is True
    assert (plugin_dir / "plugin.yaml").exists()
    assert (plugin_dir / "__init__.py").exists()
    config = (hermes_home / "config.yaml").read_text(encoding="utf-8")
    assert "whoop-local-sync" in config
    assert "whatsapp:" in config
    assert "cli:" in config
    assert "whoop" in config
    assert list(hermes_home.glob("config.yaml.bak-whoop-local-sync-*"))


def test_install_hermes_plugin_copy_only_does_not_patch_config(tmp_path):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / "config.yaml").write_text("plugins:\n  enabled: []\n", encoding="utf-8")

    install_hermes_plugin(hermes_home=hermes_home, enable=False, platforms=["whatsapp"])

    assert (hermes_home / "plugins" / "whoop-local-sync" / "plugin.yaml").exists()
    config = (hermes_home / "config.yaml").read_text(encoding="utf-8")
    assert "whoop-local-sync" not in config
    assert not list(hermes_home.glob("config.yaml.bak-whoop-local-sync-*"))
