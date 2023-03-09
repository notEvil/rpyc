import numpy
import rpyc
import rpyc.utils.factory as ru_factory
import argparse
import base64
import json
import math
import multiprocessing
import multiprocessing.managers as m_managers
import pathlib
import pickle
import random
import subprocess
import sys
import tempfile
import threading
import time


PORT = 44251  # multiprocessing


parser = argparse.ArgumentParser()

_ = "random wait"
parser.add_argument(
    "benchmark", choices=["simple", "sub 1", "sub 2", _], help="benchmark to perform"
)
parser.add_argument("clients", help="number of clients")
parser.add_argument("threads", help="number of threads per client")
parser.add_argument(
    "--validate",
    default=False,
    action="store_true",
    help="validate communication. Useful for testing",
)
parser.add_argument("--seed", help='"random wait": RNG seed. required!')
parser.add_argument(
    "--params",
    default="{}",
    help='parameters JSON. iterations "n": 1000, P(delay) "delay_p": 1, max delay "delay_s": 0.01 s, P(sub request) "sub_p": 0.5, max request depth "max_depth": 2',
)
parser.add_argument(
    "--socket",
    default="/tmp/.rpyc_benchmark.socket",
    help="path used for communication over UNIX socket",
)
parser.add_argument("--path", help="path used to dump times")
_ = "--background"
parser.add_argument(_, default="0", help="number of additional background threads")
parser.add_argument("--part", help="internal")
parser.add_argument("--authkey", help="internal")

arguments = parser.parse_args()
arguments.clients = int(arguments.clients)
arguments.threads = int(arguments.threads)

if arguments.benchmark == "random wait":
    assert arguments.seed is not None

arguments.params = json.loads(arguments.params)
arguments.socket = pathlib.Path(arguments.socket)

if arguments.path is not None:
    arguments.path = pathlib.Path(arguments.path)

arguments.background = int(arguments.background)


_ = dict(n=int(1e3), delay_p=1, delay_s=0.01, sub_p=0.5, max_depth=2)
params = _ | arguments.params


class ServerService(rpyc.Service):
    def __init__(self):
        super().__init__()

        if arguments.validate:
            self.exposed_simple = self._simple_validated
            self.exposed_sub_1 = self._sub_1_validated
            self.exposed_sub_2 = self._sub_2_validated

        else:
            self.exposed_simple = self._simple
            self.exposed_sub_1 = self._sub_1
            self.exposed_sub_2 = self._sub_2

        self._remote_sub_1 = None
        self._remote_sub_1_validated = None
        self._remote_sub_2 = None
        self._remote_sub_2_validated = None
        self._remote_random_wait = None

        self._randoms = {}  # {thread index~int: RNG~random.Random}

    def on_connect(self, connection):
        super().on_connect(connection)

        for _ in range(arguments.background):
            threading.Thread(target=connection.serve_all).start()

        remote_root = connection.root
        self._remote_sub_1 = remote_root.sub_1
        self._remote_sub_1_validated = remote_root.sub_1_validated
        self._remote_sub_2 = remote_root.sub_2
        self._remote_sub_2_validated = remote_root.sub_2_validated
        self._remote_random_wait = remote_root.random_wait

    def exposed_ready(self):
        return self._remote_random_wait is not None

    # simple

    def _simple(self):
        pass

    def _simple_validated(self, argument):
        return argument

    # sub 1

    def _sub_1(self):
        self._remote_sub_1()

    def _sub_1_validated(self, argument):
        _validate(self._remote_sub_1_validated, random)
        return argument

    # sub 2

    def _sub_2(self):
        self._remote_sub_2()

    def exposed__sub_2(self):
        pass

    def _sub_2_validated(self, argument):
        _validate(self._remote_sub_2_validated, random)
        return argument

    def exposed__sub_2_validated(self, argument):
        return argument

    # random wait

    def exposed_prepare_random_wait(self, seed, thread_index):
        self._randoms[thread_index] = random.Random(seed)

    def exposed_random_wait(self, argument, depth, thread_index):
        random = self._randoms[thread_index]

        _wait(random)

        if _sub(depth, random):
            _validate(self._remote_random_wait, random, args=(depth + 1, thread_index))
            _wait(random)

        return argument


client_randoms = {}  # {thread index~int: RNG~random.Random}


class ClientService(rpyc.Service):
    def __init__(self):
        super().__init__()

        self._remote__sub_2 = None
        self._remote__sub_2_validated = None
        self._remote_random_wait = None

    def on_connect(self, connection):
        remote_root = connection.root
        self._remote__sub_2 = remote_root._sub_2
        self._remote__sub_2_validated = remote_root._sub_2_validated
        self._remote_random_wait = remote_root.random_wait

    # sub 1

    def exposed_sub_1(self):
        pass

    def exposed_sub_1_validated(self, argument):
        return argument

    # sub 2

    def exposed_sub_2(self):
        self._remote__sub_2()

    def exposed_sub_2_validated(self, argument):
        _validate(self._remote__sub_2_validated, random)
        return argument

    # random wait

    def exposed_random_wait(self, argument, depth, thread_index):
        random = client_randoms[thread_index]

        _wait(random)

        if _sub(depth, random):
            _validate(self._remote_random_wait, random, args=(depth + 1, thread_index))
            _wait(random)

        return argument


def _wait(random):
    if random.random() < params["delay_p"]:
        time.sleep(random.uniform(0, params["delay_s"]))


def _sub(depth, random):
    return depth < params["max_depth"] and random.random() < params["sub_p"]


