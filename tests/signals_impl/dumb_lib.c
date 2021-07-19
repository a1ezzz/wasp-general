
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <errno.h>
#include <sys/time.h>

#include "common.h"

#define MAX_COND_WAIT 5

struct queue_item {
    void* payload;
    volatile void* next_item;
    volatile void* prev_item;
};

struct dumb_source {
    int signals_count;
    char** signals;
    volatile struct queue_item** queues;
    pthread_mutex_t queues_lock;
    pthread_cond_t event;
};

struct dumb_watcher {
    struct dumb_source* source;
    const char* signal;
    volatile struct queue_item* last_item;
};

void* source(char** signals, int signals_count){
    struct dumb_source* source = malloc(sizeof(struct dumb_source));
    size_t queues_mem_seg = sizeof(struct queue_item*) * signals_count;

    ASSERT_STM((source == NULL), "Unable to allocate memory for new signal source")
    source->signals = signals;
    source->signals_count = signals_count;
    source->queues = malloc(queues_mem_seg);
    ASSERT_STM((source->queues == NULL), "Unable to allocate memory for new signal queues")
    memset(source->queues, 0, queues_mem_seg);

    ASSERT_STM(pthread_mutex_init(&(source->queues_lock), NULL) != 0, "Unable to initialize lock for signals queues")

    ASSERT_STM(pthread_cond_init(&(source->event), NULL) != 0, "Unable to initialize event object")

    return source;
}

void* watcher(void* source, const char* signal){
    struct dumb_watcher* watcher = malloc(sizeof(struct dumb_watcher));
    ASSERT_STM((source == NULL), "Unable to allocate memory for new signal watcher")
    watcher->source = source;
    watcher->signal = signal;
    watcher->last_item = NULL;

    return watcher;
}

int wait_signal(struct dumb_watcher* watcher) {

    struct dumb_source* source = watcher->source;
    volatile struct queue_item* root_item = NULL;
    struct timespec timeout;
    int wait_status = -1;

    for (int i = 0; i < source->signals_count; i++) {
        if (strcmp(watcher->signal, source->signals[i]) == 0){

            pthread_mutex_lock(&(source->queues_lock));

            clock_gettime(CLOCK_REALTIME, &timeout);
            timeout.tv_sec += MAX_COND_WAIT;

            root_item = source->queues[i];
            if (root_item == NULL) {
                do {
                    wait_status = pthread_cond_timedwait(&(source->event), &(source->queues_lock), &timeout);
                    if (wait_status == ETIMEDOUT){
                        printf("Warning! Waiting for the first signal is out of time!\n");
                    }
                }
                while (source->queues[i] == NULL);
            }
            else if (root_item->prev_item == watcher->last_item) {
                do {
                    wait_status = pthread_cond_timedwait(&(source->event), &(source->queues_lock), &timeout);
                    if (wait_status == ETIMEDOUT){
                        printf("Warning! Waiting for the next signal is out of time!\n");
                    }
                }
                while (root_item->prev_item == watcher->last_item);
            }

            if (watcher->last_item == NULL) {
                watcher->last_item = source->queues[i];
            }
            else {
                watcher->last_item = watcher->last_item->next_item;
            }

            pthread_mutex_unlock(&(source->queues_lock));
            return 0;
        }
    }

    return -1;
}

int emit_signal(struct dumb_source* signal_source, const char* signal_name, void* payload){

    volatile struct queue_item* next_item = NULL;
    volatile struct queue_item* root_item = NULL;
    volatile struct queue_item* prev_item = NULL;

    for (int i = 0; i < signal_source->signals_count; i++) {
        if (strcmp(signal_name, signal_source->signals[i]) == 0){
            next_item = malloc(sizeof(struct queue_item));
            ASSERT_STM((next_item == NULL), "Unable to allocate memory for the next signal")
            next_item->payload = payload;
            next_item->next_item = NULL;

            pthread_mutex_lock(&(signal_source->queues_lock));

            root_item = signal_source->queues[i];
            if (root_item != NULL){
                prev_item = root_item->prev_item;
                next_item->next_item = root_item;
                next_item->prev_item = prev_item;

                prev_item->next_item = next_item;
                root_item->prev_item = next_item;
            }
            else { // root_item == NULL
                next_item->prev_item = next_item;
                next_item->next_item = next_item;
                signal_source->queues[i] = next_item;
            }

            pthread_cond_broadcast(&(signal_source->event));

            pthread_mutex_unlock(&(signal_source->queues_lock));

            return 0;
        }
    }

    return -1;
}
