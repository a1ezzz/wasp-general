

// shared_ptr instead of multiple new!

// https://en.cppreference.com/w/cpp/memory/shared_ptr/atomic2
// std::atomic<std::shared_ptr<T>>;

//https://en.cppreference.com/w/cpp/thread/barrier
// std::barrier

#include <queue>
#include <string>
#include <map>
#include <set>
#include <mutex>
#include <future>

// TODO: check memory order

namespace wasp {

class SignalQueueItem;

class SignalQueueItem {

    void* __payload;

    protected:
        std::atomic<SignalQueueItem*> __next;
        std::atomic<SignalQueueItem*> __prev;

    public:
        SignalQueueItem(void* payload=NULL);
        virtual ~SignalQueueItem();

        void push(SignalQueueItem*);
        void* payload();
        SignalQueueItem* prev();
        SignalQueueItem* next(SignalQueueItem* root_item);
};

class SignalQueue {
    SignalQueueItem __root_item;

    public:
        SignalQueue();
        void push(void* payload);
        SignalQueueItem* root_item();
        virtual ~SignalQueue();
};

class SignalSource;

class SignalWatcher {

    SignalQueueItem* __root_item;
    SignalQueueItem* __last_item;

    public:
        SignalWatcher(SignalQueueItem* root_item);
        virtual ~SignalWatcher();

        void* wait();
};

class SignalSource {

     std::map<std::string, SignalQueue* > __queues;

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
        this->__queues[std::string(signals[i])] = new wasp::SignalQueue();
    }
}

wasp::SignalSource::~SignalSource() {}

void wasp::SignalSource::emit(std::string signal_name, void* payload) {
    wasp::SignalQueue* queue = this->__queues[signal_name];
    queue->push(payload);
}

wasp::SignalWatcher::~SignalWatcher(){}

wasp::SignalWatcher::SignalWatcher(wasp::SignalQueueItem* root_item) {
    this->__root_item = root_item;
    this->__last_item = root_item->prev();
}

void* wasp::SignalWatcher::wait() {
    SignalQueueItem* result = this->__last_item->next(this->__root_item);
    return result->payload();
}

wasp::SignalQueueItem::SignalQueueItem(void* payload){
    this->__payload = payload;
    this->__next.store(this); // memory order check
    this->__prev.store(this); // memory order check
}

wasp::SignalQueueItem::~SignalQueueItem() {};

void wasp::SignalQueueItem::push(SignalQueueItem* next_item) {

    wasp::SignalQueueItem* prev_item;
    bool cont_try = true;

    do {
        prev_item = this->__prev.load();  // double check memory order
        next_item->__next.store(this); // double check memory order
        next_item->__prev.store(prev_item); // double check memory order
        cont_try = this->__prev.compare_exchange_weak(prev_item, next_item);   // double check memory order
    }
    while(! cont_try);

    prev_item->__next.store(next_item); // double check memory order
}

wasp::SignalQueue::SignalQueue() {}

void wasp::SignalQueue::push(void* payload){
    SignalQueueItem* next_item = new SignalQueueItem(payload);
    this->__root_item.push(next_item);
}

wasp::SignalQueueItem* wasp::SignalQueue::root_item(){
    return &(this->__root_item);
}

wasp::SignalQueue::~SignalQueue(){}

wasp::SignalWatcher* wasp::SignalSource::subscribe(std::string signal_name){
    wasp::SignalQueue* queue = this->__queues[signal_name];
    SignalWatcher* watcher = new wasp::SignalWatcher(queue->root_item());
    return watcher;
}

wasp::SignalQueueItem* wasp::SignalQueueItem::prev() {
    return this->__prev;
}

wasp::SignalQueueItem* wasp::SignalQueueItem::next(SignalQueueItem* root_item) {
    while(this->__next.load() == root_item);
    return this->__next;
}

void* wasp::SignalQueueItem::payload() {
    return this->__payload;
}