def thread_target(thread_index, rpyc_client, times, barrier):
    remote_root = rpyc_client.root

    _ = {
        "simple": "simple",
        "sub 1": "sub_1",
        "sub 2": "sub_2",
        "random wait": "random_wait",
    }[arguments.benchmark]
    function = getattr(remote_root, _)

    if arguments.validate:
        remote_function = function

        def function():
            _validate(remote_function, random)

    if arguments.benchmark == "random wait":
        seed = int(arguments.seed)

        server_seed = seed + thread_index
        remote_root.prepare_random_wait(server_seed, thread_index)

        client_seed = seed + 1000 + thread_index
        client_randoms[thread_index] = random.Random(client_seed)

        remote_function = function

        def function():
            _ = client_randoms[thread_index]
            _validate(remote_function, _, args=(0, thread_index))

    while not remote_root.ready():
        time.sleep(0.1)

    barrier.wait()  # start in sync with other threads

    for index in range(params["n"]):
        start_ns = time.perf_counter_ns()
        function()
        times[index] = time.perf_counter_ns() - start_ns


def _validate(function, random, args=()):
    expected = random.random()
    assert function(expected, *args) == expected


def get_statistics(times):
    s0 = 0
    s1 = 0
    s2 = 0

    for times in times:
        s0 += len(times)
        s1 += sum(int(time) for time in times)
        s2 += sum(int(time) ** 2 for time in times)

    avg = s1 / s0
    try:
        std = math.sqrt(s2 / s0 - avg**2)

    except Exception as exception:
        raise Exception(str(dict(s0=s0, s1=s1, s2=s2, avg=avg))) from exception

    ns = int(1e9)
    _ = "{:7.3f} s  avg: {:7.3f} ms  std: {:7.3f} ms"
    return _.format(s1 / ns, avg / ns * 1_000, std / ns * 1_000)


match arguments.part:
    case None:
        assert not arguments.socket.exists()
        server_process = None
        paths = []

        try:
            argument_list = [
                sys.executable,
                __file__,
                arguments.benchmark,
                str(arguments.clients),
                str(arguments.threads),
                "--part",
                "server",
                "--params",
                json.dumps(arguments.params),
                "--background",
                str(arguments.background),
            ]
            if arguments.validate:
                argument_list.append("--validate")
            if arguments.seed is not None:
                argument_list.extend(["--seed", arguments.seed])
            server_process = subprocess.Popen(argument_list)

            while not arguments.socket.exists():
                time.sleep(0.1)

            # barrier
            _ = arguments.clients * arguments.threads
            start_barrier = multiprocessing.Barrier(_)
            stop_barrier = multiprocessing.Barrier(arguments.clients)

            manager = m_managers.BaseManager(address=("", PORT))
            manager.register("get_start_barrier", lambda: start_barrier)
            manager.register("get_stop_barrier", lambda: stop_barrier)

            _ = threading.Thread(target=manager.get_server().serve_forever, daemon=True)
            _.start()

            _ = base64.b64encode(multiprocessing.current_process().authkey)
            authkey = _.decode()
            #

            client_processes = []
            for _ in range(arguments.clients):
                path = pathlib.Path(tempfile.mkstemp()[1])
                paths.append(path)

                argument_list = [
                    sys.executable,
                    __file__,
                    arguments.benchmark,
                    str(arguments.clients),
                    str(arguments.threads),
                    "--part",
                    "client",
                    "--authkey",
                    authkey,
                    "--path",
                    str(path),
                    "--params",
                    json.dumps(arguments.params),
                ]
                if arguments.validate:
                    argument_list.append("--validate")
                if arguments.seed is not None:
                    argument_list.extend(["--seed", arguments.seed])
                client_processes.append(subprocess.Popen(argument_list))

            for client_process in client_processes:
                assert client_process.wait() == 0

            client_times = {}

            for client_index, path in enumerate(paths):
                print("client", client_index)

                with open(path, "rb") as file:
                    thread_times = pickle.load(file)

                client_times[client_index] = thread_times

                for thread_index, times in thread_times.items():
                    _ = get_statistics([times])
                    print(" thread {:2} :  {}".format(thread_index, _))

                print(" total     :  {}".format(get_statistics(thread_times.values())))

            if arguments.path is not None:
                with open(arguments.path, "wb") as file:
                    pickle.dump(client_times, file)

            print()
            _ = [
                times
                for thread_times in client_times.values()
                for times in thread_times.values()
            ]
            print("total      :  {}".format(get_statistics(_)))

        finally:
            if server_process is not None:
                server_process.terminate()
                server_process.wait()

            for path in paths:
                path.unlink()

            if arguments.socket.exists():
                arguments.socket.unlink()

    case "server":
        rpyc.ThreadedServer(ServerService, socket_path=str(arguments.socket)).start()

    case "client":
        _ = str(arguments.socket)
        rpyc_client = ru_factory.unix_connect(_, service=ClientService)

        threads = []
        thread_times = {}

        # barrier
        manager = m_managers.BaseManager(
            address=("127.0.0.1", PORT),
            authkey=base64.b64decode(arguments.authkey.encode()),
        )
        manager.register("get_start_barrier")
        manager.register("get_stop_barrier")

        manager.connect()
        start_barrier = manager.get_start_barrier()
        stop_barrier = manager.get_stop_barrier()
        #

        for thread_index in range(arguments.threads):
            times = numpy.zeros(dtype=numpy.int64, shape=(params["n"],))
            thread_times[thread_index] = times

            thread = threading.Thread(
                target=thread_target,
                args=(thread_index, rpyc_client, times, start_barrier),
            )
            threads.append(thread)

            thread.start()

        for thread in threads:
            thread.join()

        stop_barrier.wait()

        with open(arguments.path, "wb") as file:
            pickle.dump(thread_times, file)
