
from argparse import ArgumentParser
from functools import partial
from importlib import import_module
from itertools import product

import timeit

from threading import Thread


def watcher_thread_fn(signal_watcher, signals_to_wait):
	for _ in range(signals_to_wait):
		signal_watcher.wait()
		signal_watcher.next()


def source_thread_fn(signal_source, emits, signals):
	for _ in range(emits):
		for s in signals:
			signal_source.send_signal(s, payload=1)


def timer_fn(*threads):
	for t in threads:
		t.start()

	for i in range(len(threads) - 1, -1, -1):
		threads[i].join()


def main():
	parser = ArgumentParser()
	parser.add_argument('--impl-module', metavar='module_name', type=str, required=True)
	parser.add_argument('--test-class', metavar='class_name', type=str, default='Source')
	parser.add_argument('--sources', metavar='sources_count', type=int, default=10)
	parser.add_argument('--signals', metavar='signals_count', type=int, default=10)
	parser.add_argument('--emits', metavar='emits_count', type=int, default=1000)

	args = parser.parse_args()
	print(f'Running test with the "{args.impl_module}" module')
	m = import_module(args.impl_module)

	source_threads = args.sources
	source_signals = args.signals
	emits = args.emits
	source_cls = getattr(m, args.test_class)
	#source_cls = getattr(m, 'QueueSource')

	signals = tuple(f'signal_{i}' for i in range(source_signals))
	sources = tuple(source_cls.new_source(*signals) for _ in range(source_threads))
	watchers = tuple(source.watch(signal) for signal, source in product(signals, sources))

	timeit_globals = globals()
	timeit_globals.update(locals())

	setup_stmt = 'watcher_threads = tuple(Thread(target=partial(watcher_thread_fn, w, emits)) for w in watchers);'
	setup_stmt += 'source_threads = tuple(Thread(target=partial(source_thread_fn, s, emits, signals)) for s in sources)'
	timer_stmt = 'timer_fn(*watcher_threads, *source_threads)'

	timer = timeit.Timer(timer_stmt, setup_stmt, globals=timeit_globals)
	for time_result in timer.repeat(10, 1):
		print(f'\t- {time_result}')


if __name__ == '__main__':
	main()
