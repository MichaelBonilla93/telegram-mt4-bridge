import textwrap

from src.config import load_config
from src.models import Account


def test_loads_accounts_and_globals(tmp_path):
    yaml_text = textwrap.dedent("""
        trading_enabled: true
        max_open_trades: 9
        tolerance_pips: 20
        accounts:
          - name: DEMO1
            mailbox_path: /tmp/mt4_demo1
            lot: 0.01
            symbol_suffix: ""
            active: true
          - name: DEMO2
            mailbox_path: /tmp/mt4_demo2
            lot: 0.02
            symbol_suffix: ".r"
            active: false
    """)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_text)

    cfg = load_config(str(cfg_file))

    assert cfg.trading_enabled is True
    assert cfg.max_open_trades == 9
    assert cfg.tolerance_pips == 20
    assert len(cfg.accounts) == 2
    assert isinstance(cfg.accounts[0], Account)
    assert cfg.accounts[0].name == "DEMO1"
    assert cfg.accounts[1].symbol_suffix == ".r"


def test_active_accounts_filters_inactive(tmp_path):
    yaml_text = textwrap.dedent("""
        trading_enabled: true
        max_open_trades: 9
        tolerance_pips: 20
        accounts:
          - name: A
            mailbox_path: /tmp/a
            lot: 0.01
            active: true
          - name: B
            mailbox_path: /tmp/b
            lot: 0.01
            active: false
    """)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_text)

    cfg = load_config(str(cfg_file))
    active = cfg.active_accounts()
    assert [a.name for a in active] == ["A"]
