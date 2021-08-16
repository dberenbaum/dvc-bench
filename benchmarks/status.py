import os
import shutil

from benchmarks.base import DATA_TEMPLATES, BaseBench, BaseRemoteBench
from dvc.ignore import DvcIgnore


class DVCStatusBench(BaseBench):
    repeat = 1
    number = 100

    def setup(self):
        super().setup()
        self.init_git()
        self.init_dvc()
        data_path = DATA_TEMPLATES["large"]
        os.makedirs(
            os.path.join(self.test_directory.name, "data"), exist_ok=True
        )
        self.dvc("add", "data")
        shutil.copytree(data_path, os.path.join("data", "data"))
        # calculating md5
        self.dvc("status", return_code=1)

    def time_status(self):
        self.dvc("status", return_code=1, proc=True)


class StatusCloudBench(BaseRemoteBench):
    def setup(self, remote):
        super().setup(remote)

        self.gen("data", "medium")
        self.dvc("add", "data")
        self.dvc("push", "data")

    def time_status_c(self, _):
        self.dvc("status", "data", "-c", proc=True)


class StatusCloudMissingFilesBench(StatusCloudBench):
    def setup(self, remote):
        super().setup(remote)

        self.gen("data", "large", exist_ok=True)
        self.dvc("add", "data")

    def time_status_c_with_missing(self, _):
        self.dvc("status", "data", "-c", proc=True)


class DVCIgnoreBench(DVCStatusBench):
    @staticmethod
    def add_ignore_rules(path, number):
        with open(os.path.join(path, DvcIgnore.DVCIGNORE_FILE), "w",) as f_w:
            for i in range(number):
                f_w.write("{}\n".format(i))

    def setup(self):
        super().setup()
        self.add_ignore_rules(self.test_directory.name, 30)
