
#include <queue>
#include <string>
#include <map>
#include <set>
#include <mutex>

namespace wasp {

// typedef std::pair<int, void*> queue_item;

/*class QueueItemPriority {
    public:
        bool operator() (const queue_item item1, const queue_item item2);
};*/

// typedef std::priority_queue<queue_item, std::vector<queue_item>, QueueItemPriority> raw_queue;

typedef std::list<void*> raw_queue;

class SignalQueue {
    raw_queue __queue;
    std::mutex __mutex;
    std::condition_variable __cond_var;

    public:
        void push(void* payload);
        void* wait();
        virtual ~SignalQueue();
};

class SignalSource;

class SignalWatcher {

    SignalSource* __source;
    std::string __signal_name;
    SignalQueue __queue;

    public:
        SignalWatcher(SignalSource* source, std::string signal_name);
        virtual ~SignalWatcher();

        void push(void* payload);
        void* wait();
};

class SignalSource {

     std::map<std::string, std::set<SignalWatcher*> > __watchers;

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
        this->__watchers[std::string(signals[i])] = std::set<wasp::SignalWatcher*>();
    }
}

wasp::SignalSource::~SignalSource() {

    // ADD A REAL DESTRUCTOR IF NEEDED

}

void wasp::SignalSource::emit(std::string signal_name, void* payload) {

    std::set<SignalWatcher*> watcher_set = this->__watchers[signal_name];
    for (std::set<SignalWatcher*>::iterator it = watcher_set.begin(); it != watcher_set.end(); it++){
        (*it)->push(payload);
    }
}

/*bool wasp::QueueItemPriority::operator()(const wasp::queue_item item1, const wasp::queue_item item2) {
    return item1.first > item2.first;
}*/

wasp::SignalWatcher::~SignalWatcher(){}

wasp::SignalWatcher::SignalWatcher(SignalSource* source, std::string signal_name) {
    this->__source = source;
    this->__signal_name = signal_name;
}

void* wasp::SignalWatcher::wait() {
    return this->__queue.wait();
}

void wasp::SignalQueue::push(void* payload){

    std::lock_guard<std::mutex> _lock(this->__mutex);

    this->__queue.push_back(payload);

//    this->__queue.push(
//        wasp::queue_item(
//            0, payload
//        )
//    );

    this->__cond_var.notify_all();
}

wasp::SignalQueue::~SignalQueue(){}

wasp::SignalWatcher* wasp::SignalSource::subscribe(std::string signal_name){
    SignalWatcher* watcher = new wasp::SignalWatcher(this, signal_name);
    this->__watchers[signal_name].insert(watcher);
    return watcher;
}

void wasp::SignalWatcher::push(void* payload) {
    this->__queue.push(payload);
}

void* wasp::SignalQueue::wait(){

    std::unique_lock<std::mutex> _lock(this->__mutex);

    while (this->__queue.size() == 0) {
        this->__cond_var.wait(_lock);
    }

//    queue_item result = this->__queue.top();
//    this->__queue.pop();
//    return result.second;

    void* result = this->__queue.front();
    this->__queue.pop_front();
    return result;
}
