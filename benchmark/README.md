# Benchmark

This benchmark compares default *rpyc* with thread binding in the following scenarios

- "clients: 1  threads: 1": single client, single threaded
- "clients: 4  threads: 1": default scenario
- "clients: 1  threads: 4": single client, multithreaded
- "clients: 4  threads: 4": complex scenario

It contains

- "simple": calls a trivial server function
- "sub 1": calls a server function which calls a trivial client function
- "sub 2": calls a server function which calls a client function which calls a trivial server function
- "random wait": calls a server function which pseudo randomly waits and calls a client function which does the same

With adjusted arguments, e.g. `--validate` and `--params`,  it can be used for testing.

## *rpyc* 5.3.1

After running the benchmarks a couple of times

- "simple"
    - thread binding is very close to default (bind / default < 1.2) and sometimes a little faster
- "sub 1"
    - thread binding is again very close to default, except for the complex scenario
    - using `--background`, which adds background threads to default, it is very close in all scenarios, showing that thread switching is the reason
- "sub 2"
    - thread binding is very close in the single threaded scenarios and slower in the multithreaded scenarios
    - again, with `--background` it is very close in all scenarios
- thread binding is either very close to default or slower by a reasonable margin, considering its capabilities

Additionally

- "random wait"
    - shows that default is single threaded
    - it is possible to add background threads to make it multithreaded, but it is slower than thread binding and has the aforementioned downsides

## Example

rpyc: 5.3.1
CPU: Ryzen 5 3600
OS: Arch 6.2.2-1

### CPU frequency scaling: schedutil

#### `pipenv run python ./compare.py --params '{"n": 10000}'`

```
simple
 clients: 1  threads: 1  default  1s /  1s bind
 clients: 4  threads: 1  default  2s /  3s bind
 clients: 1  threads: 4  default  4s /  4s bind
 clients: 4  threads: 4  default  9s /  8s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.074587        0.949894
        4            0.173581        1.140634
4       1            0.303404        1.191096
        4            0.852963        0.866072

sub 1
 clients: 1  threads: 1  default  2s /  2s bind
 clients: 4  threads: 1  default  5s /  5s bind
 clients: 1  threads: 4  default  6s /  7s bind
 clients: 4  threads: 4  default 20s / 32s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.127272        1.091275
        4            0.419015        1.100755
4       1            0.561018        1.151851
        4            1.969094        1.572260

sub 2
 clients: 1  threads: 1  default  2s /  3s bind
 clients: 4  threads: 1  default  7s /  7s bind
 clients: 1  threads: 4  default  8s / 11s bind
 clients: 4  threads: 4  default 29s / 46s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.188278        1.157075
        4            0.625279        1.052619
4       1            0.782233        1.346742
        4            2.818485        1.608219
```

#### `pipenv run python ./compare.py --params '{"n": 10000}' --background`

```
simple
 clients: 1  threads: 1  default  1s /  1s bind
 clients: 4  threads: 1  default  3s /  2s bind
 clients: 1  threads: 4  default  4s /  4s bind
 clients: 4  threads: 4  default 13s /  8s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.070831        0.964905
        4            0.229539        0.828957
4       1            0.325932        1.023023
        4            1.159771        0.631015

sub 1
 clients: 1  threads: 1  default  2s /  2s bind
 clients: 4  threads: 1  default  6s /  5s bind
 clients: 1  threads: 4  default  7s /  7s bind
 clients: 4  threads: 4  default 28s / 32s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.149545        0.937174
        4            0.554039        0.819385
4       1            0.641675        1.004576
        4            2.720640        1.152712

sub 2
 clients: 1  threads: 1  default  3s /  3s bind
 clients: 4  threads: 1  default  9s /  7s bind
 clients: 1  threads: 4  default 10s / 11s bind
 clients: 4  threads: 4  default 42s / 47s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.199188        1.054444
        4            0.779640        0.827347
4       1            0.927812        1.081088
        4            4.105172        1.118338
```

#### `pipenv run python ./compare.py --benchmark '["random wait"]' --seed 4093473691 --params '{"n": 1000}'`

```
random wait
 clients: 1  threads: 1  default 13s / 13s bind
 clients: 4  threads: 1  default 13s / 13s bind
 clients: 1  threads: 4  default 39s / 15s bind
 clients: 4  threads: 4  default 40s / 15s bind

                 default [ms]  bind / default
threads clients                              
1       1           12.812047        1.003621
        4           12.873592        1.001413
4       1           38.669719        0.368574
        4           38.463241        0.374252
```

#### `pipenv run python ./compare.py --benchmark '["random wait"]' --seed 4093473691 --params '{"n": 1000}' --background`

```
random wait
 clients: 1  threads: 1  default 13s / 13s bind
 clients: 4  threads: 1  default 13s / 13s bind
 clients: 1  threads: 4  default 21s / 15s bind
 clients: 4  threads: 4  default 21s / 15s bind

                 default [ms]  bind / default
threads clients                              
1       1           12.872420        0.996917
        4           12.880944        1.000976
4       1           20.222993        0.713410
        4           20.200672        0.714998
```

### CPU frequency scaling: performance

#### `pipenv run python ./compare.py --params '{"n": 10000}'`

```
simple
 clients: 1  threads: 1  default  1s /  1s bind
 clients: 4  threads: 1  default  2s /  2s bind
 clients: 1  threads: 4  default  3s /  3s bind
 clients: 4  threads: 4  default  9s /  8s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.058286        1.175689
        4            0.180881        1.028800
4       1            0.265123        1.067466
        4            0.841793        0.880103

sub 1
 clients: 1  threads: 1  default  2s /  2s bind
 clients: 4  threads: 1  default  5s /  5s bind
 clients: 1  threads: 4  default  6s /  7s bind
 clients: 4  threads: 4  default 20s / 28s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.123630        1.071334
        4            0.418387        1.071316
4       1            0.517765        1.199802
        4            1.959090        1.398171

sub 2
 clients: 1  threads: 1  default  2s /  2s bind
 clients: 4  threads: 1  default  7s /  7s bind
 clients: 1  threads: 4  default  8s / 10s bind
 clients: 4  threads: 4  default 29s / 42s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.182612        1.088229
        4            0.616597        1.027883
4       1            0.762426        1.251591
        4            2.813652        1.459502
```

#### `pipenv run python ./compare.py --params '{"n": 10000}' --background`

```
simple
 clients: 1  threads: 1  default  1s /  1s bind
 clients: 4  threads: 1  default  3s /  3s bind
 clients: 1  threads: 4  default  4s /  3s bind
 clients: 4  threads: 4  default 12s /  8s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.069119        0.982750
        4            0.213793        0.904500
4       1            0.315168        0.894447
        4            1.133367        0.644933

sub 1
 clients: 1  threads: 1  default  2s /  2s bind
 clients: 4  threads: 1  default  6s /  5s bind
 clients: 1  threads: 4  default  7s /  7s bind
 clients: 4  threads: 4  default 26s / 29s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.122012        1.159216
        4            0.516291        0.848293
4       1            0.630175        1.034028
        4            2.459458        1.139445

sub 2
 clients: 1  threads: 1  default  3s /  2s bind
 clients: 4  threads: 1  default  8s /  7s bind
 clients: 1  threads: 4  default 10s / 10s bind
 clients: 4  threads: 4  default 38s / 42s bind

                 default [ms]  bind / default
threads clients                              
1       1            0.196843        1.010480
        4            0.744829        0.859588
4       1            0.924784        1.054886
        4            3.700325        1.107068
```