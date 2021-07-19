
#include <unistd.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <math.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>
#include <sys/mman.h>

#include "common.h"

#define LIBRARY_ASSERT_STM(stmt, msg, ...) \
    if (stmt){ \
        fprintf(stderr, msg, ##__VA_ARGS__); \
        fprintf(stderr, "\n"); \
        _dlerror = dlerror(); \
        if (_dlerror != NULL){ \
            fprintf(stderr, "%s\n", _dlerror); \
        } \
        abort(); \
    }

const char* _dlerror = NULL;
void* signals_library = NULL;
const char* source_new_fn_name = "source";
const char* source_emit_fn_name = "emit_signal";
const char* watcher_new_fn_name = "watcher";
const char* watcher_wait_fn_name = "wait_signal";

struct thread_fn_emit_args {
    void* source;
    char** signals;
    int signals_count;
    int emits_count;
    void* payload;

    int (*emit_fn) (void*, const char*, void*);
};

struct thread_fn_wait_args {
    void* watcher;
    int emits_count;

    int (*wait_fn) (void*);
};

void load_library(const char* library_path){
    // NOTE: is not thread safe!
    signals_library = dlopen(library_path, RTLD_NOW | RTLD_LOCAL | RTLD_NODELETE);
    LIBRARY_ASSERT_STM((signals_library == NULL), "Unable to load the \"%s\" library", library_path)
    printf("The \"%s\" library is imported successfully\n", library_path);
}

void* library_function(const char* function_name){
    // NOTE: is not thread safe!
    ASSERT_STM((signals_library == NULL), "Library must be loaded before loading function \"%s\"", function_name)
    void* result = dlsym(signals_library, function_name);
    LIBRARY_ASSERT_STM((result == NULL), "Unable to load the \"%s\" function from a library", function_name)
    return result;
}

char** generate_signals(int signals_count){
    char** signals = NULL;
    const char* signal_prefix = "signal_";
    size_t signal_prefix_length = strlen(signal_prefix);
    long signal_number_buffer_size = -1;
    char* signal_name = NULL;

    signals = malloc(sizeof(char*) * signals_count);
    ASSERT_STM((signals == NULL), "Unable to allocate memory for %i signals", signals_count)

    for (int i = 1; i <= signals_count; i++){
        signal_number_buffer_size = (floor(log10(i))) + 2;  // extra-one for \0 symbol

        signal_name = malloc(signal_prefix_length + signal_number_buffer_size);
        ASSERT_STM((signal_name == NULL), "Unable to allocate memory for %i signal name", i)

        strncpy(signal_name, signal_prefix, signal_prefix_length);
        snprintf(signal_name + signal_prefix_length, signal_number_buffer_size, "%i", i);
        signals[i - 1] = signal_name;
    }

    printf("Signals were generated\n");
    return signals;
}

void** generate_sources(
  int sources_count,
  char** signals,
  int signals_count
){
    void** sources = NULL;
    void* (*new_source_fn) (char**, int) = library_function(source_new_fn_name);

    sources = malloc(sizeof(void*) * sources_count);
    ASSERT_STM((sources == NULL), "Unable to allocate memory for %i sources", sources_count)

    for (int i = 0; i < sources_count; i++){
         sources[i] = new_source_fn(signals, signals_count);
         ASSERT_STM((sources[i] == NULL), "Unable to generate \"%i\" source", i)
    }
    printf("Source objects was generated\n");
    return sources;
}

void** generate_watchers(
    char** signals,
    int signals_count,
    void** sources,
    int sources_count
){
    void** watchers = NULL;
    int watcher_index = -1;
    void* (*watch_source_fn) (void*, const char*) = library_function(watcher_new_fn_name);

    watchers = malloc(sizeof(void*) * signals_count * sources_count);
    ASSERT_STM((watchers == NULL), "Unable to allocate memory for watchers")
    for (int i = 0; i < sources_count; i++){
        for (int j = 0; j < signals_count; j++){
            watcher_index = (i * signals_count) + j;
            watchers[watcher_index] = watch_source_fn(sources[i], signals[j]);
            ASSERT_STM((watchers[watcher_index] == NULL), "Unable to generate \"%i\" watcher", watcher_index)
        }
    }

    printf("Watch objects was generated\n");
    return watchers;
}

void** generate_thread_fn_wait_args(
    void** watchers,
    int watchers_count,
    int emits_count
){
    struct thread_fn_wait_args* next_args = NULL;
    void** thread_args = malloc(sizeof(void*) * watchers_count);
    ASSERT_STM((thread_args == NULL), "Unable to allocate memory for thread (watchers) arguments")

    for (int i = 0; i < watchers_count; i++) {
        next_args = malloc(sizeof(struct thread_fn_wait_args));
        ASSERT_STM((next_args == NULL), "Unable to allocate memory for \"%i\" thread (watchers) argument", i)
        next_args->watcher = watchers[i];
        next_args->emits_count = emits_count;
        next_args->wait_fn = library_function(watcher_wait_fn_name);

        thread_args[i] = next_args;
    }

    return thread_args;
}

void** generate_thread_fn_emit_args(
    void** sources,
    int sources_count,
    char** signals,
    int signals_count,
    int emits_count,
    void* payload
) {

    struct thread_fn_emit_args* next_args = NULL;
    void** thread_args = malloc(sizeof(void*) * sources_count);
    ASSERT_STM((thread_args == NULL), "Unable to allocate memory for thread (source) arguments")

    for (int i = 0; i < sources_count; i++) {
        next_args = malloc(sizeof(struct thread_fn_emit_args));
        ASSERT_STM((next_args == NULL), "Unable to allocate memory for \"%i\" thread (source) argument", i)
        next_args->source = sources[i];
        next_args->signals = signals;
        next_args->signals_count = signals_count;
        next_args->emits_count = emits_count;
        next_args->payload = payload;
        next_args->emit_fn = library_function(source_emit_fn_name);

        thread_args[i] = next_args;
    }

    return thread_args;
};

pthread_t* start_threads(
    int threads_count,
    void* (*thread_fn)(void*),
    void** fn_arguments
) {
    int op_status = -1;
    pthread_t* thread_pool = malloc(sizeof(pthread_t) * threads_count);

    ASSERT_STM((thread_pool == NULL), "Unable to allocate memory for threads")

    for (int i = 0; i < threads_count; i++) {
        op_status = pthread_create(&(thread_pool[i]), NULL, thread_fn, fn_arguments[i]);
        ASSERT_STM((op_status != 0), "Unable to create a thread!")
    }

    printf("Thread pool was generated\n");
    return thread_pool;
}

void* thread_fn_emit(struct thread_fn_emit_args* args){
    for (int i = 0; i < args->emits_count; i++) {
        for (int j = 0; j < args->signals_count; j++) {
            ASSERT_STM((args->emit_fn(args->source, args->signals[j], args->payload) != 0), "Unable to send a signal")
        }
    }

    return NULL;
}

void* thread_fn_watch(struct thread_fn_wait_args* args) {

    for (int i=0; i < args->emits_count; i++){
        ASSERT_STM((args->wait_fn(args->watcher) != 0), "Unable to receive a signal")
    }
    return NULL;
}

struct timespec start_test(int signals_count, int sources_count, int emits_count){ // should be run in a separate process

    char** signals = NULL;
    void** sources = NULL;
    void** watchers = NULL;

    void** wait_args = NULL;
    int* payload = NULL;
    void** send_args = NULL;
    pthread_t* watcher_threads = NULL;
    pthread_t* senders_threads = NULL;

    struct timespec test_start, test_end, test_result;

    signals = generate_signals(signals_count);
    sources = generate_sources(sources_count, signals, signals_count);
    watchers = generate_watchers(signals, signals_count, sources, sources_count);

    wait_args = generate_thread_fn_wait_args(watchers, signals_count * sources_count, emits_count);
    payload = malloc(sizeof(int));
    ASSERT_STM((payload == NULL), "Unable to allocate memory for signal payload")
    (*payload) = 1;
    send_args = generate_thread_fn_emit_args(sources, sources_count, signals, signals_count, emits_count, payload);

    clock_gettime(CLOCK_REALTIME, &test_start);

    watcher_threads = start_threads(signals_count * sources_count, (void* (*)(void*)) thread_fn_watch, wait_args);
    senders_threads = start_threads(sources_count, (void* (*)(void*)) thread_fn_emit, send_args);

    for (int i = 0; i < sources_count; i++){
        pthread_join(senders_threads[i], NULL);
    }

    for (int i = 0; i < (signals_count * sources_count); i++){
        pthread_join(watcher_threads[i], NULL);
    }

    clock_gettime(CLOCK_REALTIME, &test_end);

    test_result.tv_sec = (test_end.tv_sec - test_start.tv_sec);
    test_result.tv_nsec = (test_end.tv_nsec - test_start.tv_nsec);
    if (test_result.tv_nsec < 0) {
       test_result.tv_nsec = 1000000000 - test_result.tv_nsec;
       test_result.tv_sec -= 1;
    }

    printf(
        "Test is finished. Test took %li seconds %li milliseconds\n",
        test_result.tv_sec,
        (test_result.tv_nsec / 1000000)
    );
    return test_result;
}

int main(int argc, char** argv){
    int c = 0;
    char* library_path = NULL;
    int signals_count = 10;
    int sources_count = 10;
    int emits_count = 1000;
    pid_t test_run_pid;
    int test_run_status = -1;
    const int test_runs_count = 10;
    struct timespec test_single_result, *test_single_result_ptr;
    void* test_results = mmap(
        NULL,
        sizeof(struct timespec) * test_runs_count,
        PROT_READ | PROT_WRITE,
        MAP_SHARED | MAP_ANONYMOUS,
        -1,
        0
    );
    ASSERT_STM((test_results == MAP_FAILED), "Unable to allocate memory for results")

    while ((c = getopt (argc, argv, "i:s:t:e:")) != -1){
        switch (c) {
            case 'i':
                library_path = optarg;
                break;
            case 's':
                signals_count = atoi(optarg);
                break;
            case 't':
                sources_count = atoi(optarg);
                break;
            case 'e':
                emits_count = atoi(optarg);
                break;
            default:
                fprintf(stderr, "Unknown argument spotted!\n");
                abort();
        }
    }

    ASSERT_STM((library_path == NULL), "Unable to find a library to use. \"-i\" argument must be used!")
    ASSERT_STM((signals_count <= 0), "Signals count can not be non-positive: %i!", signals_count)
    ASSERT_STM((sources_count <= 0), "Sources count can not be non-positive: %i!", sources_count)
    ASSERT_STM((emits_count <= 0), "Emits count can not be non-positive: %i!", emits_count)

    printf("The \"%s\" library is going to be imported\n", library_path);
    printf("Each signal source (thread) will have %i signals\n", signals_count);
    printf("There will be %i sources (threads)\n", sources_count);
    printf("There will be %i emits of each signal\n", emits_count);
    printf("\n");

    load_library(library_path);

    for (int i = 0; i < test_runs_count; i++){
        printf("====================\n");
        printf("Running %i iteration\n", i);
        printf("====================\n");

        test_run_pid = fork();
        ASSERT_STM((test_run_pid == -1), "Unable to fork a test run")

        if (test_run_pid == 0) {
            test_single_result = start_test(signals_count, sources_count, emits_count);
            memcpy(test_results + (sizeof(struct timespec) * i), &test_single_result, sizeof(struct timespec));
            exit(0);
        }
        else {
             test_run_status = -1;
             waitpid(test_run_pid, &test_run_status, 0);
             ASSERT_STM((test_run_status != 0), "Non-zero status code of the test: %i!", test_run_status)
        }
    }

    printf("\n");
    printf("=============\n");
    printf("Tests results\n");
    printf("=============\n");

    for (int i = 0; i < test_runs_count; i++) {
        test_single_result_ptr = test_results + (sizeof(struct timespec) * i);
        printf(
            "Test %i took %li seconds %li milliseconds\n",
            i,
            test_single_result_ptr->tv_sec,
            (test_single_result_ptr->tv_nsec / 1000000)
        );
    }
}
