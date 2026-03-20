from customer_support_agent import __version__


def test_version(pyproject_version):
    """Verify package version matches pyproject.toml"""
    assert __version__ == pyproject_version
