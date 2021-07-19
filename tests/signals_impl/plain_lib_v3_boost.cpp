
#include <queue>
#include <string>
#include <map>
#include <set>
#include <mutex>
#include <iostream>

#include <boost/lockfree/queue.hpp>

#define QUEUE_LIMIT 10000

namespace wasp {

typedef boost::lockfree::queue<void*> raw_queue;

class SignalSource;

class SignalWatcher {

        raw_queue* __queue;

    public:
        SignalWatcher(raw_queue* queue);
        virtual ~SignalWatcher();

        void* wait();
};

class SignalSource {

    std::map<std::string, raw_queue*> __queues;

    public:
        SignalSource(char** signals, const int signals_count);
        virtual ~SignalSource();

        void emit(std::string signal_name, void* payload);
        SignalWatcher* subscribe(std::string signal_name);
};

};  // namespace wasp

extern "C" {
    void* source(char** signals, int signals_count);
    void* watcher(void* source, const char* signal);
    int wait_signal(void* watcher);
    int emit_signal(void* source, const char* signal_name, void* payload);
};

void* source(char** signals, int signals_count) {
    return new wasp::SignalSource(signals, signals_count);
}

void* watcher(void* void_source, const char* signal) {
    wasp::SignalSource* source = static_cast<wasp::SignalSource*> (void_source);
    return source->subscribe(signal);
}

int wait_signal(void* void_watcher) {
    wasp::SignalWatcher* watcher = static_cast<wasp::SignalWatcher*>(void_watcher);
    watcher->wait();
    return 0;
}

int emit_signal(void* void_source, const char* signal_name, void* payload) {
    wasp::SignalSource* source = static_cast<wasp::SignalSource*>(void_source);
    source->emit(std::string(signal_name), payload);
    return 0;
}

wasp::SignalSource::SignalSource(char** signals, const int signals_count) {
    for (int i = 0; i < signals_count; i++) {
        this->__queues[std::string(signals[i])] = new raw_queue(QUEUE_LIMIT);
    }
}

wasp::SignalSource::~SignalSource() {

    // ADD A REAL DESTRUCTOR IF NEEDED

}

void wasp::SignalSource::emit(std::string signal_name, void* payload) {
    raw_queue* queue = this->__queues[signal_name];
    while (! queue->push(payload));
}

wasp::SignalWatcher::~SignalWatcher(){}

wasp::SignalWatcher::SignalWatcher(raw_queue* queue) {
    this->__queue = queue;
}

void* wasp::SignalWatcher::wait() {
    void* value;
    while (! this->__queue->pop(value));
    return value;
}
wasp::SignalWatcher* wasp::SignalSource::subscribe(std::string signal_name){
    SignalWatcher* watcher = new wasp::SignalWatcher(this->__queues[signal_name]);
    return watcher;
}
