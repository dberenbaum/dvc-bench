import os
import shutil
from subprocess import Popen

import pytest
from dulwich.porcelain import clone
from pytest_virtualenv import VirtualEnv


def pytest_generate_tests(metafunc):
    str_revs = metafunc.config.getoption("--dvc-revs")
    revs = str_revs.split(",") if str_revs else [None]
    if "dvc_rev" in metafunc.fixturenames:
        metafunc.parametrize("dvc_rev", revs, scope="session")


@pytest.fixture(scope="session")
def make_dvc_venv(tmp_path_factory):
    def _make_dvc_venv(name):
        venv_dir = tmp_path_factory.mktemp(f"dvc-venv-{name}")
        return VirtualEnv(workspace=venv_dir)

    return _make_dvc_venv


@pytest.fixture(scope="session")
def dvc_venvs():
    return {}


@pytest.fixture(scope="session")
def dvc_git_repo(tmp_path_factory, test_config):
    url = test_config.dvc_git_repo

    if os.path.isdir(url):
        return url

    tmp_path = os.fspath(tmp_path_factory.mktemp("dvc-git-repo"))
    clone(url, tmp_path)

    return tmp_path


@pytest.fixture(scope="session")
def dvc_bin(dvc_rev, dvc_venvs, make_dvc_venv, dvc_git_repo, test_config):
    if dvc_rev:
        venv = dvc_venvs.get(dvc_rev)
        if not venv:
            venv = make_dvc_venv(dvc_rev)
            venv.run("pip install -U pip")
            # NOTE: temporary workaround for
            # https://github.com/iterative/scmrepo/issues/73
            venv.run("pip install dulwich==0.20.37")
            venv.run(
                f"pip install git+file://{dvc_git_repo}@{dvc_rev} "
                "--only-binary=dulwich"
            )
            dvc_venvs[dvc_rev] = venv
        dvc_bin = venv.virtualenv / "bin" / "dvc"
    else:
        dvc_bin = test_config.dvc_bin

    def _dvc_bin(*args):
        proc = Popen([dvc_bin, *args])
        proc.communicate()
        assert proc.returncode == 0

    return _dvc_bin


@pytest.fixture(scope="function")
def make_bench(request):
    def _make_bench(name):
        import pytest_benchmark.plugin

        # hack from https://github.com/ionelmc/pytest-benchmark/issues/166
        bench = pytest_benchmark.plugin.benchmark.__pytest_wrapped__.obj(
            request
        )

        suffix = f"-{name}"

        def add_suffix(_name):
            start, sep, end = _name.partition("[")
            return start + suffix + sep + end

        bench.name = add_suffix(bench.name)
        bench.fullname = add_suffix(bench.fullname)

        return bench

    return _make_bench


@pytest.fixture(scope="function")
def bench_dvc(dvc_bin, make_bench):
    def _bench_dvc(*args, **kwargs):
        name = kwargs.pop("name", None)
        name = f"-{name}" if name else ""
        bench = make_bench(args[0] + name)
        return bench.pedantic(dvc_bin, args=args, **kwargs)

    return _bench_dvc


@pytest.fixture
def make_dataset(request, test_config, tmp_dir, pytestconfig):
    def _make_dataset(
        dvcfile=False, files=True, cache=False, commit=False, remote=False
    ):
        from dvc.repo import Repo
        from dvc.exceptions import CheckoutError, DownloadError

        path = tmp_dir / "dataset"
        root = pytestconfig.rootpath
        src = root / "data" / test_config.size / "dataset"
        src_dvc = src.with_suffix(".dvc")

        dvc = Repo(root)

        while True:
            try:
                dvc.pull([str(src_dvc)])
                break
            except (CheckoutError, DownloadError):
                pass

        if files:
            shutil.copytree(src, path)
        if dvcfile:
            shutil.copy(src.with_suffix(".dvc"), path.with_suffix(".dvc"))
        if cache:
            shutil.copytree(
                root / ".dvc" / "cache", tmp_dir / ".dvc" / "cache"
            )
        if remote:
            assert dvcfile
            assert not cache
            assert tmp_dir.dvc
            # FIXME temporary hack, we should try to push from home repo
            # directly to this remote instead
            shutil.copytree(
                root / ".dvc" / "cache", tmp_dir / ".dvc" / "cache"
            )
            tmp_dir.dvc.push(
                [str(path.with_suffix(".dvc").relative_to(tmp_dir))]
            )
            shutil.rmtree(tmp_dir / ".dvc" / "cache")
        if commit:
            assert dvcfile
            assert tmp_dir.scm
            tmp_dir.scm.add(
                [str(path.with_suffix(".dvc").relative_to(tmp_dir))]
            )
            tmp_dir.scm.commit("add dataset")
        return path

    return _make_dataset


@pytest.fixture
def dataset(make_dataset):
    return make_dataset(dvcfile=False, files=True, cache=False)


@pytest.fixture
def remote_dataset(test_config):
    pytest.skip("fixme")
