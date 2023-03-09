import numpy
import pandas
import argparse
import json
import math
import os
import pathlib
import pickle
import subprocess
import sys
import tempfile
import time


PATH = pathlib.Path(__file__).parent


parser = argparse.ArgumentParser()

parser.add_argument(
    "--benchmarks", default='["simple", "sub 1", "sub 2"]', help="benchmarks to perform"
)
parser.add_argument("--clients", default="4", help="number of clients")
parser.add_argument("--threads", default="4", help="number of threads per client")
parser.add_argument("--params", default="{}", help="parameters JSON")
parser.add_argument("--validate", default=False, action="store_true")
parser.add_argument("--seed", help="same as benchmark.py --seed")
parser.add_argument(
    "--background",
    default=False,
    action="store_true",
    help="add additional background threads to default",
)

arguments = parser.parse_args()

arguments.benchmarks = json.loads(arguments.benchmarks)
arguments.clients = int(arguments.clients)
arguments.threads = int(arguments.threads)


def get_statistics(times):
    s0 = 0
    s1 = 0
    s2 = 0

    for times in times:
        s0 += len(times)
        s1 += sum(int(time) for time in times)
        s2 += sum(int(time) ** 2 for time in times)

    avg = s1 / s0
    std = math.sqrt(s2 / s0 - avg**2)
    return (avg, std)


for benchmark in arguments.benchmarks:
    print(benchmark)
    rows = []

    for thread_n in [1, arguments.threads]:
        for client_n in [1, arguments.clients]:
            _ = " clients: {}  threads: {}  default ".format(client_n, thread_n)
            print(_, end="")
            sys.stdout.flush()

            with tempfile.NamedTemporaryFile() as file:
                argument_list = [
                    sys.executable,
                    PATH / "benchmark.py",
                    benchmark,
                    str(client_n),
                    str(thread_n),
                    "--params",
                    arguments.params,
                    "--path",
                    file.name,
                ]
                if arguments.validate:
                    argument_list.append("--validate")
                if arguments.seed is not None:
                    argument_list.extend(["--seed", arguments.seed])
                if arguments.background:
                    argument_list.extend(["--background", str(thread_n)])

                start_time = time.monotonic()
                _ = subprocess.Popen(argument_list, stdout=subprocess.DEVNULL).wait()
                assert _ == 0
                print("{:2}s / ".format(int(time.monotonic() - start_time)), end="")
                sys.stdout.flush()

                with open(file.name, "rb") as file:
                    default_times = pickle.load(file)

            with tempfile.NamedTemporaryFile() as file:
                argument_list = [
                    sys.executable,
                    PATH / "benchmark.py",
                    benchmark,
                    str(client_n),
                    str(thread_n),
                    "--params",
                    arguments.params,
                    "--path",
                    file.name,
                ]
                if arguments.validate:
                    argument_list.append("--validate")
                if arguments.seed is not None:
                    argument_list.extend(["--seed", arguments.seed])

                start_time = time.monotonic()
                _ = subprocess.Popen(
                    argument_list,
                    env=os.environ | dict(RPYC_BIND_THREADS="true"),
                    stdout=subprocess.DEVNULL,
                ).wait()
                assert _ == 0
                print("{:2}s bind".format(int(time.monotonic() - start_time)))

                with open(file.name, "rb") as file:
                    bind_times = pickle.load(file)

            _ = default_times.values()
            default_avg, _ = get_statistics(
                [times for thread_times in _ for times in thread_times.values()]
            )

            _ = bind_times.values()
            bind_avg, _ = get_statistics(
                [times for thread_times in _ for times in thread_times.values()]
            )

            ns = int(1e9)
            _ = {
                "threads": thread_n,
                "clients": client_n,
                "default [ms]": default_avg / ns * 1_000,
                "bind / default": bind_avg / default_avg,
            }
            rows.append(_)

    print()
    print(pandas.DataFrame(rows).set_index(["threads", "clients"]).to_string())
    print()
