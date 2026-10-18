import pytest

from cuaas.allowlist import ALLOWED
from cuaas.runner import check_argv


@pytest.mark.parametrize("cmd", sorted(ALLOWED))
def test_allowed_names_pass_check_argv(cmd):
    check_argv([cmd])


@pytest.mark.parametrize(
    "cmd", ["env", "nice", "nohup", "timeout", "stdbuf", "runcon", "chroot", "sort"]
)
def test_nothing_that_runs_other_commands(cmd):
    assert cmd not in ALLOWED
