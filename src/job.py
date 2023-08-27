import util

jobs_dict = {job["id"]: job for job in util.load_json("data/jobs")}


class Job:
    def __init__(self, id):
        job = jobs_dict[id]
        self.__dict__.update(job)

    @classmethod
    def all(cls):
        return [Job(job_id) for job_id in jobs_dict.keys()]

    @classmethod
    def get_idx(cls, id):
        return list(jobs_dict.keys()).index(id)
